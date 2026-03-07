"""ParsedCommand module from Clapy."""

from dataclasses import dataclass
from typing import Any

from clapy.argument import ArgAction, ParsedArg


@dataclass(slots=True)
class InexistentParsedArgumentError(Exception):
    """
    Clapy Exception class for errors occurred when fetching inexistent arguments from a ParsedCommand.
    """

    id: str

    def __repr__(self) -> str:
        return f"No parsed argument found for id '{self.id}'"


@dataclass(slots=True)
class NoParsedSubcommandError(Exception):
    """
    Clapy Exception class for errors occurred when fetching a inexistent subcommand from a ParsedCommand.
    """

    def __repr__(self) -> str:
        return "No parsed subcommand found for ParsedCommand"


@dataclass(slots=True)
class NotSingleValueError(Exception):
    """
    Clapy Exception class for errors occurred when fetching a single value using `get_many` wihtout forcing a tuple.
    """

    id: str

    def __repr__(self) -> str:
        return f"Using `get_one` to retrieve a tuple of values from argument '{id}'. Use `get_many` or `get_any` instead"


@dataclass(slots=True)
class NotMultipleValuesError(Exception):
    """
    Clapy Exception class for errors occurred when fetching multiple values using `get_one`.
    """

    id: str

    def __repr__(self) -> str:
        return f"Using `get_many` to retrieve a single value from argument '{id}'. Use `get_one`, `get_any` or this method with `force` instead"


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

    def subcommand(self) -> ParsedCommand:
        """
        Returns the invoked parsed subcommand.
        """
        if self._parsed_subcommand is not None:
            return self._parsed_subcommand
        raise NoParsedSubcommandError()

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
        raise InexistentParsedArgumentError(id)

    def get_one(self, id: str) -> Any:
        """
        Returns the value associated with an argument if it was parsed.
        Raises an ClapyParsedCommandError if there are several values (use `get_many` or `get_any` instead), or if no parsed argument with `id` exists.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action in (ArgAction.Set, ArgAction.Append)
            if isinstance(parsed_arg.value, tuple):
                raise NotSingleValueError(id)
            return parsed_arg.value
        raise InexistentParsedArgumentError(id)

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
                raise NotMultipleValuesError(id)

            return parsed_arg.value
        raise InexistentParsedArgumentError(id)

    def get_flag(self, id: str) -> bool:
        """
        Returns the value of a flag argument (An argument with either the StoreTrue or StoreFalse action).
        Raises an ClapyParsedCommandError if the argument is not a flag, or if no parsed argument with `id` exists.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action in [ArgAction.StoreFalse, ArgAction.StoreTrue]
            return parsed_arg.value
        raise InexistentParsedArgumentError(id)

    def get_count(self, id: str) -> int:
        """
        Returns the amount of times a counted argument appeared (An argument with the Count action).
        Raises an ClapyParsedCommandError if the argument is not countable, or if no parsed argument with `id` exists.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action is ArgAction.Count
            return parsed_arg.value
        raise InexistentParsedArgumentError(id)
