#!/usr/bin/env python

"""xsessionp command line interface."""

import logging
import os
import re
import subprocess
import sys

from multiprocessing import Process
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from textwrap import dedent
from time import sleep
from traceback import print_exception
from typing import cast, Dict, Generator, List, NamedTuple, Optional, TypedDict, Union

import click
import yaml

from click.core import Context
from flatten_dict import flatten, unflatten
from Xlib.xobject.drawable import Window

from .muffin import Muffin, TileMode as TileModeMuffin, TileType as TileTypeMuffin
from .utils import (
    LOGGING_DEFAULT,
    logging_options,
    run,
    set_log_levels,
)
from .xdotool import XDOTOOL
from .xprop import XPROP
from .xsession import XSession

EXTENSIONS = ["json", "yaml", "yml"]
LOGGER = logging.getLogger(__name__)
XSESSION = None


class TypingContextObject(NamedTuple):
    # pylint: disable=missing-class-docstring
    verbosity: int
    xsession: XSession


class TypingWindowConfiguration(TypedDict):
    # pylint: disable=missing-class-docstring
    command: Union[List, str]
    desktop: Optional[int]
    do_not_copy_environment: Optional[bool]
    environment: Optional[Dict[str, str]]
    focus: Optional[bool]
    geometry: Optional[str]
    id: Optional[int]
    position: Optional[str]
    shell: Optional[bool]
    snapped: Optional[bool]
    start_directory: Optional[str]
    tile: Optional[str]
    title_hint: Optional[str]


class TypingWindowMetadata(NamedTuple):
    # pylint: disable=missing-class-docstring
    id: int
    name: str


def do_load(*, path: Path, verbosity: int, xsession: XSession):
    # pylint: disable=too-many-branches
    """
    Loads a given xsessionp configuration file.

    Args:
        path: Path of the configuration file to be loaded.
        verbosity: Verbosity level under which to execute.
        xsession: Underlying XSession object.
    """
    try:
        LOGGER.info("Loading: %s", path)
        config = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.SafeLoader)
        # LOGGER.debug("Configuration:\n%s", yaml.dump(config))

        for i, window in enumerate(
            cast(List[TypingWindowConfiguration], config["windows"])
        ):
            # Instantiate the window configuration ...
            window = inherit_globals(config=config, window=window)

            # Construct: environment ...
            env = {}
            if (
                not key_enabled(key="do_not_copy_environment", window=window)
                or not window["do_not_copy_environment"]
            ):
                env = os.environ.copy()
            if key_enabled(key="environment", window=window):
                env.update(window["environment"])

            # Construct: shell ...
            shell = False
            if key_enabled(key="shell", window=window):
                shell = window["shell"]

            # Construct: start_directory ...
            start_directory = "/"
            if key_enabled(key="start_directory", window=window):
                start_directory = window["start_directory"]

            # Construct: title_hint ...
            title_hint = r"^.+$"
            if key_enabled(key="title_hint", window=window):
                title_hint = window["title_hint"]

            # Start the process, find the window ...
            LOGGER.debug("Executing: %s", window["command"])
            with open(os.devnull, "wb") as devnull:
                potential_windows = launch_command(
                    args=window["command"],
                    cwd=start_directory,
                    env=env,
                    preexec_fn=os.setpgrp(),
                    shell=shell,
                    stderr=devnull,
                    stdout=devnull,
                    xsession=xsession,
                )
            # TODO: Why do we need to double assign to get activate to work after the loop?
            config["windows"][i]["id"] = window["id"] = guess_window(
                title_hint=title_hint,
                windows=potential_windows,
                xsession=xsession,
            )
            LOGGER.debug("Guessed window ID: %s", window["id"])
            if window["id"] is None:
                LOGGER.error("Unable to locate spawned window!")
                continue

            # Position the window ...
            if key_enabled(key="desktop", window=window):
                xsession.set_window_desktop(
                    desktop=window["desktop"], window=window["id"]
                )
            if key_enabled(key="geometry", window=window):
                (width, height) = map(
                    int, re.split(pattern=r"x|,", string=window["geometry"])
                )
                xsession.set_window_dimensions(
                    height=height, width=width, window=window["id"]
                )
            if key_enabled(key="position", window=window):
                (position_x, position_y) = map(
                    int, re.split(pattern=r"x|,", string=window["position"])
                )
                xsession.set_window_position(
                    position_x=position_x, position_y=position_y, window=window["id"]
                )
            if key_enabled(key="tile", window=window):
                snapped = None
                if key_enabled(key="snapped", window=window):
                    snapped = bool(window["snapped"])

                tile_window(
                    tile_mode=window["tile"],
                    tile_type="SNAPPED" if snapped else "TILED",
                    window_id=window["id"],
                    xsession=xsession,
                )

        # Activate a (single) window, after all windows are finished being placed ...
        # TODO: Reconcile focus and no_focus
        windows = [
            w
            for w in config["windows"]
            if key_enabled(key="focus", window=w) and w["focus"]
        ]
        if len(windows) > 1:
            LOGGER.error(
                "Only 1 window may defined as focusable; refusing to set focus!"
            )
        elif len(windows) > 0:
            xsession.set_window_active(window=windows[0]["id"])

    except Exception as exception:  # pylint: disable=broad-except
        if verbosity > 0:
            logging.fatal(exception)
        if verbosity > LOGGING_DEFAULT:
            exc_info = sys.exc_info()
            print_exception(*exc_info)
        sys.exit(1)


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


def get_window_manager_name(*, xsession: XSession) -> str:
    """Returns the raw name of the window manager."""
    window = xsession.get_window_manager()
    return xsession.get_window_name(window=window)


def guess_window(
    *,
    sane: bool = True,
    title_hint: str,
    windows: List[Window],
    xsession: XSession,
) -> Optional[int]:
    # pylint: disable=protected-access
    """Attempts to isolate a single window from a list of potential matches."""

    def must_have_state(win: Window) -> bool:
        return xsession.get_window_state(check=False, window=win) is not None

    LOGGER.debug(
        "Guessing against %d windows using title_hint: %s",
        len(windows),
        title_hint,
    )
    if not windows:
        return None

    # Quick an dirty ...
    if len(windows) == 1:
        matches = []
        if sane:
            # First try going up ...
            matches = xsession._traverse_parents(
                matcher=must_have_state, max_results=1, window=windows[0]
            )
            # ... then try going down ...
            if not matches:
                matches = xsession._traverse_children(
                    matcher=must_have_state, max_results=1, window=windows[0]
                )
        return matches[0].id if matches else windows[0].id

    # TODO: Can we try matching NET_WM_PID here? ... if so, how do we capture the pid
    #       in the first place, when only the child process knows it?
    #       (disk?, named pipes?)

    # If we have hint, use it; otherwise, try looking for things with ANY title ...
    pattern = re.compile(title_hint)
    guesses = []
    for window in windows:
        name = xsession.get_window_name(check=False, window=window)
        if pattern.match(name):
            guesses.append(TypingWindowMetadata(id=window.id, name=name))

    if not guesses:
        LOGGER.warning("No matching titles; try relaxing 'title_hint'!")
        return
    elif len(guesses) == 1:
        LOGGER.debug("Found matching title: %s", guesses[0].name)
        return guesses[0].id
    else:
        LOGGER.warning(
            "Too many matching titles: %d; try constraining 'title_hint'!", len(guesses)
        )
        # ... it should still be better to use things with titles ...

    LOGGER.debug("Best effort at an ID-based match ...")
    # The greater the id, the later the window was created?!? ¯\_(ツ)_/¯
    return sorted(guesses, key=lambda x: x.id, reverse=True)[0].id


def inherit_globals(
    *, config: Dict, window: TypingWindowConfiguration
) -> TypingWindowConfiguration:
    """Inherits global values into a given window configuration."""
    base = flatten({key: value for (key, value) in config.items() if key != "windows"})
    base.update(flatten(window))
    return unflatten(base)


def key_enabled(*, key: str, window: TypingWindowConfiguration):
    """Checks if a given key is "enabled". Keys are enabled IFF the key is present and the disabler is not."""
    return key in window and f"no_{key}" not in window


def launch_command(
    *, delay: int = 1, tries: int = 3, xsession: XSession, **kwargs
) -> List[Window]:
    """
    Executes a command and attempts to identify the window(s) that were created as a result.
    https://stackoverflow.com/a/13096649
    """
    windows_before = xsession.search()

    def launcher(count: int = 0) -> Optional[Process]:
        """Nested process wrapper intended to orphan a child process."""
        if count:
            with subprocess.Popen(**kwargs) as process:
                LOGGER.debug("Started pid: %s", process.pid)
                sys.exit()

        process = Process(args=(count + 1,), name=f"child{count}", target=launcher)
        process.daemon = False
        process.start()
        return process

    process_launcher = launcher()
    sleep(0.1)
    process_launcher.terminate()

    result = []
    for _ in range(tries):
        xsession.get_display().sync()
        windows_after = xsession.search()
        result = [x for x in windows_after if x not in windows_before]
        if result:
            break
        sleep(delay)

    return result


# TODO: Need to test on something other than Linux Mint Cinnamon ...
def tile_window(
    *,
    tile_mode: str = None,
    tile_type: str = None,
    window_id: int,
    xsession: XSession,
):
    """Tiles a given window."""
    window_manager = get_window_manager_name(xsession=xsession).lower()
    if "muffin" in window_manager:
        window_manager = "muffin"
        LOGGER.debug(
            "Tiling [%s] window %d to: %s [%s]",
            window_manager,
            window_id,
            tile_mode,
            tile_mode,
        )
        muffin = Muffin(xsession=xsession)
        muffin.window_tile(
            tile_mode=TileModeMuffin[tile_mode.upper()],
            tile_type=TileTypeMuffin[tile_type.upper()],
            window=window_id,
        )
    else:
        raise NotImplementedError(f"Unsupported window manager: {window_manager}")


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

    context.obj = TypingContextObject(verbosity=verbosity, xsession=XSession())


@cli.command()
@click.pass_context
def learn(context: Context):
    # pylint: disable=protected-access
    """
    Capture metadata from a graphically selected window.

    Once execute, the cursor of the display manger should be altered until a window is selected by clicking on it.
    """
    ctx = get_context_object(context=context)

    window = ctx.xsession.window_select()
    pid = ctx.xsession.get_window_pid(window=window)
    if pid:
        command = run(args=["ps", "-o", "cmd", "-p", str(pid), "h"])
    else:
        command = "/bin/false"
        LOGGER.warning(
            "Unable to determine process ID for window: %d",
            ctx.xsession._get_window_id(window=window),
        )

    desktop = ctx.xsession.get_window_desktop(window=window)
    dimensions = ctx.xsession.get_window_dimensions(window=window)
    position = ctx.xsession.get_window_position(window=window)
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
@click.pass_context
def load(context: Context, config):
    """Load configuration file(s)."""
    ctx = get_context_object(context=context)

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
        do_load(path=path, verbosity=ctx.verbosity, xsession=ctx.xsession)


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
            desktop: {ctx.xsession.get_desktop_active()}
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
        do_load(path=path, verbosity=ctx.verbosity, xsession=ctx.xsession)


@cli.command()
def version():
    """Displays the utility version."""
    # Note: This cannot be imported above, as it causes a circular import!
    from . import __version__  # pylint: disable=import-outside-toplevel

    print(__version__)


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    cli()
