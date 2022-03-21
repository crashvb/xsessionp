# xsessionp

## Overview

A declarative window instantiation utility for x11 sessions, heavily inspired by tmuxp.

## Compatibility

* Tested with python 3.8

## Installation
### From [pypi.org](https://pypi.org/project/xsessionp/)

```
$ pip install xsessionp
```

### From source code

```bash
$ git clone https://github.com/crashvb/xsessionp
$ cd xsessionp
$ virtualenv env
$ source env/bin/activate
$ python -m pip install --editable .[dev]
```

## Usage

### TL;DR

Define a configuration file(s) declaring the desired end state:

```yaml
# ~/.xsessionp/example.yml
---
desktop: 0
environment:
  xsp: makes_life_easy
windows:
- command:
  - /usr/bin/xed
  - --new-window
  copy_environment: false
  focus: true
  dimensions: 926x656
  hints:
    name: ^Unsaved Document.*
  position: 166,492
- command:
  - /usr/bin/gnome-terminal
  - --
  - tmux
  desktop: 0
  environment:
    GNOME_TERMINAL_SCREEN: ""
  dimensions: 1174x710
  hints:
    name: ^Terminal$
    class: ^\['gnome-terminal-server', 'Gnome-terminal'\]$
  position: 213,134
  shell: true
  start_directory: /tmp
```

A configuration can be instantiated using the <tt>load</tt> command:

```bash
$ xsp load example
Loading: /home/user/.xsessionp/example.yml
```
### Commands

This packages makes available the `xsessionp` command, and the shorter `xsp` alias.

A listing of commands is available by executing: `xsp --help`. Command-specific usage is available by executing `--help` after the command (e.g.: `xsp ls --help`).

#### <a name="command_close_window"></a> close-window

Closes a managed window(s).

```bash
$ xsp close-window --target /home/user/.xsessionp/example.yml:window[0]:262512556
Closed window: 119537674
```

#### <a name="command_learn"></a> learn

Capture metadata from a graphically selected window. Intended to assist with developing workspace configurations.

```bash
$ xsp learn
---
windows:
- command:
  - nemo
  - /home/user
  desktop: 0
  dimensions: 1667x918
  environment:
  - DBUS_SESSION_BUS_ADDRESS=unix:path /run/user/1000/bus
  hints:
    name: ^Home$
  position: 1717,264

```

#### <a name="command_list_windows"></a> list-windows

Lists managed windows in a given format.

```bash
$ xsp list-windows
ID         XSP:NAME                                         DESKTOP  POSITION    DIMENSIONS    NAME
119537674  /tmp/tmpqf3bcpzt/xclock.yml:window[0]:262512556  0        [25, 49]    [300, 300]    xclock
138412043  /tmp/tmpqf3bcpzt/xclock.yml:window[1]:262512711  0        [25, 399]   [300, 40]     xclock

```

#### <a name="command_load"></a> load

Loads an xsessionp workspace for each instance of CONFIG specified.

```bash
$ xsp load example
Loading: /home/user/.xsessionp/example.yml
```

#### <a name="command_ls"></a> ls

Lists xsessionp workspace(s) discovered within each default configuration directory.

```bash
$ xsp ls
example
$ xsp ls --qualified
/home/user/.xsessionp/example.yml
```

#### <a name="command_reposition_window"></a> reposition-window

Aligns the current position of a managed window(s) to match the embedded metadata.

```bash
$ xsp reposition-window -t /tmp/tmpqf3bcpzt/xclock.yml:window[0]:262512556
Repositioned window: 119537674
```

#### <a name="command_test"></a> test

Perform basic acceptance tests by launching two xclock instances on the current desktop

```bash
$ xsp test
...
Loading: /tmp/tmpqf3bcpzt/xclock.yml
```

#### <a name="command_version"></a> version

```bash
$ xsp version
x.y.z
```

### Configuration

Any key defined at the root level (globals) will propagate to all windows as the default value for that key.
Globals can be overridden in individual window configurations (locals), or omitted by added a key with a "no_" prefix (e.g.: no_dimensions).
Keys with a `no_` prefix have a higher precedence then those without.

#### <a name="config_command"></a> command (type: `list`, `str`)

Command used to launch the window. Provided as `args` to [subprocess.Popen](https://docs.python.org/3/library/subprocess.html#subprocess.Popen).

#### <a name="config_copy_environment"></a> copy_environment (type: `bool`, default: `True`)

If true, the environment of xsessionp will be used as the base for launched windows. Otherwise, and empty environment will be used instead. This does not affect values declared via <a href="#config_environment">environment</a>.

#### <a name="config_desktop"></a> desktop (type: `int`)

The X11 desktop to be assigned to the launched window. If not provided, desktop assignment is not performed, and defaults to the behavior of the underlying window manager.

#### <a name="config_dimensions"></a> dimensions (type: `str`)

The dimensions (geometry) to assigned to the launched window. Values should take the form of `{width}x{height}` or `{width},{height}`. If not provided, no sizing is performed.

#### <a name="config_disable"></a> disabled (type: `bool`, default: `False`)

If true, the window will not be selected when the configuration is loaded. This is intended to allow complex window configuration(s) to remain inline without needing to comment them.

#### <a name="config_environment"></a> environment (type `Dict[str, str]`)

Key value pairs to be provided via the environment of the launched window. These values have precedence over the "base" environment; see <a href="#config_copy_environment">copy_environment</a>.

#### <a name="config_focus"></a> focus (type: `bool`, default: `False`)

If true, the window will be activated after all windows have been launched. If more than one window contains this value, the value is ignored.

#### <a name="config_hint_method"></a> hint_method (type: `enum`, values: `AND`, `OR`)

Boolean method by which <a href="#config_hints">hints</a> are evaluated.

#### <a name="config_hints"></a> hints (type: `Dict[str, str]`)

Distinguishing characteristics of the launched window that can be used to identify (guess) amongst otherwise ambiguous deltas.

Deterministically identifying the X11 window(s) that are created when a process is launched is difficult. Often the `WM_PID` atom is missing, or doesn't align with the PID of the process that was invoked, for various reasons.
As such, a listing of X11 windows is captured both *before* and *after* the process is executed, and the difference (delta) is used to guess the correct window. If the size of the delta is equal to 1, then it is assumed to correspond to the execute process.
If the size of the delta is greater than 1, then these hints are used to restrict which window is selected.

Common hints include: `class`, `name`, `state`, and `type`. Hint values are compiled into regular expression patterns prior to evaluating.

#### <a name="config_name"></a> name (type: `str`, default: *generated*)

Name (`xsp:name`) use to select windows when the configuration is loaded, and to identify the window when executing commands.

#### <a name="config_position"></a> position (type: `str`)

The position to assigned to the launched window. Values should take the form of `{x},{y}` or `{x},{y}`. If not provided, no positioning is performed.

#### <a name="config_search_delay"></a> search_delay (type: `float`, default: `0`)

The amount of time, in seconds, to wait before searching for launched windows. See <a href="#config_hints">hints</a> for an explanation of the methodology.

#### <a name="config_shell"></a> shell (type: `bool`, default: `False`)

If true, <a href="config_command">command</a> will be executed via a shell. Provided as `shell` to [subprocess.Popen](https://docs.python.org/3/library/subprocess.html#subprocess.Popen).

#### <a name="config_snapped"></a> snapped (type: `bool`, default: `False`)

If true, supporting window managers will be instructed to [snap](https://unix.stackexchange.com/a/511794), rather than tile, the launched window.

#### <a name="config_start_directory"></a> start_directory (type: `str`, default: `/`)

The working directory of the launched window. Provided as `cwd` to [subprocess.Popen](https://docs.python.org/3/library/subprocess.html#subprocess.Popen).

#### <a name="config_start_timeout"></a> start_timeout (type: `int`, default: `3`)

The maximum amount of time, in seconds, to wait for launched windows to be visible, prior to sizing and positioning.

#### <a name="config_tile"></a> tile (type: `str`)

Mode to use when tiling the launched window. Tiling occurs after window sizing and positioning. If not specified, no tiling is performed.

##### Supported Tiling Modes

Linux Mint Cinnamon: `BOTTOM`, `LEFT`, `LEFT_BOTTOM`, `LEFT_TOP`, `MAXIMIZE`, `NONE`, `RIGHT`, `RIGHT_BOTTOM`, `RIGHT_TOP`, `TOP`

### Environment Variables

| Variable | Default Value | Description |
| ---------| ------------- | ----------- |
| XSESSIONP_CONFIGDIR | ~/.xsessionp | xsessionp configuration directory.

## Development

[Source Control](https://github.com/crashvb/xsessionp)
