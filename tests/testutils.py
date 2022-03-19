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


# TODO: Is there a way to make this deterministic?
def allow_xserver_to_sync():
    """Attempt to allow the X11 server to process events."""
    sleep(QUASI_DETERMINISTIC_DELAY)


def get_xclock_hints() -> Dict[str, Pattern]:
    """Retrieves hints to match an xclock window."""
    return {"name": re.compile(r"^xclock$")}


def kill_all_xclock_instances():
    # pylint: disable=subprocess-run-check
    """Terminate ... with extreme prejudice!"""
    LOGGER.debug("Terminating all xclock instances ...")
    subprocess.run(args=["killall", "-9", "xclock"])
    # Some display managers are not able to keep up with pytest creating and destroying windows. While
    # this is not exactly deterministic, it does seem to help.
    sleep(QUASI_DETERMINISTIC_DELAY)


@contextmanager
def temporary_environment_variable(key: str, value: str):
    """Context manager to globally define the xdg configuration directory."""
    old = os.environ.get(key, None)
    os.environ[key] = value
    yield None
    if old is not None:
        os.environ[key] = old
    else:
        del os.environ[key]
