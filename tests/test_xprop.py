#!/usr/bin/env python

# pylint: disable=redefined-outer-name

"""xprop tests."""

import logging

import pytest

from xsessionp import (
    get_xproperties,
    get_xproperty,
    get_root_xproperties,
    get_root_xproperty,
    parse_xproperties,
    remove_xproperties,
    remove_xproperty,
    remove_root_xproperties,
    remove_root_xproperty,
    set_xproperties,
    set_xproperty,
    set_root_xproperties,
    set_root_xproperty,
    TypingXProperty,
    xprop,
)

LOGGER = logging.getLogger(__name__)


def test_get_root_properties():
    """Tests properties can be retrieved from the root window."""
    assert get_root_xproperties()


def test_get_root_property():
    """Tests a property can be retrieved from the root window."""
    xproperties = get_root_xproperties()
    assert xproperties
    assert get_root_xproperty(xproperty=list(xproperties.keys())[-1])
    assert get_root_xproperty(xproperty="DOEST_NOT_EXIST") is None


@pytest.mark.xclock
def test_get_xproperties(window_id: int):
    """Tests properties can be retrieved from a given window."""
    xprop0 = TypingXProperty(format=None, name="WM_NAME", type="STRING", value="xclock")

    xproperties = get_xproperties(window_id=window_id)
    assert xproperties
    assert xprop0.name in xproperties
    assert xproperties[xprop0.name].name == xprop0.name
    assert xproperties[xprop0.name].type == xprop0.type
    assert xproperties[xprop0.name].value == f'"{xprop0.value}"'

    xproperties = get_xproperties(window_name="xclock")
    assert xproperties
    assert xprop0.name in xproperties
    assert xproperties[xprop0.name].name == xprop0.name
    assert xproperties[xprop0.name].type == xprop0.type
    assert xproperties[xprop0.name].value == f'"{xprop0.value}"'


@pytest.mark.xclock
def test_get_xproperty(window_id: int):
    """Tests a property can be retrieved from a given window."""
    xprop0 = TypingXProperty(format=None, name="WM_NAME", type="STRING", value="xclock")

    xproperty = get_xproperty(window_id=window_id, xproperty=xprop0.name)
    assert xproperty
    assert xproperty.name == xprop0.name
    assert xproperty.type == xprop0.type
    assert xproperty.value == f'"{xprop0.value}"'

    xproperty = get_xproperty(window_name="xclock", xproperty=xprop0.name)
    assert xproperty
    assert xproperty.name == xprop0.name
    assert xproperty.type == xprop0.type
    assert xproperty.value == f'"{xprop0.value}"'

    assert get_xproperty(window_name="xclock", xproperty="DOEST_NOT_EXIST") is None


@pytest.mark.xclock
def test_parse_xproperties(window_id: int):
    """Tests that properties can be parsed."""
    stdout = xprop("-id", str(window_id))
    assert stdout

    xprop0 = TypingXProperty(format=None, name="WM_NAME", type="STRING", value="xclock")

    xproperties = parse_xproperties(stdout=stdout)
    assert xproperties
    assert xprop0.name in xproperties
    assert xproperties[xprop0.name].name == xprop0.name
    assert xproperties[xprop0.name].type == xprop0.type
    assert xproperties[xprop0.name].value == f'"{xprop0.value}"'


@pytest.mark.xclock
def test_remove_xproperties(window_id: int):
    """Tests that select properties can be removed from a given window."""
    property_names = ["WM_HINTS", "WM_ICON_NAME"]
    xproperties = get_xproperties(window_id=window_id)
    for property_name in property_names:
        assert xproperties[property_name].name == property_name

    remove_xproperties(window_id=window_id, xproperties=property_names)
    xproperties = get_xproperties(window_id=window_id)
    for property_name in property_names:
        assert property_name not in xproperties

    property_names = ["WM_LOCALE_NAME", "WM_NORMAL_HINTS"]
    for property_name in property_names:
        assert xproperties[property_name].name == property_name

    remove_xproperties(window_name="xclock", xproperties=property_names)
    xproperties = get_xproperties(window_id=window_id)
    for property_name in property_names:
        assert property_name not in xproperties


@pytest.mark.xclock
def test_remove_xproperty(window_id: int):
    """Tests that a property can be removed from a given window."""
    property_name = "WM_ICON_NAME"
    xproperties = get_xproperties(window_id=window_id)
    assert xproperties[property_name].name == property_name

    remove_xproperty(window_id=window_id, xproperty=property_name)
    xproperties = get_xproperties(window_id=window_id)
    assert property_name not in xproperties

    property_name = "WM_HINTS"
    assert xproperties[property_name].name == property_name

    remove_xproperty(window_name="xclock", xproperty=property_name)
    xproperties = get_xproperties(window_id=window_id)
    assert property_name not in xproperties


def test_set_root_xproperties_remove_root_xproperties():
    """Tests properties can be assigned to the root window."""
    # Assumed to not exist for the root window ...
    xprops = [
        TypingXProperty(
            format=None, name="WM_ICON_NAME", type="STRING", value="pytest0"
        ),
        TypingXProperty(format=None, name="WM_NAME", type="STRING", value="pytest1"),
    ]

    # Ensure the host was not left in a bad state from a previous run ...
    for xprop0 in xprops:
        assert get_root_xproperty(xproperty=xprop0) is None

    try:
        set_root_xproperties(xproperties=xprops)
        for xprop0 in xprops:
            xproperty = get_root_xproperty(xproperty=xprop0)
            assert xproperty
            assert xproperty.name == xprop0.name
            assert xproperty.type == xprop0.type
            assert xproperty.value == f'"{xprop0.value}"'
    finally:
        # Clean up, as it's the root window and may leave the host in a bad state ...
        remove_root_xproperties(xproperties=xprops)
        for xprop0 in xprops:
            assert get_root_xproperty(xproperty=xprop0) is None


def test_set_root_xproperty_remove_root_xproperty():
    """Tests that a property can be assigned to the root window."""
    # Assumed to not exist for the root window ...
    xprop0 = TypingXProperty(
        format=None, name="WM_ICON_NAME", type="STRING", value="pytest0"
    )

    # Ensure the host was not left in a bad state from a previous run ...
    assert get_root_xproperty(xproperty=xprop0) is None

    try:
        set_root_xproperty(xproperty=xprop0)
        xproperty = get_root_xproperty(xproperty=xprop0)
        assert xproperty
        assert xproperty.name == xprop0.name
        assert xproperty.type == xprop0.type
        assert xproperty.value == f'"{xprop0.value}"'
    finally:
        # Clean up, as it's the root window and may leave the host in a bad state ...
        remove_root_xproperty(xproperty=xprop0)
        assert get_root_xproperty(xproperty=xprop0) is None


@pytest.mark.xclock
def test_set_xproperties(window_id: int):
    """Tests properties can be assigned to a given window."""
    xprops = [
        TypingXProperty(
            format=None, name="WM_ICON_NAME", type="STRING", value="pytest0"
        ),
        TypingXProperty(format=None, name="WM_NAME", type="STRING", value="pytest1"),
    ]
    for xprop0 in xprops:
        xproperty = get_xproperty(window_id=window_id, xproperty=xprop0.name)
        assert xproperty.value != f'"{xprop0.value}"'

    set_xproperties(window_id=window_id, xproperties=xprops)
    for xprop0 in xprops:
        xproperty = get_xproperty(window_id=window_id, xproperty=xprop0.name)
        assert xproperty.value == f'"{xprop0.value}"'

    # TODO: Do we need to test using a different property so that WM_NAME doesn't change and we can use it again for
    #       get_set_xproperty(window_name="xclock" ...) ?


@pytest.mark.xclock
def test_set_xproperty(window_id: int):
    """Tests that aproperty can be assigned to a given window."""
    xprop0 = TypingXProperty(
        format=None, name="WM_ICON_NAME", type="STRING", value="xclock"
    )
    xproperty = get_xproperty(window_id=window_id, xproperty=xprop0.name)
    assert xproperty
    assert xproperty.name == xprop0.name
    assert xproperty.type == xprop0.type
    assert xproperty.value == f'"{xprop0.value}"'

    xprop0 = TypingXProperty(
        format=None, name=xprop0.name, type="STRING", value="window_id"
    )
    set_xproperty(window_id=window_id, xproperty=xprop0)
    xproperty = get_xproperty(window_id=window_id, xproperty=xprop0.name)
    assert xproperty
    assert xproperty.name == xprop0.name
    assert xproperty.type == xprop0.type
    assert xproperty.value == f'"{xprop0.value}"'

    xprop0 = TypingXProperty(
        format=None, name=xprop0.name, type="STRING", value="window_name"
    )
    set_xproperty(window_name="xclock", xproperty=xprop0)
    xproperty = get_xproperty(window_id=window_id, xproperty=xprop0.name)
    assert xproperty
    assert xproperty.name == xprop0.name
    assert xproperty.type == xprop0.type
    assert xproperty.value == f'"{xprop0.value}"'


def test_xprop():
    """Tests that the current desktop can be retrieved."""
    assert xprop("-version")
