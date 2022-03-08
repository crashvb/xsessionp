#!/usr/bin/env python

"""A declarative window instantiation utility for x11 sessions, heavily inspired by tmuxp."""

import json
import logging
import os
import re
import subprocess
import sys

from multiprocessing import Process
from pathlib import Path
from re import Pattern
from time import sleep
from typing import cast, Dict, List, NamedTuple, Optional, TypedDict, Union

import yaml

from flatten_dict import flatten, unflatten
from Xlib.error import BadWindow
from Xlib.xobject.drawable import Window
from Xlib.X import IsViewable
from Xlib.Xatom import STRING

from .muffin import Muffin, TileMode as TileModeMuffin, TileType as TileTypeMuffin
from .xsession import get_uptime, XSession

EXTENSIONS = ["json", "yaml", "yml"]
LOGGER = logging.getLogger(__name__)
XSESSION = None

XSESSIONP_METADATA = "_XSESSIONP_METADATA"


class TypingWindowConfiguration(TypedDict):
    # pylint: disable=missing-class-docstring
    id: Optional[int]  # Should only be assigned internally

    command: Union[List, str]
    desktop: Optional[int]
    do_not_copy_environment: Optional[bool]
    environment: Optional[Dict[str, str]]
    focus: Optional[bool]
    geometry: Optional[str]
    name: Optional[str]
    position: Optional[str]
    shell: Optional[bool]
    snapped: Optional[bool]
    start_directory: Optional[str]
    start_timeout: Optional[int]
    tile: Optional[str]
    title_hint: Optional[str]


class TypingWindowMetadata(NamedTuple):
    # pylint: disable=missing-class-docstring
    id: int
    name: str


class XSessionp(XSession):
    """Orchestrates with X11 window managers."""

    def __init__(self, check: bool = True, xsession: XSession = None):
        super().__init__(check=check)

        if xsession:
            self.check = xsession.check
            self.display = xsession.display

    def get_window_manager_name(self) -> str:
        """Returns the raw name of the window manager."""
        window = self.get_window_manager()
        return self.get_window_name(window=window)

    @staticmethod
    def generate_name(*, index: int, path: Path) -> str:
        """Generates a predictable name from a given set of context parameters."""
        return f"{path}:window[{index}]:{get_uptime()}"

    def guess_window(
        self,
        *,
        sane: bool = True,
        title_hint: str,
        windows: List[Window],
    ) -> Optional[int]:
        # pylint: disable=protected-access
        """Attempts to isolate a single window from a list of potential matches."""

        def must_have_state(win: Window) -> bool:
            return self.get_window_state(check=False, window=win) is not None

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
                matches = self._traverse_parents(
                    check=False,
                    matcher=must_have_state,
                    max_results=1,
                    window=windows[0],
                )
                # ... then try going down ...
                if not matches:
                    matches = self._traverse_children(
                        check=False,
                        matcher=must_have_state,
                        max_results=1,
                        window=windows[0],
                    )
            return matches[0].id if matches else windows[0].id

        # TODO: Can we try matching NET_WM_PID here? ... if so, how do we capture the pid
        #       in the first place, when only the child process knows it?
        #       (disk?, named pipes?)

        # If we have hint, use it; otherwise, try looking for things with ANY title ...
        pattern = re.compile(title_hint)
        guesses = []
        for window in windows:
            try:
                name = self.get_window_name(check=False, window=window)
                if pattern.match(name):
                    guesses.append(TypingWindowMetadata(id=window.id, name=name))
            except BadWindow:
                # Ignore state changes during traversal
                ...

        if not guesses:
            LOGGER.warning("No matching titles; try relaxing 'title_hint'!")
            return None
        if len(guesses) == 1:
            LOGGER.debug("Found matching title: %s", guesses[0].name)
            return guesses[0].id

        LOGGER.warning(
            "Too many matching titles: %d; try constraining 'title_hint'!", len(guesses)
        )
        # ... it should still be better to use things with titles ...

        LOGGER.debug("Best effort at an ID-based match ...")
        # The greater the id, the later the window was created?!? ¯\_(ツ)_/¯
        return sorted(guesses, key=lambda x: x.id, reverse=True)[0].id

    @staticmethod
    def inherit_globals(
        *, config: Dict, window: TypingWindowConfiguration
    ) -> TypingWindowConfiguration:
        """Inherits global values into a given window configuration."""
        base = flatten(
            {key: value for (key, value) in config.items() if key != "windows"}
        )
        base.update(flatten(window))
        return unflatten(base)

    @staticmethod
    def key_enabled(*, key: str, window: TypingWindowConfiguration):
        """Checks if a given key is "enabled". Keys are enabled IFF the key is present and the disabler is not."""
        return key in window and f"no_{key}" not in window

    def launch_command(
        self, *, delay: int = 1, tries: int = 3, **kwargs
    ) -> List[Window]:
        """
        Executes a command and attempts to identify the window(s) that were created as a result.
        https://stackoverflow.com/a/13096649
        """
        windows_before = self.search()

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
            self.get_display().sync()
            windows_after = self.search()
            result = [x for x in windows_after if x not in windows_before]
            if result:
                break
            sleep(delay)

        return result

    def load(
        self, *, indices: List[int] = None, names: List[Pattern] = None, path: Path
    ):
        # pylint: disable=protected-access
        """
        Loads a given xsessionp configuration file.

        Args:
            indices: Window indices by which to filter.
            names: Window names by which to filter.
            path: Path of the configuration file to be loaded.
        """
        LOGGER.info("Loading: %s", path)
        config = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.SafeLoader)
        config = self.sanitize_config(config=config)
        # LOGGER.debug("Configuration:\n%s", yaml.dump(config))

        LOGGER.debug("Indices : %s", ",".join(map(str, indices)))
        LOGGER.debug("Names   :")
        for name in names:
            LOGGER.debug("  %s", name.pattern)

        for i, window in enumerate(
            cast(List[TypingWindowConfiguration], config["windows"])
        ):
            # Generate: name ...
            if "name" not in window:
                window["name"] = self.generate_name(index=i, path=path)

            # Filter, if requested.
            if indices and i not in indices:
                continue
            if names and not any([name.match(string=window["name"]) for name in names]):
                continue

            # Instantiate the window configuration ...
            window = self.inherit_globals(config=config, window=window)

            # Construct: environment ...
            env = {}
            if (
                not self.key_enabled(key="do_not_copy_environment", window=window)
                or not window["do_not_copy_environment"]
            ):
                env = os.environ.copy()
            if self.key_enabled(key="environment", window=window):
                env.update(window["environment"])

            # Construct: shell ...
            shell = False
            if self.key_enabled(key="shell", window=window):
                shell = window["shell"]

            # Construct: start_directory ...
            start_directory = "/"
            if self.key_enabled(key="start_directory", window=window):
                start_directory = window["start_directory"]

            # Construct: title_hint ...
            title_hint = r"^.+$"
            if self.key_enabled(key="title_hint", window=window):
                title_hint = window["title_hint"]

            # TODO: Check to see if a window already exists with the "name" attribute ...

            # Start the process, find the window ...
            LOGGER.debug("Executing: %s", window["command"])
            with open(os.devnull, "wb") as devnull:
                potential_windows = self.launch_command(
                    args=window["command"],
                    cwd=start_directory,
                    env=env,
                    preexec_fn=os.setpgrp(),
                    shell=shell,
                    stderr=devnull,
                    stdout=devnull,
                )
            # TODO: Why do we need to double assign to get activate to work after the loop?
            config["windows"][i]["id"] = window["id"] = self.guess_window(
                title_hint=title_hint, windows=potential_windows
            )
            LOGGER.debug("Guessed window ID: %s", window["id"])
            if window["id"] is None:
                LOGGER.error("Unable to locate spawned window!")
                continue

            # Add metadata to the new window ...
            self.get_atom(
                name=XSESSIONP_METADATA, only_if_exists=False
            )  # Bootstrap creation of atom
            self._change_property(
                atom=XSESSIONP_METADATA,
                data=json.dumps(obj=window, sort_keys=True),
                property_type=STRING,
                window=window["id"],
            )

            start_timeout = 3
            if self.key_enabled(key="start_timeout", window=window):
                start_timeout = window["start_timeout"]
            self.wait_visible_window(retry=start_timeout, window=window["id"])

            # Position the window ...
            self.position_window(window=window)

        # Activate a (single) window, after all windows are finished being placed ...
        # TODO: Reconcile focus and no_focus
        windows = [
            w
            for w in config["windows"]
            if self.key_enabled(key="focus", window=w) and w["focus"]
        ]
        if len(windows) > 1:
            LOGGER.error(
                "Only 1 window may defined as focusable; refusing to set focus!"
            )
        # Note: No windows will have an ID if filter(s) resulted in an empty set.
        elif len(windows) > 0 and id in windows[0]:
            self.set_window_active(window=windows[0]["id"])

    def position_window(self, *, window: TypingWindowConfiguration):
        """Positions a window from a given configuration."""
        if self.key_enabled(key="desktop", window=window):
            self.set_window_desktop(desktop=window["desktop"], window=window["id"])
        if self.key_enabled(key="geometry", window=window):
            (width, height) = map(
                int, re.split(pattern=r"x|,", string=window["geometry"])
            )
            self.set_window_dimensions(height=height, width=width, window=window["id"])
        if self.key_enabled(key="position", window=window):
            (position_x, position_y) = map(
                int, re.split(pattern=r"x|,", string=window["position"])
            )
            self.set_window_position(
                position_x=position_x, position_y=position_y, window=window["id"]
            )
        if self.key_enabled(key="tile", window=window):
            snapped = None
            if self.key_enabled(key="snapped", window=window):
                snapped = bool(window["snapped"])

            self.tile_window(
                tile_mode=window["tile"],
                tile_type="SNAPPED" if snapped else "TILED",
                window_id=window["id"],
            )

    @staticmethod
    def sanitize_config(*, config: dict) -> dict:
        """Best effort at ensuring a sane configuration prior to processing."""
        for invalid_global in ["focus", "name"]:
            if invalid_global in config:
                LOGGER.warning(
                    'Global attribute "%s" is invalid; removing ...', invalid_global
                )
                config.pop(invalid_global)

        # Check for and remove user-provided IDs ...
        if any([window.get("id") for window in config["windows"]]):
            LOGGER.warning('Reserved attribute "id" defined by user; ignoring ...')

        return config

    # TODO: Need to test on something other than Linux Mint Cinnamon ...
    def tile_window(
        self, *, tile_mode: str = None, tile_type: str = None, window_id: int
    ):
        """Tiles a given window."""
        window_manager = self.get_window_manager_name().lower()
        if "muffin" in window_manager:
            window_manager = "muffin"
            LOGGER.debug(
                "Tiling [%s] window %d to: %s [%s]",
                window_manager,
                window_id,
                tile_mode,
                tile_type.lower(),
            )
            muffin = Muffin(xsession=self)
            muffin.window_tile(
                tile_mode=TileModeMuffin[tile_mode.upper()],
                tile_type=TileTypeMuffin[tile_type.upper()],
                window=window_id,
            )
        else:
            raise NotImplementedError(f"Unsupported window manager: {window_manager}")

    def wait_visible_window(
        self, *, delay: int = 1, retry: int = 3, window: Union[int, Window]
    ):
        """Waits for a window to be visible."""
        window = self._get_window(window=window)
        while retry:
            LOGGER.debug(
                "Waiting for window to be visible (try #%d): %s",
                retry,
                self._get_window_id(window=window),
            )
            get_window_attributes = window.get_attributes()
            if get_window_attributes.map_state == IsViewable:
                LOGGER.debug("Window is visible.")
                break
            retry -= 1
            sleep(delay)
