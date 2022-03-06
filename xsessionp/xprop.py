#!/usr/bin/env python

"""xprop wrappers."""

import logging
import re

from re import Match, Pattern
from typing import Any, Dict, List, NamedTuple, Optional, Union

from .utils import get_path, run

LOGGER = logging.getLogger(__name__)
PATTERN_LINE_VALUE = re.compile(r"^\s+(?P<value>.*)$")
PATTERN_LINE_SINGLE = re.compile(
    r"^(?P<name>\S+)\((?P<type>[^)]+)\)\s*[=:](?:\s(?P<value>.*))?$"
)
XPROP = "xprop"


class TypingXProperty(NamedTuple):
    # pylint: disable=missing-class-docstring
    format: Optional[str]
    name: str
    type: str
    value: Any


def get_root_xproperties(*, args: List[str] = None) -> Dict[str, TypingXProperty]:
    """Retrieves properties from the root window."""
    args = args if args else []
    return parse_xproperties(stdout=xprop("-root", *args))


def get_root_xproperty(
    *, args: List[str] = None, xproperty: Union[str, TypingXProperty]
) -> TypingXProperty:
    """Retrieves a property from the root window."""
    xproperties = get_root_xproperties(args=args)
    if isinstance(xproperty, TypingXProperty):
        xproperty = xproperty.name
    return xproperties.get(xproperty)


def get_xproperties(
    *, args: List[str] = None, window_id: int = -1, window_name: str = None
) -> Dict[str, TypingXProperty]:
    """Retrieves properties from a given window."""
    if bool(window_id == -1) == bool(window_name is None):
        raise Exception("Either window_id or window_name must be provided!")

    args = args if args else []
    window_id = ["-id", str(window_id)] if window_id else []
    window_name = ["-name", window_name] if window_name else []
    return parse_xproperties(stdout=xprop(*window_id, *window_name, *args))


def get_xproperty(
    *,
    args: List[str] = None,
    window_id: int = -1,
    window_name: str = None,
    xproperty: Union[str, TypingXProperty],
) -> Optional[TypingXProperty]:
    """Retrieves a property from a given window."""
    xproperties = get_xproperties(
        args=args, window_id=window_id, window_name=window_name
    )
    if isinstance(xproperty, TypingXProperty):
        xproperty = xproperty.name
    return xproperties.get(xproperty)


def parse_xproperties(*, stdout: str) -> Dict[str, TypingXProperty]:
    """Parses the stdout from xprop into a typed list of properties."""

    # WM_CLASS(STRING) = "xclock", "XClock"
    # WM_PROTOCOLS(ATOM): protocols  WM_DELETE_WINDOW
    # WM_HINTS(WM_HINTS):
    #                 Client accepts input or input focus: False
    #                 Initial state is Normal State.
    result = {}

    def match_or_raise(*, _line: str, pattern: Pattern) -> Match:
        _match = pattern.match(_line)
        if not _match:
            raise Exception(f"Unable to parse output:\n{_line}")
        return _match

    last_name = None
    for line in stdout.split("\n"):
        if line.startswith((" ", "\t")):
            match = match_or_raise(_line=line, pattern=PATTERN_LINE_VALUE)
            if last_name is None:
                raise Exception("Cannot append multiline value to None!")
            item = result[last_name]
            result[last_name] = TypingXProperty(
                format=None,
                name=item.name,
                type=item.type,
                value=f"{item.value}\n{match.group('value').strip()}",
            )
        else:
            match = match_or_raise(_line=line, pattern=PATTERN_LINE_SINGLE)
            last_name = match.group("name")
            value = match.group("value") or ""
            result[last_name] = TypingXProperty(
                format=None, name=last_name, type=match.group("type"), value=value
            )
    return result


def remove_root_xproperties(
    *, args: List[str] = None, xproperties: List[Union[str, TypingXProperty]]
):
    """Removes properties from the root window."""
    args = args if args else []
    xproperties = [
        xproperty.name if isinstance(xproperty, TypingXProperty) else xproperty
        for xproperty in xproperties
    ]
    xproperties = sum([["-remove", xproperty] for xproperty in xproperties], [])
    xprop("-root", *xproperties, *args)


def remove_root_xproperty(
    *, args: List[str] = None, xproperty: Union[str, TypingXProperty]
):
    """Removes a property from the root window."""
    args = args if args else []
    remove_root_xproperties(args=args, xproperties=[xproperty])


def remove_xproperties(
    *,
    args: List[str] = None,
    window_id: int = -1,
    window_name: str = None,
    xproperties: List[Union[str, TypingXProperty]],
):
    """Removes properties from a given window."""
    if bool(window_id == -1) == bool(window_name is None):
        raise Exception("Either window_id or window_name must be provided!")

    args = args if args else []
    window_id = ["-id", str(window_id)] if window_id else []
    window_name = ["-name", window_name] if window_name else []
    xproperties = [
        xproperty.name if isinstance(xproperty, TypingXProperty) else xproperty
        for xproperty in xproperties
    ]
    xproperties = sum([["-remove", xproperty] for xproperty in xproperties], [])
    xprop(*window_id, *window_name, *xproperties, *args)


def remove_xproperty(
    *,
    args: List[str] = None,
    window_id: int = -1,
    window_name: str = None,
    xproperty: Union[str, TypingXProperty],
):
    """Removes a property from a given window."""
    remove_xproperties(
        args=args, window_id=window_id, window_name=window_name, xproperties=[xproperty]
    )


def set_root_xproperties(*, args: List[str] = None, xproperties: List[TypingXProperty]):
    """Assigns properties to the root window."""
    for xproperty in xproperties:
        set_root_xproperty(args=args, xproperty=xproperty)


def set_root_xproperty(*, args: List[str] = None, xproperty: TypingXProperty):
    """Assigns a property to the root window."""
    args = args if args else []
    xprop("-root", "-set", xproperty.name, str(xproperty.value), *args)


def set_xproperties(
    *,
    args: List[str] = None,
    window_id: int = -1,
    window_name: str = None,
    xproperties: List[TypingXProperty],
):
    """Assigns properties to a given window."""
    for xproperty in xproperties:
        set_xproperty(
            args=args,
            window_id=window_id,
            window_name=window_name,
            xproperty=xproperty,
        )


def set_xproperty(
    *,
    args: List[str] = None,
    omit_formats: bool = False,
    window_id: int = -1,
    window_name: str = None,
    xproperty: TypingXProperty,
):
    """Assigns a property to a given window."""
    if bool(window_id == -1) == bool(window_name is None):
        raise Exception("Either window_id or window_name must be provided!")

    args = args if args else []
    xformat = ["-f", xproperty.name, xproperty.format] if xproperty.format else []
    xformats = (
        ["-fs", str(get_path("data/xprop.formats", __name__))]
        if not omit_formats
        else []
    )
    window_id = ["-id", str(window_id)] if window_id else []
    window_name = ["-name", window_name] if window_name else []
    xprop(
        *window_id,
        *xformats,
        *xformat,
        *window_name,
        "-set",
        xproperty.name,
        str(xproperty.value),
        *args,
    )


def xprop(*args) -> str:
    """xprop wrapper."""
    return run(args=[XPROP, *args])
