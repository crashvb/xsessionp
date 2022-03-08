#!/usr/bin/env python

"""xsessionp command line interface."""

import logging
import os
import sys

from pathlib import Path
from re import Pattern
from shutil import which
from tempfile import TemporaryDirectory
from textwrap import dedent
from traceback import print_exception
from typing import Generator, List, NamedTuple

import click

from click.core import Context

from .utils import (
    LOGGING_DEFAULT,
    logging_options,
    run,
    set_log_levels,
    to_list_int,
    to_pattern,
)
from .xdotool import XDOTOOL
from .xprop import XPROP
from .xsessionp import XSessionp

EXTENSIONS = ["json", "yaml", "yml"]
LOGGER = logging.getLogger(__name__)
XSESSION = None

XSESSIONP_METADATA = "_XSESSIONP_METADATA"


class TypingContextObject(NamedTuple):
    # pylint: disable=missing-class-docstring
    verbosity: int
    xsessionp: XSessionp


def get_config_dirs() -> Generator[Path, None, None]:
    """Returns the xsessionp configuration directory(ies)."""
    paths = []
    if "XSESSIONP_CONFIGDIR" in os.environ:
        paths.append(os.environ["XSESSIONP_CONFIGDIR"])
    if "XDG_CONFIG_HOME" in os.environ:
        paths.append(os.path.join(os.environ["XDG_CONFIG_HOME"], "xsessionp"))
    else:
        paths.append("~/.config/xsessionp")
    paths.append("~/.xsessionp")
    paths = [Path(path).expanduser() for path in paths]

    for path in paths:
        if path.exists():
            yield path


def get_context_object(*, context: Context) -> TypingContextObject:
    """Wrapper method to enforce type checking."""
    return context.obj


@click.group()
@logging_options
@click.pass_context
def cli(
    context: Context,
    verbosity: int = LOGGING_DEFAULT,
):
    """A declarative window instantiation utility based on xsession."""

    if verbosity is None:
        verbosity = LOGGING_DEFAULT

    set_log_levels(verbosity)

    context.obj = TypingContextObject(verbosity=verbosity, xsessionp=XSessionp())


@cli.command()
@click.pass_context
def learn(context: Context):
    # pylint: disable=protected-access
    """
    Capture metadata from a graphically selected window.

    Once execute, the cursor of the display manger should be altered until a window is selected by clicking on it.
    """
    ctx = get_context_object(context=context)

    window = ctx.xsessionp.window_select()
    pid = ctx.xsessionp.get_window_pid(window=window)
    if pid:
        command = run(args=["ps", "-o", "cmd", "-p", str(pid), "h"])
    else:
        command = "/bin/false"
        LOGGER.warning(
            "Unable to determine process ID for window: %d",
            ctx.xsessionp._get_window_id(window=window),
        )

    desktop = ctx.xsessionp.get_window_desktop(window=window)
    dimensions = ctx.xsessionp.get_window_dimensions(window=window)
    position = ctx.xsessionp.get_window_position(window=window)
    template = dedent(
        f"""
        windows:
        - command: {command}
          desktop: {desktop}
          geometry: {dimensions[0]}x{dimensions[1]}
          position: {position[0]},{position[1]}
        """
    )
    LOGGER.info(template)


@cli.command()
@click.argument("config", nargs=-1)
@click.option(
    "-i",
    "--index",
    callback=to_list_int,
    help="Window indices to be loaded. Can be specified multiple times, or provided as a comma-separated list.",
    multiple=True,
)
@click.option(
    "-n",
    "--name",
    callback=to_pattern,
    help="Window names to be loaded. Will be evaluated as a regular expression. Can be passed multiple times.",
    multiple=True,
)
@click.pass_context
def load(context: Context, config: List[str], index: List[int], name: List[Pattern]):
    """Load configuration file(s)."""
    ctx = get_context_object(context=context)

    try:
        configs = []
        paths = [Path(c) for c in config]
        for path in paths:
            # Is it qualified or relative to the CWD?
            if path.exists():
                configs.append(path)
                continue

            # Is it relative to a configuration directory?
            for config_dir in get_config_dirs():
                lpath = config_dir.joinpath(path)
                if lpath.exists():
                    configs.append(lpath)
                    break
                found = False
                for extension in EXTENSIONS:
                    lpath = config_dir.joinpath(f"{str(path)}.{extension}")
                    if lpath.exists():
                        configs.append(lpath)
                        found = True
                        break
                if found:
                    break

        for path in configs:
            ctx.xsessionp.load(indices=index, names=name, path=path)
    except Exception as exception:  # pylint: disable=broad-except
        if ctx.verbosity > 0:
            logging.fatal(exception)
        if ctx.verbosity > LOGGING_DEFAULT:
            exc_info = sys.exc_info()
            print_exception(*exc_info)
        sys.exit(1)


@cli.command()
def ls():
    # pylint: disable=invalid-name
    """List configuration file(s)."""
    files = []
    for config_dir in get_config_dirs():
        for extension in EXTENSIONS:
            files.extend(config_dir.glob(f"**/*.{extension}"))
    for file in sorted(files):
        print(file)


@cli.command()
@click.pass_context
def test(context: Context):
    """Perform basic acceptance tests."""
    ctx = get_context_object(context=context)

    try:
        LOGGER.info("Python Version:\n\t%s\n", "\n\t".join(sys.version.split("\n")))
        LOGGER.info(
            "Configuration Directories:\n\t%s\n",
            "\n\t".join([str(path) for path in get_config_dirs()]),
        )
        LOGGER.info(
            "Tool Location:\n\t%s\n\t%s\n",
            which(XDOTOOL) or f"'{XDOTOOL}' not found!",
            which(XPROP) or f"'{XPROP} not found!",
        )
        LOGGER.info("Subprocess Test:\n\t%s\n", run(args="pwd"))

        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir).joinpath("xclock.yml")
            data = dedent(
                f"""
                desktop: {ctx.xsessionp.get_desktop_active()}
                windows:
                - command: xclock
                  geometry: 300x300
                  focus: true
                  position: 25,25
                  shell: true
                  title_hint: ^xclock$
                - command:
                  - xclock
                  - -digital
                  geometry: 300x40
                  position: 25,375
                  title_hint: ^xclock$
                """
            )
            path.write_text(data=data, encoding="utf-8")
            LOGGER.info("Test Configuration:\n\t%s\n", "\n\t".join(data.split("\n")))

            ctx.xsessionp.load(path=path)
    except Exception as exception:  # pylint: disable=broad-except
        if ctx.verbosity > 0:
            logging.fatal(exception)
        if ctx.verbosity > LOGGING_DEFAULT:
            exc_info = sys.exc_info()
            print_exception(*exc_info)
        sys.exit(1)


@cli.command()
def version():
    """Displays the utility version."""
    # Note: This cannot be imported above, as it causes a circular import!
    from . import __version__  # pylint: disable=import-outside-toplevel

    print(__version__)


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    cli()
