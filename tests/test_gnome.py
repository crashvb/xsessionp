#!/usr/bin/env python

# pylint: disable=redefined-outer-name

"""gnome-shell tests."""

import logging

import pytest

from xsessionp import Gnome, NET_WM_STATE_MAXIMIZED_HORZ, NET_WM_STATE_MAXIMIZED_VERT
from xsessionp.ewmh import NET_WM_STATE_FOCUSED
from xsessionp.gnome import TileMode, WINDOW_MANAGER

from .testutils import allow_xserver_to_sync


LOGGER = logging.getLogger(__name__)


def test___init__(gnome: Gnome):
    """Test that a Gnome can be instantiated."""
    assert gnome


@pytest.mark.skip_travis("xvfb failure: Unable to intern atom: _NET_ACTIVE_WINDOW")
@pytest.mark.require_window_managers(WINDOW_MANAGER)
@pytest.mark.xlogo
def test_window_tile(gnome: Gnome, window_id: int):
    # pylint: disable=too-many-locals,too-many-statements
    """Tests that a window can be tiled."""
    atom_net_wm_state_focused = gnome.get_atom(name=NET_WM_STATE_FOCUSED)
    atom_net_wm_state_maximized_horz = gnome.get_atom(name=NET_WM_STATE_MAXIMIZED_HORZ)
    atom_net_wm_state_maximized_vert = gnome.get_atom(name=NET_WM_STATE_MAXIMIZED_VERT)

    gnome.set_window_active(window=window_id)

    # Verify untiled ...
    position0 = gnome.get_window_position(window=window_id)
    assert position0
    dimensions0 = gnome.get_window_dimensions(window=window_id)
    assert dimensions0
    state0 = gnome.get_window_state(window=window_id)
    assert atom_net_wm_state_focused in state0
    assert atom_net_wm_state_maximized_horz not in state0
    assert atom_net_wm_state_maximized_vert not in state0

    # Tile left ...
    gnome.window_tile(tile_mode=TileMode.LEFT, window=window_id)
    allow_xserver_to_sync()
    position1 = gnome.get_window_position(window=window_id)
    assert position1 != position0
    dimensions1 = gnome.get_window_dimensions(window=window_id)
    assert dimensions1 != dimensions0
    state1 = gnome.get_window_state(window=window_id)
    assert state1
    assert atom_net_wm_state_maximized_horz not in state1
    assert atom_net_wm_state_maximized_vert in state1

    # Untile ...
    gnome.window_tile(tile_mode=TileMode.NONE, window=window_id)
    allow_xserver_to_sync()
    position2 = gnome.get_window_position(window=window_id)
    assert position2 == position0
    dimensions2 = gnome.get_window_dimensions(window=window_id)
    assert dimensions2 == dimensions0
    state2 = gnome.get_window_state(window=window_id)
    assert atom_net_wm_state_maximized_horz not in state2
    assert atom_net_wm_state_maximized_vert not in state2

    # Tile right ...
    gnome.window_tile(tile_mode=TileMode.RIGHT, window=window_id)
    allow_xserver_to_sync()
    position3 = gnome.get_window_position(window=window_id)
    assert position3 != position0
    assert position3 != position1
    dimensions3 = gnome.get_window_dimensions(window=window_id)
    assert dimensions3 != dimensions0
    state3 = gnome.get_window_state(window=window_id)
    assert state3
    assert atom_net_wm_state_maximized_horz not in state3
    assert atom_net_wm_state_maximized_vert in state3

    # Untile ...
    gnome.window_tile(tile_mode=TileMode.NONE, window=window_id)
    allow_xserver_to_sync()
    position4 = gnome.get_window_position(window=window_id)
    assert position4 == position0
    dimensions4 = gnome.get_window_dimensions(window=window_id)
    assert dimensions4 == dimensions0
    state4 = gnome.get_window_state(window=window_id)
    assert atom_net_wm_state_maximized_horz not in state4
    assert atom_net_wm_state_maximized_vert not in state4

    # Tile top ...
    gnome.window_tile(tile_mode=TileMode.TOP, window=window_id)
    allow_xserver_to_sync()
    position5 = gnome.get_window_position(window=window_id)
    assert position5 != position0
    assert position5 != position3
    dimensions5 = gnome.get_window_dimensions(window=window_id)
    assert dimensions5 != dimensions0
    state5 = gnome.get_window_state(window=window_id)
    assert state5
    assert atom_net_wm_state_maximized_horz in state5
    assert atom_net_wm_state_maximized_vert in state5
