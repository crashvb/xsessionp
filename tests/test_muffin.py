#!/usr/bin/env python

# pylint: disable=redefined-outer-name

"""muffin tests."""

import logging
import os

import pytest

from xsessionp import Muffin, NET_WM_STATE_TILED, TileMode, TileType

from .testutils import allow_xserver_to_sync


LOGGER = logging.getLogger(__name__)


def test___init__(muffin: Muffin):
    """Test that an Muffin can be instantiated."""
    assert muffin


@pytest.mark.skipif(
    "TRAVIS" in os.environ,
    reason="xvfb failure: Unable to intern atom: _NET_WM_WINDOW_TILE_INFO",
)
@pytest.mark.xclock
def test_get_set_window_tile_info(muffin: Muffin, window_id: int):
    """Tests that tile information can be retrieved / assigned to a window."""
    tile_info0 = muffin.get_window_tile_info(window=window_id)
    assert not tile_info0

    desktop = muffin.get_window_desktop(window=window_id)
    height = 10
    position_x = 20
    position_y = 30
    width = 40
    muffin.set_window_tile_info(
        desktop=desktop,
        height=height,
        position_x=position_x,
        position_y=position_y,
        tile_mode=TileMode.LEFT_BOTTOM,
        tile_type=TileType.TILED,
        width=width,
        window=window_id,
    )
    allow_xserver_to_sync()
    tile_info1 = muffin.get_window_tile_info(window=window_id)
    assert tile_info1
    assert tile_info1 != tile_info0


@pytest.mark.skipif(
    "TRAVIS" in os.environ,
    reason="xvfb failure: Unable to intern atom: _NET_ACTIVE_WINDOW",
)
@pytest.mark.xclock
def test_window_tile(muffin: Muffin, window_id: int):
    # pylint: disable=too-many-locals,too-many-statements
    """Tests that a window can be tiled."""

    atom_net_wm_state_tiled = muffin.get_atom(name=NET_WM_STATE_TILED)

    # TODO: Why is set_window_focus() in _send_Keys failing sometimes?
    muffin.set_window_active(window=window_id)

    # Verify untiled ...
    position0 = muffin.get_window_position(window=window_id)
    assert position0
    dimensions0 = muffin.get_window_dimensions(window=window_id)
    assert dimensions0
    frame_extends0 = muffin.get_window_frame_extents(window=window_id)
    assert frame_extends0
    tile_info0 = muffin.get_window_tile_info(check=False, window=window_id)
    assert not tile_info0
    state0 = muffin.get_window_state(window=window_id)
    assert not state0

    # Tile left bottom ...
    muffin.window_tile(tile_mode=TileMode.LEFT_BOTTOM, window=window_id)
    allow_xserver_to_sync()
    position1 = muffin.get_window_position(window=window_id)
    assert position1 != position0
    dimensions1 = muffin.get_window_dimensions(window=window_id)
    assert dimensions1 != dimensions0
    frame_extends1 = muffin.get_window_frame_extents(window=window_id)
    assert frame_extends1 != frame_extends0
    tile_info1 = muffin.get_window_tile_info(check=False, window=window_id)
    assert tile_info1
    state1 = muffin.get_window_state(window=window_id)
    assert state1
    assert atom_net_wm_state_tiled in state1

    # Untile ...
    muffin.window_tile(tile_mode=TileMode.NONE, window=window_id)
    allow_xserver_to_sync()
    position2 = muffin.get_window_position(window=window_id)
    assert position2 == position0
    dimensions2 = muffin.get_window_dimensions(window=window_id)
    assert dimensions2 == dimensions0
    frame_extends2 = muffin.get_window_frame_extents(window=window_id)
    assert frame_extends2 == frame_extends0
    tile_info2 = muffin.get_window_tile_info(check=False, window=window_id)
    assert not tile_info2
    state2 = muffin.get_window_state(window=window_id)
    assert atom_net_wm_state_tiled not in state2

    # Tile right top ...
    muffin.window_tile(tile_mode=TileMode.RIGHT_TOP, window=window_id)
    allow_xserver_to_sync()
    position3 = muffin.get_window_position(window=window_id)
    assert position3 != position0
    assert position3 != position1
    dimensions3 = muffin.get_window_dimensions(window=window_id)
    assert dimensions3 != dimensions0
    frame_extends3 = muffin.get_window_frame_extents(window=window_id)
    assert frame_extends3 != frame_extends0
    assert frame_extends3 != frame_extends1
    tile_info3 = muffin.get_window_tile_info(check=False, window=window_id)
    assert tile_info3
    assert tile_info3 != tile_info1
    state3 = muffin.get_window_state(window=window_id)
    assert state3
    assert atom_net_wm_state_tiled in state3
