#!/usr/bin/env python

"""xsessionp tests."""

import logging
import os
import subprocess

from pathlib import Path
from time import time

import pytest
from _pytest.logging import LogCaptureFixture

from xsessionp import XSessionp, XSESSIONP_ENV_NAME

from .testutils import (
    get_xlogo_hints,
    kill_all_xlogo_instances,
    WINDOW_MANAGER_FLUXBOX,
)

LOGGER = logging.getLogger(__name__)


@pytest.mark.xlogo
def test_find_xsessionp_windows(window_id: int, xsessionp: XSessionp):
    """Tests that a xsessionp windows can be located."""
    xsessionp.set_window_xsessionp_metadata(data=f"data:{time()}", window=window_id)

    windows = xsessionp.find_xsessionp_windows()
    assert windows
    assert any(
        (
            xsessionp.get_window_name(check=False, window=window) == "xlogo"
            for window in windows
        )
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


@pytest.mark.xlogo
def test_get_window_property_xsp(window_id: int, xsessionp: XSessionp):
    """Tests that a property can be retrieved from a windows by name."""
    name = xsessionp.get_window_property_xsp(name="name", window=window_id)
    assert name
    assert name == "xlogo"

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


@pytest.mark.xlogo
def test_get_set_window_xsessionp_metadata(window_id: int, xsessionp: XSessionp):
    """Tests that a xsessionp metadata can be retrieved for a window."""
    xsessionp_metadata = xsessionp.get_window_xsessionp_metadata(window=window_id)
    assert not xsessionp_metadata

    data = f"value: {time}"
    xsessionp.set_window_xsessionp_metadata(data=data, window=window_id)
    xsessionp_metadata = xsessionp.get_window_xsessionp_metadata(window=window_id)
    assert xsessionp_metadata == data.encode("latin-1")


@pytest.mark.xlogo
def test_launch_command_guess_window(xsessionp: XSessionp):
    """Tests that we can guess for a window (at least sometimes ...)."""
    try:
        pid, potential_windows = xsessionp.launch_command(args=["xlogo"])
        assert isinstance(pid, int)
        assert pid > 0
        assert Path(f"/proc/{pid}/comm").read_text().strip() == "xlogo"
        window_id = xsessionp.guess_window_delta(
            hints=get_xlogo_hints(), windows=potential_windows
        )
        assert window_id
    finally:
        kill_all_xlogo_instances()


@pytest.mark.exclude_window_managers(WINDOW_MANAGER_FLUXBOX)
@pytest.mark.xlogo
@pytest.mark.parametrize("command", [["xlogo"], ["/bin/sh", "-c", "xlogo & wait"]])
def test_guess_window_pid(xsessionp: XSessionp, command):
    """Tests identifying an xlogo window owned by the command or its child."""
    try:
        env = os.environ.copy()
        env[XSESSIONP_ENV_NAME] = f"{__name__}:{time()}"
        pid, _ = xsessionp.launch_command(args=command, env=env)
        assert isinstance(pid, int)
        assert pid > 0

        window_id = xsessionp.guess_window_pid(pid=pid)
        assert window_id
        assert xsessionp.get_window_name(window=window_id) == "xlogo"
    finally:
        kill_all_xlogo_instances()


@pytest.mark.exclude_window_managers(WINDOW_MANAGER_FLUXBOX)
def test_guess_window_pid_process_error(xsessionp: XSessionp):
    """Tests that an exited process leaves detection to the delta fallback."""
    with subprocess.Popen(["/bin/true"]) as process:
        process.wait()
    assert xsessionp.guess_window_pid(pid=process.pid) is None


# TODO: def test_load(xsessionp: XSessionp):


# TODO: def test_position_window(xsessionp: XSessionp):


@pytest.mark.xlogo
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
