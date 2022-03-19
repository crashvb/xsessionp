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

Define a configuration file(s) containing the desired end state:

```yaml
# Any value provided at the root level (globals) will propagate to all windows as the default value for that key.
# Globals can be overridden in individual window configurations, or omitted by added a key with a "no_" prefix (e.g.
# no_geometry).
desktop: 0
windows:
- command:
  - /usr/bin/xed
  - --new-window
  focus: true
  geometry: 926x656
  hints:
    name: ^Unsaved Document.*
  position: 166,492
  # Regular expression to help locate the window
- command:
  - /usr/bin/gnome-terminal
  - --command=tmux
  - --full-screen
  - --hide-menubar
  - --window-with-profile=tmux
  desktop: 1
  # By default, windows are started with a copy of the parent environment, then augmented. Uncomment the line below
  # to augment an empty environment instead.
  #   copy_environment: false
  environment:
    foo: bar
    asdf: qwer
  geometry: 1174x710
  hint_method: OR
  hints:
    class: Gnome-terminal
    name: Terminal
  position: 213,134
  shell: true
  start_directory: /tmp
```

Configurations can be listed using the <tt>ls</tt> command:

```bash
$ xsessionp ls
/home/user/.xsessionp/python-dev.yml
```

A configuration can be instantiated using the <tt>load</tt> command:

```bash
$ xsessionp load desktop0
Loading: /home/user/.xsessionp/python-dev.yml
```

To assist with developing configurations, the <tt>learn</tt> command can be used to graphically select a window and
capture metadata:

```bash
$ xsessionp learn

windows:
- command: nemo /home/user
  desktop: 0
  geometry: 1236x689
  position: 2210,476
```

### Environment Variables

| Variable | Default Value | Description |
| ---------| ------------- | ----------- |
| XSESSIONP_CONFIGDIR | ~/.xsessionp | xsessionp configuration directory.

## Development

[Source Control](https://github.com/crashvb/xsessionp)
