#!/usr/bin/env python

"""gnome-shell window manager statics."""

import logging

from enum import Enum
from typing import Union

from Xlib.xobject.drawable import Window
from Xlib.X import KeyPress, KeyRelease

from .xsession import TypingKeyInput, XSession

LOGGER = logging.getLogger(__name__)

WINDOW_MANAGER = "gnome shell"


class TileMethod(Enum):

    # MOVERESIZE = 0
    # WMSTATE = 1
    KEYBOARD = 2


class TileMode(Enum):
    # pylint: disable=missing-function-docstring
    NONE = 0
    LEFT = 1
    RIGHT = 2
    TOP = 7

    def is_bottom(self: "TileMode"):
        return self in []

    def is_full_height(self: "TileMode"):
        return self in [TileMode.LEFT, TileMode.RIGHT]

    def is_full_width(self: "TileMode"):
        return self in [TileMode.TOP]

    def is_left(self: "TileMode"):
        return self in [TileMode.LEFT]

    def is_right(self: "TileMode"):
        return self in [TileMode.RIGHT]

    def is_top(self: "TileMode"):
        return self in [TileMode.TOP]


class TileType(Enum):

    NONE = 0
    TILED = 1


class Gnome(XSession):
    """Interacts with gnome-shell."""

    def __init__(self, check: bool = True, xsession: XSession = None):
        super().__init__(check=check)

        if xsession:
            self.check = xsession.check
            self.display = xsession.display

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
                    # No matter where we are at, send it to NONE ...
                    TypingKeyInput(event_type=KeyPress, key="Super_L"),
                    TypingKeyInput(event_type=KeyPress, key="Down"),
                    TypingKeyInput(event_type=KeyRelease, key="Down"),
                    TypingKeyInput(event_type=KeyRelease, key="Super_L"),
                ],
                window=window,
            )

        if tile_mode == TileMode.NONE:
            untile()
            return

        untile()

        key_inputs = [TypingKeyInput(event_type=KeyPress, key="Super_L")]

        if tile_mode.is_left():
            key_inputs.append(TypingKeyInput(event_type=KeyPress, key="Left"))
            key_inputs.append(TypingKeyInput(event_type=KeyRelease, key="Left"))
        elif tile_mode.is_right():
            key_inputs.append(TypingKeyInput(event_type=KeyPress, key="Right"))
            key_inputs.append(TypingKeyInput(event_type=KeyRelease, key="Right"))
        elif tile_mode.is_top():
            key_inputs.append(TypingKeyInput(event_type=KeyPress, key="Up"))
            key_inputs.append(TypingKeyInput(event_type=KeyRelease, key="Up"))

        key_inputs.append(TypingKeyInput(event_type=KeyRelease, key="Super_L"))

        self._send_keys(
            check=check,
            key_inputs=key_inputs,
            window=window,
        )

    # def _window_tile_moveresize(
    #     self,
    #     *,
    #     check: bool = None,
    #     tile_mode: TileMode = TileMode.NONE,
    #     tile_type: TileType = TileType.TILED,
    #     window: Union[int, Window],
    # ):
    #     ...
    #
    # def _window_tile_wmstate(
    #     self,
    #     *,
    #     check: bool = None,
    #     tile_mode: TileMode = TileMode.NONE,
    #     tile_type: TileType = TileType.TILED,
    #     window: Union[int, Window],
    # ):
    #     ...

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

        if tile_method == TileMethod.KEYBOARD:
            self._window_tile_keyboard(
                check=check, tile_mode=tile_mode, tile_type=tile_type, window=window
            )
        # elif tile_method == TileMethod.MOVERESIZE:
        #     self._window_tile_moveresize(
        #         check=check, tile_mode=tile_mode, tile_type=tile_type, window=window
        #     )
        # elif tile_method == TileMethod.WMSTATE:
        #     self._window_tile_wmstate(
        #         check=check, tile_mode=tile_mode, tile_type=tile_type, window=window
        #     )
        else:
            LOGGER.error("Unsupported tile method: %s", tile_method)
