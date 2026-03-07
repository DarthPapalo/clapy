"""Clapy, a simple command line argument parser."""

from .argument import Arg, ArgAction
from .command import Command
from .parsed_command import ClapyParsedCommandError, ParsedCommand
from .style import ClapyRichStyle

__all__: list[str] = [
    "Arg",
    "ArgAction",
    "Command",
    "ParsedCommand",
    "ClapyRichStyle",
    "ClapyParsedCommandError",
]
