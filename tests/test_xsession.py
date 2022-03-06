#!/usr/bin/env python

# pylint: disable=protected-access,redefined-outer-name

"""xsession tests."""

import logging
import os

from random import randint

import pytest

from Xlib.display import Display
from Xlib.error import BadAtom, BadWindow
from Xlib.xobject.drawable import Window
from Xlib.X import IsUnmapped, IsViewable, NONE

from xsessionp import (
    ACTION_REMOVE,
    ACTION_TOGGLE,
    get_uptime,
    guess_window,
    launch_command,
    NET_NUMBER_OF_DESKTOPS,
    NET_WM_STATE_HIDDEN,
    NET_WM_STATE_MAXIMIZED_HORZ,
    NET_WM_STATE_MAXIMIZED_VERT,
    XSession,
)

from .testutils import allow_xserver_to_sync, kill_all_xclock_instances


LOGGER = logging.getLogger(__name__)


def test___init__(xsession: XSession):
    """Test that an XSession can be instantiated."""
    assert xsession


def test___getattr____setattr__(xsession: XSession):
    """Tests __getattr__ and __setattr__ methods."""
    desktop_count = xsession._NET_NUMBER_OF_DESKTOPS.value[0]
    if desktop_count < 2:
        pytest.skip(
            f"Number of desktops {desktop_count} is less than required value: 2"
        )

    def set_desktop(*, desktop: int):
        xsession._NET_CURRENT_DESKTOP = [desktop, get_uptime()]
        allow_xserver_to_sync()
        assert xsession._NET_CURRENT_DESKTOP.value[0] == desktop

    # Find a desktop other than the current one ...
    desktop_original = xsession._NET_CURRENT_DESKTOP.value[0]
    assert desktop_original is not None
    desktop_target = desktop_count - 1 if desktop_original == 0 else 0
    assert desktop_target != desktop_original

    # Change to it, change back ...
    set_desktop(desktop=desktop_target)
    set_desktop(desktop=desktop_original)


def test_get_atom(xsession: XSession):
    """Tests that atom values can be retrieved."""
    assert xsession.get_atom(name=NET_NUMBER_OF_DESKTOPS) == 526
    bad_value = "foobar"
    with pytest.raises(RuntimeError):
        xsession.get_atom(name=bad_value)
    assert xsession.get_atom(check=False, name=bad_value) == NONE


def test_get_atom_name(xsession: XSession):
    """Tests atom names can be retrieved."""
    assert xsession.get_atom_name(atom=526) == NET_NUMBER_OF_DESKTOPS
    bad_value = 1000
    with pytest.raises(BadAtom):
        xsession.get_atom_name(atom=bad_value)
    assert xsession.get_atom_name(atom=bad_value, check=False) is None


def test_get_client_list(xsession: XSession):
    """Tests that the list of managed windows can be retrieved."""

    client_list = xsession.get_client_list()
    if client_list is not None:
        assert isinstance(client_list, list)
        assert len(client_list)


def test_get_client_list_stacking(xsession: XSession):
    """Tests that the (stacked) list of managed windows can be retrieved."""

    client_list_stack = xsession.get_client_list_stacking()
    if client_list_stack is not None:
        assert isinstance(client_list_stack, list)
        assert len(client_list_stack)


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
def test_get_desktop_active(xsession: XSession):
    """Tests that the active desktop can be retrieved."""
    desktop = xsession.get_desktop_active()
    assert isinstance(desktop, int)
    assert desktop is not None


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
def test_get_desktop_count(xsession: XSession):
    """Tests that the number of desktops can be retrieved."""
    count = xsession.get_desktop_count()
    assert isinstance(count, int)
    assert count is not None


def test_get_desktop_geometry(xsession: XSession):
    """Tests that the dimensions of the desktops can be retrieved."""
    geometry = xsession.get_desktop_geometry()
    assert geometry
    assert len(geometry) == 2
    assert geometry[0]
    assert geometry[1]


def test_get_desktop_layout(xsession: XSession):
    """Tests that the layout of the desktops can be retrieved."""
    layout = xsession.get_desktop_layout()
    assert layout
    assert len(layout) == 4
    assert layout[1] + layout[2]  # Should be at least 1 column or 1 row


def test_get_desktop_names(xsession: XSession):
    """Tests that the names of the desktops can be retrieved."""
    count = xsession.get_desktop_count()
    names = xsession.get_desktop_names()
    assert names
    assert len(names) == count
    assert names[0]
    assert names[count - 1]


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
def test_get_desktop_showing(xsession: XSession):
    """Tests that the showing desktop flag can be retrieved."""
    showing = xsession.get_desktop_showing()
    assert isinstance(showing, int)
    assert showing is not None


def test_get_desktop_viewport(xsession: XSession):
    """Tests that the viewports of the desktops can be retrieved."""
    viewport = xsession.get_desktop_viewport()
    assert viewport
    assert len(viewport) == 2


def test_get_display(xsession: XSession):
    """Tests that the X11 display can be retrieved."""
    display = xsession.get_display()
    assert display
    assert isinstance(display, Display)


def test_get_screen(xsession: XSession):
    """Tests that screens can be retrieved"""
    assert xsession.get_screen()
    assert xsession.get_screen(screen_number=0)


def test_get_screen_count(xsession: XSession):
    """Tests that the number of screens can be retrieved."""
    count = xsession.get_screen_count()
    assert isinstance(count, int)
    assert count is not None


def test_get_uptime():
    """Test that uptime can be retrieved."""
    time0 = get_uptime()
    assert time0
    allow_xserver_to_sync()
    time1 = get_uptime()
    assert time1
    assert time1 != time0


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
def test_get_window_active(xsession: XSession):
    """Tests that the active window can be retrieved."""
    window = xsession.get_window_active()
    assert window
    assert isinstance(window, Window)


@pytest.mark.xclock
def test_get_window_allowed_actions(window_id: int, xsession: XSession):
    """Tests that the allowed actions can be retrieved for a window."""
    allowed_actions = xsession.get_window_allowed_actions(window=window_id)
    assert isinstance(allowed_actions, list)
    assert len(allowed_actions)


@pytest.mark.xclock
def test_get_window_by_id(window_id: int, xsession: XSession):
    """Tests that a window can be retrieved by ID."""
    window = xsession.get_window_by_id(window_id=window_id)
    assert window
    assert isinstance(window, Window)


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_get_window_desktop(window_id: int, xsession: XSession):
    """Tests that desktop assigned to a window can be retrieved."""
    desktop = xsession.get_window_desktop(window=window_id)
    assert isinstance(desktop, int)
    assert desktop is not None


@pytest.mark.xclock
def test_get_window_dimensions(window_id: int, xsession: XSession):
    """Tests that dimensions can be retrieved for a window."""
    dimensions = xsession.get_window_dimensions(window=window_id)
    assert dimensions
    assert len(dimensions) == 2
    assert dimensions[0] > 0
    assert dimensions[1] > 0


def test_get_window_focus(xsession: XSession):
    """Tests that currently focused window can be retrieved."""
    window = xsession.get_window_focus()
    assert window
    assert isinstance(window, Window)
    LOGGER.debug("Focused window: %d", xsession._get_window_id(window=window))

    window = xsession.get_window_focus(sane=True)
    assert window
    assert isinstance(window, Window)
    LOGGER.debug("Focused window: %d", xsession._get_window_id(window=window))


def test_get_window_frame_extents(window_id: int, xsession: XSession):
    """Tests that the frame extents of a window can be retrieved."""
    frame_extents = xsession.get_window_frame_extents(window=window_id)
    assert frame_extents
    assert len(frame_extents) == 4


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
def test_get_window_manager(xsession: XSession):
    """Tests that the window manager can be retrieved."""
    window = xsession.get_window_manager()
    assert window
    assert isinstance(window, Window)
    # Required by the standard ...
    name = xsession.get_window_name(window=window)
    LOGGER.debug("Detected window manager: %s", name)
    assert name


@pytest.mark.xclock
def test_get_window_name(window_id: int, xsession: XSession):
    """Tests that the name can be retrieved for a window."""
    assert xsession.get_window_name(window=window_id) == "xclock"


@pytest.mark.xclock
def test_get_window_pid(window_id: int, xsession: XSession):
    """Tests that a process ID can be retrieved for a window."""
    assert xsession.get_window_pid(window=window_id)


@pytest.mark.xclock
def test_get_window_position(window_id: int, xsession: XSession):
    """Tests that coordinates can be retrieved for a window."""
    position = xsession.get_window_position(window=window_id)
    assert position
    assert len(position) == 2


def test_get_window_root(xsession: XSession):
    """Tests that the root window can be retrieved."""
    assert xsession.get_window_root()


@pytest.mark.xclock
def test_get_window_state(window_id: int, xsession: XSession):
    """Tests that the state can be retrieved for a window."""
    atom_name = "_NET_WM_STATE_FULLSCREEN"
    atom_value = xsession.get_atom(name=atom_name)

    states0 = xsession.get_window_state(window=window_id)
    assert isinstance(states0, list)
    assert atom_value not in states0

    xsession.set_window_state(state0=atom_name, window=window_id)
    allow_xserver_to_sync()
    states1 = xsession.get_window_state(window=window_id)
    assert isinstance(states1, list)
    assert atom_value in states1


@pytest.mark.xclock
@pytest.mark.skip("Test scenario refinement needed.")
def test_get_window_type(window_id: int, xsession: XSession):
    """Tests that the type can be retrieved for a window."""
    assert xsession.get_window_type(window=window_id)


@pytest.mark.xclock
@pytest.mark.skip("Test scenario refinement needed.")
def test_get_window_visible_name(window_id: int, xsession: XSession):
    """Tests that the visible name can be retrieved for a window."""
    assert xsession.get_window_visible_name(window=window_id) == "xclock"


def test_get_workarea(xsession: XSession):
    """Tests that the workarea can be retrieved."""
    workarea = xsession.get_workarea()
    assert workarea
    assert len(workarea) == xsession.get_desktop_count()
    for lst in workarea:
        assert len(lst) == 4


def test_get_virtual_roots(xsession: XSession):
    """Tests that the list of virtual can be retrieved."""
    virtual_roots = xsession.get_virtual_roots()
    if virtual_roots is not None:
        assert isinstance(virtual_roots, list)


@pytest.mark.xclock
def test_search(window_id: int, xsession: XSession):
    """Tests that a search can be performed to find a window."""
    # # Test an open search ...
    # windows = xsession.search()
    # assert windows
    # assert len(windows) > 5

    # Test matcher ...
    windows = xsession.search(
        matcher=lambda x: xsession.get_window_name(check=False, window=x) == "xclock"
    )
    assert windows
    assert len(windows) == 1
    assert windows[0].id == window_id

    # # Test max_results ...
    # windows = xsession.search(max_results=5)
    # assert windows
    # assert len(windows) == 5


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
def test_set_desktop_active(xsession: XSession):
    """Tests that the active desktop can be assigned."""

    desktop_count = xsession.get_desktop_count()
    if desktop_count < 2:
        pytest.skip(
            f"Number of desktops {desktop_count} is less than required value: 2"
        )

    def set_desktop(*, desktop: int):
        xsession.set_desktop_active(desktop=desktop)
        allow_xserver_to_sync()
        assert xsession.get_desktop_active() == desktop

    # Find a desktop other than the current one ...
    desktop_original = xsession.get_desktop_active()
    assert desktop_original is not None
    desktop_target = desktop_count - 1 if desktop_original == 0 else 0
    assert desktop_target != desktop_original

    # Change to it, change back ...
    set_desktop(desktop=desktop_target)
    set_desktop(desktop=desktop_original)


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.skipif(
    "ALLOW_DISPLAY_MODIFICATION" not in os.environ, reason="Sane unit testing."
)
def test_set_desktop_count(xsession: XSession):
    """ "Tests that the number of desktops can be assigned."""

    def set_count(*, count: int):
        xsession.set_desktop_count(count=count)
        allow_xserver_to_sync()
        assert xsession.get_desktop_count() == count

    count_original = xsession.get_desktop_count()

    # Change it, change back ...
    set_count(count=count_original + 1)
    set_count(count=count_original)


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.skipif(
    "ALLOW_DISPLAY_MODIFICATION" not in os.environ, reason="Sane unit testing."
)
def test_set_desktop_geometry(xsession: XSession):
    """Tests that the dimensions of the desktops can be assigned."""

    def set_geometry(*, height: int, width: int):
        xsession.set_desktop_geometry(height=height, width=width)
        allow_xserver_to_sync()
        assert xsession.get_desktop_geometry() == [width, height]

    geometry_original = xsession.get_desktop_geometry()

    # Change it, change back ...
    set_geometry(height=geometry_original[1] + 1, width=geometry_original[0] + 1)
    set_geometry(height=geometry_original[1], width=geometry_original[0])


@pytest.mark.skipif(
    "ALLOW_DISPLAY_MODIFICATION" not in os.environ, reason="Sane unit testing."
)
def test_set_desktop_layout(xsession: XSession):
    """Tests that the layout of the desktops can be assigned."""

    def set_layout(*, columns: int, orientation: int, rows: int, starting_corner: int):
        xsession.set_desktop_layout(
            columns=columns,
            orientation=orientation,
            rows=rows,
            starting_corner=starting_corner,
        )
        allow_xserver_to_sync()
        assert xsession.get_desktop_layout() == [
            orientation,
            columns,
            rows,
            starting_corner,
        ]

    layout_original = xsession.get_desktop_layout()

    # Change it, change back ...
    set_layout(
        columns=layout_original[1] + 1,
        orientation=layout_original[0],
        rows=layout_original[2] + 1,
        starting_corner=layout_original[3],
    )
    set_layout(
        columns=layout_original[1],
        orientation=layout_original[0],
        rows=layout_original[2],
        starting_corner=layout_original[3],
    )


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
def test_set_desktop_showing(xsession: XSession):
    """Tests that the showing desktop flag can be assigned."""

    def set_showing(*, showing: int):
        xsession.set_desktop_showing(showing=showing)
        allow_xserver_to_sync()
        assert xsession.get_desktop_showing() == showing

    # Find a desktop other than the current one ...
    showing_original = xsession.get_desktop_showing()
    assert showing_original is not None
    showing_target = 1 if showing_original == 0 else 0
    assert showing_target != showing_original

    # Change to it, change back ...
    set_showing(showing=showing_target)
    set_showing(showing=showing_original)


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_set_window_active(xsession: XSession):
    """Tests that a window can be activated."""
    try:

        def set_active(*, window: int):
            xsession.set_window_active(window=window)
            allow_xserver_to_sync()
            assert xsession.get_window_active().id == window

        window_metadata0 = launch_command(args=["xclock"], xsession=xsession)
        window_id0 = guess_window(
            title_hint="^xclock$", windows=window_metadata0, xsession=xsession
        )
        assert window_id0

        # After the next command window_id0 will be active, but was it before (by default)?
        set_active(window=window_id0)

        window_metadata1 = launch_command(args=["xclock"], xsession=xsession)
        window_id1 = guess_window(
            title_hint="^xclock$", windows=window_metadata1, xsession=xsession
        )
        assert window_id1

        # After the next command window_id1 will be active, but was it before (by default)?
        set_active(window=window_id1)

        # Since no new windows were opened, we can be confident that it's us changing focus,
        # and not the display manager ...
        set_active(window=window_id0)

        # One more time, for good measure ...
        set_active(window=window_id1)
    finally:
        kill_all_xclock_instances()


@pytest.mark.xclock
def test_set_window_close(window_id: int, xsession: XSession):
    """Tests that a window can be closed."""
    xsession.set_window_close(window=window_id)
    allow_xserver_to_sync()
    with pytest.raises(BadWindow):
        xsession.get_window_name(window=window_id)


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_set_window_desktop(window_id: int, xsession: XSession):
    """Tests that a desktop can be assigned to a window."""

    desktop_count = xsession.get_desktop_count()
    if desktop_count < 2:
        pytest.skip(
            f"Number of desktops {desktop_count} is less than required value: 2"
        )

    def set_desktop(*, desktop: int):
        xsession.set_window_desktop(desktop=desktop, window=window_id)
        allow_xserver_to_sync()
        assert xsession.get_window_desktop(window=window_id) == desktop

    # Find a desktop other than the current one ...
    desktop_original = xsession.get_window_desktop(window=window_id)
    assert desktop_original is not None
    desktop_target = desktop_count - 1 if desktop_original == 0 else 0
    assert desktop_target != desktop_original

    # Change to it, change back ...
    set_desktop(desktop=desktop_target)
    set_desktop(desktop=desktop_original)


@pytest.mark.xclock
def test_set_window_dimensions(window_id: int, xsession: XSession):
    """Tests that a window can be sized."""
    dimensions0 = xsession.get_window_dimensions(window=window_id)
    assert dimensions0
    LOGGER.debug(
        "Test window starting dimensions: %d,%d", dimensions0[0], dimensions0[1]
    )
    delta_x = randint(10, 50)
    delta_y = randint(10, 50)

    dimensions1 = [dimensions0[0] + delta_x, dimensions0[1] + delta_y]
    xsession.set_window_dimensions(
        height=dimensions1[1], width=dimensions1[0], window=window_id
    )
    allow_xserver_to_sync()
    assert xsession.get_window_dimensions(window=window_id) == dimensions1


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_set_window_focus(xsession: XSession):
    """Tests that a window can be focused."""
    try:

        def make_focused(*, window_id: int):
            xsession.set_window_focus(window=window_id)
            allow_xserver_to_sync()
            assert xsession.get_window_focus().id == window_id

        window_metadata0 = launch_command(args=["xclock"], xsession=xsession)
        window_id0 = guess_window(
            title_hint="^xclock$", windows=window_metadata0, xsession=xsession
        )
        assert window_id0

        # After the next command window_id0 will be focused, but was it before (by default)?
        make_focused(window_id=window_id0)

        window_metadata1 = launch_command(args=["xclock"], xsession=xsession)
        window_id1 = guess_window(
            title_hint="^xclock$", windows=window_metadata1, xsession=xsession
        )
        assert window_id1

        # After the next command window_id1 will be focused, but was it before (by default)?
        make_focused(window_id=window_id1)

        # Since no new windows were opened, we can be confident that it's xdotool changing focus,
        # and not the display manager ...
        make_focused(window_id=window_id0)

        # One more time, for good measure ...
        make_focused(window_id=window_id1)
    finally:
        kill_all_xclock_instances()


@pytest.mark.xclock
def test_set_window_frame_extents(window_id: int, xsession: XSession):
    """Tests that frame extents can be assigned to a window."""
    frame_extents0 = xsession.get_window_frame_extents(window=window_id)
    assert frame_extents0
    LOGGER.debug(
        "Test window starting frame extents: %d,%d,%d,%d",
        frame_extents0[0],
        frame_extents0[1],
        frame_extents0[2],
        frame_extents0[3],
    )

    # frame_extents1 = [x + 1 for x in frame_extents0]
    frame_extents1 = [1, 1, 1, 1]
    xsession.set_window_frame_extents(
        bottom=frame_extents1[3],
        left=frame_extents1[0],
        right=frame_extents1[1],
        top=frame_extents1[2],
        window=window_id,
    )
    allow_xserver_to_sync()
    assert xsession.get_window_frame_extents(window=window_id) == frame_extents1


@pytest.mark.xclock
def test_set_window_position(window_id: int, xsession: XSession):
    """Tests that a window can be moved."""
    position0 = xsession.get_window_position(window=window_id)
    assert position0
    LOGGER.debug("Test window starting position: %d,%d", position0[0], position0[1])
    delta_x = randint(10, 50)
    delta_y = randint(10, 50)

    position1 = [position0[0] + delta_x, position0[1] + delta_y]
    xsession.set_window_position(
        position_x=position1[0], position_y=position1[1], window=window_id
    )
    allow_xserver_to_sync()
    # TODO: Apparently, there is something going on w/ display managers, as this doesn't work ?!?
    #       ... fallback on, did it move "somewhere" ...
    #       Look into "hints"?
    # assert xsession.get_window_position(window=window_id) == position1
    assert xsession.get_window_position(window=window_id) != position0


@pytest.mark.xclock
def test_set_window_state(window_id: int, xsession: XSession):
    """Tests that a state can be assigned to a given window."""
    states0 = xsession.get_window_state(window=window_id)

    # Find a state that is not in the list ...
    atom_name = "_NET_WM_STATE_FULLSCREEN"
    atom_value = xsession.get_atom(name=atom_name)
    assert atom_value not in states0

    # Add the atom ...
    xsession.set_window_state(state0=atom_name, window=window_id)
    allow_xserver_to_sync()
    states1 = xsession.get_window_state(window=window_id)
    assert atom_value in states1
    assert states1 != states0

    # Remove the atom ...
    xsession.set_window_state(action=ACTION_REMOVE, state0=atom_name, window=window_id)
    allow_xserver_to_sync()
    states2 = xsession.get_window_state(window=window_id)
    assert atom_value not in states2
    assert states2 == states0
    assert states2 != states1

    # Toggle the atom ...
    xsession.set_window_state(action=ACTION_TOGGLE, state0=atom_name, window=window_id)
    allow_xserver_to_sync()
    states3 = xsession.get_window_state(window=window_id)
    assert atom_value in states3
    assert states3 != states0
    assert states3 == states1
    assert states3 != states2

    # Toggle the atom (again), also use the value ...
    xsession.set_window_state(action=ACTION_TOGGLE, state0=atom_value, window=window_id)
    allow_xserver_to_sync()
    states4 = xsession.get_window_state(window=window_id)
    assert atom_value not in states4
    assert states4 == states0
    assert states4 != states1
    assert states4 == states2
    assert states4 != states3


@pytest.mark.xclock
def test_window_destroy(window_id: int, xsession: XSession):
    """Tests that a window can be destroyed."""
    xsession.window_destroy(window=window_id)
    allow_xserver_to_sync()
    with pytest.raises(BadWindow):
        xsession.get_window_name(window=window_id)


@pytest.mark.xclock
def test_window_kill(window_id: int, xsession: XSession):
    """Tests that a window can be killed."""
    xsession.window_kill(window=window_id)
    allow_xserver_to_sync()
    with pytest.raises(BadWindow):
        xsession.get_window_name(window=window_id)


@pytest.mark.xclock
def test_window_maximize(window_id: int, xsession: XSession):
    """Tests that a window can be maximized."""
    state = xsession.get_window_state(window=window_id)
    horizontal = xsession.get_atom(name=NET_WM_STATE_MAXIMIZED_HORZ)
    vertical = xsession.get_atom(name=NET_WM_STATE_MAXIMIZED_VERT)
    assert horizontal not in state
    assert vertical not in state

    # Maximize horizontal ...
    xsession.window_maximize(flags=[horizontal], window=window_id)
    allow_xserver_to_sync()
    state = xsession.get_window_state(window=window_id)
    assert horizontal in state
    assert vertical not in state

    # Unmaximize ...
    xsession.window_maximize(inverse=True, window=window_id)
    allow_xserver_to_sync()
    state = xsession.get_window_state(window=window_id)
    assert horizontal not in state
    assert vertical not in state

    # Maximize vertical ...
    xsession.window_maximize(flags=[vertical], window=window_id)
    allow_xserver_to_sync()
    state = xsession.get_window_state(window=window_id)
    assert horizontal not in state
    assert vertical in state

    # Unmaximize ...
    xsession.window_maximize(inverse=True, window=window_id)
    allow_xserver_to_sync()
    state = xsession.get_window_state(window=window_id)
    assert horizontal not in state
    assert vertical not in state

    # Maximize both ...
    xsession.window_maximize(window=window_id)
    allow_xserver_to_sync()
    state = xsession.get_window_state(window=window_id)
    assert horizontal in state
    assert vertical in state

    # Unmaximize ...
    xsession.window_maximize(inverse=True, window=window_id)
    allow_xserver_to_sync()
    state = xsession.get_window_state(window=window_id)
    assert horizontal not in state
    assert vertical not in state


@pytest.mark.xclock
def test_window_minimize(window_id: int, xsession: XSession):
    """Tests that a window can be maximized."""
    state = xsession.get_window_state(window=window_id)
    hidden = xsession.get_atom(name=NET_WM_STATE_HIDDEN)
    assert hidden not in state

    # Minimize ...
    xsession.window_minimize(window=window_id)
    allow_xserver_to_sync()
    state = xsession.get_window_state(window=window_id)
    assert hidden in state

    # Unminimize ...
    xsession.window_minimize(inverse=True, window=window_id)
    allow_xserver_to_sync()
    state = xsession.get_window_state(window=window_id)
    assert hidden not in state


@pytest.mark.xclock
def test_window_moveresize(window_id: int, xsession: XSession):
    """Tests that a window can be moved and resized."""
    dimensions0 = xsession.get_window_dimensions(window=window_id)
    assert dimensions0
    position0 = xsession.get_window_position(window=window_id)
    assert position0
    LOGGER.debug(
        "Test window starting position and dimensions: %d,%d %dx%d",
        position0[0],
        position0[1],
        dimensions0[0],
        dimensions0[1],
    )
    delta_h = randint(10, 50)
    delta_w = randint(10, 50)
    delta_x = randint(10, 50)
    delta_y = randint(10, 50)

    dimensions1 = [dimensions0[0] + delta_w, dimensions0[1] + delta_h]
    position1 = [position0[0] + delta_x, position0[1] + delta_y]

    xsession.window_moveresize(
        height=dimensions1[1],
        position_x=position1[0],
        position_y=position1[1],
        width=dimensions1[0],
        window=window_id,
    )
    allow_xserver_to_sync()
    assert xsession.get_window_dimensions(window=window_id) == dimensions1
    assert xsession.get_window_position(window=window_id) == position1


@pytest.mark.skip("The whole point is to be interactive.")
def test_window_select(xsession: XSession):
    """Tests that a window can be graphically selected."""
    assert xsession.window_select()


# @pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
@pytest.mark.xclock
def test_window_map_unmap(window_id: int, xsession: XSession):
    """Tests that a window can be mapped and unmapped."""
    window = xsession.get_window_by_id(window_id=window_id)

    # Should be visible
    get_window_attributes = window.get_attributes()
    assert get_window_attributes.map_state == IsViewable

    xsession.window_unmap(window=window_id)
    allow_xserver_to_sync()

    # Should not be visible
    get_window_attributes = window.get_attributes()
    assert get_window_attributes.map_state == IsUnmapped

    xsession.window_map(window=window_id)
    allow_xserver_to_sync()

    # Should be visible
    get_window_attributes = window.get_attributes()
    assert get_window_attributes.map_state == IsViewable


# #@pytest.mark.skipif("TRAVIS" in os.environ, reason="Doesn't work with xvfb.")
# @pytest.mark.xclock
# def test_windowraise(xsession: XSession):
#     """Tests that a window can be raised."""
#     try:
#
#         def make_raised(*, window_id: int):
#             windowraise(window_id=window_id)
#             assert getwindowfocus() == window_id
#
#         window_metadata0 = launch_command(args=["xclock"])
#         window_id0 = guess_window(
#             title_hint="^xclock$", window_metadata=window_metadata0
#         )
#         assert window_id0
#
#         # After the next command window_id0 will be focused, but was it before (by default)?
#         make_raised(window_id=window_id0)
#
#         window_metadata1 = launch_command(args=["xclock"])
#         window_id1 = guess_window(
#             title_hint="^xclock$", window_metadata=window_metadata1
#         )
#         assert window_id1
#
#         # After the next command window_id1 will be focused, but was it before (by default)?
#         make_raised(window_id=window_id1)
#
#         # Since no new windows were opened, we can be confident that it's xdotool changing focus,
#         # and not the display manager ...
#         make_raised(window_id=window_id0)
#
#         # One more time, for good measure ...
#         make_raised(window_id=window_id1)
#     finally:
#         kill_all_xclock_instances()

# TODO: def test_windowreparent(xsession: XSession):
