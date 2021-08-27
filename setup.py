#!/usr/bin/env python

import io

from setuptools import find_packages, setup  # type: ignore

with io.open("README.md", encoding="utf-8") as readme_file:
    long_description = readme_file.read()

__name__ = "wagtail_picture_proposal"
__version__ = "0.1.0"
__description__ = "Early-stage proposal for responsive images in Wagtail"
__author__ = "Torchbox"
__url__ = "https://github.com/torchbox/wagtail_picture_proposal"
__license__ = "MIT"
__copyright__ = "Copyright 2021 Torchbox"

setup(
    name=__name__,
    version=__version__,
    description=__description__,
    url=__url__,
    author=__author__,
    license=__license__,
    copyright=__copyright__,
    packages=find_packages(include=["wagtail_picture_proposal"]),
    include_package_data=True,
    package_data={
        "": ["templates/*"],
    },
    python_requires=">=3.7",
)
