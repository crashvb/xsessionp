#!/usr/bin/env python

# pylint: disable=redefined-outer-name

"""xsessionp tests."""

import logging

from shutil import rmtree

import pytest

from _pytest.tmpdir import TempPathFactory

from xsessionp import (
    get_config_dirs,
    guess_window,
    launch_command,
    XSession,
)

from .testutils import kill_all_xclock_instances, temporary_environment_variable

LOGGER = logging.getLogger(__name__)


def test_get_config_dirs(tmp_path_factory: TempPathFactory):
    """Tests configuration directory retrieval."""
    tmpdir_home = tmp_path_factory.mktemp(f"{__name__}")
    tmpdir_default0 = tmpdir_home.joinpath(".config/xsessionp")
    tmpdir_default1 = tmpdir_home.joinpath(".xsessionp")
    tmpdir_xdg_config_home = tmpdir_home.joinpath("xdg_config_home/xsessionp")
    tmpdir_xsessionp_configdir = tmpdir_home.joinpath("xsessionp_configdir")
    for path in [
        tmpdir_default0,
        tmpdir_default1,
        tmpdir_xdg_config_home,
        tmpdir_xsessionp_configdir,
    ]:
        path.mkdir(parents=True)
    with temporary_environment_variable(
        key="HOME", value=str(tmpdir_home)
    ), temporary_environment_variable(
        key="XSESSIONP_CONFIGDIR", value=str(tmpdir_xsessionp_configdir)
    ):
        config_dirs = list(get_config_dirs())
        assert tmpdir_default0 in config_dirs
        assert tmpdir_default1 in config_dirs
        assert tmpdir_xdg_config_home not in config_dirs
        assert tmpdir_xsessionp_configdir in config_dirs
        with temporary_environment_variable(
            key="XDG_CONFIG_HOME", value=str(tmpdir_xdg_config_home.parent)
        ):
            config_dirs = list(get_config_dirs())
            assert tmpdir_default0 not in config_dirs
            assert tmpdir_default1 in config_dirs
            assert tmpdir_xdg_config_home in config_dirs
            assert tmpdir_xsessionp_configdir in config_dirs
    rmtree(tmpdir_home, ignore_errors=True)


@pytest.mark.xclock
def test_guess_window(xsession: XSession):
    """Tests that we can guess for a window (at least sometimes ...)."""
    try:
        potential_windows = launch_command(args=["xclock"], xsession=xsession)
        window_id = guess_window(
            title_hint="^xclock$", windows=potential_windows, xsession=xsession
        )
        assert window_id
    finally:
        kill_all_xclock_instances()


# TODO: def test_inherit_globals():


@pytest.mark.xclock
def test_launch_command(xsession: XSession):
    """Tests that commands can be launched."""
    try:
        assert launch_command(args=["xclock"], xsession=xsession)
    finally:
        kill_all_xclock_instances()
