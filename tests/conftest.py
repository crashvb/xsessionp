#!/usr/bin/env python

# pylint: disable=redefined-outer-name

"""Configures execution of pytest."""

import pytest

from xsessionp import Muffin, XSession, XSessionp

from .testutils import get_xclock_hints, kill_all_xclock_instances


def pytest_addoption(parser):
    """pytest add option."""
    parser.addoption(
        "--allow-xclock-termination",
        action="store_true",
        default=False,
        help="Allow blind termination of xclock instances. This may impact xclock instances that are outside the scope "
        "of the executing test(s).",
    )


def pytest_collection_modifyitems(config, items):
    """pytest collection modifier."""

    skip_xclock = pytest.mark.skip(
        reason="Execution of xclock tests requires --allow-xclock-termination option."
    )
    for item in items:
        if "xclock" in item.keywords and not config.getoption(
            "--allow-xclock-termination"
        ):
            item.add_marker(skip_xclock)


def pytest_configure(config):
    """pytest configuration hook."""
    config.addinivalue_line(
        "markers", "xclock: allow blind termination of xclock instances."
    )


@pytest.fixture
def muffin() -> Muffin:
    """Provides an Muffin instance."""
    return Muffin()


@pytest.fixture()
def window_id(xsessionp: XSessionp) -> int:
    """Provides the window ID of a launched xclock instance."""
    window_metadata = xsessionp.launch_command(args=["xclock"])
    try:
        yield xsessionp.guess_window(hints=get_xclock_hints(), windows=window_metadata)
    finally:
        kill_all_xclock_instances()


@pytest.fixture
def xsession() -> XSession:
    """Provides an XSession instance."""
    return XSession()


@pytest.fixture
def xsessionp(xsession: XSession) -> XSessionp:
    """Provides an XSessionp instance."""
    return XSessionp(xsession=xsession)
