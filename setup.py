#!/usr/bin/env python

import os
import re

from setuptools import setup, find_packages


def find_version(*segments):
    root = os.path.abspath(os.path.dirname(__file__))
    abspath = os.path.join(root, *segments)
    with open(abspath, "r") as file:
        content = file.read()
    match = re.search(r"^__version__ = ['\"]([^'\"]+)['\"]", content, re.MULTILINE)
    if match:
        return match.group(1)
    raise RuntimeError("Unable to find version string!")


setup(
    author="Richard Davis",
    author_email="crashvb@gmail.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: POSIX :: Linux",
    ],
    description="A declarative window instantiation utility for x11 sessions, heavily inspired by tmuxp.",
    entry_points="""
        [console_scripts]
        xsessionp=xsessionp.cli:cli
        xsp=xsessionp.cli:cli
    """,
    extras_require={
        "dev": [
            "black",
            "pylint",
            "pytest",
            "python-xlib",
            "twine",
            "wheel",
        ]
    },
    include_package_data=True,
    install_requires=["click", "flatten-dict", "python-xlib", "pyyaml"],
    keywords="instantiation sessions window x11 xsession xsessionp xsp",
    license="Apache Software License",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    name="xsessionp",
    packages=find_packages(),
    package_data={"": ["data/*"]},
    project_urls={
        "Bug Reports": "https://github.com/crashvb/xsessionp/issues",
        "Source": "https://github.com/crashvb/xsessionp",
    },
    tests_require=["pytest"],
    test_suite="tests",
    url="https://pypi.org/project/xsessionp/",
    version=find_version("xsessionp", "__init__.py"),
)
