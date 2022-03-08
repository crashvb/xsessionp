#!/usr/bin/env python

# pylint: disable=redefined-outer-name

"""Utility tests."""

import logging

from shutil import rmtree

from _pytest.tmpdir import TempPathFactory

from xsessionp.utils import run

LOGGER = logging.getLogger(__name__)


def test_run(tmp_path_factory: TempPathFactory):
    """Tests running commands and retrieving output."""
    tmp_path = tmp_path_factory.mktemp(f"{__name__}")
    stdout = run(args=["pwd"], cwd=tmp_path)
    assert str(tmp_path) in stdout
    rmtree(tmp_path, ignore_errors=True)
