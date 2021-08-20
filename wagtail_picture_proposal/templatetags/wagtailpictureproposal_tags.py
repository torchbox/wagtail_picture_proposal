import re

from django import template
from django.conf import settings
from django.template.base import FilterExpression
from django.template.loader import render_to_string

from wagtail.images.models import Filter

from wagtail_picture_proposal.shortcuts import get_renditions_or_not_found


register = template.Library()
# TODO–DONE Update to add the extra syntax needed.
# allowed_filter_pattern = re.compile(r"^[A-Za-z0-9_\-\.]+$")
allowed_filter_pattern = re.compile(r"^[A-Za-z0-9_\-\.{},]+$")


@register.tag(name="img_srcset_wip")
def img_srcset_wip(parser, token):
    bits = token.split_contents()[1:]
    image_expr = parser.compile_filter(bits[0])
    bits = bits[1:]

    filter_specs = []
    attrs = {}
    output_var_name = None

    as_context = False  # if True, the next bit to be read is the output variable name
    is_valid = True

    for bit in bits:
        if bit == 'as':
            # token is of the form {% image self.photo max-320x200 as img %}
            as_context = True
        elif as_context:
            if output_var_name is None:
                output_var_name = bit
            else:
                # more than one item exists after 'as' - reject as invalid
                is_valid = False
        else:
            try:
                name, value = bit.split('=')
                attrs[name] = parser.compile_filter(value)  # setup to resolve context variables as value
            except ValueError:
                try:
                    # Resolve filter expressions as value
                    filter_expr = parser.compile_filter(bit)
                    filter_specs.append(filter_expr)
                except template.TemplateSyntaxError:
                    if allowed_filter_pattern.match(bit):
                        filter_specs.append(bit)
                    else:
                        # TODO-DONE Update error message.
                        raise template.TemplateSyntaxError(
                            "filter specs in 'picture_wip' tag may only contain A-Z, a-z, 0-9, dots, hyphens, curly braces, and underscores. "
                            "(given filter: {})".format(bit)
                        )

    if as_context and output_var_name is None:
        # context was introduced but no variable given ...
        is_valid = False

    if output_var_name and attrs:
        # attributes are not valid when using the 'as img' form of the tag
        is_valid = False

    if len(filter_specs) == 0:
        # there must always be at least one filter spec provided
        is_valid = False

    if len(bits) == 0:
        # no resize rule provided eg. {% image page.image %}
        # TODO-DONE Update error message.
        raise template.TemplateSyntaxError(
            "no resize rule provided. "
            "'picture_wip' tag should be of the form {% picture_wip self.photo max-320x200 [ custom-attr=\"value\" ... ] %} "
            "or {% picture_wip self.photo max-320x200 as img %}"
        )

    if is_valid:
        return ImgSrcsetNode(image_expr, filter_specs, attrs=attrs, output_var_name=output_var_name)
    else:
        raise template.TemplateSyntaxError(
            "'picture_wip' tag should be of the form {% picture_wip self.photo max-320x200 [ custom-attr=\"value\" ... ] %} "
            "or {% picture_wip self.photo max-320x200 as img %}"
        )


class ImgSrcsetNode(template.Node):
    tag_name = 'img_srcset_wip'

    def __init__(self, image_expr, filter_specs, output_var_name=None, attrs=None):
        self.image_expr = image_expr
        self.output_var_name = output_var_name
        self.attrs = attrs or {}
        self.filter_specs = filter_specs

    def raw_filter_specs(self, context):
        # Space-separated filters, to be concatenated.
        spaced_filters = []
        # Brace-expanded filters, to generate multiple renditions at once.
        braced_filters = []

        named_filters = getattr(settings, 'WAGTAIL_PICTURE_PROPOSAL_NAMED_FILTERS', {})

        for spec in self.filter_specs:
            raw_filter = spec.resolve(context) if isinstance(spec, FilterExpression) else spec
            # TODO If the filter matches one of the predefined named filters.
            # Do we want those to be expanded as well?
            raw_filter = named_filters.get(raw_filter, raw_filter)
            if "{" in raw_filter:
                if len(braced_filters) > 0:
                    raise ValueError(f"{self.tag_name} tag supports at most one pattern with brace-expansion, got {braced_filters:r} and {raw_filter:r}")

                # Example: fill-{1600x900,800x450}-c80
                split_filter = raw_filter.split('{')
                filter_prefix, repeat_pattern_suffixed = split_filter

                if len(split_filter) > 2:
                    raise ValueError(f"{self.tag_name} tag expected at most one brace-expansion pattern in the filter, got {len(split_filter) - 1} in {raw_filter:r}")

                repeat_pattern, filter_suffix = repeat_pattern_suffixed.split('}')
                repeats = repeat_pattern.split(',')
                braced_filters = [f"{filter_prefix}{repeat}{filter_suffix}" for repeat in repeats]
            else:
                spaced_filters.append(raw_filter)

        if braced_filters:
            raw_combined_filters = ['|'.join((f, *spaced_filters)) for f in braced_filters]
        else:
            raw_combined_filters = ['|'.join(spaced_filters)]

        return raw_combined_filters

    def render(self, context):
        try:
            image = self.image_expr.resolve(context)
        except template.VariableDoesNotExist:
            return ''

        if not image:
            if self.output_var_name:
                context[self.output_var_name] = None
            return ''

        if not hasattr(image, 'get_rendition'):
            raise ValueError(f"{self.tag_name} tag expected an Image object, got {image!r}")

        filters = [Filter(spec=f) for f in self.raw_filter_specs(context)]
        renditions = get_renditions_or_not_found(image, filters)

        if self.output_var_name:
            # return the rendition object in the given variable
            context[self.output_var_name] = renditions
            return ''
        else:
            # render the rendition's image tag now
            resolved_attrs = {}
            for key in self.attrs:
                resolved_attrs[key] = self.attrs[key].resolve(context)

            return render_to_string('img_srcset_wip.html', {
                "fallback_renditions": renditions,
                "attributes": resolved_attrs
            })


@register.tag(name="webp_picture_wip")
def webp_picture_wip(parser, token):
    """
    Use in place of wagtail_images.image to render a <picture> tag instead
    of a normal <img> tag, with a webp version added as a <source> for those
    browsers that support it.
    The tag supports one additional argument, that allows the quality of the image
    to be more easily specified. You can use 'quality-50' or 'q-50' (the shorthand
    version) to indicate this. e.g.:
    {% load wagtail_picture %}
    {% webp_picture_wip page.photo width-400 q-85 %}
    {% webp_picture_wip page.photo width-400 quality-85 %}
    By default, lossy WebP renditions are generated, with a quality level of
    settings.WAGTAILIMAGES_WEBP_QUALITY. To generate a lossless WebP rendition
    instead, add 'q-100' or 'quality-100' to the tag like so:
    {% webp_picture_wip page.photo width-400 q-100 %}
    The <img> element still receives the alt text attribute and any other attribute
    overrides provided to the tag. e.g.:
    {% webp_picture_wip page.photo width-400 class="foo" id="bar" %}
    If the source image is a webp image, a PNG will be generated from it to use
    as the fallback image (in order to preserve any alpha transparency that may
    be present). In most cases though, a JPEG format will probably make a more suitable
    fallback. You can enforce this by adding 'format-jpeg' to the tag, e.g.:
    {% webp_picture_wip page.photo width-400 format-jpeg q-80 %}
    NOTE: When 'format-jpeg' is specified, or the source image is already a jpeg,
    any 'q' or 'quality' option value will be applied to both the jpeg
    and webp renditions for consistency.
    """
    bits = token.split_contents()[1:]
    image_expr = parser.compile_filter(bits[0])
    bits = bits[1:]

    filter_specs = []
    attrs = {}
    output_var_name = None

    as_context = False  # if True, the next bit to be read is the output variable name
    is_valid = True

    for bit in bits:
        if bit == 'as':
            # token is of the form {% image self.photo max-320x200 as img %}
            as_context = True
        elif as_context:
            if output_var_name is None:
                output_var_name = bit
            else:
                # more than one item exists after 'as' - reject as invalid
                is_valid = False
        else:
            try:
                name, value = bit.split('=')
                attrs[name] = parser.compile_filter(value)  # setup to resolve context variables as value
            except ValueError:
                try:
                    # Resolve filter expressions as value
                    filter_expr = parser.compile_filter(bit)
                    filter_specs.append(filter_expr)
                except template.TemplateSyntaxError:
                    if allowed_filter_pattern.match(bit):
                        filter_specs.append(bit)
                    else:
                        # TODO-DONE Update error message.
                        raise template.TemplateSyntaxError(
                            "filter specs in 'webp_picture_wip' tag may only contain A-Z, a-z, 0-9, dots, hyphens, curly braces, and underscores. "
                            "(given filter: {})".format(bit)
                        )

    if as_context and output_var_name is None:
        # context was introduced but no variable given ...
        is_valid = False

    if output_var_name and attrs:
        # attributes are not valid when using the 'as img' form of the tag
        is_valid = False

    if len(filter_specs) == 0:
        # there must always be at least one filter spec provided
        is_valid = False

    if len(bits) == 0:
        # no resize rule provided eg. {% image page.image %}
        # TODO-DONE Update error message.
        raise template.TemplateSyntaxError(
            "no resize rule provided. "
            "'webp_picture_wip' tag should be of the form {% webp_picture_wip self.photo max-320x200 [ custom-attr=\"value\" ... ] %} "
            "or {% webp_picture_wip self.photo max-320x200 as img %}"
        )

    if is_valid:
        return WebPPictureNode(image_expr, filter_specs, attrs=attrs, output_var_name=output_var_name)
    else:
        raise template.TemplateSyntaxError(
            "'webp_picture_wip' tag should be of the form {% webp_picture_wip self.photo max-320x200 [ custom-attr=\"value\" ... ] %} "
            "or {% webp_picture_wip self.photo max-320x200 as img %}"
        )


class WebPPictureNode(ImgSrcsetNode):
    def __init__(self, image_expr, filter_specs, output_var_name=None, attrs=None):
        # TODO Should be None, no default quality.
        self.quality = 100
        self.specified_format = None
        for i, spec in enumerate(filter_specs):
            if spec.startswith("q-") or spec.startswith("quality-"):
                self.quality = filter_specs.pop(i).split("-")[-1]
            if spec.startswith("format-"):
                self.specified_format = filter_specs.pop(i).split("-")[-1]

        super().__init__(image_expr, filter_specs, output_var_name, attrs or {})

    def extract_native_format(self, image):
        ext = image.file.name.lower().split(".").pop()
        if ext in ("jpg", "jpeg"):
            return "jpeg"
        return ext

    def fallback_filter_specs(self, source_spec_list):
        """
        TODO Update docs
        Return a ``wagtail.images.models.Filter`` instance
        to use for creating <img> tag rendition. This will
        serve as our IE11/Safari fallback, so needs to be
        a png, jpeg or gif (not webp).
        By default, webp images are converted to png in order
        to preserve transparency. Add 'format-jpeg' to convert
        to jpegs instead.
        """
        target_format = None
        appended_specs = []
        if self.specified_format:
            target_format = self.specified_format
            if target_format in ("webp", "webp-lossless"):
                target_format = "png"
        elif self.native_format == "webp":
            target_format = "png"
        if target_format:
            appended_specs.append(f"format-{target_format}")

        if target_format == "jpeg" or self.native_format == "jpeg":
            if "jpegquality-" not in source_spec_list[0]:
                appended_specs.append(f"jpegquality-{self.quality}")

        if len(appended_specs) == 0:
            return source_spec_list

        return [f"{s}|{'|'.join(appended_specs)}" for s in source_spec_list]

    def webp_filter_specs(self, source_spec_list):
        """
        TODO update docs
        Return a ``wagtail.images.models.Filter`` instance
        to use for webp ``source`` rendition.
        By default, lossy webp renditions are created, but
        you can add 'q-100' or 'quality-100' to use
        webp-lossless.
        """
        target_format = "webp"
        appended_specs = []
        if self.quality:
            if self.quality == "100":
                target_format = "webp-lossless"
            elif "webpquality-" not in source_spec_list[0]:
                appended_specs.append(f"webpquality-{self.quality}")

        appended_specs.append(f"format-{target_format}")

        return [f"{s}|{'|'.join(appended_specs)}" for s in source_spec_list]

    def render(self, context):
        try:
            image = self.image_expr.resolve(context)
        except template.VariableDoesNotExist:
            return ''

        if not image:
            if self.output_var_name:
                context[self.output_var_name] = None
            return ''

        self.native_format = self.extract_native_format(image)

        if not hasattr(image, 'get_rendition'):
            raise ValueError("webp_picture_wip tag expected an Image object, got %r" % image)

        source_filter_specs = self.raw_filter_specs(context)
        fallback_specs = self.fallback_filter_specs(source_filter_specs)
        webp_specs = self.webp_filter_specs(source_filter_specs)
        filter_specs = [] + fallback_specs + webp_specs
        filters = [Filter(spec=f) for f in filter_specs]
        renditions = get_renditions_or_not_found(image, filters)

        webp_renditions = []
        fallback_renditions = []

        for r in renditions:
            if self.extract_native_format(r) == "webp":
                webp_renditions.append(r)
            else:
                fallback_renditions.append(r)

        output_context = {
            "webp_source": webp_renditions,
            "fallback_source": fallback_renditions,
            "fallback": fallback_renditions[0],
            "fallback_mime": f"image/{self.extract_native_format(fallback_renditions[0])}"
        }

        if self.output_var_name:
            # return the rendition object in the given variable
            context[self.output_var_name] = output_context
            return ''

        # render the rendition's image tag now
        resolved_attrs = {}
        sizes = None
        for key in self.attrs:
            value = self.attrs[key].resolve(context)
            if key == "sizes":
                sizes = value
            else:
                resolved_attrs[key] = value

        return render_to_string('webp_picture_wip.html', {
            **output_context,
            "attributes": resolved_attrs,
            "sizes": sizes,
        })

