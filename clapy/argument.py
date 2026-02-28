"""Argument module from Clapy."""

from re import fullmatch
from enum import Enum
from dataclasses import dataclass
from typing import Any, Iterable, Literal
from collections.abc import Callable


LONG_ALIAS_REGEX: str = r"^--[^-].+$"
SHORT_ALIAS_REGEX: str = r"^-[^-]$"
SHORT_EXPANDABLE_ALIAS_REGEX: str = r"^-(.)\1+$"


@dataclass(slots=True)
class ClapyArgumentError(Exception):
    """
    Clapy Exception class for errors related to `Arg` objects.
    """

    msg: str


class ArgAction(Enum):
    """
    Enum representing the different possible actions from a parsed argument.
    """

    Set = "set"  # Sets a value
    Append = "append"  # Appends each occurence of the argument's values to a list
    StoreTrue = "store_true"  # Saves 'True'
    StoreFalse = "store_false"  # Saves 'False'
    Count = "count"  # Counts times the argument is parsed


@dataclass(slots=True)
class ParsedArg:
    value: Any
    action: ArgAction


@dataclass(slots=True)
class _ArgData:
    """
    Internal argument data used by Clapy.
    """

    id: str
    short: str | None = None
    long: str | None = None
    help: str | None = None
    action: ArgAction = ArgAction.Set
    default: Any = None
    nargs: int | Literal["+", "*"] | range = 1
    value_parser: Callable[[str], Any] = str
    propagate: bool = False
    valid_values: set[Any] | None = None

    def is_positional(self) -> bool:
        return self.short is None and self.long is None

    def is_named(self) -> bool:
        return not self.is_positional()

    def alias_help_text(self) -> str:
        return f"{self.short + ('/' if self.long is not None else '') if self.short is not None else ''}{self.long if self.long is not None else ''}"

    def validate(self) -> None:
        # Validate nargs
        match self.action:
            case ArgAction.Set | ArgAction.Append:
                invalid: bool = False
                value: int = -666
                if isinstance(self.nargs, int):
                    invalid = self.nargs <= 0
                    value = self.nargs
                elif isinstance(self.nargs, range):
                    invalid = self.nargs.start <= 0
                    value = self.nargs.start

                if invalid:
                    raise ClapyArgumentError(
                        f"Argument '{self.id}' can't have a negative number of associated values ({value})."
                    )

            case ArgAction.StoreTrue | ArgAction.StoreFalse | ArgAction.Count:
                if not isinstance(self.nargs, int) or self.nargs != 0:
                    raise ClapyArgumentError(
                        f"Argument '{self.id}' can't have multiple associated values with StoreTrue, StoreFalse or Count action."
                    )


class Arg:
    """
    A CLI argument that can be associated to a Command.
    """

    data: _ArgData

    def __init__(self, name: str) -> None:
        self.data = _ArgData(name)

    # ===============
    # Builder methods
    # ===============
    def short(self, short: str) -> Arg:
        """
        Add a short alias to an argument (Example: -a).
        Turns the argument into a named argument.
        """
        if fullmatch(SHORT_ALIAS_REGEX, short) is None:
            raise ClapyArgumentError(
                f"Short argument alias can only be a single character ({short})"
            )
        self.data.short = short
        return self

    def long(self, long: str) -> Arg:
        """
        Add a long alias to an argument (Example: --argument).
        Turns the argument into a named argument.
        """
        if fullmatch(LONG_ALIAS_REGEX, long) is None:
            raise ClapyArgumentError(
                f"Long argument alias should start with -- and have at least 2 characters ({long})."
            )
        self.data.long = long
        return self

    def help(self, text: str) -> Arg:
        """
        Help message for the argument.
        """
        self.data.help = text
        return self

    def action(self, action: ArgAction) -> Arg:
        """
        Action that defines the argument behaviour when parsed.
        """
        self.data.action = action
        match action:
            case ArgAction.StoreTrue | ArgAction.StoreFalse | ArgAction.Count:
                self.data.nargs = 0
        return self

    def default(self, value: Any) -> Arg:
        """
        A default value for the arugment.
        Makes the argument not required.
        """
        self.data.default = value
        return self

    def nargs(self, n: int | Literal["+", "*"] | range) -> Arg:
        """
        The number of associated values to this argument.
        StoreTrue, StoreFalse and Count actions can't have multiple associated values (nargs = 0).
        """
        self.data.nargs = n
        return self

    def value_parser(self, func: Callable[[str], Any]) -> Arg:
        """
        Function that turns the value strings into another type.
        """
        self.data.value_parser = func
        return self

    def propagate(self, value: bool) -> Arg:
        """
        Makes the argument propagate to subcommands.
        It will be parsed if the command is the parent of the subcommand called.
        """
        self.data.propagate = value
        return self

    def valid_values(self, valid_options: Iterable[Any]) -> Arg:
        """
        Set a list of options of which the values associated with the argument must be in.
        """
        self.data.valid_values = set(valid_options)
        return self

    def flag(self) -> Arg:
        """
        Makes the argument a flag.
        Same as setting the action to Action.StoreTrue.
        """
        self.action(ArgAction.StoreTrue)
        return self

    def count(self) -> Arg:
        """
        Makes the argument a count argument.
        Same as setting the action into Action.Count.
        """
        self.action(ArgAction.Count)
        return self
