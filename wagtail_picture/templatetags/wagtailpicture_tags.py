from django import template
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from wagtail.images.models import Filter
from wagtail.images.shortcuts import get_rendition_or_not_found
from wagtail.images.templatetags.wagtailimages_tags import (
    ImageNode,
    image as wagtail_image,
)

register = template.Library()

@register.tag(name="webp_picture")
def webp_picture(parser, token):
    """
    Use in place of wagtail_images.image to render a <picture> tag instead
    of a normal <img> tag, with a webp version added as a <source> for those
    browsers that support it.
    The tag supports one additional argument, that allows the quality of the image
    to be more easily specified. You can use 'quality-50' or 'q-50' (the shorthand
    version) to indicate this. e.g.:
    {% load wagtail_picture %}
    {% webp_picture page.photo width-400 q-85 %}
    {% webp_picture page.photo width-400 quality-85 %}
    By default, lossy WebP renditions are generated, with a quality level of
    settings.WAGTAILIMAGES_WEBP_QUALITY. To generate a lossless WebP rendition
    instead, add 'q-100' or 'quality-100' to the tag like so:
    {% webp_picture page.photo width-400 q-100 %}
    The <img> element still recieves the alt text attribute and any other attribute
    overrides provided to the tag. e.g.:
    {% webp_picture page.photo width-400 class="foo" id="bar" %}
    If the source image is a webp image, a PNG will be generated from it to use
    as the fallback image (in order to preserve any alpha transparency that may
    be present). In most cases though, a JPEG format will probably make a more suitable
    fallback. You can enforce this by adding 'format-jpeg' to the tag, e.g.:
    {% webp_picture page.photo width-400 format-jpeg q-80 %}
    NOTE: When 'format-jpeg' is specified, or the source image is already a jpeg,
    any 'q' or 'quality' option value will be applied to both the jpeg
    and webp renditions for consistency.
    """

    image_node = wagtail_image(parser, token)
    return WebPImageNode(
        image_node.image_expr,
        image_node.filter_spec,
        image_node.output_var_name,
        image_node.attrs,
    )


class WebPImageNode(ImageNode):
    def __init__(self, image_expr, filter_spec, output_var_name=None, attrs=None):
        self.quality = None
        self.specified_format = None
        spec_list = filter_spec.split("|")
        for i, spec in enumerate(spec_list):
            if spec.startswith("q-") or spec.startswith("quality-"):
                self.quality = spec_list.pop(i).split("-").pop()
            if spec.startswith("format-"):
                self.specified_format = spec_list.pop(i).split("-").pop()
        super().__init__(image_expr, "|".join(spec_list), output_var_name, attrs or {})

    def extract_native_format(self, image):
        ext = image.file.name.lower().split(".").pop()
        if ext in ("jpg", "jpeg"):
            self.native_format = "jpeg"
        else:
            # Should be png, gif or webp
            self.native_format = ext

    @cached_property
    def filter(self):
        """
        Return a ``wagtail.images.models.Filter`` instance
        to use for creating <img> tag rendition. This will
        serve as our IE11/Safari fallback, so needs to be
        a png, jpeg or gif (not webp).
        By default, webp images are convered to png in order
        to preserve transparency. Add 'format-jpeg' to convert
        to jpegs instead.
        """
        target_format = None
        spec_list = self.filter_spec.split("|")
        if self.specified_format:
            target_format = self.specified_format
            if target_format in ("webp", "webp-lossless"):
                target_format = "png"
        elif self.native_format == "webp":
            target_format = "png"
        if target_format:
            spec_list.append(f"format-{target_format}")
        if target_format == "jpeg":
            if "jpegquality-" not in self.filter_spec:
                spec_list.append(f"jpegquality-{self.quality}")
        return Filter("|".join(spec_list))

    @cached_property
    def webp_filter(self):
        """
        Return a ``wagtail.images.models.Filter`` instance
        to use for webp ``source`` rendition.
        By default, lossy webp renditions are created, but
        you can add 'q-100' or 'quality-100' to use
        webp-lossless.
        """
        target_format = "webp"
        spec_list = self.filter_spec.split("|")
        if self.quality:
            if self.quality == "100":
                target_format = "webp-lossless"
            elif "webpquality-" not in self.filter_spec:
                spec_list.append(f"webpquality-{self.quality}")
        spec_list.append(f"format-{target_format}")
        return Filter("|".join(spec_list))

    def render(self, context):
        image = self.image_expr.resolve(context)
        # set 'self.native_format' for 'filter()' to pick up
        self.extract_native_format(image)
        # generate the <img> tag using 'filter' for the rendition
        img_tag = super().render(context)
        if not img_tag:
            return img_tag
        # now wrap in a <picture> tag with the webp version as a source
        webp_rendition = get_rendition_or_not_found(image, self.webp_filter)
        return format_html(
            '<picture><source srcset="{}" type="image/webp">{}</picture>',
            webp_rendition.url,
            mark_safe(img_tag),
        )
