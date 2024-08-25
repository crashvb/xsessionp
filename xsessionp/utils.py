#!/usr/bin/env python

"""Utility classes."""

import json
import re
import subprocess

from enum import Enum
from re import Pattern
from typing import List

import yaml


class OutputFormat(Enum):
    """Output serialization format"""

    JSON = 0
    PLAIN = 1
    YAML = 2


def print_list(
    *,
    lst: List[str],
    output_format: OutputFormat = OutputFormat.PLAIN,
):
    """Prints a table to stdout."""
    if output_format == OutputFormat.JSON:
        print(json.dumps(obj=lst))
    elif output_format == OutputFormat.PLAIN:
        print("  ".join(lst))
    else:
        print(yaml.dump(data=lst))


def print_table(
    *, output_format: OutputFormat = OutputFormat.PLAIN, table: List[List[str]]
):
    """Prints a table to stdout."""
    if output_format == OutputFormat.JSON:
        print(json.dumps(obj=table))
    elif output_format == OutputFormat.PLAIN:
        column_width = []
        if table:
            for i in range(0, len(table[0])):
                column_width.append(max([len(row[i]) for row in table]))
        for row in table:
            for i, column in enumerate(row):
                print(column.ljust(column_width[i]), end="  ")
            print()
    else:
        print(yaml.dump(data=table))


def run(**kwargs) -> str:
    """Executes a command return the output."""
    return subprocess.check_output(**kwargs).decode("utf-8").strip()


def to_list_int(context, param, value: str) -> List[int]:
    # pylint: disable=unused-argument
    """Constructs a list of integers from a comma-separated string."""
    result = []
    for val in value:
        val = re.sub(pattern=r"[^0-9,-]", repl="", string=val)
        for i in list(filter(len, val.split(","))):
            if "-" in i:
                bound_lower, bound_upper = map(int, i.split("-"))
                result.extend(range(bound_lower, bound_upper + 1))
            else:
                result.append(int(i))
    return sorted(list(set(result)), key=int)


def to_pattern(context, param, value: str) -> List[Pattern]:
    # pylint: disable=unused-argument
    """Compiles a regular expression pattern from a string."""
    return [re.compile(pattern=v) for v in value]
