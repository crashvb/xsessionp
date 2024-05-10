#!/usr/bin/env python

"""Utility classes."""

import logging
import os
import re
import subprocess

from contextlib import contextmanager
from re import Pattern
from time import sleep
from typing import Dict


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
