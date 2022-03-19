#!/usr/bin/env python

"""linuxmint/muffin window manager statics."""

import logging

from enum import Enum
from typing import List, Optional, Union

from Xlib.xobject.drawable import Window
from Xlib.X import AnyPropertyType, KeyPress, KeyRelease, StaticGravity
from Xlib.Xatom import CARDINAL

from .ewmh import ACTION_ADD, ACTION_REMOVE
from .xsession import TypingKeyInput, XSession

LOGGER = logging.getLogger(__name__)

NET_WM_WINDOW_TILE_INFO = "_NET_WM_WINDOW_TILE_INFO"

NET_WM_STATE_MAXIMIZED_VERT = "_NET_WM_STATE_MAXIMIZED_VERT"
NET_WM_STATE_TILED = "_NET_WM_STATE_TILED"


class TileMethod(Enum):
    """
    Holding our breath ...
    https://github.com/linuxmint/muffin/issues/612
    """

    MOVERESIZE = 0
    WMSTATE = 1
    KEYBOARD = 2


class TileMode(Enum):
    # pylint: disable=missing-function-docstring
    """linuxmint/muffin:/src/meta/common.h::MetaTileMode"""
    NONE = 0
    LEFT = 1
    RIGHT = 2
    LEFT_TOP = 3
    LEFT_BOTTOM = 4
    RIGHT_TOP = 5
    RIGHT_BOTTOM = 6
    TOP = 7
    BOTTOM = 8
    MAXIMIZE = 9

    def is_bottom(self: "TileMode"):
        return self in [
            TileMode.BOTTOM,
            TileMode.LEFT_BOTTOM,
            TileMode.RIGHT_BOTTOM,
        ]

    def is_full_height(self: "TileMode"):
        return self in [TileMode.LEFT, TileMode.RIGHT]

    def is_full_width(self: "TileMode"):
        return self in [TileMode.BOTTOM, TileMode.TOP]

    def is_left(self: "TileMode"):
        return self in [TileMode.LEFT, TileMode.LEFT_BOTTOM, TileMode.LEFT_TOP]

    def is_right(self: "TileMode"):
        return self in [TileMode.RIGHT, TileMode.RIGHT_BOTTOM, TileMode.RIGHT_TOP]

    def is_top(self: "TileMode"):
        return self in [TileMode.LEFT_TOP, TileMode.RIGHT_TOP, TileMode.TOP]


class TileType(Enum):
    """linuxmint/muffin:/src/meta/common.h::MetaWindowTileType"""

    NONE = 0
    TILED = 1
    SNAPPED = 2


class Muffin(XSession):
    """Interacts with muffin."""

    def __init__(self, check: bool = True, xsession: XSession = None):
        super().__init__(check=check)

        if xsession:
            self.check = xsession.check
            self.display = xsession.display

    def _do_math(self, *, tile_mode: TileMode = TileMode.NONE):
        """Calculates the geometry and dimensions for a given tile location."""

        # Captured from a 5120x1415 desktop:
        # muffin:/src/core/window.c::void set_net_wm_state(MetaWindow)
        #                tile_mode, tile_type, position_x, position_y, width, height, monitor, custom_snap_size (bool)
        # left         = 1,         1,         0,          0,          2560,  1415,   0,       0
        # right        = 2,         1,         2560,       0,          2560,  1415,   0,       0
        # left-top     = 3,         1,         0,          0,          2560,  707,    0,       0
        # left-bottom  = 4,         1,         0,          707,        2560,  707,    0,       0
        # right-top    = 5,         1,         2560,       0,          2560,  707,    0,       0
        # right-bottom = 6,         1,         2560,       707,        2560,  707,    0,       0
        # top          = 7,         1,         0,          0,          5120,  707,    0,       0
        # bottom       = 8,         1,         0,          707,        5120,  707,    0,       0

        # Assign _NET_WM_WINDOW_TILE_INFO values based on the table above ...
        (desktop_width, desktop_height) = self.get_desktop_geometry()
        height = (
            desktop_height if tile_mode.is_full_height() else int(desktop_height / 2)
        )
        position_x = int(desktop_width / 2) if tile_mode.is_right() else 0
        position_y = int(desktop_height / 2) if tile_mode.is_bottom() else 0
        width = desktop_width if tile_mode.is_full_width() else int(desktop_width / 2)

        # TODO: Add adjustments (frame extents?) for hints from the WM ...

        return height, position_x, position_y, width

    def _window_tile_keyboard(
        self,
        *,
        check: bool = None,
        tile_mode: TileMode = TileMode.NONE,
        tile_type: TileType = TileType.TILED,
        window: Union[int, Window],
    ):
        """It's unfortunate that it's come to this, but seems to be effective =/."""

        def untile():
            """Untiles the window."""
            self._send_keys(
                check=check,
                key_inputs=[
                    # No matter where we are at, send it to LEFT_TOP ...
                    TypingKeyInput(event_type=KeyPress, key="Super_L"),
                    TypingKeyInput(event_type=KeyPress, key="Left"),
                    TypingKeyInput(event_type=KeyRelease, key="Left"),
                    TypingKeyInput(event_type=KeyPress, key="Left"),
                    TypingKeyInput(event_type=KeyRelease, key="Left"),
                    TypingKeyInput(event_type=KeyPress, key="Up"),
                    TypingKeyInput(event_type=KeyRelease, key="Up"),
                    TypingKeyInput(event_type=KeyPress, key="Up"),
                    TypingKeyInput(event_type=KeyRelease, key="Up"),
                    # ... then back to normal ...
                    TypingKeyInput(event_type=KeyPress, key="Right"),
                    TypingKeyInput(event_type=KeyRelease, key="Right"),
                    TypingKeyInput(event_type=KeyPress, key="Down"),
                    TypingKeyInput(event_type=KeyRelease, key="Down"),
                    TypingKeyInput(event_type=KeyRelease, key="Super_L"),
                ],
                window=window,
            )

        if tile_mode == TileMode.NONE:
            untile()
            return

        # TODO: This is especially messy! Do we "really" need to do this?
        # untile()

        key_inputs = [TypingKeyInput(event_type=KeyPress, key="Super_L")]
        if tile_type == TileType.SNAPPED:
            key_inputs.append(TypingKeyInput(event_type=KeyPress, key="Control_L"))

        if tile_mode.is_left():
            key_inputs.append(TypingKeyInput(event_type=KeyPress, key="Left"))
            key_inputs.append(TypingKeyInput(event_type=KeyRelease, key="Left"))
        elif tile_mode.is_right():
            key_inputs.append(TypingKeyInput(event_type=KeyPress, key="Right"))
            key_inputs.append(TypingKeyInput(event_type=KeyRelease, key="Right"))

        if tile_mode.is_bottom():
            key_inputs.append(TypingKeyInput(event_type=KeyPress, key="Down"))
            key_inputs.append(TypingKeyInput(event_type=KeyRelease, key="Down"))
        elif tile_mode.is_top():
            key_inputs.append(TypingKeyInput(event_type=KeyPress, key="Up"))
            key_inputs.append(TypingKeyInput(event_type=KeyRelease, key="Up"))

        if tile_type == TileType.SNAPPED:
            key_inputs.append(TypingKeyInput(event_type=KeyRelease, key="Control_L"))
        key_inputs.append(TypingKeyInput(event_type=KeyRelease, key="Super_L"))

        self._send_keys(
            check=check,
            key_inputs=key_inputs,
            window=window,
        )

    def _window_tile_moveresize(
        self,
        *,
        check: bool = None,
        tile_mode: TileMode = TileMode.NONE,
        tile_type: TileType = TileType.TILED,
        window: Union[int, Window],
    ):
        # pylint: disable=unused-argument
        """This is not tiling, but it does "something" ..."""
        if tile_mode == TileMode.NONE:
            LOGGER.warning("tile_method=MOVERESIZE and tile_mode=NONE not supported!")
            return

        # TODO: Can anything be done to honor the requested tile_type?
        (height, position_x, position_y, width) = self._do_math(tile_mode=tile_mode)
        self.window_moveresize(
            check=check,
            gravity=StaticGravity,
            height=height,
            position_x=position_x,
            position_y=position_y,
            width=width,
            window=window,
        )

    def _window_tile_wmstate(
        self,
        *,
        check: bool = None,
        tile_mode: TileMode = TileMode.NONE,
        tile_type: TileType = TileType.TILED,
        window: Union[int, Window],
    ):
        """This is an example of when "2 + 2 = None"."""
        if tile_mode == TileMode.NONE:
            self._remove_property(
                atom=NET_WM_WINDOW_TILE_INFO, check=check, window=window
            )
            self.set_window_frame_extents(
                bottom=0, left=0, right=0, top=24, window=window
            )
            self.set_window_state(
                action=ACTION_REMOVE,
                check=check,
                state0=NET_WM_STATE_MAXIMIZED_VERT,
                state1=NET_WM_STATE_TILED,
                window=window,
            )
            return

        # TODO: What do we do about tiled vs snapped?

        (height, position_x, position_y, width) = self._do_math(tile_mode=tile_mode)
        # Note: Unmapping the window allows the properties to be assigned, but they
        #       are "reset" when it is remapped!?!
        # self.window_unmap(check=check, window=window)
        self.set_window_tile_info(
            check=check,
            height=height,
            position_x=position_x,
            position_y=position_y,
            tile_mode=tile_mode,
            tile_type=tile_type,
            width=width,
            window=window,
        )
        self.set_window_frame_extents(
            bottom=1, check=check, left=0, right=1, top=24, window=window
        )
        # Note: This does not perform send_event to the root window; hence, the
        #       properties are assigned, but do nothing ...
        # self._change_property(
        #     atom=NET_WM_STATE,
        #     check=check,
        #     # data=[self.get_atom(name=NET_WM_STATE_TILED)],
        #     data=[self.get_atom(name=NET_WM_STATE_MAXIMIZED_VERT), self.get_atom(name=NET_WM_STATE_TILED)],
        #     window=window,
        # )
        self.set_window_state(
            action=ACTION_ADD,
            check=check,
            state0=NET_WM_STATE_TILED,
            # TODO: Why does passing the second state negate the first?
            # state1=NET_WM_STATE_MAXIMIZED_VERT,
            window=window,
        )
        self.get_display().flush()
        # self.window_map(check=check, window=window)

    def get_window_tile_info(
        self, *, check: bool = None, window: Union[int, Window]
    ) -> Optional[List[int]]:
        """Retrieves the tile information for a given window."""
        result = self.get_window_property(
            atom=NET_WM_WINDOW_TILE_INFO,
            check=check,
            property_type=AnyPropertyType,
            window=window,
        )
        return list(result) if result else None

    def set_window_tile_info(
        self,
        *,
        check: bool = None,
        custom_snap_size: bool = False,
        desktop: int = None,
        height: int = None,
        position_x: int = None,
        position_y: int = None,
        tile_mode: TileMode = TileMode.NONE,
        tile_type: TileType = TileType.NONE,
        width: int = None,
        window: Union[int, Window],
        **kwargs,
    ):
        """Assigns tile information to a given window."""
        LOGGER.debug(
            "Assigning tile information to window %d: %d %d %s %s %s %s %s %d",
            self._get_window_id(window),
            tile_mode.value,
            tile_type.value,
            position_x,
            position_y,
            width,
            height,
            desktop,
            int(custom_snap_size),
        )
        if desktop is None:
            desktop = self.get_window_desktop(check=check, window=window)
        self._change_property(
            atom=NET_WM_WINDOW_TILE_INFO,
            check=check,
            data=[
                tile_mode.value,
                tile_type.value,
                position_x,
                position_y,
                width,
                height,
                desktop,
                int(custom_snap_size),
            ],
            property_type=CARDINAL,
            window=window,
            **kwargs,
        )

    def window_tile(
        self,
        *,
        check: bool = None,
        tile_method: TileMethod = TileMethod.KEYBOARD,
        tile_mode: TileMode = TileMode.NONE,
        tile_type: TileType = TileType.TILED,
        window: Union[int, Window],
    ):
        """Tiles a given window."""

        # HACK: Odd that Muffin would enumerate things this way, but okay ...
        if tile_mode == TileMode.MAXIMIZE:
            self.window_maximize(check=check, window=window)
            return

        if tile_method == TileMethod.KEYBOARD:
            self._window_tile_keyboard(
                check=check, tile_mode=tile_mode, tile_type=tile_type, window=window
            )
        elif tile_method == TileMethod.MOVERESIZE:
            self._window_tile_moveresize(
                check=check, tile_mode=tile_mode, tile_type=tile_type, window=window
            )
        elif tile_method == TileMethod.WMSTATE:
            self._window_tile_wmstate(
                check=check, tile_mode=tile_mode, tile_type=tile_type, window=window
            )
        else:
            LOGGER.error("Unsupported tile method: %s", tile_method)
