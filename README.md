# Wagtail `<picture>` support proposal

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

## Responsive images

The complexity of writing this code manually becomes apparent for [responsive images](https://developer.mozilla.org/en-US/docs/Learn/HTML/Multimedia_and_embedding/Responsive_images), where we need to generate multiple renditions for different viewport widths. Here is the ideal output:

```html
<picture> 
  <source srcset="/media/images/test.width-792.webp 924w, /media/images/test.width-392.webp 688w" sizes="(max-width: 768px) 688px, 924px" type="image/webp">
  <source srcset="/media/images/test.width-793.png 924w, /media/images/test.width-393.png 688w" sizes="(max-width: 768px) 688px, 924px" type="image/png">
  <img src="/media/images/test.width-793.png" alt="">
</picture>
```

Here are proposed APIs to generate this output.

### Repeated resize rules

Note how `width-800` is used twice, thereby generating two entries in `srcset` attributes.

The [`sizes`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#attr-sizes) attribute is manually created to get the most flexibility.

```html
{% webp_picture page.test_image width-800 width-400 sizes="(max-width: 600px) 480px, 800px" alt="original" %}
```

### New resize rules

We use a special `width-{800,400}` syntax, where each entry inside the curly brackets will create one entry in srcset.
This syntax is inspired by shell expansion syntax.

The [`sizes`](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#attr-sizes) attribute is manually created to get the most flexibility.

```html
{% webp_picture page.test_image width-{800,400} sizes="(max-width: 600px) 480px, 800px" alt="original" %}
```
