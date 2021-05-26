# Wagtail `<picture>` support proposal

This is an early-stage proposal for Wagtail: [Create a tag for the picture element + support for responsive image sets #285](https://github.com/wagtail/wagtail/issues/285)

Draft proposal: see below, and [#2](https://github.com/torchbox/wagtail_picture_proposal/pull/2).

--

## Try this out locally

This project has been bootstrapped with `wagtail start`.
Clone the repository, create a virtual environment, and,

```sh
pip install -r requirements.txt
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
```

Go to the admin at `/admin/` and add an image on the homepage.

## Proposal

Currently Wagtail allows you to do this:

```html
<picture>
  {% image page.test_image width-782 format-webp as webp_image %}
  <source srcset="{{ webp_image.url }}" type="image/webp">
  {% image page.test_image width-782 alt="original" %}
</picture>
```

This is straightforward enough to write for WebP and a fallback format, but can become tedious as more and more formats are added. A `picture` template tag in Wagtail could help:

```html
{% webp_picture page.test_image width-782 alt="original" %}
```

### Responsive images

The complexity of writing this code manually becomes apparent for [responsive images](https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Responsive_images), where we need to generate multiple renditions for different viewport widths. Here is the ideal output:

```html
<picture> 
  <source srcset="/media/images/test.width-792.webp 924w, /media/images/test.width-392.webp 688w" sizes="(max-width: 768px) 688px, 924px" type="image/webp">
  <source srcset="/media/images/test.width-793.png 924w, /media/images/test.width-393.png 688w" sizes="(max-width: 768px) 688px, 924px" type="image/png">
  <img src="/media/images/test.width-793.png" alt="">
</picture>
```

Here are proposed APIs to generate this output.

#### Repeated resize rules

Note how `width-800` is used twice, thereby generating two entries in `srcset` attributes.

The [`sizes`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#attr-sizes) attribute is manually created to get the most flexibility.

```html
{% webp_picture page.test_image width-800 width-400 sizes="(max-width: 600px) 480px, 800px" alt="original" %}
```

#### New resize rules

We use a special `width-{800,400}` syntax, where each entry inside the curly brackets will create one entry in srcset.
This syntax is inspired by shell expansion syntax.

The [`sizes`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#attr-sizes) attribute is manually created to get the most flexibility.

```html
{% webp_picture page.test_image width-{800,400} sizes="(max-width: 600px) 480px, 800px" alt="original" %}
```

### Art direction

Art direction when changing focal points only:

```html
{% webp_picture page.test_image fill-{800x600,400x300-c100} sizes="(max-width: 600px) 480px, 800px" alt="original" %}
```

Art direction when changing the source image would require manually writing the `<picture>` tag markup.

## Open questions

1. What is the best template tag API for developers?
2. Can we (how do we) use this new tag to query all needed renditions at once?
3. Can we switch to generating signed dynamic image serve URLs? So the server only has to do DB operations to render the template, and image resizing operations only happen when images are loaded.
4. What should the tag(s) be called, to help with support for future image formats?

## References

- Wagtail: [Create a tag for the picture element + support for responsive image sets #285](https://github.com/wagtail/wagtail/issues/285)
- Wagtail: [Allow images to be generated without width and height attributes #5289](https://github.com/wagtail/wagtail/issues/5289)
- Willow: [[WIP] Image optimisation operations #69](https://github.com/wagtail/Willow/pull/69) 
- <https://github.com/ephes/wagtail_srcset> 
- <https://github.com/ptrck/wagtail-lazyimages> 
- wp_image tag from Andy: <https://gist.github.com/thibaudcolas/3c6b9c354e7d636f08133f93b65e7978>
