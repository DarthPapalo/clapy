"""Clapy, a simple command line argument parser."""

from .argument import Arg, ArgAction
from .command import Command
from .parsed_command import (
    InexistentParsedArgumentError,
    NoParsedSubcommandError,
    NotMultipleValuesError,
    NotSingleValueError,
    ParsedCommand,
)
from .style import ClapyRichStyle

__all__: list[str] = [
    "Arg",
    "ArgAction",
    "Command",
    "ParsedCommand",
    "ClapyRichStyle",
    "InexistentParsedArgumentError",
    "NoParsedSubcommandError",
    "NotSingleValueError",
    "NotMultipleValuesError",
]
