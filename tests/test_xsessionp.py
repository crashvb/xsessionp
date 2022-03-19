#!/usr/bin/env python

"""xsessionp tests."""

import logging
import os

from pathlib import Path
from time import time

import pytest
from _pytest.logging import LogCaptureFixture

from xsessionp import Muffin, NET_WM_STATE_TILED, XSessionp

from .testutils import (
    allow_xserver_to_sync,
    get_xclock_hints,
    kill_all_xclock_instances,
)

LOGGER = logging.getLogger(__name__)


@pytest.mark.skipif(
    "TRAVIS" in os.environ,
    reason="xvfb failure: Unable to intern atom: _XSESSIONP_METADATA",
)
@pytest.mark.xclock
def test_find_xsessionp_windows(window_id: int, xsessionp: XSessionp):
    """Tests that a xsessionp windows can be located."""
    xsessionp.set_window_xsessionp_metadata(data=f"data:{time()}", window=window_id)

    windows = xsessionp.find_xsessionp_windows()
    assert windows
    assert any(
        (
            xsessionp.get_window_name(check=False, window=window) == "xclock"
            for window in windows
        )
    )


@pytest.mark.skipif(
    "TRAVIS" in os.environ,
    reason="xvfb failure: Unable to intern atom: _NET_SUPPORTING_WM_CHECK",
)
def test_get_window_manager_name(xsessionp: XSessionp):
    """Tests that the name of the window manager can be retrieved."""
    assert xsessionp.get_window_manager_name()


def test_generate_name(xsessionp: XSessionp):
    """Tests that the name of the window manager can be retrieved."""
    assert xsessionp.generate_name(index=123, path=Path(f"/{time()}"))


def test_get_window_properties_xsp(xsessionp: XSessionp):
    """Tests that a list of valid properties can be retrieved."""
    properties = xsessionp.get_window_properties_xsp()
    assert properties
    assert "pid" in properties
    assert all(x not in properties for x in ["id", "xname"])


@pytest.mark.xclock
def test_get_window_property_xsp(window_id: int, xsessionp: XSessionp):
    """Tests that a property can be retrieved from a windows by name."""
    name = xsessionp.get_window_property_xsp(name="name", window=window_id)
    assert name
    assert name == "xclock"

    foobar = xsessionp.get_window_property_xsp(
        check=False, name="foobar", window=window_id
    )
    assert foobar is None


def test_inherit_global(xsessionp: XSessionp):
    """Tests that global values can be inherited."""
    config = {
        "global0": f"global:{time()}",
        "global1": f"global:{time()}",
        "windows": [{"global2": f"global:{time()}"}],
    }
    window = {"global1": f"notglobal:{time()}", "local0": f"local:{time()}"}
    result = xsessionp.inherit_globals(config=config, window=window)
    assert result
    assert all((key in result for key in ["global0", "global1"]))
    assert "global2" not in result
    assert result["global0"] == config["global0"]
    assert result["global1"] == window["global1"]
    assert result["local0"] == window["local0"]


def test_key_enabled(xsessionp: XSessionp):
    """Tests that key overriding works."""
    window = {
        "key0": f"key0:{time()}",
        "key1": f"key1:{time()}",
        "no_key1": True,
        "no_key2": True,
    }
    assert xsessionp.key_enabled(key="key0", window=window)
    assert not xsessionp.key_enabled(key="key1", window=window)
    assert not xsessionp.key_enabled(key="key2", window=window)


@pytest.mark.skipif(
    "TRAVIS" in os.environ,
    reason="xvfb failure: Unable to intern atom: _XSESSIONP_METADATA",
)
@pytest.mark.xclock
def test_get_set_window_xsessionp_metadata(window_id: int, xsessionp: XSessionp):
    """Tests that a xsessionp metadata can be retrieved for a window."""
    xsessionp_metadata = xsessionp.get_window_xsessionp_metadata(window=window_id)
    assert not xsessionp_metadata

    data = f"value: {time}"
    xsessionp.set_window_xsessionp_metadata(data=data, window=window_id)
    xsessionp_metadata = xsessionp.get_window_xsessionp_metadata(window=window_id)
    assert xsessionp_metadata == data.encode("latin-1")


@pytest.mark.xclock
def test_launch_command_guess_window(xsessionp: XSessionp):
    """Tests that we can guess for a window (at least sometimes ...)."""
    try:
        potential_windows = xsessionp.launch_command(args=["xclock"])
        window_id = xsessionp.guess_window(
            hints=get_xclock_hints(), windows=potential_windows
        )
        assert window_id
    finally:
        kill_all_xclock_instances()


# TODO: def test_load(xsessionp: XSessionp):


# TODO: def test_position_window(xsessionp: XSessionp):


@pytest.mark.xclock
def test_sanitize_config(caplog: LogCaptureFixture, xsessionp: XSessionp):
    """Tests that configurations can be sanitized."""
    caplog.clear()
    caplog.set_level(logging.DEBUG)

    config = {
        "focus": f"focus:{time()}",
        "name": f"name:{time()}",
        "foo": f"bar{time()}",
        "windows": [{"id": f"id:{time()}"}],
    }
    result = xsessionp.sanitize_config(config=config)
    assert all((key not in result for key in ["focus", "name"]))
    assert result["foo"] == config["foo"]
    assert 'Global attribute "focus" is invalid' in caplog.text
    assert 'Global attribute "name" is invalid' in caplog.text
    assert 'Reserved attribute "id" defined by user' in caplog.text


@pytest.mark.skipif(
    "TRAVIS" in os.environ,
    reason="xvfb failure: Unable to intern atom: _NET_ACTIVE_WINDOW",
)
@pytest.mark.xclock
def test_window_tile_muffin(muffin: Muffin, window_id: int, xsessionp: XSessionp):
    # pylint: disable=too-many-locals,too-many-statements
    """Tests that a window can be tiled."""

    window_manager = xsessionp.get_window_manager_name().lower()
    if "muffin" not in window_manager:
        pytest.skip("Test requires window manager: muffin")

    atom_net_wm_state_tiled = xsessionp.get_atom(name=NET_WM_STATE_TILED)

    # TODO: Why is set_window_focus() in _send_Keys failing sometimes?
    xsessionp.set_window_active(window=window_id)

    # Verify untiled ...
    position0 = xsessionp.get_window_position(window=window_id)
    assert position0
    dimensions0 = xsessionp.get_window_dimensions(window=window_id)
    assert dimensions0
    frame_extends0 = xsessionp.get_window_frame_extents(window=window_id)
    assert frame_extends0
    tile_info0 = muffin.get_window_tile_info(check=False, window=window_id)
    assert not tile_info0
    state0 = xsessionp.get_window_state(window=window_id)
    assert not state0

    # Tile left bottom ...
    xsessionp.window_tile(tile_mode="left_bottom", tile_type="tiled", window=window_id)
    allow_xserver_to_sync()
    position1 = xsessionp.get_window_position(window=window_id)
    assert position1 != position0
    dimensions1 = xsessionp.get_window_dimensions(window=window_id)
    assert dimensions1 != dimensions0
    frame_extends1 = xsessionp.get_window_frame_extents(window=window_id)
    assert frame_extends1 != frame_extends0
    tile_info1 = muffin.get_window_tile_info(check=False, window=window_id)
    assert tile_info1
    state1 = xsessionp.get_window_state(window=window_id)
    assert state1
    assert atom_net_wm_state_tiled in state1

    # Untile ...
    xsessionp.window_tile(tile_mode="none", tile_type="tiled", window=window_id)
    allow_xserver_to_sync()
    position2 = xsessionp.get_window_position(window=window_id)
    assert position2 == position0
    dimensions2 = xsessionp.get_window_dimensions(window=window_id)
    assert dimensions2 == dimensions0
    frame_extends2 = xsessionp.get_window_frame_extents(window=window_id)
    assert frame_extends2 == frame_extends0
    tile_info2 = muffin.get_window_tile_info(check=False, window=window_id)
    assert not tile_info2
    state2 = xsessionp.get_window_state(window=window_id)
    assert atom_net_wm_state_tiled not in state2

    # Tile right top ...
    xsessionp.window_tile(tile_mode="right_top", tile_type="tiled", window=window_id)
    allow_xserver_to_sync()
    position3 = xsessionp.get_window_position(window=window_id)
    assert position3 != position0
    assert position3 != position1
    dimensions3 = xsessionp.get_window_dimensions(window=window_id)
    assert dimensions3 != dimensions0
    frame_extends3 = xsessionp.get_window_frame_extents(window=window_id)
    assert frame_extends3 != frame_extends0
    assert frame_extends3 != frame_extends1
    tile_info3 = muffin.get_window_tile_info(check=False, window=window_id)
    assert tile_info3
    assert tile_info3 != tile_info1
    state3 = xsessionp.get_window_state(window=window_id)
    assert state3
    assert atom_net_wm_state_tiled in state3
