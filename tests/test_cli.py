#!/usr/bin/env python

"""CLI tests."""

import logging

from shutil import rmtree

from _pytest.tmpdir import TempPathFactory

from xsessionp.cli import get_config_dirs

from .testutils import temporary_environment_variable

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
