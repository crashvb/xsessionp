#!/usr/bin/env python

"""Utility classes."""

import logging
import subprocess
import sys

from pathlib import Path
from typing import Union

import click
import pkg_resources

LOGGING_DEFAULT = 2


def get_path(path: Union[Path, str], name: str = __name__) -> Path:
    """
    Resolves the absolute path for a given relative path in reference to a file.

    Args:
        path: The relative path to be resolved.
        name: The name of the file from which to resolve the relative path.

    Returns:
        Path: The absolute path.
    """
    top_package = name[: name.index(".")]
    return Path(pkg_resources.resource_filename(top_package, path))


def logging_options(function):
    """Common logging options."""

    function = click.option(
        "-s",
        "--silent",
        "verbosity",
        flag_value=LOGGING_DEFAULT - 2,
        help="Suppress all output.",
    )(function)
    function = click.option(
        "-q",
        "--quiet",
        "verbosity",
        flag_value=LOGGING_DEFAULT - 1,
        help="Restrict output to warnings and errors.",
    )(function)
    function = click.option(
        "-d",
        "--debug",
        "-v",
        "--verbose",
        "verbosity",
        flag_value=LOGGING_DEFAULT + 1,
        help="Show debug logging.",
    )(function)
    function = click.option(
        "-vv",
        "--very-verbose",
        "verbosity",
        flag_value=LOGGING_DEFAULT + 2,
        help="Enable all logging.",
    )(function)

    return function


def run(**kwargs) -> str:
    """Executes a command return the output."""
    return subprocess.check_output(**kwargs).decode("utf-8").strip()


def set_log_levels(verbosity: int = LOGGING_DEFAULT):
    """
    Assigns the logging levels in a consistent way.

    Args:
        verbosity: The logging verbosity level from  0 (least verbose) to 4 (most verbose).
    """
    levels = {
        0: logging.FATAL + 10,
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.DEBUG,
        4: logging.NOTSET,
    }

    _format = None
    # normal, quiet, silent ...
    if verbosity <= LOGGING_DEFAULT:
        _format = "%(message)s"
    # debug / verbose ...
    elif verbosity == LOGGING_DEFAULT + 1:
        _format = "%(asctime)s %(levelname)-8s %(message)s"
    # very verbose ...
    else:
        # _format = "%(asctime)s.%(msecs)d %(levelname)-8s %(name)s %(message)s"
        _format = "%(asctime)s.%(msecs)d %(levelname)-8s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"

    logging.basicConfig(
        stream=sys.stdout,
        level=levels[verbosity],
        format=_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
