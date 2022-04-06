#!/usr/bin/env python

"""xsessionp command line interface."""

import logging
import json
import os
import sys

from pathlib import Path
from re import escape, Pattern
from tempfile import TemporaryDirectory
from traceback import print_exception
from typing import Generator, List, NamedTuple, Optional, Union

import click
import yaml

from click.core import Context

from .utils import (
    LOGGING_DEFAULT,
    logging_options,
    OutputFormat,
    print_list,
    print_table,
    run,
    set_log_levels,
    to_list_int,
    to_pattern,
)
from .xsessionp import TypingWindowConfiguration, XSessionp, XSESSIONP_PREFIX

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


@cli.command(name="close-window", short_help="Closes the target window(s).")
@click.option(
    "-a",
    "--all",
    help="If specified, all windows except the target will be closed.",
    is_flag=True,
)
@click.option("-d", "--desktop", help="The target desktop.", type=int)
@click.option("-t", "--target", help="The target window xsp:name.")
@click.pass_context
def close_windows(context: Context, all: bool, desktop: int, target: str):
    # pylint: disable=protected-access,redefined-builtin
    """Closes a managed window(s)."""
    ctx = get_context_object(context=context)
    try:
        if desktop is not None and target is not None:
            LOGGER.fatal("Options 'desktop' and 'target' are mutually exclusive!")
            sys.exit(1)

        ctx = get_context_object(context=context)
        windows = ctx.xsessionp.find_xsessionp_windows()
        for window in windows:
            conditional = False
            if desktop is not None:
                conditional = ctx.xsessionp.get_window_desktop(window=window) == desktop
            if target is not None:
                xsessionp_metadata = ctx.xsessionp.get_window_xsessionp_metadata(
                    window=window
                )
                xsessionp_metadata = json.loads(xsessionp_metadata)
                conditional = xsessionp_metadata["name"] == target
            if all != conditional:
                ctx.xsessionp.set_window_close(window=window)
                LOGGER.info(
                    "Closed window: %s", ctx.xsessionp._get_window_id(window=window)
                )
    except Exception as exception:  # pylint: disable=broad-except
        if ctx.verbosity > 0:
            logging.fatal(exception)
        if ctx.verbosity > LOGGING_DEFAULT:
            exc_info = sys.exc_info()
            print_exception(*exc_info)
        sys.exit(1)


@cli.command(name="dump-windows", short_help="Lists X11 window(s).")
@click.option(
    "-a",
    "--all",
    help="If specified, all windows will be listed, otherwise only those on the active desktop.",
    is_flag=True,
)
@click.option(
    "-c",
    "--columns",
    default="id,desktop,position,dimensions,name",
    help="A comma-separated list of columns. Use --columns= for a list of valid columns.",
    show_default=True,
)
@click.option(
    "-n",
    "--no-headers",
    help="If specified, column headers will be omitted.",
    is_flag=True,
)
@click.option(
    "-o",
    "--output",
    help="Output format.",
    default="plain",
    type=click.Choice(["json", "plain", "yaml"], case_sensitive=False),
    show_default=True,
)
@click.pass_context
def dump_windows(
    context: Context, all: bool, columns: str, no_headers: bool, output: str
):
    # pylint: disable=protected-access,redefined-builtin,too-many-branches,too-many-locals
    """
    Lists X11 windows in a given format.

    The output columns can be specified as a colon-separated list of column names, each of which will be populated
    from the corresponding xsessionp.get_window_<column>() method.
    """
    output = output.lower()
    if columns == "":
        list_columns(context=context, output=output)
        return

    ctx = get_context_object(context=context)
    columns = [column for column in columns.split(",") if column]
    desktop = ctx.xsessionp.get_desktop_active()
    rows = []
    windows = ctx.xsessionp.search(prune_matches=False)
    for window in windows:
        if not all and ctx.xsessionp.get_window_desktop(window=window) != desktop:
            continue
        row = []
        for fmt in columns:
            if fmt == "id":
                value = ctx.xsessionp._get_window_id(window=window)
            elif fmt.startswith(XSESSIONP_PREFIX):
                xsessionp_metadata = ctx.xsessionp.get_window_xsessionp_metadata(
                    window=window
                )
                value = None
                if xsessionp_metadata:
                    xsessionp_metadata = json.loads(xsessionp_metadata)
                    value = xsessionp_metadata.get(fmt[len(XSESSIONP_PREFIX) :], None)
            else:
                value = ctx.xsessionp.get_window_property_xsp(
                    check=False, name=fmt, window=window
                )
            value = str(value) if value is not None else "-"
            row.append(value)
        if row:
            rows.append(row)

    rows = sorted(rows, key=lambda x: x[0])
    if not no_headers:
        rows.insert(0, [column.upper() for column in columns])
    print_table(output_format=OutputFormat[output.upper()], table=rows)


@cli.command()
@click.option(
    "--filter-environment/--no-filter-environment",
    default=True,
    help="Toggles filtering environment variables common to the target process and 'this' one.",
    is_flag=True,
    show_default=True,
)
@click.pass_context
def learn(context: Context, filter_environment: bool = True):
    # pylint: disable=protected-access
    """
    Capture metadata from a graphically selected window.

    Once execute, the cursor of the display manger will be altered until a window is selected (by clicking on it).
    """
    ctx = get_context_object(context=context)
    try:
        window = ctx.xsessionp.window_select()
        if window is None:
            LOGGER.info("Selection aborted.")
            return

        pid = ctx.xsessionp.get_window_pid(window=window)
        if pid:
            LOGGER.debug("Inspecting pid: %s", pid)

            # Command ...
            command = run(args=["strings", f"/proc/{str(pid)}/cmdline"]).splitlines()
            if len(command) == 1:
                command = command[0]

            # Environment ...
            environment = run(args=["strings", f"/proc/{str(pid)}/environ"])
            environment = {
                y[0]: " ".join(y[1:])
                for y in (x.split("=") for x in environment.splitlines())
            }
            if filter_environment:
                # Assumption: Environment variables common between the selected process and "this" process most-likely
                #             originate from the user profile, and as such, do not need to be defined explicitly. The
                #             corresponding assumption is that the filtered environment variables will already be
                #             available to xsessionp.load() so-long-as the user does not define copy_environment=False.
                environment = dict(set(environment.items()) - set(os.environ.items()))
            environment = sorted([f"{k}={v}" for k, v in environment.items()])
        else:
            command = "/bin/false"
            environment = {"environment_capture": "failed"}
            LOGGER.warning(
                "Unable to determine process ID for window: %s",
                ctx.xsessionp._get_window_id(window=window),
            )

        # Name ...
        name = ctx.xsessionp.get_window_name(window=window)

        desktop = ctx.xsessionp.get_window_desktop(window=window)
        dimensions = ctx.xsessionp.get_window_dimensions(window=window)
        position = ctx.xsessionp.get_window_position(window=window)
        template = {
            "windows": [
                {
                    "command": command,
                    "desktop": desktop,
                    "dimensions": f"{dimensions[0]}x{dimensions[1]}",
                    "environment": environment,
                    "hints": {"name": f"^{escape(pattern=name)}$"},
                    "position": f"{position[0]},{position[1]}",
                }
            ]
        }
        LOGGER.info("---\n%s", yaml.dump(data=template))
    except Exception as exception:  # pylint: disable=broad-except
        if ctx.verbosity > 0:
            logging.fatal(exception)
        if ctx.verbosity > LOGGING_DEFAULT:
            exc_info = sys.exc_info()
            print_exception(*exc_info)
        sys.exit(1)


def list_columns(*, context: Context, output: str = "plain"):
    # pylint: disable=no-member
    """Lists valid column names for formatting."""
    ctx = get_context_object(context=context)
    columns = ctx.xsessionp.get_window_properties_xsp()
    columns.append("id")
    columns.extend(
        [
            f"{XSESSIONP_PREFIX}{key}"
            for key in TypingWindowConfiguration.__annotations__.keys()
        ]
    )
    columns = sorted(columns)
    print_list(lst=columns, output_format=OutputFormat[output.upper()])


@cli.command(name="list-windows", short_help="Lists managed xsessionp window(s).")
@click.option(
    "-a",
    "--all",
    help="If specified, all windows will be listed, otherwise only those on the active desktop.",
    is_flag=True,
)
@click.option(
    "-c",
    "--columns",
    default=f"id,{XSESSIONP_PREFIX}name,desktop,position,dimensions,name",
    help="A comma-separated list of columns. Use --columns= for a list of valid columns.",
    show_default=True,
)
@click.option(
    "-n",
    "--no-headers",
    help="If specified, column headers will be omitted.",
    is_flag=True,
)
@click.option(
    "-o",
    "--output",
    help="Output format.",
    default="plain",
    type=click.Choice(["json", "plain", "yaml"], case_sensitive=False),
    show_default=True,
)
@click.pass_context
def list_windows(
    context: Context, all: bool, columns: str, no_headers: bool, output: str
):
    # pylint: disable=protected-access,redefined-builtin,too-many-branches,too-many-locals
    """
    Lists managed windows in a given format.

    The output columns can be specified as a colon-separated list of column names, each of which will be populated
    from the corresponding xsessionp.get_window_<column>() method.
    """
    output = output.lower()
    if columns == "":
        list_columns(context=context, output=output)
        return

    ctx = get_context_object(context=context)
    columns = [column for column in columns.split(",") if column]
    desktop = ctx.xsessionp.get_desktop_active()
    rows = []
    windows = ctx.xsessionp.find_xsessionp_windows()
    for window in windows:
        if not all and ctx.xsessionp.get_window_desktop(window=window) != desktop:
            continue
        row = []
        for fmt in columns:
            if fmt == "id":
                value = ctx.xsessionp._get_window_id(window=window)
            elif fmt.startswith(XSESSIONP_PREFIX):
                xsessionp_metadata = ctx.xsessionp.get_window_xsessionp_metadata(
                    window=window
                )
                xsessionp_metadata = json.loads(xsessionp_metadata)
                value = xsessionp_metadata.get(fmt[len(XSESSIONP_PREFIX) :], None)
            else:
                value = ctx.xsessionp.get_window_property_xsp(
                    check=False, name=fmt, window=window
                )
            value = str(value) if value is not None else "-"
            row.append(value)
        if row:
            rows.append(row)

    rows = sorted(rows, key=lambda x: x[0])
    if not no_headers:
        rows.insert(0, [column.upper() for column in columns])
    print_table(output_format=OutputFormat[output.upper()], table=rows)


@cli.command(short_help="Load xsessionp workspace(s).")
@click.argument("config", nargs=-1)
@click.option(
    "-i",
    "--index",
    callback=to_list_int,
    help="Window indices to be loaded. Can be specified multiple times, provided as a comma-separated list(s), "
    "supports inclusive range notation.",
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
    """
    Loads an xsessionp workspace for each instance of CONFIG specified.

    Each CONFIG will be evaluated with the following precedence:

    1. As an absolute path.
    2. As a relative path to the CWD.
    3. As a relative path to each default configuration directory.
    4. As a relative path to each default configuration directory, after applying .{json, yaml, yml} extension.

    See "ls --help" for an overview of default configuration directories.

    If at least one filter is specified, only matching windows will be selected for launched; otherwise, all configured
    windows that are not disabled will be selected.

    Windows can be selected by specifying their index location within the "windows" list (e.g.: 0,2,4-7,9), or by
    specifying a regular expression pattern to be matched against their name (e.g.: ^Unsaved Document.*$). If multiple
    indices are provided they will be aggregated; however, if multiple names are provided a window will be selected if
    any patterns match.

    If both indices and names are provided, indices have higher precedence.

    If a window does not have a configured name, a predictable name will be generated following the pattern
    "{path}:window[{index}]:{get_uptime()}" prior to selection filtering.
    """
    ctx = get_context_object(context=context)
    try:
        configs = []
        # Resolve all provided configurations prior to loading any ...
        for cfg in config:
            path = resolve_config(config=cfg)
            if path:
                configs.append(path)
        for path in configs:
            ctx.xsessionp.load(indices=index, names=name, path=path)
    except Exception as exception:  # pylint: disable=broad-except
        if ctx.verbosity > 0:
            logging.fatal(exception)
        if ctx.verbosity > LOGGING_DEFAULT:
            exc_info = sys.exc_info()
            print_exception(*exc_info)
        sys.exit(1)


@cli.command(short_help="Lists discovered xsessionp workspace(s).")
@click.option(
    "--qualified/--no-qualified",
    default=False,
    help="Toggles outputting qualified file locations instead of unqualified workspace names.",
    is_flag=True,
    show_default=True,
)
@click.pass_context
def ls(context: Context, qualified: bool):
    # pylint: disable=invalid-name
    """
    Lists xsessionp workspace(s) discovered within each default configuration directory.

    Default configuration directories are evaluated with the following precedence:

    1. At the location defined within the XSESSIONP_CONFIGDIR environment variable.
    2. At the location defined within the XDG_CONFIG_HOME environment variable, under the "xsessionp" subdirectory.
    3. At the fixed location "~/.config/xsessionp", if the XDG_CONFIG_HOME environment variable is not populated.
    4. At the fixed location "~/.xsessionp".

    Valid file extensions include: ".json", ".yaml", and ".yml".
    """
    ctx = get_context_object(context=context)
    try:
        files = []
        for config_dir in get_config_dirs():
            for extension in EXTENSIONS:
                files.extend(config_dir.glob(f"**/*.{extension}"))
        for file in sorted(files):
            print(file if qualified else file.stem)
    except Exception as exception:  # pylint: disable=broad-except
        if ctx.verbosity > 0:
            logging.fatal(exception)
        if ctx.verbosity > LOGGING_DEFAULT:
            exc_info = sys.exc_info()
            print_exception(*exc_info)
        sys.exit(1)


@cli.command(name="reposition-window", short_help="Reposition the target window(s).")
@click.option(
    "-a",
    "--all",
    help="If specified, all windows except the target will be repositioned.",
    is_flag=True,
)
@click.option("-d", "--desktop", help="The target desktop.", type=int)
@click.option("-t", "--target", help="The target window name.")
@click.pass_context
def reposition_windows(context: Context, all: bool, desktop: int, target: str):
    # pylint: disable=protected-access,redefined-builtin
    """Aligns the current position of a managed window(s) to match the embedded metadata."""
    ctx = get_context_object(context=context)
    try:
        if desktop is not None and target is not None:
            LOGGER.fatal("Options 'desktop' and 'target' are mutually exclusive!")
            sys.exit(1)

        ctx = get_context_object(context=context)
        windows = ctx.xsessionp.find_xsessionp_windows()
        for window in windows:
            conditional = False
            xsessionp_metadata = ctx.xsessionp.get_window_xsessionp_metadata(
                window=window
            )
            xsessionp_metadata = json.loads(xsessionp_metadata)
            if desktop is not None:
                conditional = ctx.xsessionp.get_window_desktop(window=window) == desktop
            if target is not None:
                conditional = xsessionp_metadata["name"] == target
            if all != conditional:
                ctx.xsessionp.position_window(window=xsessionp_metadata)
                LOGGER.info(
                    "Repositioned window: %s",
                    ctx.xsessionp._get_window_id(window=window),
                )
    except Exception as exception:  # pylint: disable=broad-except
        if ctx.verbosity > 0:
            logging.fatal(exception)
        if ctx.verbosity > LOGGING_DEFAULT:
            exc_info = sys.exc_info()
            print_exception(*exc_info)
        sys.exit(1)


def resolve_config(*, config: Union[Path, str]) -> Optional[Path]:
    """Resolves a config to an absolute Path."""
    path = config if isinstance(config, Path) else Path(config)

    # Is it absolute, or relative to the CWD?
    if path.exists():
        return path

    # Is it relative to a configuration directory?
    for config_dir in get_config_dirs():
        lpath = config_dir.joinpath(path)
        if lpath.exists():
            return lpath
        for extension in EXTENSIONS:
            lpath = config_dir.joinpath(f"{str(path)}.{extension}")
            if lpath.exists():
                return lpath
    return None


@cli.command(short_help="Perform basic acceptance tests.")
@click.pass_context
def test(context: Context):
    """
    Perform basic acceptance tests by launching two xclock instances on the current desktop at position (25, 25) and
    (25, 375).
    """
    ctx = get_context_object(context=context)
    try:
        LOGGER.info("Python Version:\n\t%s\n", "\n\t".join(sys.version.split("\n")))
        LOGGER.info(
            "Configuration Directories:\n\t%s\n",
            "\n\t".join([str(path) for path in get_config_dirs()]),
        )
        LOGGER.info("Subprocess Test:\n\t%s\n", run(args="pwd"))

        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir).joinpath("xclock.yml")
            data = {
                "desktop": ctx.xsessionp.get_desktop_active(),
                "windows": [
                    {
                        "command": "xclock",
                        "dimensions": "300x300",
                        "hints": {"name": r"^xclock$"},
                        "focus": True,
                        "position": "25,25",
                        "shell": True,
                    },
                    {
                        "command": ["xclock", "-digital"],
                        "dimensions": "300x40",
                        "hints": {"name": r"^xclock$"},
                        "position": "25,375",
                    },
                ],
            }
            data = yaml.dump(data=data)
            path.write_text(data=data, encoding="utf-8")
            LOGGER.info("Test Configuration:\n%s", data)

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
