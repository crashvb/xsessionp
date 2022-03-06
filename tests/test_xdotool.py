#!/usr/bin/env python

# pylint: disable=redefined-outer-name

"""xdotool tests."""

import logging
import os

from random import randint
from subprocess import CalledProcessError
from time import sleep

import pytest

from xsessionp import (
    get_desktop,
    get_desktop_for_window,
    get_num_desktops,
    getactivewindow,
    getdisplaygeometry,
    getwindowfocus,
    getwindowgeometry,
    getwindowname,
    getwindowpid,
    guess_window,
    launch_command,
    search,
    set_desktop_for_window,
    windowactivate,
    windowclose,
    windowfocus,
    windowkill,
    windowmap,
    windowminimize,
    windowmove,
    windowsize,
    windowraise,
    windowunmap,
    XSession,
)

from .testutils import kill_all_xclock_instances, QUASI_DETERMINISTIC_DELAY


LOGGER = logging.getLogger(__name__)


@pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
def test_get_desktop():
    """Tests that the current desktop can be retrieved."""
    assert get_desktop() > -1


@pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_get_desktop_for_window(window_id: int):
    """Tests that desktop assigned to a window can be retrieved."""
    assert get_desktop_for_window(window_id=window_id) > -1


@pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
def test_get_num_desktop():
    """Tests that the number of desktops can be retrieved."""
    assert get_num_desktops()


@pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_getactivewindow(window_id: int):
    """Tests that the active window can be retrieved.."""
    windowactivate(sync=True, window_id=window_id)
    assert getactivewindow()


def test_getdisplaygeometry():
    """Tests that geometry can be retrieved for a display"""
    match = getdisplaygeometry()
    assert match.group("height")
    assert match.group("width")


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_getwindowfocus(window_id: int):
    """Tests that the focused window can be retrieved.."""
    windowfocus(sync=True, window_id=window_id)
    assert getwindowfocus()


@pytest.mark.xclock
def test_getwindowgeometry(window_id: int):
    """Tests that geometry can be retrieved for a window."""
    match = getwindowgeometry(window_id=window_id)
    assert match.group("geometry")
    assert match.group("position")
    assert match.group("screen")
    assert match.group("window")


@pytest.mark.xclock
def test_getwindowname(window_id: int):
    """Tests that the name can be retrieved for a window."""
    assert getwindowname(window_id=window_id)


@pytest.mark.xclock
def test_getwindowpid(window_id: int):
    """Tests that a pid can be retrieved for a window."""
    assert getwindowpid(window_id=window_id)


@pytest.mark.xclock
def test_search(window_id: int):
    """Tests that a search can be performed to find a window."""
    assert window_id  # Make pylint happy
    assert search(
        args=[
            "--class",
            "--classname",
            "--maxdepth=2",
            "--name",
            "--onlyvisible",
            "^xclock$",
        ]
    )


# TODO: How to test selectwindow()?!?


@pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_set_desktop_for_window(window_id: int):
    """Tests that a desktop can be assigned to a window."""
    num_desktops = get_num_desktops()
    if int(num_desktops) < 2:
        pytest.skip(f"Number of desktops {num_desktops} is less than required value: 2")
        return

    def set_desktop(*, desktop: int):
        set_desktop_for_window(desktop=desktop, window_id=window_id)
        sleep(
            QUASI_DETERMINISTIC_DELAY
        )  # There is no "sync" for set_desktop_for_window =/ ...
        assert get_desktop_for_window(window_id=window_id) == desktop

    # After the next command window_id will be on desktop=0, but was it before (by default)?
    set_desktop(desktop=0)

    # Since we know it changed, we can be confident that xdotool moved it ...
    set_desktop(desktop=1)


# TODO: def test_set_window():


@pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_windowactivate(xsession: XSession):
    """Tests that a window can be activated."""
    try:

        def make_active(*, window_id: int):
            windowactivate(sync=True, window_id=window_id)
            assert getactivewindow() == window_id

        window_metadata0 = launch_command(args=["xclock"], xsession=xsession)
        window_id0 = guess_window(
            title_hint="^xclock$", windows=window_metadata0, xsession=xsession
        )
        assert window_id0

        # After the next command window_id0 will be active, but was it before (by default)?
        make_active(window_id=window_id0)

        window_metadata1 = launch_command(args=["xclock"], xsession=xsession)
        window_id1 = guess_window(
            title_hint="^xclock$", windows=window_metadata1, xsession=xsession
        )
        assert window_id1

        # After the next command window_id1 will be active, but was it before (by default)?
        make_active(window_id=window_id1)

        # Since no new windows were opened, we can be confident that it's xdotool changing focus,
        # and not the display manager ...
        make_active(window_id=window_id0)

        # One more time, for good measure ...
        make_active(window_id=window_id1)
    finally:
        kill_all_xclock_instances()


@pytest.mark.xclock
def test_windowclose(window_id: int):
    """Tests that a window can be closed."""
    windowclose(window_id=window_id)
    with pytest.raises(CalledProcessError) as exc_info:
        getwindowname(window_id=window_id)
    assert "returned non-zero exit status" in str(exc_info.value)


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_windowfocus(xsession: XSession):
    """Tests that a window can be focused."""
    try:

        def make_focused(*, window_id: int):
            windowfocus(sync=True, window_id=window_id)
            assert getwindowfocus() == window_id

        window_metadata0 = launch_command(args=["xclock"], xsession=xsession)
        window_id0 = guess_window(
            title_hint="^xclock$", windows=window_metadata0, xsession=xsession
        )
        assert window_id0

        # After the next command window_id0 will be active, but was it before (by default)?
        make_focused(window_id=window_id0)

        window_metadata1 = launch_command(args=["xclock"], xsession=xsession)
        window_id1 = guess_window(
            title_hint="^xclock$", windows=window_metadata1, xsession=xsession
        )
        assert window_id1

        # After the next command window_id1 will be active, but was it before (by default)?
        make_focused(window_id=window_id1)

        # Since no new windows were opened, we can be confident that it's xdotool changing focus,
        # and not the display manager ...
        make_focused(window_id=window_id0)

        # One more time, for good measure ...
        make_focused(window_id=window_id1)
    finally:
        kill_all_xclock_instances()


@pytest.mark.xclock
def test_windowkill(window_id: int):
    """Tests that a window can be killed."""
    windowkill(window_id=window_id)
    with pytest.raises(CalledProcessError) as exc_info:
        getwindowname(window_id=window_id)
    assert "returned non-zero exit status" in str(exc_info.value)


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_windowmap_windowunmap(window_id: int):
    """Tests that a window can be mapped and unmapped."""
    search_args = ["--maxdepth=2", "--name", "--onlyvisible", "xclock"]

    # Should be visible
    assert int(search(allow_empty=True, args=search_args) or -1) == window_id

    windowunmap(sync=True, window_id=window_id)

    # Should not be visible
    assert int(search(allow_empty=True, args=search_args) or -1) == -1

    windowmap(sync=True, window_id=window_id)

    # Should be visible
    assert int(search(allow_empty=True, args=search_args) or -1) == window_id


@pytest.mark.skip("Test scenario refinement needed.")
# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_windowminimize(window_id: int):
    """Tests that a window can be minimized."""
    search_args = ["--maxdepth=2", "--name", "--onlyvisible", "xclock"]

    # Should be visible
    win_id = int(search(allow_empty=True, args=search_args) or -1)
    assert win_id == window_id

    windowminimize(sync=True, window_id=window_id)

    # TODO: Apparently, this is not how display managers work?!?
    #       Do we need to check under _NET_WM_something???
    # # Should not be visible
    # win_id = int(search(allow_empty=True, args=search_args) or -1)
    # assert win_id == -1


@pytest.mark.xclock
def test_windowmove(window_id: int):
    """Tests that a window can be moved."""
    (position_x, position_y) = (
        getwindowgeometry(window_id=window_id).group("position").split(",")
    )
    delta_x = randint(10, 50)
    delta_y = randint(10, 50)
    position_new = f"{int(position_x) + delta_x},{int(position_y) + delta_y}"

    windowmove(position=position_new, sync=True, window_id=window_id)
    # TODO: Apparently, there is something going on w/ display managers, as this doesn't work ?!?
    #       ... fallback on, did it move "somewhere" ...
    # assert get_window_geometry(window_id=window_id).group("position") == position_new
    assert (
        getwindowgeometry(window_id=window_id).group("position")
        != f"{position_x},{position_y}"
    )


@pytest.mark.skip("Test scenario refinement needed.")
# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_windowraise(xsession: XSession):
    """Tests that a window can be raised."""
    try:

        def make_raised(*, window_id: int):
            windowraise(window_id=window_id)
            # TODO: Apparently, this is not how display managers work?!?
            #       Is it focused, active, or what?
            # assert getwindowfocus() == window_id

        window_metadata0 = launch_command(args=["xclock"], xsession=xsession)
        window_id0 = guess_window(
            title_hint="^xclock$", windows=window_metadata0, xsession=xsession
        )
        assert window_id0

        # After the next command window_id0 will be focused, but was it before (by default)?
        make_raised(window_id=window_id0)

        window_metadata1 = launch_command(args=["xclock"], xsession=xsession)
        window_id1 = guess_window(
            title_hint="^xclock$", windows=window_metadata1, xsession=xsession
        )
        assert window_id1

        # After the next command window_id1 will be focused, but was it before (by default)?
        make_raised(window_id=window_id1)

        # Since no new windows were opened, we can be confident that it's xdotool changing focus,
        # and not the display manager ...
        make_raised(window_id=window_id0)

        # One more time, for good measure ...
        make_raised(window_id=window_id1)
    finally:
        kill_all_xclock_instances()


# TODO: def test_windowreparent():


@pytest.mark.xclock
def test_windowsize(window_id: int):
    """Tests that a window can be sized."""
    (width, height) = (
        getwindowgeometry(window_id=window_id).group("geometry").split("x")
    )
    delta_x = randint(10, 50)
    delta_y = randint(10, 50)
    geometry_new = f"{int(width) + delta_x}x{int(height) + delta_y}"

    windowsize(geometry=geometry_new, sync=True, window_id=window_id)
    assert getwindowgeometry(window_id=window_id).group("geometry") == geometry_new
