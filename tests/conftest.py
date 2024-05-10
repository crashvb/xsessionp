#!/usr/bin/env python

# pylint: disable=redefined-outer-name

"""Configures execution of pytest."""
import os

import pytest

from xsessionp import Gnome, Muffin, XSession, XSessionp

from .testutils import get_xlogo_hints, kill_all_xlogo_instances


def pytest_addoption(parser):
    """pytest add option."""
    parser.addoption(
        "--allow-xlogo-termination",
        action="store_true",
        default=False,
        help="Allow blind termination of xlogo instances. This may impact xlogo instances that are outside the scope "
        "of the executing test(s).",
    )


def pytest_collection_modifyitems(config, items):
    """pytest collection modifier."""

    skip_xlogo = pytest.mark.skip(
        reason="Execution of xlogo tests requires --allow-xlogo-termination option."
    )
    for item in items:
        if "xlogo" in item.keywords and not config.getoption(
            "--allow-xlogo-termination"
        ):
            item.add_marker(skip_xlogo)


def pytest_configure(config):
    """pytest configuration hook."""
    config.addinivalue_line(
        "markers",
        "exclude_window_managers(list): skip tests if using a listed window manager.",
    )
    config.addinivalue_line(
        "markers",
        "require_window_managers(list): skip tests unless using a listed window manager.",
    )
    config.addinivalue_line(
        "markers", "skip_travis(reason): skip tests when executing under travis."
    )
    config.addinivalue_line(
        "markers", "xlogo: allow blind termination of xlogo instances."
    )


@pytest.fixture(autouse=True)
def exclude_window_managers(request, window_manager_name: str):
    """Skips tests if using a given window manager(s)."""
    marker = request.node.get_closest_marker("exclude_window_managers")
    if marker and window_manager_name in marker.args:
        pytest.skip(f"Skipping; window manager '{window_manager_name}' is excluded.")


@pytest.fixture(autouse=True)
def require_window_managers(request, window_manager_name: str):
    """Skips tests unless using a given window manager(s)."""
    marker = request.node.get_closest_marker("require_window_managers")
    if marker and window_manager_name not in marker.args:
        pytest.skip(
            f"Skipping; window manager '{window_manager_name}' is not supported."
        )


@pytest.fixture(autouse=True)
def skip_travis(request):
    """Skips tests when executing under travis."""
    marker = request.node.get_closest_marker("skip_travis")
    if marker and "TRAVIS" in os.environ:
        pytest.skip(f"Skipping test under travis; {marker.args}")


@pytest.fixture
def gnome() -> Gnome:
    """Provides an Gnome instance."""
    return Gnome()


@pytest.fixture
def muffin() -> Muffin:
    """Provides an Muffin instance."""
    return Muffin()


@pytest.fixture()
def window_id(xsessionp: XSessionp) -> int:
    """Provides the window ID of a launched xlogo instance."""
    window_metadata = xsessionp.launch_command(args=["xlogo"])
    try:
        yield xsessionp.guess_window(hints=get_xlogo_hints(), windows=window_metadata)
    finally:
        kill_all_xlogo_instances()


@pytest.fixture()
def window_manager_name(xsessionp: XSessionp) -> str:
    """Provides the name of the window manager."""
    return xsessionp.get_window_manager_name().lower()


@pytest.fixture
def xsession() -> XSession:
    """Provides an XSession instance."""
    return XSession()


@pytest.fixture
def xsessionp(xsession: XSession) -> XSessionp:
    """Provides an XSessionp instance."""
    return XSessionp(xsession=xsession)
