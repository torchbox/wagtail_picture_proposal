# Wagtail [RFC 71: support for responsive images](https://github.com/wagtail/rfcs/pull/71)

This is a prototype implementation of [RFC 71: support for responsive images](https://github.com/wagtail/rfcs/pull/71). Join the discussion in [#lean-images on the Wagtail Slack](https://github.com/wagtail/wagtail/wiki/Slack).

--

## Try out the demo

This project has been bootstrapped with `wagtail start`.
Clone the repository, create a virtual environment, and,

```sh
pip install -r requirements.txt
./manage.py migrate
./manage.py createsuperuser
./manage.py runserver
```

Go to the admin at `/admin/` and add an image on the homepage.

## Try it on an existing project

1. Download [wagtail_picture_proposal-0.1.0-py3-none-any.zip](https://github.com/torchbox/wagtail_picture_proposal/files/7065386/wagtail_picture_proposal-0.1.0-py3-none-any.zip)
2. Rename from `.zip` to `.whl`
3. From your project, `pip install wagtail_picture_proposal-0.1.0-py3-none-any.whl` (or `poetry add ./wagtail_picture_proposal-0.1.0-py3-none-any.whl` for a Poetry project)
4. Add `wagtail_picture_proposal` to `INSTALLED_APPS` in Django settings.

Then edit a Wagtail page template using images:

```jinja
{% load wagtailpictureproposal_tags %}

{% webp_picture_wip my_image fill-{430x210,365x210} q-80 sizes="30vw, (max-width: 375px) 365px" loading="lazy" %}
```

View more examples in [home_page.html](https://github.com/torchbox/wagtail_picture_proposal/blob/feature/rfc-prototype/home/templates/home/home_page.html).

## References

- Wagtail: [Create a tag for the picture element + support for responsive image sets #285](https://github.com/wagtail/wagtail/issues/285)
- Wagtail: [Allow images to be generated without width and height attributes #5289](https://github.com/wagtail/wagtail/issues/5289)
- Willow: [[WIP] Image optimisation operations #69](https://github.com/wagtail/Willow/pull/69)
- wp_image tag from [@ababic](https://github.com/ababic): <https://gist.github.com/thibaudcolas/3c6b9c354e7d636f08133f93b65e7978>
- <https://gist.github.com/coredumperror/41f9f8fe511ac4e88547487d6d43c69b>
- <https://github.com/ephes/wagtail_srcset>
- <https://github.com/ptrck/wagtail-lazyimages>
- <https://github.com/jams2/wagtail-responsive-images>
- <https://pypi.org/project/easy-thumbnails/>
- <https://nextjs.org/docs/api-reference/next/image>
- <https://www.gatsbyjs.com/plugins/gatsby-plugin-image>

## Credits

The bulk of the code in this repository comes from [wagtail/wagtail](https://github.com/wagtail/wagtail). Additional modifications by Thibaud Colas, with support from Chris Lawton. WebP picture tag prototype by Andy Babic. Thank you to Jane Hughes and Lara Thompson for early feedback on the proposed APIs.
