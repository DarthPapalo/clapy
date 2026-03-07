"""ParsedCommand module from Clapy."""

from dataclasses import dataclass
from typing import Any

from clapy._errors import ERROR_MSGS, ClapyErrors
from clapy.argument import ArgAction, ParsedArg


@dataclass(slots=True)
class ClapyParsedCommandError(Exception):
    """
    Clapy Exception class for errors occurred when fetching from a ParsedCommand.
    """

    msg: str


class ParsedCommand:
    """
    Result obtained from parsing a `Command` and it's subcommands according to some arguments.
    Contains several methods to obtain the parsed arguments.
    """

    name: str
    _parsed_subcommand: ParsedCommand | None
    _parsed_arguments: dict[str, ParsedArg]

    def __init__(self, name: str) -> None:
        self.name = name
        self._parsed_subcommand = None
        self._parsed_arguments = {}

    def subcommand(self) -> ParsedCommand | None:
        """
        Returns the invoked parsed subcommand.
        """
        return self._parsed_subcommand

    def subcommand_name(self) -> str | None:
        """
        Returns the invoked parsed subcommand name or None if none where invoked.
        """
        if self._parsed_subcommand is not None:
            return self._parsed_subcommand.name
        return None

    # ====== Retrieve parsed arguments methods ======
    def get_any(self, id: str) -> Any:
        """
        Returns the value or values associated with an argument if it was parsed.
        Raises a ClapyParsedCommandError if no parsed argument with `id` exists.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            return parsed_arg.value
        raise ClapyParsedCommandError(
            ERROR_MSGS[ClapyErrors.INVALID_ARGUMENT_ID].format(id)
        )

    def get_one(self, id: str) -> Any:
        """
        Returns the value associated with an argument if it was parsed.
        Raises an ClapyParsedCommandError if there are several values (use `get_many` or `get_any` instead), or if no parsed argument with `id` exists.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action in (ArgAction.Set, ArgAction.Append)
            if isinstance(parsed_arg.value, tuple):
                raise ClapyParsedCommandError(
                    f"Using get_one to retrieve a tuple of values from argument '{id}'. Use get_many or get_any instead."
                )
            return parsed_arg.value
        raise ClapyParsedCommandError(
            ERROR_MSGS[ClapyErrors.INVALID_ARGUMENT_ID].format(id)
        )

    def get_many(self, id: str, *, force: bool = False) -> tuple[Any, ...]:
        """
        Returns the tuple of values associated with an argument if it was parsed.
        Raises an ClapyParsedCommandError if there is only one value (use `force` to get the value(s) into a tuple), or if no parsed argument with `id` exists.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action in (ArgAction.Set, ArgAction.Append)
            if not isinstance(parsed_arg.value, tuple):
                if force:
                    return (parsed_arg.value,)
                raise ClapyParsedCommandError(
                    f"Using get_many to retrieve a single value from argument '{id}'. Use get_one, get_any or this method with 'force' instead."
                )

            return parsed_arg.value
        raise ClapyParsedCommandError(
            ERROR_MSGS[ClapyErrors.INVALID_ARGUMENT_ID].format(id)
        )

    def get_flag(self, id: str) -> bool:
        """
        Returns the value of a flag argument (An argument with either the StoreTrue or StoreFalse action).
        Raises an ClapyParsedCommandError if the argument is not a flag, or if no parsed argument with `id` exists.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action in [ArgAction.StoreFalse, ArgAction.StoreTrue]
            return parsed_arg.value
        raise ClapyParsedCommandError(
            ERROR_MSGS[ClapyErrors.INVALID_ARGUMENT_ID].format(id)
        )

    def get_count(self, id: str) -> int:
        """
        Returns the amount of times a counted argument appeared (An argument with the Count action).
        Raises an ClapyParsedCommandError if the argument is not countable, or if no parsed argument with `id` exists.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action is ArgAction.Count
            return parsed_arg.value
        raise ClapyParsedCommandError(
            ERROR_MSGS[ClapyErrors.INVALID_ARGUMENT_ID].format(id)
        )
