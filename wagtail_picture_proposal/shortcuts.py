from django.core.cache import InvalidCacheBackendError, caches
import os.path
from io import BytesIO
from django.core.files import File
from django.db.models import Q

from wagtail.images.models import Filter, SourceImageIOError


def image_get_renditions(image, filters):
    self = image
    filters = [Filter(spec=f) if isinstance(f, str) else f for f in filters]
    cache_keys = [f.get_cache_key(self) for f in filters]
    rendition_params = list(zip(filters, cache_keys))
    Rendition = self.get_rendition_model()

    rendition_cache_keys = []

    try:
        rendition_caching = True
        cache = caches['renditions']
        cached_renditions = []
        for filter, cache_key in rendition_params:
            rendition_cache_key = Rendition.construct_cache_key(
                self.id,
                cache_key,
                filter.spec
            )
            rendition_cache_keys.append(rendition_cache_key)
            cached_rendition = cache.get(rendition_cache_key)
            if cached_rendition:
                cached_renditions.append(cached_rendition)
        return cached_renditions
    except InvalidCacheBackendError:
        rendition_caching = False

    # We need to get renditions that have both attributes matching in pairs.
    q_objects = Q()
    for filter, cache_key in rendition_params:
        q_objects |= Q(filter_spec=filter.spec, focal_point_key=cache_key)
    renditions = list(self.renditions.filter(q_objects))

    # TODO-DONE This should only create renditions that don’t exist.
    created_renditions = []
    missing_rendition_params = []
    for filter, cache_key in rendition_params:
        if len([r for r in renditions if r.filter_spec == filter.spec and r.focal_point_key == cache_key]) == 0:
            missing_rendition_params.append((filter, cache_key))
    if len(missing_rendition_params) > 0:
        bulk_objs = []
        # TODO-DONE Currently only generates a single rendition.
        for filter, cache_key in missing_rendition_params:
            # Generate the rendition image
            generated_image = filter.run(self, BytesIO())

            # Generate filename
            input_filename = os.path.basename(self.file.name)
            input_filename_without_extension, input_extension = os.path.splitext(input_filename)

            # A mapping of image formats to extensions
            FORMAT_EXTENSIONS = {
                'jpeg': '.jpg',
                'png': '.png',
                'gif': '.gif',
                'webp': '.webp',
            }

            output_extension = filter.spec.replace('|', '.') + FORMAT_EXTENSIONS[generated_image.format_name]
            if cache_key:
                output_extension = cache_key + '.' + output_extension

            # Truncate filename to prevent it going over 60 chars
            output_filename_without_extension = input_filename_without_extension[:(59 - len(output_extension))]
            output_filename = output_filename_without_extension + '.' + output_extension

            bulk_objs.append(Rendition(
                image=self,
                filter_spec=filter.spec,
                focal_point_key=cache_key,
                file=File(generated_image.f, name=output_filename),
            ))

        created_renditions = list(Rendition.objects.bulk_create(bulk_objs))

    renditions.extend(created_renditions)
    def rendition_position(rendition):
        return [i for i, f in enumerate(filters) if f.spec == rendition.filter_spec]
    renditions.sort(key=rendition_position)

    if rendition_caching:
        i = 0
        for rendition_cache_key in rendition_cache_keys:
            cache.set(rendition_cache_key, renditions[i])
            i += 1

    return renditions


def get_renditions_or_not_found(image, specs):
    """
    Like Wagtail’s own get_rendition_or_not_found, but for multiple renditions.
    Tries to get / create the renditions for the image or renders not-found images if the image does not exist.

    :param image: AbstractImage
    :param specs: list of str filter specifications
    :return: Rendition
    """
    try:
        # TODO-DONE Fetch multiple renditions at once
        # return image.get_rendition(spec)
        return image_get_renditions(image, specs)
    except SourceImageIOError:
        # TODO-DONE Return as many dummy renditions as there are items in the spec
        # Image file is (probably) missing from /media/original_images - generate a dummy
        # rendition so that we just output a broken image, rather than crashing out completely
        # during rendering.
        Rendition = image.renditions.model  # pick up any custom Image / Rendition classes that may be in use
        rendition = Rendition(image=image, width=0, height=0)
        rendition.file.name = 'not-found'
        return [rendition for spec in specs]
