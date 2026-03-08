#!/usr/bin/env python

"""CLI tests."""

import logging

from shutil import rmtree
from typing import List

import pytest

from click.testing import CliRunner
from _pytest.logging import LogCaptureFixture
from _pytest.tmpdir import TempPathFactory

from xsessionp import __version__, XSessionp
from xsessionp.cli import (
    get_config_dirs,
    close_windows as command_close_windows,
    version as command_version,
    TypingContextObject,
)
from crashvb_logging_utilities import LOGGING_DEFAULT

from .testutils import (
    allow_xserver_to_sync,
    kill_all_xlogo_instances,
    launch_windows,
    temporary_environment_variable,
)

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
        assert path.exists()
    with temporary_environment_variable(
        key="HOME", value=str(tmpdir_home)
    ), temporary_environment_variable(
        key="XSESSIONP_CONFIGDIR", value=str(tmpdir_xsessionp_configdir)
    ):
        with temporary_environment_variable(key="XDG_CONFIG_HOME", value=None):
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


@pytest.mark.xlogo
def test_close_window_empty(cli_runner: CliRunner, xsessionp: XSessionp):
    try:
        window_id0, window_id1 = launch_windows(xsessionp)

        result = cli_runner.invoke(
            cli=command_close_windows,
            obj=TypingContextObject(verbosity=LOGGING_DEFAULT, xsessionp=xsessionp),
        )
        assert result.exit_code == 0
        assert not result.output

        assert xsessionp.get_window_name(window=window_id0)
        assert xsessionp.get_window_name(window=window_id1)
    finally:
        kill_all_xlogo_instances()


@pytest.mark.xlogo
def test_close_window_all(
    caplog: LogCaptureFixture, cli_runner: CliRunner, xsessionp: XSessionp
):
    try:
        window_id0, window_id1 = launch_windows(xsessionp)

        # Workaround: https://github.com/pallets/click/issues/824
        caplog.set_level(100000)

        result = cli_runner.invoke(
            cli=command_close_windows,
            args=["--all"],
            obj=TypingContextObject(verbosity=LOGGING_DEFAULT, xsessionp=xsessionp),
        )
        caplog.set_level(logging.DEBUG)
        assert result.exit_code == 0
        assert not result.output

        allow_xserver_to_sync()
        xsessionp.get_display().flush()
        allow_xserver_to_sync()

        with pytest.raises(RuntimeError):
            xsessionp.get_window_name(window=window_id0)
        with pytest.raises(RuntimeError):
            xsessionp.get_window_name(window=window_id1)
    finally:
        kill_all_xlogo_instances()


def test_version(cli_runner: CliRunner, xsessionp: XSessionp):
    result = cli_runner.invoke(
        cli=command_version,
        obj=TypingContextObject(verbosity=LOGGING_DEFAULT, xsessionp=xsessionp),
    )
    assert result.exit_code == 0
    assert __version__ in result.output
