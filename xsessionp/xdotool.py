#!/usr/bin/env python

"""xdotool wrappers."""

import logging
import re

from subprocess import CalledProcessError
from typing import List

from .utils import run

LOGGER = logging.getLogger(__name__)
PATTERN_GEOMETRY_DISPLAY = re.compile(r"^(?P<width>\d+)\s+(?P<height>\d+)$")
PATTERN_GEOMETRY_WINDOW = re.compile(
    r"Window\s+(?P<window>\d+)\s+Position:\s(?P<position>\S+)\s\(screen: (?P<screen>\d+)\)\s+Geometry:"
    r"\s(?P<geometry>\S+)"
)
XDOTOOL = "xdotool"


def get_desktop() -> int:
    """Retrieves the current desktop."""
    return int(run(args=[XDOTOOL, "get_desktop"]) or -1)


def get_desktop_for_window(*, window_id: int) -> int:
    """Retrieves the desktop containing a given window."""
    return int(run(args=[XDOTOOL, "get_desktop_for_window", str(window_id)]) or -1)


# TODO: def get_desktop_viewport() -> int:


def get_num_desktops() -> int:
    """Retrieves the number of desktops."""
    return int(run(args=[XDOTOOL, "get_num_desktops"]) or -1)


def getactivewindow() -> int:
    """Retrieves the active window ID."""
    return int(run(args=[XDOTOOL, "getactivewindow"]) or -1)


def getdisplaygeometry() -> re.Match:
    """UNDOCUMENTED: Retrieves the geometry for a display."""
    stdout = run(args=[XDOTOOL, "getdisplaygeometry"])
    match = PATTERN_GEOMETRY_DISPLAY.match(stdout)
    if not match:
        raise Exception(f"Unable to parse output:\n{stdout}")
    return match


def getwindowfocus(*, force: bool = False) -> int:
    """Retrieves the focused window ID."""
    force = ["-f"] if force else []
    return int(run(args=[XDOTOOL, "getwindowfocus", *force]) or -1)


def getwindowgeometry(*, window_id: int) -> re.Match:
    """Retrieves the geometry for a given window."""
    stdout = run(args=[XDOTOOL, "getwindowgeometry", str(window_id)])
    match = PATTERN_GEOMETRY_WINDOW.match(stdout)
    if not match:
        raise Exception(f"Unable to parse output:\n{stdout}")
    return match


def getwindowname(*, window_id: int) -> str:
    """Retrieves the name for a given window."""
    return run(args=[XDOTOOL, "getwindowname", str(window_id)])


def getwindowpid(*, window_id: int) -> int:
    """Retrieves the PID for a given window."""
    return int(run(args=[XDOTOOL, "getwindowpid", str(window_id)]) or -1)


def search(*, args: List[str], allow_empty: bool = True) -> str:
    """Search for windows."""
    try:
        return run(args=[XDOTOOL, "search", *args])
    except CalledProcessError as exception:
        if not allow_empty:
            raise
        return exception.stdout.strip()


def selectwindow() -> int:
    """Graphically selects window (interactive via UI)."""
    return int(run(args=[XDOTOOL, "selectwindow"]) or -1)


def set_desktop(*, desktop: int) -> str:
    """Assigns the current desktop."""
    return run(args=[XDOTOOL, "set_desktop", str(desktop)])


def set_desktop_for_window(*, desktop: int, window_id: int) -> str:
    """Assigns a desktop to a given desktop."""
    LOGGER.debug("Assigning desktop %d to window: %d", desktop, window_id)
    return run(args=[XDOTOOL, "set_desktop_for_window", str(window_id), str(desktop)])


# TODO: def set_desktop_viewport(position_x: int, position_y: int):


def set_window(
    *,
    cls: str = None,
    class_name: str = None,
    icon_name: str = None,
    name: str = None,
    role: str = None,
    window_id: int,
    **kwargs,
) -> str:
    """Sets window properties."""
    LOGGER.debug("Setting properties of window: %d", window_id)
    cls = ["--class", cls] if cls else []
    class_name = ["--classname", class_name] if class_name else []
    icon_name = ["--icon-name", icon_name] if icon_name else []
    name = ["--name", name] if name else []
    overriderdirect = (
        ["--overrideredirect", int(bool(kwargs["overrideredirect"]))]
        if "overrideredirect" in kwargs
        else []
    )
    role = ["--role", role] if role else []
    urgency = ["--urgency", int(bool(kwargs["urgency"]))] if "urgency" in kwargs else []
    return run(
        args=[
            XDOTOOL,
            "set_window",
            *cls,
            *class_name,
            *icon_name,
            *name,
            *overriderdirect,
            *role,
            *urgency,
            str(window_id),
        ]
    )


def windowactivate(*, sync: bool = False, window_id: int) -> str:
    """Activates a given window."""
    LOGGER.debug("Activating window: %d", window_id)
    sync = ["--sync"] if sync else []
    return run(args=[XDOTOOL, "windowactivate", *sync, str(window_id)])


def windowclose(*, window_id: int) -> str:
    """Closes a given window."""
    LOGGER.debug("Closing window: %d", window_id)
    return run(args=[XDOTOOL, "windowclose", str(window_id)])


def windowfocus(*, sync: bool = False, window_id: int) -> str:
    """Focus a given window."""
    LOGGER.debug("Focusing window: %d", window_id)
    sync = ["--sync"] if sync else []
    return run(args=[XDOTOOL, "windowfocus", *sync, str(window_id)])


def windowkill(*, window_id: int) -> str:
    """Kills a given window."""
    LOGGER.debug("Killing window: %d", window_id)
    return run(args=[XDOTOOL, "windowkill", str(window_id)])


def windowmap(*, sync: bool = False, window_id: int) -> str:
    """Maps a given window."""
    LOGGER.debug("Mapping window: %d", window_id)
    sync = ["--sync"] if sync else []
    return run(args=[XDOTOOL, "windowmap", *sync, str(window_id)])


def windowminimize(*, sync: bool = False, window_id: int) -> str:
    """Minimizes a given window."""
    LOGGER.debug("Minimizing window: %d", window_id)
    sync = ["--sync"] if sync else []
    return run(args=[XDOTOOL, "windowminimize", *sync, str(window_id)])


def windowmove(*, position: str, sync: bool = False, window_id: int) -> str:
    """Moves a window to a given position."""
    (position_x, position_y) = position.split(",")
    LOGGER.debug("Moving window %d to: %s", window_id, position)
    sync = ["--sync"] if sync else []
    return run(
        args=[XDOTOOL, "windowmove", *sync, str(window_id), position_x, position_y]
    )


def windowraise(*, window_id: int) -> str:
    """Raises a given window."""
    LOGGER.debug("Raising window: %d", window_id)
    return run(args=[XDOTOOL, "windowraise", str(window_id)])


def windowreparent(*, window_id: int, parent_window_id: int) -> str:
    """Reparents a given window as the child of a given parent window."""
    LOGGER.debug("Reparenting window %d as child of: %d", window_id, parent_window_id)
    return run(args=[XDOTOOL, "windowreparent", str(window_id), str(parent_window_id)])


def windowsize(
    *, geometry: str, sync: bool = False, use_hints: bool = False, window_id: int
) -> str:
    """Resizes a window to a given geometry."""
    (width, height) = geometry.split("x")
    LOGGER.debug("Sizing window %d to: %s", window_id, geometry)
    sync = ["--sync"] if sync else []
    use_hints = ["--usehints"] if use_hints else []
    return run(
        args=[XDOTOOL, "windowsize", *sync, *use_hints, str(window_id), width, height]
    )


def windowunmap(*, sync: bool = False, window_id: int) -> str:
    """Unmaps a given window."""
    LOGGER.debug("Unmapping window: %d", window_id)
    sync = ["--sync"] if sync else []
    return run(args=[XDOTOOL, "windowunmap", *sync, str(window_id)])
