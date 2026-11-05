#!/usr/bin/env python

"""Utility classes."""

import json
import logging
import os
import re
import subprocess

from contextlib import contextmanager
from re import Pattern
from time import sleep
from typing import Dict, List

from xsessionp import XSessionp

LOGGER = logging.getLogger(__name__)

QUASI_DETERMINISTIC_DELAY = 2
WINDOW_MANAGER_FLUXBOX = "fluxbox"


# TODO: Is there a way to make this deterministic?
def allow_xserver_to_sync():
    """Attempt to allow the X11 server to process events."""
    sleep(QUASI_DETERMINISTIC_DELAY)


def get_xlogo_hints() -> Dict[str, Pattern]:
    """Retrieves hints to match an xlogo window."""
    return {"name": re.compile(r"^xlogo$")}


def kill_all_xlogo_instances():
    # pylint: disable=subprocess-run-check
    """Terminate ... with extreme prejudice!"""
    LOGGER.debug("Terminating all xlogo instances ...")
    subprocess.run(args=["killall", "-9", "xlogo"])
    # Some display managers are not able to keep up with pytest creating and destroying windows. While
    # this is not exactly deterministic, it does seem to help.
    sleep(QUASI_DETERMINISTIC_DELAY)


@contextmanager
def temporary_environment_variable(key: str, value: str = None):
    """Context manager to globally define the xdg configuration directory."""
    old = os.environ.get(key, None)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    yield None
    if old is not None:
        os.environ[key] = old
    else:
        os.environ.pop(key, None)


def launch_windows(xsessionp: XSessionp, *, count: int = 2) -> List[int]:
    """Launches xlogo windows with xsessionp metadata."""
    window_ids = []
    for i in range(count):
        _, window_metadata = xsessionp.launch_command(args=["xlogo"])
        window_id = xsessionp.guess_window_delta(
            hints=get_xlogo_hints(), windows=window_metadata
        )
        allow_xserver_to_sync()
        assert window_id
        xsessionp.set_window_xsessionp_metadata(
            data=json.dumps({"name": f"test:window[{i}]:{window_id}"}), window=window_id
        )
        LOGGER.debug(f"window_id{i}: {window_id}")
        window_ids.append(window_id)
    return window_ids
