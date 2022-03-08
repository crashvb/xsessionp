#!/usr/bin/env python

"""xsessionp tests."""

import logging

import pytest

from xsessionp import XSessionp

from .testutils import kill_all_xclock_instances

LOGGER = logging.getLogger(__name__)


@pytest.mark.xclock
def test_launch_command_guess_window(xsessionp: XSessionp):
    """Tests that we can guess for a window (at least sometimes ...)."""
    try:
        potential_windows = xsessionp.launch_command(args=["xclock"])
        window_id = xsessionp.guess_window(
            title_hint="^xclock$", windows=potential_windows
        )
        assert window_id
    finally:
        kill_all_xclock_instances()


# TODO: Implemented tests for the remaining methods ...
