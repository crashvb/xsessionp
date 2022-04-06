#!/usr/bin/env python

"""A declarative window instantiation utility for x11 sessions, heavily inspired by tmuxp."""

import inspect
import json
import logging
import os
import re
import subprocess
import sys

from enum import Enum
from multiprocessing import Process
from pathlib import Path
from re import Pattern
from time import sleep
from typing import Any, cast, Dict, List, Optional, TypedDict, Union

import yaml

from flatten_dict import flatten, unflatten
from Xlib.error import BadWindow
from Xlib.xobject.drawable import Window
from Xlib.X import AnyPropertyType
from Xlib.Xatom import STRING

from .muffin import Muffin, TileMode as TileModeMuffin, TileType as TileTypeMuffin
from .xsession import get_uptime, XSession

EXTENSIONS = ["json", "yaml", "yml"]
LOGGER = logging.getLogger(__name__)
XSESSION = None

XSESSIONP_METADATA = "_XSESSIONP_METADATA"
XSESSIONP_PREFIX = "xsp:"


class HintMethod(Enum):
    """Boolean method used to relate hint criteria."""

    AND = 0
    OR = 1


class TypingWindowConfiguration(TypedDict):
    # pylint: disable=missing-class-docstring
    id: Optional[int]  # Should only be assigned internally

    command: Union[list, str]
    copy_environment: Optional[bool]
    desktop: Optional[int]
    dimensions: Optional[str]
    disabled: Optional[bool]
    environment: Optional[Dict[str, str]]
    focus: Optional[bool]
    hint_method: Optional[str]
    hints: Optional[Dict[str, str]]
    name: Optional[str]
    position: Optional[str]
    search_delay: Optional[float]
    shell: Optional[bool]
    snapped: Optional[bool]
    start_directory: Optional[str]
    start_timeout: Optional[int]
    tile: Optional[str]


class XSessionp(XSession):
    """Orchestrates with X11 window managers."""

    def __init__(self, check: bool = True, xsession: XSession = None):
        super().__init__(check=check)

        if xsession:
            self.check = xsession.check
            self.display = xsession.display

    def find_xsessionp_windows(self) -> Optional[List[Window]]:
        """Locates windows containing metadata from xsessionp."""
        return self.search(
            matcher=lambda x: self.get_window_xsessionp_metadata(check=False, window=x)
            is not None
        )

    def get_window_manager_name(self) -> str:
        """Returns the raw name of the window manager."""
        window = self.get_window_manager()
        return self.get_window_name(window=window)

    def get_window_xsessionp_metadata(
        self, *, check: bool = None, window: Union[int, Window]
    ) -> Optional[str]:
        """Retrieves the desktop containing a given window."""
        return self.get_window_property(
            atom=XSESSIONP_METADATA,
            check=check,
            property_type=AnyPropertyType,
            window=window,
        )

    @staticmethod
    def generate_name(*, index: int, path: Path) -> str:
        """Generates a predictable name from a given set of context parameters."""
        return f"{path}:window[{index}]:{get_uptime()}"

    def get_window_properties_xsp(self) -> List[str]:
        """Retrieves the list of valid property names that can be retrieved from a window using introspection."""
        result = []
        for method in dir(self):
            if (
                method.startswith("get_window_")
                and "window" in inspect.getfullargspec(getattr(self, method)).kwonlyargs
            ):
                name = method[11:]
                if name not in ["property", "property_xsp"]:
                    result.append(name)
        return result

    def get_window_property_xsp(
        self, *, check: bool = None, name: str, window: Union[int, Window]
    ) -> Optional[Any]:
        """Retrieves a given property from a window by name using introspection."""
        try:
            method = getattr(self, f"get_window_{name.lower()}", None)
            if method:
                return method(window=window)
        except:  # pylint: disable=bare-except
            if self._get_check(check=check):
                LOGGER.error(
                    'Unable to retrieve property "%s" from window: %s', name, window
                )
                raise
        return None

    def guess_window(
        self,
        *,
        sane: bool = True,
        hint_method: HintMethod = HintMethod.AND,
        hints: Dict[str, Pattern],
        windows: List[Window],
    ) -> Optional[int]:
        # pylint: disable=protected-access,too-many-branches
        """Attempts to isolate a single window from a list of potential matches."""

        def must_have_state(win: Window) -> bool:
            return self.get_window_state(check=False, window=win) is not None

        LOGGER.debug(
            "Guessing against %d windows using hints (method: %s):\n%s",
            len(windows),
            hint_method.name,
            "\n".join([f"{k} : {v.pattern}" for k, v in hints.items()]),
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

        # Try to match based on hints provided ...
        matches = []
        for window in windows:
            try:
                found = True
                for name, pattern in hints.items():
                    if name == "id":
                        value = self._get_window_id(window=window)
                    elif name.startswith(XSESSIONP_PREFIX):
                        xsessionp_metadata = self.get_window_xsessionp_metadata(
                            window=window
                        )
                        xsessionp_metadata = json.loads(xsessionp_metadata)
                        value = xsessionp_metadata.get(
                            name[len(XSESSIONP_PREFIX) :], None
                        )
                    else:
                        # TODO: get_window_property_xsp() or get_window_property() ... edge cases???
                        value = self.get_window_property_xsp(
                            check=False, name=name, window=window
                        )
                    if value is not None:
                        found &= pattern.match(str(value)) is not None
                        if found and hint_method == HintMethod.OR:
                            break
                    elif hint_method == HintMethod.AND:
                        found = False
                        break

                if found:
                    matches.append(window.id)
            except BadWindow:
                # Ignore state changes during traversal
                ...

        if not matches:
            LOGGER.warning("No matching windows; try relaxing constraints!")
            return None
        if len(matches) == 1:
            LOGGER.debug("Found matching window: %s", matches[0])
            return matches[0]

        LOGGER.warning(
            "Too many matching windows: %d; try tightening constrains!", len(matches)
        )

        LOGGER.debug("Best effort at an ID-based match ...")
        # The greater the id, the later the window was created?!? ¯\_(ツ)_/¯
        return sorted(matches, reverse=True)[0]

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
        self, *, delay: int = 1, search_delay: float = 0, tries: int = 3, **kwargs
    ) -> List[Window]:
        """
        Executes a command and attempts to identify the window(s) that were created as a result.
        https://stackoverflow.com/a/13096649
        """
        windows_before = self.search(prune_matches=False)

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
        if search_delay != 0.0:
            LOGGER.debug("Delaying %s seconds ...", search_delay)
            sleep(search_delay)
        for _ in range(tries):
            self.get_display().sync()
            windows_after = self.search(prune_matches=False)
            result = [x for x in windows_after if x not in windows_before]
            if result:
                break
            sleep(delay)

        return result

    def load(
        self, *, indices: List[int] = None, names: List[Pattern] = None, path: Path
    ):
        # pylint: disable=protected-access,too-many-branches,too-many-locals,too-many-statements
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

        if indices is None:
            indices = []
        if names is None:
            names = []
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

            # Check: indices and names ...
            if indices and i not in indices:
                LOGGER.debug("Skipping; window[%s] filtered by index.", i)
                continue
            if names and not any((name.match(string=window["name"]) for name in names)):
                LOGGER.debug("Skipping; window[%s] filtered by name.", i)
                continue

            # Instantiate the window configuration ...
            window = self.inherit_globals(config=config, window=window)

            # Check: disabled ...
            disabled = False
            if self.key_enabled(key="disabled", window=window):
                disabled = bool(window["disabled"])
            if disabled:
                LOGGER.debug("Skipping; window[%s] disabled.", i)
                continue

            # Construct: environment ...
            copy_environment = True
            env = {}
            if self.key_enabled(key="copy_environment", window=window):
                copy_environment = bool(window["copy_environment"])
            if copy_environment:
                env = os.environ.copy()
            if self.key_enabled(key="environment", window=window):
                env.update(window["environment"])

            # Construct: hint_method ...
            hint_method = HintMethod.AND
            if self.key_enabled(key="hint_method", window=window):
                hint_method = HintMethod[str(window["hint_method"]).upper()]

            # Construct: hints ...
            hints = {}
            if self.key_enabled(key="hints", window=window):
                hints = window["hints"]
            hints = hints if hints else {"title": r"^.+$"}
            hints = {str(k).lower(): re.compile(v) for k, v in hints.items()}

            # Construct: search_delay ...
            search_delay = 0
            if self.key_enabled(key="search_delay", window=window):
                search_delay = float(window["search_delay"])

            # Construct: shell ...
            shell = False
            if self.key_enabled(key="shell", window=window):
                shell = bool(window["shell"])

            # Construct: start_directory ...
            start_directory = "/"
            if self.key_enabled(key="start_directory", window=window):
                start_directory = window["start_directory"]

            # TODO: Check to see if a window already exists with the "name" attribute ...

            # Start the process, find the window ...
            LOGGER.debug("Executing: %s", window["command"])
            with open(os.devnull, "wb") as devnull:
                potential_windows = self.launch_command(
                    args=window["command"],
                    cwd=start_directory,
                    env=env,
                    preexec_fn=os.setpgrp(),
                    search_delay=search_delay,
                    shell=shell,
                    stderr=devnull,
                    stdout=devnull,
                )
            # Note: Loop variables in python are allocated from the heap =/
            config["windows"][i]["id"] = window["id"] = self.guess_window(
                hint_method=hint_method, hints=hints, windows=potential_windows
            )
            LOGGER.debug("Guessed window[%s] ID: %s", i, window["id"])
            if window["id"] is None:
                LOGGER.error("Unable to locate spawned window!")
                continue

            # Add metadata to the new window (bootstrap atom creation) ...
            self.get_atom(name=XSESSIONP_METADATA, only_if_exists=False)
            self.set_window_xsessionp_metadata(
                data=json.dumps(obj=window, sort_keys=True), window=window["id"]
            )

            start_timeout = 3
            if self.key_enabled(key="start_timeout", window=window):
                start_timeout = window["start_timeout"]
            self.wait_window_visible(retry=start_timeout, window=window["id"])

            # Position the window ...
            self.position_window(window=window)

        # Focus a (single) window, after all windows are finished being positioned ...
        # TODO: Reconcile focus and no_focus
        windows = [
            w
            for w in config["windows"]
            if self.key_enabled(key="focus", window=w) and bool(w["focus"])
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
        if self.key_enabled(key="dimensions", window=window):
            (width, height) = map(
                int, re.split(pattern=r"x|,", string=window["dimensions"])
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
            snapped = False
            if self.key_enabled(key="snapped", window=window):
                snapped = bool(window["snapped"])

            self.window_tile(
                tile_mode=window["tile"],
                tile_type="SNAPPED" if snapped else "TILED",
                window=window["id"],
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
        if any((window.get("id") for window in config["windows"])):
            LOGGER.warning('Reserved attribute "id" defined by user; ignoring ...')

        return config

    def set_window_xsessionp_metadata(
        self,
        *,
        check: bool = None,
        data: str,
        window: Union[int, Window],
        **kwargs,
    ):
        """Assigns a desktop to a given window."""
        LOGGER.debug(
            "Assigning xsessionp metadata to window %d", self._get_window_id(window)
        )
        self._change_property(
            atom=XSESSIONP_METADATA,
            check=check,
            data=data,
            property_type=STRING,
            window=window,
            **kwargs,
        )

    def window_tile(
        self,
        *,
        tile_mode: str = None,
        tile_type: str = None,
        window: Union[int, Window],
    ):
        """Tiles a given window."""
        window_manager = self.get_window_manager_name().lower()
        if "muffin" in window_manager:
            window_manager = "muffin"
            LOGGER.debug(
                "Tiling [%s] window %d to: %s [%s]",
                window_manager,
                self._get_window_id(window=window),
                tile_mode,
                tile_type.lower(),
            )
            muffin = Muffin(xsession=self)
            muffin.window_tile(
                tile_mode=TileModeMuffin[tile_mode.upper()],
                tile_type=TileTypeMuffin[tile_type.upper()],
                window=window,
            )
        # TODO: Add support for window managers common outside of Linux Mint Cinnamon ...
        else:
            raise NotImplementedError(f"Unsupported window manager: {window_manager}")
