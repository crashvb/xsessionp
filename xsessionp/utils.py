#!/usr/bin/env python

"""Utility classes."""

import logging
import re
import subprocess
import sys

from logging import Formatter
from pathlib import Path
from re import Pattern
from typing import List, Union

import click
import pkg_resources

LOGGING_DEFAULT = 2


class CustomFormatter(Formatter):
    # pylint: disable=too-few-public-methods
    """Allows for ANSI coloring of logs."""
    COLORS = {
        logging.DEBUG: "[38;20m",
        logging.INFO: "[34;20m",
        logging.WARNING: "[33;20m",
        logging.ERROR: "[31;20m",
        logging.CRITICAL: "[31;1m",
    }

    def format(self, record):
        return f"\x1b{CustomFormatter.COLORS[record.levelno]}{super().format(record=record)}\x1b[0m"


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
    # pylint: disable=protected-access
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

    # No need to loop over handlers or perform None checks as we know from basicConfig() there is only one, and it has
    # a formatter assigned.
    handler = logging.getLogger().handlers[0]
    handler.formatter = CustomFormatter(fmt=handler.formatter._fmt)


def to_list_int(context, param, value: str) -> List[int]:
    # pylint: disable=unused-argument
    """Constructs a list of integers from a comma-separated string."""
    result = []
    for val in value:
        val = re.sub(pattern=r"[^0-9,-]", repl="", string=val)
        for i in list(filter(len, val.split(","))):
            if "-" in i:
                bound_lower, bound_upper = map(int, i.split("-"))
                result.extend(range(bound_lower, bound_upper + 1))
            else:
                result.append(int(i))
    return sorted(list(set(result)), key=int)


def to_pattern(context, param, value: str) -> List[Pattern]:
    # pylint: disable=unused-argument
    """Compiles a regular expression pattern from a string."""
    return [re.compile(pattern=v) for v in value]
