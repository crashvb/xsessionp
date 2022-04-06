#!/usr/bin/env python

# pylint: disable=too-many-lines

"""
A shameless, low quality, adaptation of select portions of tools to python:

* https://github.com/jordansissel/xdotool
* https://github.com/parkouss/pyewmh
* https://specifications.freedesktop.org/wm-spec/1.3/
"""

import logging

from contextlib import contextmanager
from functools import lru_cache, wraps
from time import perf_counter, sleep
from typing import Any, Callable, Generator, List, NamedTuple, Optional, Union

from Xlib.display import Display
from Xlib.error import BadAtom, BadWindow, CatchError, XError
from Xlib.ext.xtest import fake_input
from Xlib.protocol.event import ClientMessage
from Xlib.protocol.request import GetProperty, GetGeometry
from Xlib.protocol.rq import DictWrapper, Event
from Xlib.xobject.cursor import Cursor
from Xlib.xobject.drawable import Window
from Xlib.xobject.fontable import Font
from Xlib.X import (
    AnyPropertyType,
    Button1,
    ButtonReleaseMask,
    GrabModeAsync,
    GrabModeSync,
    GrabSuccess,
    IsViewable,
    NONE,
    PropModeReplace,
    RevertToParent,
    StaticGravity,
    SubstructureNotifyMask,
    SubstructureRedirectMask,
    SyncPointer,
)
from Xlib.Xatom import ATOM, CARDINAL, STRING
from Xlib.Xcursorfont import crosshair as xcf_crosshair
from Xlib.XK import string_to_keysym
from Xlib.Xutil import IconicState

from .ewmh import (
    ACTION_ADD,
    ACTION_REMOVE,
    NET_ACTIVE_WINDOW,
    NET_CLOSE_WINDOW,
    NET_FRAME_EXTENTS,
    NET_MOVERESIZE_WINDOW,
    NET_SUPPORTED,
    NET_SUPPORTING_WM_CHECK,
    NET_VIRTUAL_ROOTS,
    NET_WM_ALLOWED_ACTIONS,
    NET_WM_CLASS,
    NET_WM_DESKTOP,
    NET_WM_NAME,
    NET_WM_PID,
    NET_WM_STATE,
    NET_WM_STATE_MAXIMIZED_HORZ,
    NET_WM_STATE_MAXIMIZED_VERT,
    NET_WM_VISIBLE_NAME,
    NET_WM_WINDOW_TYPE,
    NET_WORKAREA,
    SOURCE_PAGER,
)
from .icccm import WM_CHANGE_STATE, WM_CLASS, WM_NAME

LOGGER = logging.getLogger(__name__)
# TODO: Reconcile why documentation states "latin-1", while python-xlib seems to return "utf-8"?!?
XSESSION_ENCODING = "utf-8"


def get_uptime() -> int:
    """Returns the system uptime in milliseconds."""
    # return int(float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0]) * 1000)
    return round(perf_counter() * 1000)


def window_type_safety(func):
    # pylint: disable=protected-access
    """Ensures that that the window parameter will be of type Window."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        if "window" in kwargs:
            check = {"check": kwargs["check"]} if "check" in kwargs else {}
            kwargs["window"] = self._get_window(**check, window=kwargs["window"])
        else:
            LOGGER.warning(
                "Decorator %s used on %s without parameter: window!",
                __name__,
                func,
            )
        return func(*args, **kwargs)

    return wrapper


class TypingKeyInput(NamedTuple):
    # pylint: disable=missing-class-docstring
    event_type: int
    key: str

    def keycode(self, *, display: Display) -> int:
        """Retrieves the corresponding keycode."""
        return display.keysym_to_keycode(keysym=string_to_keysym(keysym=self.key))


class XSession:
    # pylint: disable=too-many-public-methods
    """Interacts with X11 window managers."""

    def __del__(self):
        if self.__dict__["display"] is not None:
            self.__dict__["display"].close()
            del self.__dict__["display"]

    def __getattr__(self, item):
        if str(item).lower().startswith("_net_"):
            atom = self._get_supported_atom(atom=item)
            return self.get_window_property(atom=atom, check=self.__dict__["check"])
        return self.__dict__[item]

    def __init__(self, check: bool = True):
        self.__dict__["check"] = check
        self.__dict__["display"] = None

    def __setattr__(self, key, value):
        if str(key).lower().startswith("_net_"):
            atom = self._get_supported_atom(atom=key)
            self._set_property(atom=atom, check=self.__dict__["check"], data=value)
        else:
            self.__dict__[key] = value

    @window_type_safety
    def _change_property(
        self,
        *,
        atom: Union[int, str],
        check: bool = None,
        data: Any,
        data_format: int = 0,
        mode: int = PropModeReplace,
        property_type: int = ATOM,
        sync: bool = True,
        window: Union[int, Window],
    ):
        """Changes a property to a given window."""
        atom = self._get_atom(check=check, atom=atom)

        if not data_format:
            if property_type == STRING:
                data = data.encode(XSESSION_ENCODING)
                data_format = 8
            else:
                data_format = 32

        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window.change_property(
                data=data,
                format=data_format,
                mode=mode,
                onerror=cerror,
                property=atom,
                property_type=property_type,
            )

    def _get_atom(self, *, check: bool = None, atom: Union[int, str]) -> int:
        """Retrieves an atom (object) from a given atom or atom name."""
        if isinstance(atom, str):
            return self.get_atom(check=check, name=atom)
        return atom

    def _get_check(self, *, check: bool) -> bool:
        """Retrieves the propagated value of the check parameter."""
        return self.check if check is None else check

    def _get_property(
        self,
        *,
        atom: Union[int, str],
        check: bool = None,
        property_type: int = AnyPropertyType,
        window: Union[int, Window] = None,
    ) -> Optional[GetProperty]:
        """Retrieves a raw property from a given window."""
        atom = self._get_atom(check=check, atom=atom)
        if window is None:
            window = self.get_window_root()
        window = self._get_window(check=check, window=window)
        try:
            result = window.get_full_property(
                property=atom, property_type=property_type
            )
            # TODO: Do we also need to check result.error?
            return result
        except XError:
            if check:
                LOGGER.error(
                    "Unable to retrieve property %s from window: %s",
                    str(atom),
                    self._get_window_id(window),
                )
                raise
        return None

    @lru_cache(maxsize=None, typed=True)
    def _get_supported_atom(self, atom: Union[int, str], check: bool = None) -> int:
        """Retrieves a supported atom or raises an exception."""
        if NET_SUPPORTED not in self.__dict__:
            self.__dict__[NET_SUPPORTED] = list(
                self.get_window_property(atom=NET_SUPPORTED)
            )
        atom = self._get_atom(atom=atom, check=check)
        if atom not in self.__dict__[NET_SUPPORTED]:
            raise KeyError(f"Unsupported atom: {atom}")
        return atom

    def _get_window(self, *, check: bool = None, window: Union[int, Window]) -> Window:
        """Retrieves a window (object) from a given window or window ID."""
        if isinstance(window, Window):
            return window
        return self.get_window_by_id(check=check, window_id=window)

    @window_type_safety
    def _get_window_geometry(
        self, *, check: bool = None, window: Union[int, Window]
    ) -> Optional[GetGeometry]:
        """Retrieves the dimensions of a given window."""
        try:
            return window.get_geometry()
        except XError as exception:
            LOGGER.error(
                "Unable to retrieve geometry of window %d: %s",
                self._get_window_id(window),
                exception,
            )
            if self._get_check(check=check):
                raise
        return None

    @staticmethod
    def _get_window_id(window: Union[int, Window]) -> Window:
        """Retrieves the ID of a window (int) from a given window or window ID."""
        return window.id if isinstance(window, Window) else window

    def _remove_property(
        self,
        *,
        atom: Union[int, str],
        check: bool = None,
        sync: bool = True,
        window: Union[int, Window] = None,
    ):
        """Deletes a property from a given window."""
        atom = self._get_atom(check=check, atom=atom)
        if window is None:
            window = self.get_window_root()
        window = self._get_window(check=check, window=window)
        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window.delete_property(property=atom, onerror=cerror)

    def _send_keys(
        self,
        *,
        check: bool = None,
        delay: float = 0.1,
        key_inputs: List[TypingKeyInput],
        sync: bool = True,
        window: Union[int, Window] = None,
    ):
        """Emulates keyboard input to a given window."""
        if window is None:
            window = self.get_window_root()
        window = self._get_window(check=check, window=window)

        # Keyboard events only seems to work when the desktop and window are both active, AND the window is focused.
        # This is counterintuitive, as isn't that the whole point of "focused" vs "active"??? ...
        self.get_display().sync()
        self.set_window_active(check=check, window=window)
        self.wait_window_active(window=window)
        self.set_window_focus(check=check, sync=sync, window=window)
        self.wait_window_focused(window=window)

        display = self.get_display()
        for key_input in key_inputs:
            keycode = key_input.keycode(display=display)
            LOGGER.debug(
                "Sending Key Input: %s %s (%s)",
                key_input.event_type,
                key_input.key,
                keycode,
            )
            with self.display_sync(sync=sync):
                fake_input(
                    detail=keycode,
                    event_type=key_input.event_type,
                    root=window,
                    self=display,
                    # TODO: Why doesn't providing time work?
                    # time=get_uptime(),
                )
                sleep(delay)

    def _set_property(
        self,
        *,
        atom: Union[int, str],
        check: bool = None,
        data: Any,
        data_format: int = 0,
        event_mask: int = (SubstructureNotifyMask | SubstructureRedirectMask),
        propagate: bool = True,
        sync: bool = True,
        window: Union[int, Window] = None,
        window_root: Window = None,
    ):
        """Assigns a property to a given window."""
        atom = self._get_atom(check=check, atom=atom)
        if window_root is None:
            window_root = self.get_window_root()
        window_root = self._get_window(check=check, window=window_root)
        if window is None:
            window = window_root
        window = self._get_window(check=check, window=window)

        if not data_format:
            if isinstance(data, str):
                data = list(data)
                data_format = 8
            else:
                data = (data + [0] * (5 - len(data)))[:5]
                data_format = 32

        # http://python-xlib.sourceforge.net/doc/html/python-xlib_7.html
        # Target client messages at "window", but send events to "root" ...
        client_message = ClientMessage(
            client_type=atom, data=(data_format, data), window=window
        )
        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window_root.send_event(
                event=client_message,
                event_mask=event_mask,
                onerror=cerror,
                propagate=int(propagate),
            )

    @window_type_safety
    def _traverse_children(
        self,
        *,
        check: bool = None,
        matcher: Callable[[Window], bool],
        max_results: int = None,
        prune_matches: bool = True,
        window: Union[int, Window],
    ) -> List[Window]:
        """Traverse children looking for matches."""
        result = []
        try:
            stack = list(window.query_tree().children)
            while stack:
                win = stack.pop(0)
                try:
                    # Do not continue to search the children of a match
                    match = matcher(win)
                    if match:
                        result.append(win)
                        if max_results and len(result) == max_results:
                            break
                    if not match or not prune_matches:
                        stack.extend(win.query_tree().children)
                except BadWindow:
                    # Ignore state changes during traversal
                    ...
        except XError as exception:
            LOGGER.error("Unable to traverse children: %s", exception)
            if self._get_check(check=check):
                raise
        return result

    @window_type_safety
    def _traverse_parents(
        self,
        *,
        check: bool = None,
        matcher: Callable[[Window], bool],
        max_results: int = None,
        prune_matches: bool = True,
        window: Union[int, Window],
        window_root: Union[int, Window] = None,
    ) -> List[Window]:
        """Traverse parents looking for matches."""
        result = []
        if not window_root:
            window_root = self.get_window_root()
        window_root = self._get_window(check=check, window=window_root)
        try:
            while window.id != window_root.id:
                try:
                    parent = window.query_tree().parent
                    match = matcher(parent)
                    if match:
                        result.append(parent)
                        if max_results and len(result) == max_results:
                            break
                    if not match or not prune_matches:
                        window = parent
                except BadWindow:
                    # Ignore state changes during traversal
                    ...
        except XError as exception:
            LOGGER.error("Unable to traverse parents: %s", exception)
            if self._get_check(check=check):
                raise
        return result

    @staticmethod
    def _retry(
        *, checker: Callable[[int], bool], delay: int = 1, retry: int = 3
    ) -> bool:
        """Waits for a condition at a fixed interval."""
        while retry:
            result = checker(retry)
            if result:
                return result
            retry -= 1
            sleep(delay)
        return False

    @contextmanager
    def catch_error(self, *, check: bool = None) -> Generator[CatchError, None, None]:
        """Context manager to catch and raise errors."""
        instance = CatchError(XError)
        yield instance
        if self._get_check(check=check) and instance.get_error():
            raise instance.get_error()  # pylint: disable=raising-bad-type

    @contextmanager
    def display_sync(self, *, sync: bool = True) -> Generator[None, None, None]:
        """Context manager to synchronize the display."""
        yield None
        if sync:
            self.get_display().sync()

    @lru_cache(maxsize=None, typed=True)
    def get_atom(
        self, *, name: str, check: bool = None, only_if_exists: bool = True
    ) -> int:
        """Retrieves the integer value corresponding to an atom by a given string name."""
        atom = self.get_display().intern_atom(name=name, only_if_exists=only_if_exists)
        if self._get_check(check=check) and atom == NONE:
            raise RuntimeError(f"Unable to intern atom: {name}")
        return atom

    @lru_cache(maxsize=None, typed=True)
    def get_atom_name(self, *, atom: int, check: bool = None) -> str:
        """Retrieves the string name corresponding to an atom by a given integer value."""
        name = None
        try:
            name = self.get_display().get_atom_name(atom=atom)
        except BadAtom:
            if self._get_check(check=check):
                raise
        return name

    def get_client_list(self) -> Optional[List[int]]:
        """Retrieves the list of managed windows."""
        result = self._NET_CLIENT_LIST
        return list(result) if result is not None else None

    def get_client_list_stacking(self) -> Optional[List[int]]:
        """Retrieves the list of managed windows (stacked)."""
        result = self._NET_CLIENT_LIST_STACKING
        return list(result) if result is not None else None

    def get_desktop_active(self) -> Optional[int]:
        """Retrieves the active desktop."""
        result = self._NET_CURRENT_DESKTOP
        return int(result[0]) if result is not None else None

    def get_desktop_count(self) -> Optional[int]:
        """Retrieves the number of desktops."""
        result = self._NET_NUMBER_OF_DESKTOPS
        return int(result[0]) if result is not None else None

    def get_desktop_geometry(self) -> Optional[List[int]]:
        """Retrieves the dimensions of the desktops."""
        result = self._NET_DESKTOP_GEOMETRY
        return [int(x) for x in result] if result is not None else None

    def get_desktop_layout(self) -> Optional[List[int]]:
        """Retrieves the layout of the desktops."""
        result = self._NET_DESKTOP_LAYOUT
        return [int(x) for x in result] if result is not None else None

    def get_desktop_names(self) -> Optional[List[str]]:
        """Retrieves the names of the desktops."""
        result = self._NET_DESKTOP_NAMES
        return result.decode("utf-8").split("\x00")[:-1] if result is not None else None

    def get_desktop_showing(self) -> Optional[int]:
        """Retrieves the showing desktop flag."""
        result = self._NET_SHOWING_DESKTOP
        return int(result[0]) if result is not None else None

    def get_desktop_viewport(self) -> Optional[List[int]]:
        """Retrieves the viewport of the desktops."""
        result = self._NET_DESKTOP_VIEWPORT
        return [int(x) for x in result] if result is not None else None

    def get_display(self) -> Display:
        """Retrieves the X11 display."""
        if self.__dict__["display"] is None:
            self.__dict__["display"] = Display()
        return self.__dict__["display"]

    def get_screen(self, *, screen_number: int = None) -> DictWrapper:
        """Retrieves a given screen, or the default screen if none is provided."""
        screen_number = {"sno": screen_number} if screen_number is not None else {}
        return self.get_display().screen(**screen_number)

    def get_screen_count(self) -> int:
        """Retrieves the number of screens."""
        return self.get_display().screen_count()

    def get_window_active(self) -> Optional[Window]:
        """Retrieves the active window."""
        result = self._NET_ACTIVE_WINDOW
        return (
            self.get_window_by_id(window_id=int(result[0]))
            if result is not None
            else None
        )

    def get_window_allowed_actions(
        self, *, check: bool = None, window: Union[int, Window]
    ) -> Optional[List[int]]:
        """Retrieves the allowed actions for a given window."""
        result = self.get_window_property(
            atom=NET_WM_ALLOWED_ACTIONS,
            check=check,
            property_type=AnyPropertyType,
            window=window,
        )
        return list(result) if result is not None else None

    def get_window_by_id(
        self, *, check: bool = None, window_id: int
    ) -> Optional[Window]:
        """Retrieves a window by ID."""
        try:
            return self.get_display().create_resource_object(
                id=window_id, type="window"
            )
        except XError as exception:
            LOGGER.error("Unable to retrieve window %d: %s", window_id, exception)
            if self._get_check(check=check):
                raise
        return None

    def get_window_class(
        self,
        *,
        check: bool = None,
        encoding: str = XSESSION_ENCODING,
        window: Union[int, Window],
    ) -> Optional[List[str]]:
        """Retrieves the class of a given window."""
        for atom in [NET_WM_CLASS, WM_CLASS]:
            result = None
            try:
                result = self.get_window_property(
                    atom=atom, check=False, property_type=AnyPropertyType, window=window
                )
            except BadAtom:
                ...
            if result is not None:
                return (
                    result.decode(encoding).split("\x00")[:-1]
                    if result is not None
                    else None
                )
        if self._get_check(check=check):
            raise RuntimeError(f"Unable to retrieve class of window: {window}")
        return None

    def get_window_desktop(
        self, *, check: bool = None, window: Union[int, Window]
    ) -> Optional[int]:
        """Retrieves the desktop containing a given window."""
        result = self.get_window_property(
            atom=NET_WM_DESKTOP,
            check=check,
            property_type=AnyPropertyType,
            window=window,
        )
        return int(result[0]) if result is not None else None

    def get_window_dimensions(
        self, *, check: bool = None, window: Union[int, Window]
    ) -> Optional[List[int]]:
        """Retrieves the dimensions of a given window."""
        get_geometry = self._get_window_geometry(check=check, window=window)
        return [get_geometry.width, get_geometry.height] if get_geometry else None

    def get_window_focus(
        self, *, check: bool = None, sane: bool = True
    ) -> Optional[Window]:
        """
        Retrieves the currently focused window.
        """

        # https://tronche.com/gui/x/icccm/sec-4.html#s-4.1.3.1
        def must_have_state(win: Window) -> bool:
            return self.get_window_state(check=False, window=win) is not None

        try:
            window = self.get_display().get_input_focus().focus
            if sane:
                windows = self._traverse_parents(
                    check=check, matcher=must_have_state, max_results=1, window=window
                )
                if windows:
                    window = windows[0]
            return window
        except XError as exception:
            LOGGER.error("Unable to retrieve currently focused window: %s", exception)
            if self._get_check(check=check):
                raise
        return None

    def get_window_frame_extents(
        self, *, check: bool = None, window: Union[int, Window]
    ) -> Optional[List[int]]:
        """Retrieves the desktop containing a given window."""
        result = self.get_window_property(
            atom=NET_FRAME_EXTENTS,
            check=check,
            property_type=AnyPropertyType,
            window=window,
        )
        return list(result) if result is not None else None

    def get_window_manager(self, check: bool = None) -> Optional[Window]:
        """Retrieves the window manager child window."""
        result = self.get_window_property(atom=NET_SUPPORTING_WM_CHECK, check=check)
        return (
            self.get_window_by_id(window_id=int(result[0]))
            if result is not None
            else None
        )

    def get_window_name(
        self,
        *,
        check: bool = None,
        encoding: str = XSESSION_ENCODING,
        window: Union[int, Window],
    ) -> Optional[str]:
        """Retrieves the name of a given window."""
        for atom in [NET_WM_NAME, WM_NAME]:
            result = self.get_window_property(
                atom=atom, check=False, property_type=AnyPropertyType, window=window
            )
            if result is not None:
                return result.decode(encoding)
        if self._get_check(check=check):
            raise RuntimeError(f"Unable to retrieve name of window: {window}")
        return None

    def get_window_pid(
        self, *, check: bool = None, window: Union[int, Window]
    ) -> Optional[int]:
        """Retrieves the process ID of a given window."""
        result = self.get_window_property(
            atom=NET_WM_PID, check=check, property_type=AnyPropertyType, window=window
        )
        return int(result[0]) if result is not None else None

    @window_type_safety
    def get_window_position(
        self, *, absolute: bool = True, check: bool = None, window: Union[int, Window]
    ) -> Optional[List[int]]:
        """
        Retrieves the position of a given window.
        https://stackoverflow.com/a/59221890
        """
        get_geometry = self._get_window_geometry(check=check, window=window)
        (position_x, position_y) = (get_geometry.x, get_geometry.y)
        window_root = self.get_window_root()
        while absolute and window.id != window_root.id:
            window = window.query_tree().parent
            get_geometry = self._get_window_geometry(check=check, window=window)
            position_x += get_geometry.x
            position_y += get_geometry.y
        return [position_x, position_y]

    @window_type_safety
    def get_window_properties(self, *, window: Union[int, Window]) -> List[int]:
        # pylint: disable=no-self-use
        """Retrieves the list of properties from a given window."""
        return window.list_properties()

    def get_window_property(
        self,
        *,
        atom: Union[int, str],
        check: bool = None,
        property_type: int = AnyPropertyType,
        window: Union[int, Window] = None,
    ) -> Optional[Any]:
        """Retrieves a property from a given window."""
        get_property = self._get_property(
            atom=atom, check=check, property_type=property_type, window=window
        )
        return get_property.value if get_property is not None else None

    def get_window_root(self, *, screen_number: int = None) -> Window:
        """Retrieves the root window of a given screen."""
        return self.get_screen(screen_number=screen_number).root

    def get_window_state(
        self, *, check: bool = None, window: Union[int, Window]
    ) -> Optional[List[int]]:
        """Retrieves the state(s) of a given window."""
        result = self.get_window_property(
            atom=NET_WM_STATE,
            check=check,
            property_type=AnyPropertyType,
            window=window,
        )
        return list(result) if result is not None else None

    def get_window_type(
        self, *, check: bool = None, window: Union[int, Window]
    ) -> Optional[int]:
        """Retrieves the type of a given window."""
        result = self.get_window_property(
            atom=NET_WM_WINDOW_TYPE,
            check=check,
            property_type=AnyPropertyType,
            window=window,
        )
        return int(result) if result is not None else None

    def get_window_visible_name(
        self,
        *,
        check: bool = None,
        encoding: str = XSESSION_ENCODING,
        window: Union[int, Window],
    ) -> Optional[str]:
        """Retrieves the visible name of a given window."""
        result = self.get_window_property(
            atom=NET_WM_VISIBLE_NAME,
            check=check,
            property_type=AnyPropertyType,
            window=window,
        )
        return result.decode(encoding) if result is not None else None

    def get_workarea(self, *, check: bool = None) -> Optional[List[List[int]]]:
        """Retrieves the workarea(s) for all desktops."""
        result = self.get_window_property(
            atom=NET_WORKAREA, check=check, property_type=AnyPropertyType
        )
        if not result:
            return None
        workarea = []
        for i in range(0, len(result), 4):
            workarea.append([int(x) for x in result[i : i + 4]])
        return workarea

    def get_virtual_roots(self, *, check: bool = None) -> Optional[List[int]]:
        """Retrieves the list of virtual roots."""
        result = self.get_window_property(atom=NET_VIRTUAL_ROOTS, check=check)
        return list(result) if result is not None else None

    def search(
        self,
        *,
        check: bool = None,
        matcher: Callable[[Window], bool] = None,
        max_results: int = None,
        prune_matches: bool = True,
        screen_number: int = None,
    ) -> Optional[List[Window]]:
        """Search for windows."""

        def match_all(*_) -> bool:
            return True

        result = []
        screens = (
            [screen_number]
            if screen_number is not None
            else range(0, self.get_screen_count())
        )

        for screen in screens:
            matcher = matcher if matcher else match_all
            window_root = self.get_window_root(screen_number=screen)
            # LOGGER.debug("Searching root: %s", self._get_window_id(window=window_root))
            result.extend(
                self._traverse_children(
                    check=check,
                    matcher=matcher,
                    max_results=max_results,
                    prune_matches=prune_matches,
                    window=window_root,
                )
            )

        return result

    def set_desktop_active(self, *, desktop: int):
        # pylint: disable=attribute-defined-outside-init,invalid-name
        """Assigns the active desktop."""
        LOGGER.debug("Assigning current desktop to: %d", desktop)
        self._NET_CURRENT_DESKTOP = [desktop, get_uptime()]

    def set_desktop_count(self, *, count: int):
        # pylint: disable=attribute-defined-outside-init,invalid-name
        """Assigns the number of desktops."""
        LOGGER.debug("Assigning number of desktops to: %d", count)
        self._NET_NUMBER_OF_DESKTOPS = [count]

    def set_desktop_geometry(self, *, height: int, width: int):
        # pylint: disable=attribute-defined-outside-init,invalid-name
        """Assigns the dimensions of the desktops."""
        LOGGER.debug("Assigning desktop geometry to : %dx%d", width, height)
        self._NET_DESKTOP_GEOMETRY = [width, height]

    def set_desktop_layout(
        self, *, columns: int, orientation: int, rows: int, starting_corner: int
    ):
        # pylint: disable=attribute-defined-outside-init,invalid-name
        """Assigns the dimensions of the desktops."""
        LOGGER.debug(
            "Assigning desktop layout to : %d %d %d %d",
            orientation,
            columns,
            rows,
            starting_corner,
        )
        self._NET_DESKTOP_LAYOUT = [orientation, columns, rows, starting_corner]

    # TODO: def set_desktop_names(...)

    def set_desktop_showing(self, *, showing: int):
        # pylint: disable=attribute-defined-outside-init,invalid-name
        """Assigns the showing desktop flag."""
        LOGGER.debug("Assigning desktop showing to : %d", showing)
        self._NET_SHOWING_DESKTOP = [showing]

    # TODO: def set_desktop_viewport(...)

    def set_window_active(
        self, *, check: bool = None, window: Union[int, Window], **kwargs
    ):
        """Assigns the active window."""
        LOGGER.debug("Activating window: %d", self._get_window_id(window))

        window_id = self._get_window_id(window=window)
        self._set_property(
            atom=NET_ACTIVE_WINDOW,
            check=check,
            data=[SOURCE_PAGER, get_uptime(), window_id],
            window=window,
            **kwargs,
        )

    def set_window_close(
        self, *, check: bool = None, window: Union[int, Window], **kwargs
    ):
        """Closes a given window."""
        LOGGER.debug("Closing window: %d", self._get_window_id(window))
        self._set_property(
            atom=NET_CLOSE_WINDOW,
            check=check,
            data=[get_uptime(), SOURCE_PAGER],
            window=window,
            **kwargs,
        )

    def set_window_desktop(
        self, *, check: bool = None, desktop: int, window: Union[int, Window], **kwargs
    ):
        """Assigns a desktop to a given window."""
        LOGGER.debug(
            "Assigning desktop to window %d: %d", self._get_window_id(window), desktop
        )
        self._set_property(
            atom=NET_WM_DESKTOP,
            check=check,
            data=[desktop, SOURCE_PAGER],
            window=window,
            **kwargs,
        )

    @window_type_safety
    def set_window_dimensions(
        self,
        *,
        check: bool = None,
        height: int,
        sync: bool = True,
        width: int,
        window: Union[int, Window],
    ):
        """Sizes a window."""
        LOGGER.debug(
            "Sizing window %d to: %dx%d", self._get_window_id(window), width, height
        )
        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window.configure(height=height, onerror=cerror, width=width)

    @window_type_safety
    def set_window_focus(
        self,
        *,
        check: bool = None,
        revert_to: int = RevertToParent,
        sync: bool = True,
        window: Union[int, Window],
    ):
        """Focuses a window."""
        LOGGER.debug("Assigning focus to window: %d", self._get_window_id(window))
        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window.set_input_focus(
                revert_to=revert_to, time=get_uptime(), onerror=cerror
            )

    def set_window_frame_extents(
        self,
        *,
        bottom: int,
        check: bool = None,
        left: int,
        right: int,
        top: int,
        window: Union[int, Window],
        **kwargs,
    ):
        """Assigns a desktop to a given window."""
        LOGGER.debug(
            "Assigning frame extends to window %d: %d %d %d %d",
            self._get_window_id(window),
            left,
            right,
            top,
            bottom,
        )
        self._change_property(
            atom=NET_FRAME_EXTENTS,
            check=check,
            data=[left, right, top, bottom],
            property_type=CARDINAL,
            window=window,
            **kwargs,
        )

    @window_type_safety
    def set_window_position(
        self,
        *,
        check: bool = None,
        position_x: int,
        position_y: int,
        sync: bool = True,
        window: Union[int, Window],
    ):
        """Moves a window."""
        LOGGER.debug(
            "Moving window %d to: %d,%d",
            self._get_window_id(window),
            position_x,
            position_y,
        )
        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window.configure(onerror=cerror, x=position_x, y=position_y)
            # TODO: Is this needed?
            # window.change_attributes(win_gravity=X.NorthWestGravity, bit_gravity=X.StaticGravity)
            # .. or this?
            # window.configure(..., stack_mode=Xlib.X.Above)

    def set_window_state(
        self,
        *,
        action: int = ACTION_ADD,
        check: bool = None,
        state0: Union[int, str],
        state1: Union[int, str] = 0,
        window: Union[int, Window],
        **kwargs,
    ):
        """
        Modifies up to two state(s) on a given window.

        https://specifications.freedesktop.org/wm-spec/1.3/ar01s05.html#idm44949527936624
        """
        LOGGER.debug(
            "Assigning state(s) to window %s: %s, %s",
            self._get_window_id(window),
            state0,
            state1,
        )
        if not isinstance(state0, int):
            state0 = self.get_atom(name=state0)
        if not isinstance(state1, int):
            state1 = self.get_atom(name=state1)
        self._set_property(
            atom=NET_WM_STATE,
            check=check,
            data=[action, state0, state1, SOURCE_PAGER],
            window=window,
            **kwargs,
        )

    def wait_desktop_active(
        self, *, delay: int = 1, desktop: int, retry: int = 3
    ) -> bool:
        """Waits for a desktop to be active."""

        def desktop_is_active(attempt: int):
            LOGGER.debug(
                "Waiting for desktop to be active (try: %d): %s", attempt, desktop
            )
            desktop_active = self.get_desktop_active()
            if desktop == desktop_active:
                LOGGER.debug("Desktop is active.")
                return True
            return False

        return XSession._retry(checker=desktop_is_active, delay=delay, retry=retry)

    @window_type_safety
    def wait_window_active(
        self, *, delay: int = 1, retry: int = 3, window: Union[int, Window]
    ) -> bool:
        """Waits for a window to be active."""

        def window_is_active(attempt: int):
            LOGGER.debug(
                "Waiting for window to be active (try: %d): %s", attempt, window_id
            )
            window_id_active = self._get_window_id(window=self.get_window_active())
            if window_id == window_id_active:
                LOGGER.debug("Window is active.")
                return True
            return False

        window_id = self._get_window_id(window=window)
        return XSession._retry(checker=window_is_active, delay=delay, retry=retry)

    @window_type_safety
    def wait_window_focused(
        self, *, delay: int = 1, retry: int = 3, window: Union[int, Window]
    ) -> bool:
        """Waits for a window to be focused."""

        def window_is_focused(attempt: int):
            LOGGER.debug(
                "Waiting for window to be focused (try: %d): %s", attempt, window_id
            )
            window_id_focused = self._get_window_id(window=self.get_window_active())
            if window_id == window_id_focused:
                LOGGER.debug("Window is focused.")
                return True
            return False

        window_id = self._get_window_id(window=window)
        return XSession._retry(checker=window_is_focused, delay=delay, retry=retry)

    @window_type_safety
    def wait_window_visible(
        self, *, delay: int = 1, retry: int = 3, window: Union[int, Window]
    ) -> bool:
        """Waits for a window to be visible."""

        def window_is_visible(attempt: int):
            LOGGER.debug(
                "Waiting for window to be visible (try: %d): %s",
                attempt,
                self._get_window_id(window=window),
            )
            get_window_attributes = window.get_attributes()
            if get_window_attributes.map_state == IsViewable:
                LOGGER.debug("Window is visible.")
                return True
            return False

        return XSession._retry(checker=window_is_visible, delay=delay, retry=retry)

    @window_type_safety
    def window_destroy(
        self, *, check: bool = None, sync: bool = True, window: Union[int, Window]
    ):
        """Destroys a window."""
        LOGGER.debug("Destroying window: %d", self._get_window_id(window))
        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window.destroy(onerror=cerror)

    @window_type_safety
    def window_kill(
        self, *, check: bool = None, sync: bool = True, window: Union[int, Window]
    ):
        """Kills a window."""
        LOGGER.debug("Killing window: %d", self._get_window_id(window))
        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window.kill_client(onerror=cerror)

    @window_type_safety
    def window_map(
        self, *, check: bool = None, sync: bool = True, window: Union[int, Window]
    ):
        """Maps a window."""
        LOGGER.debug("Mapping window: %d", self._get_window_id(window))
        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window.map(onerror=cerror)

    def window_maximize(
        self,
        *,
        check: bool = None,
        flags: List[Union[int, str]] = None,
        inverse: bool = False,
        window: Union[int, Window],
        **kwargs,
    ):
        """Maximizes a given window."""
        LOGGER.debug(
            "%s window: %d",
            "Restoring" if inverse else "Maximizing",
            self._get_window_id(window),
        )

        if not flags:
            flags = [NET_WM_STATE_MAXIMIZED_HORZ, NET_WM_STATE_MAXIMIZED_VERT]

        state1 = {"state1": flags[1]} if len(flags) > 1 else {}
        self.set_window_state(
            action=ACTION_REMOVE if inverse else ACTION_ADD,
            check=check,
            state0=flags[0],
            **state1,
            window=window,
            **kwargs,
        )

    def window_minimize(
        self,
        *,
        check: bool = None,
        inverse: bool = False,
        window: Union[int, Window],
        **kwargs,
    ):
        """Maximizes a given window."""
        LOGGER.debug(
            "%s window: %d",
            "Restoring" if inverse else "Minimizing",
            self._get_window_id(window),
        )

        if inverse:
            # Passing XUtil.NormalState does not work.
            # Per https://tronche.com/gui/x/icccm/sec-4.html#s-4.1.4 this is supposed
            # to use self.window_map(); however, that too does not work unless the
            # window is unmapped first?!?
            self.set_window_active(check=check, window=window)
        else:
            self._set_property(
                atom=WM_CHANGE_STATE,
                check=check,
                data=[IconicState],
                window=window,
                **kwargs,
            )

    def window_moveresize(
        self,
        *,
        check: bool = None,
        gravity: int = StaticGravity,
        height: int = None,
        position_x: int = None,
        position_y: int = None,
        width: int = None,
        window: Union[int, Window],
        **kwargs,
    ):
        # pylint: disable=line-too-long
        """
        Moves and / or resizes a given window.
        https://tronche.com/gui/x/xlib/window/attributes/gravity.html
        """
        LOGGER.debug(
            "Moving and resizing window %d to: %s,%s %sx%s %d",
            self._get_window_id(window=window),
            position_x,
            position_y,
            width,
            height,
            gravity,
        )

        # |                        Source |     H       W       Y       X |                           ??? |                       Gravity |
        # |    15 |    14 |    13 |    12 |    11 |    10 |     9 |     8 |     7 |     6 |     5 |     4 |     3 |     2 |     1 |     0 |
        # | 32768 | 16384 |  8192 |  4096 |  2048 |  1024 |   512 |   256 |   128 |    64 |    32 |    16 |     8 |     4 |     2 |     0 |

        if height is not None:
            gravity = gravity | 2048
        if position_x is not None:
            gravity = gravity | 256
        if position_y is not None:
            gravity = gravity | 512
        if width is not None:
            gravity = gravity | 1024
        gravity = gravity | 4096
        LOGGER.debug("Gravity with flags: %s", format(gravity, "016b"))

        (height, position_x, position_y, width) = map(
            lambda x: 0 if x is None else x, [height, position_x, position_y, width]
        )
        self._set_property(
            atom=NET_MOVERESIZE_WINDOW,
            check=check,
            data=[gravity, position_x, position_y, width, height],
            window=window,
            **kwargs,
        )

    @window_type_safety
    def window_raise(
        self, *, check: bool = None, sync: bool = True, window: Union[int, Window]
    ):
        """Raises a window."""
        LOGGER.debug("Raising window: %d", self._get_window_id(window))
        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window.raise_window(onerror=cerror)

    def window_select(
        self, *, check: bool = None, delay: int = 1, retry: int = 3
    ) -> Optional[Window]:
        # pylint: disable=too-many-branches
        """
        Graphically selects window (interactive via UI).
        https://github.com/jordansissel/xdotool/blob/735e301665e7f9b8fe850588e88a3a0973695eec/xdo.c#L735
        """
        display = self.get_display()
        window_root = self.get_window_root()

        font = display.open_font("cursor")  # type: Font
        LOGGER.debug("Retrieved font: %s", font.id)

        cursor = font.create_glyph_cursor(
            mask=font,
            source_char=xcf_crosshair,
            mask_char=xcf_crosshair + 1,
            foreground=[65535, 65535, 65535],
            background=[0, 0, 0],
        )  # type: Cursor
        LOGGER.debug("Created cursor: %s", cursor.id)

        while retry:
            try:
                grab_pointer = window_root.grab_pointer(
                    confine_to=window_root,
                    cursor=cursor,
                    event_mask=ButtonReleaseMask,
                    keyboard_mode=GrabModeAsync,
                    owner_events=False,
                    pointer_mode=GrabModeSync,
                    time=get_uptime(),
                )
                if grab_pointer != GrabSuccess:
                    raise RuntimeError(f"Grab pointer not successful: {grab_pointer}")
                break
            except RuntimeError as exception:
                LOGGER.error("%s; try #%d ...", exception, retry)
                if retry:
                    retry -= 1
                    sleep(delay)
                elif self._get_check(check=check):
                    raise
            except XError as exception:
                LOGGER.error("Unable to grab pointer: %s", exception)
                if self._get_check(check=check):
                    raise
        LOGGER.debug("Pointer grabbed successfully.")

        with self.catch_error(check=check) as cerror:
            display.allow_events(mode=SyncPointer, onerror=cerror, time=get_uptime())
        with self.catch_error(check=check) as cerror:
            window_root.change_attributes(event_mask=ButtonReleaseMask, onerror=cerror)

        # FIXME: Try to avoid quirky race conditions?!?
        sleep(0.5)

        try:
            LOGGER.debug("Waiting for event ...")
            event = display.next_event()  # type: Event
            LOGGER.debug("Received event: %s", event)
        finally:
            with self.catch_error(check=check) as cerror:
                display.ungrab_pointer(onerror=cerror, time=get_uptime())
            with self.catch_error(check=check) as cerror:
                cursor.free(onerror=cerror)

        if event.detail != Button1:
            LOGGER.debug("Selection aborted with button: %s", event.detail)
            return None

        if not event.child:
            window = event.window
        else:
            stack = event.child.query_tree().children
            while (
                len(stack)
                and self.get_window_state(check=False, window=stack[0]) is None
            ):
                stack.append(stack.pop(0).query_tree().children)
            window = stack[0]

        LOGGER.debug("Selected window: %d", self._get_window_id(window))
        return window

    @window_type_safety
    def window_unmap(
        self, *, check: bool = None, sync: bool = True, window: Union[int, Window]
    ):
        """Unmaps a window."""
        LOGGER.debug("Unmapping window: %d", self._get_window_id(window))
        with self.catch_error(check=check) as cerror, self.display_sync(sync=sync):
            window.unmap(onerror=cerror)
