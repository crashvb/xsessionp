#!/usr/bin/env python

# pylint: disable=invalid-name

"""
Extended Window Manager Hints
https://specifications.freedesktop.org/wm-spec/1.5/
"""

NET_ACTIVE_WINDOW = "_NET_ACTIVE_WINDOW"
NET_CLIENT_LIST = "_NET_CLIENT_LIST"
NET_CLIENT_LIST_STACKING = "_NET_CLIENT_LIST_STACKING"
NET_CLOSE_WINDOW = "_NET_CLOSE_WINDOW"
NET_CURRENT_DESKTOP = "_NET_CURRENT_DESKTOP"
NET_DESKTOP_GEOMETRY = "_NET_DESKTOP_GEOMETRY"
NET_DESKTOP_LAYOUT = "_NET_DESKTOP_LAYOUT"
NET_DESKTOP_NAMES = "_NET_DESKTOP_NAMES"
NET_DESKTOP_VIEWPORT = "_NET_DESKTOP_VIEWPORT"
NET_FRAME_EXTENTS = "_NET_FRAME_EXTENTS"
NET_NUMBER_OF_DESKTOPS = "_NET_NUMBER_OF_DESKTOPS"
NET_MOVERESIZE_WINDOW = "_NET_MOVERESIZE_WINDOW"
# NET_REQUEST_FRAME_EXTENTS = "_NET_REQUEST_FRAME_EXTENTS"
# NET_RESTACK_WINDOW = "_NET_RESTACK_WINDOW"
NET_SHOWING_DESKTOP = "_NET_SHOWING_DESKTOP"
NET_SUPPORTED = "_NET_SUPPORTED"
NET_SUPPORTING_WM_CHECK = "_NET_SUPPORTING_WM_CHECK"
NET_WM_ALLOWED_ACTIONS = "_NET_WM_ALLOWED_ACTIONS"
NET_WM_DESKTOP = "_NET_WM_DESKTOP"
# NET_WM_HANDLED_ICONS = "_NET_WM_HANDLED_ICONS"
# NET_WM_ICON = "_NET_WM_ICON"
# NET_WM_ICON_NAME = "_NET_WM_ICON_NAME"
# NET_WM_MOVERESIZE = "_NET_WM_MOVERESIZE"
NET_WM_NAME = "_NET_WM_NAME"
NET_WM_PID = "_NET_WM_PID"
# NET_WM_PING = "_NET_WM_PING"
# NET_WM_SYNC_REQUEST = "_NET_WM_SYNC_REQUEST"
NET_WM_STATE = "_NET_WM_STATE"
# NET_WM_STRUT = "_NET_WM_STRUT"
# NET_WM_STRUT_PARTIAL = "_NET_WM_STRUT_PARTIAL"
# NET_WM_USER_TIME = "_NET_WM_USER_TIME"
NET_WM_WINDOW_TYPE = "_NET_WM_WINDOW_TYPE"
NET_WM_VISIBLE_NAME = "_NET_WM_VISIBLE_NAME"
NET_WORKAREA = "_NET_WORKAREA"
NET_VIRTUAL_ROOTS = "_NET_VIRTUAL_ROOTS"

ACTION_REMOVE = 0
ACTION_ADD = 1
ACTION_TOGGLE = 2

SOURCE_APPLICATION = 1
SOURCE_PAGER = 2

# NET_WM_ACTION_ABOVE = "_NET_WM_ACTION_ABOVE"
# NET_WM_ACTION_BELOW = "_NET_WM_ACTION_BELOW"
# NET_WM_ACTION_CHANGE_DESKTOP = "_NET_WM_ACTION_CHANGE_DESKTOP"
# NET_WM_ACTION_CLOSE = "_NET_WM_ACTION_CLOSE"
# NET_WM_ACTION_FULLSCREEN = "_NET_WM_ACTION_FULLSCREEN"
# NET_WM_ACTION_MAXIMIZE_HORZ = "_NET_WM_ACTION_MAXIMIZE_HORZ"
# NET_WM_ACTION_MAXIMIZE_VERT = "_NET_WM_ACTION_MAXIMIZE_VERT"
# NET_WM_ACTION_MINIMIZE = "_NET_WM_ACTION_MINIMIZE"
# NET_WM_ACTION_MOVE = "_NET_WM_ACTION_MOVE"
# NET_WM_ACTION_RESIZE = "_NET_WM_ACTION_RESIZE"
# NET_WM_ACTION_SHADE = "_NET_WM_ACTION_SHADE"
# NET_WM_ACTION_STICK = "_NET_WM_ACTION_STICK"

# NET_WM_STATE_ABOVE = "_NET_WM_STATE_ABOVE"
# NET_WM_STATE_BELOW = "_NET_WM_STATE_BELOW"
# NET_WM_STATE_DEMANDS_ATTENTION = "_NET_WM_STATE_ATTENTION"
# NET_WM_STATE_FULLSCREEN = "_NET_WM_STATE_FULLSCREEN"
NET_WM_STATE_HIDDEN = "_NET_WM_STATE_HIDDEN"
NET_WM_STATE_MAXIMIZED_HORZ = "_NET_WM_STATE_MAXIMIZED_HORZ"
NET_WM_STATE_MAXIMIZED_VERT = "_NET_WM_STATE_MAXIMIZED_VERT"
# NET_WM_STATE_MODAL = "_NET_WM_STATE_MODAL"
# NET_WM_STATE_SHADED = "_NET_WM_STATE_SHADED"
# NET_WM_STATE_SKIP_PAGER = "_NET_WM_STATE_SKIP_PAGER"
# NET_WM_STATE_SKIP_TASKBAR = "_NET_WM_STATE_SKIP_TASKBAR"
# NET_WM_STATE_STICKY = "_NET_WM_STATE_STICKY"