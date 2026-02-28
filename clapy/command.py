"""Command module from Clapy."""

import sys
from re import fullmatch
from itertools import chain, zip_longest
from collections.abc import Callable
from collections import defaultdict
from typing import Any, Literal, Iterable, cast
from dataclasses import dataclass, field

from clapy.argument import (
    Arg,
    ParsedArg,
    ArgAction,
    _ArgData,
    ClapyArgumentError,
    SHORT_EXPANDABLE_ALIAS_REGEX,
    SHORT_ALIAS_REGEX,
    LONG_ALIAS_REGEX,
)


NAMED_ARGUMENTS_STOP_TOKEN = "--"
NAMED_ARGUMENT_INLINE_VALUE_SEPARATOR = "="


@dataclass(slots=True)
class ClapyParsingError(Exception):
    """
    Clapy Exception class for errors occurred during argument parsing.
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

    def get_any(self, id: str) -> Any | None:
        """
        Returns the value or values associated with an argument if it was parsed.
        Doesn't make any checks.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            return parsed_arg.value
        return None

    def get_one(self, id: str) -> Any | None:
        """
        Returns the value associated with an argument if it was parsed.
        Raises an Exception if there are several values, use `get_many` or `get_any` instead.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action in (ArgAction.Set, ArgAction.Append)
            if isinstance(parsed_arg.value, tuple):
                raise ClapyArgumentError(
                    f"Using get_one to retrieve a tuple of values from argument '{id}'. Use get_many or get_any instead."
                )
            return parsed_arg.value
        return None

    def get_many(self, id: str, *, force: bool = False) -> tuple[Any, ...] | None:
        """
        Returns the tuple of values associated with an argument if it was parsed.
        Raises an Exception if there is only one value, use `force` to get the value(s) into a tuple.
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action in (ArgAction.Set, ArgAction.Append)
            if not isinstance(parsed_arg.value, tuple):
                if force:
                    return (parsed_arg.value,)
                raise ClapyArgumentError(
                    f"Using get_many to retrieve a single value from argument '{id}'. Use get_one, get_any or this method with 'force' instead."
                )

            return parsed_arg.value
        return None

    def get_flag(self, id: str) -> bool | None:
        """
        Returns the value of a flag argument (An argument with either the StoreTrue or StoreFalse action).
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action in [ArgAction.StoreFalse, ArgAction.StoreTrue]
            return parsed_arg.value
        return None

    def get_count(self, id: str) -> int | None:
        """
        Returns the amount of times a counted argument appeared (An argument with the Count action).
        """
        parsed_arg: ParsedArg | None = self._parsed_arguments.get(id, None)
        if parsed_arg is not None:
            assert parsed_arg.action is ArgAction.Count
            return parsed_arg.value
        return None


@dataclass(slots=True)
class _CommandData:
    """
    Internal Command data used by Clapy.
    """

    name: str
    mandatory_subcommand: bool = True
    no_args_requests_help: bool = True
    help_options: list[str] = field(default_factory=lambda: ["--help", "-h"])
    help_print_method: Callable[[str], None] = print
    help: str | None = None
    arguments: list[Arg] = field(default_factory=list)
    subcommands: dict[str, Command] = field(default_factory=dict)


@dataclass(slots=True)
class Command:
    """
    A command that can be called through a CLI.
    Has several methods to customize its behaviour.
    """

    data: _CommandData
    _parent: Command | None

    def __init__(self, name: str) -> None:
        self.data = _CommandData(name)
        self._parent = None

    # =============================================
    #                Builder methods
    # =============================================
    def mandatory_subcommand(self, yes: bool) -> Command:
        """
        If the Command has subcommands, using one of them will be mandatory.
        """
        self.data.mandatory_subcommand = yes
        return self

    def help_options(self, options: list[str]) -> Command:
        """
        List of the options that can be specified to show the Command help.
        Default: [-h, --help]
        """
        self.data.help_options = options
        return self

    def help_print_method(self, method: Callable[[str], None]) -> Command:
        """
        Python method used to print the help messages to the CLI.
        Default: std.print()
        """
        self.data.help_print_method = method
        return self

    def help(self, text: str) -> Command:
        """
        The help message for the command.
        """
        self.data.help = text
        return self

    def argument(self, arg: Arg) -> Command:
        """
        Adds an argument to the command.
        """
        arg.data.validate()
        self.data.arguments.append(arg)
        return self

    def arguments(self, args: Iterable[Arg]) -> Command:
        """
        Adds multiple arguments to the command.
        """
        for arg in args:
            arg.data.validate()
            self.data.arguments.append(arg)
        return self

    def subcommand(self, c: Command) -> Command:
        """
        Adds a subcommand to the command.
        """
        assert c.data.name not in self.data.subcommands
        self.data.subcommands[c.data.name] = c
        c._parent = self
        return self

    # =============================================
    #                 Info methods
    # =============================================
    def _show_help(self) -> None:
        help_print = self.data.help_print_method

        # ========= Print current command help =========
        current_command_help: str = ""
        if self.data.help is not None:
            current_command_help = self.data.help + "\n"

        # ================ Print usage =================
        full_command_path: str = f"{self.data.name}"
        current_command: Command = self
        while current_command._parent is not None:
            full_command_path = (
                f"{current_command._parent.data.name} " + full_command_path
            )
            current_command = current_command._parent

        full_positional_names: str = ""
        for p in [a.data for a in self.data.arguments if a.data.is_positional()]:
            full_positional_names += f"<{p.id.upper()}> "

        full_named_names: str = ""
        for n in [a.data for a in self.data.arguments if a.data.is_named()]:
            full_named_names += f" {n.alias_help_text()} |"

        # ========= Print Subcommands =========
        subcommands_available: str = ""
        if len(self.data.subcommands) > 0:
            subcommands_available += "Subcommands:\n"
            for sub_cmd in self.data.subcommands.values():
                subcommands_available += f"    {sub_cmd.data.name}{f': {sub_cmd.data.help}' if sub_cmd.data.help is not None else ''}\n"

        # ========= Print arguments ===========
        named_arguments: str = (
            "Named arguments:\n"
            if len([a for a in self.data.arguments if a.data.is_named()]) > 0
            else ""
        )
        positional_arguments: str = (
            "Positional arguments:\n"
            if len([a for a in self.data.arguments if a.data.is_positional()]) > 0
            else ""
        )
        for arg in self.data.arguments:
            if arg.data.is_named():
                named_arguments += f"    {arg.data.alias_help_text()}{f': {arg.data.help}' if arg.data.help is not None else ''}\n"
            else:
                positional_arguments += f"    {arg.data.id.upper()}{f': {arg.data.help}' if arg.data.help is not None else ''}\n"

        # ========= Print propagated arguments ===========
        propagated_arguments: str = ""
        propagated_positional_arguments_strings: dict[str, list[str]] = defaultdict(
            list[str]
        )
        propagated_named_arguments_strings: dict[str, list[str]] = defaultdict(
            list[str]
        )
        sub_cmds: list[str] = []
        last_parent = self._parent

        while last_parent is not None:
            propagated_positional_args: list[Arg] = [
                a
                for a in last_parent.data.arguments
                if a.data.is_positional() and a.data.propagate
            ]
            propagated_named_args: list[Arg] = [
                a
                for a in last_parent.data.arguments
                if a.data.is_named() and a.data.propagate
            ]

            propagated_named_arguments = ""

            for arg in propagated_positional_args:
                propagated_positional_arguments_strings[last_parent.data.name].append(
                    f"{arg.data.id.upper()}{f': {arg.data.help}' if arg.data.help is not None else ''}"
                )
            for arg in propagated_named_args:
                propagated_named_arguments_strings[last_parent.data.name].append(
                    f"{arg.data.alias_help_text()}{f': {arg.data.help}' if arg.data.help is not None else ''}"
                )

            sub_cmds.insert(0, last_parent.data.name)
            last_parent = last_parent._parent

        propagated_arguments += "Propagated arguments:\n" if len(sub_cmds) > 0 else ""
        for sub_cmd in sub_cmds:
            propagated_sub_cmd_arguments = f"    {sub_cmd}:\n"

            propagated_positional_arguments: str = (
                "        Positional arguments:\n"
                if len(propagated_positional_arguments_strings) > 0
                else ""
            )
            propagated_named_arguments: str = (
                "        Named arguments:\n"
                if len(propagated_named_arguments_strings) > 0
                else ""
            )

            for propagated_arg in propagated_positional_arguments_strings[sub_cmd]:
                propagated_positional_arguments += f"            {propagated_arg}\n"
            for propagated_arg in propagated_named_arguments_strings[sub_cmd]:
                propagated_named_arguments += f"            {propagated_arg}\n"

            propagated_sub_cmd_arguments += propagated_positional_arguments
            propagated_sub_cmd_arguments += "\n" + propagated_named_arguments

            propagated_arguments += propagated_sub_cmd_arguments

        help_print(
            f"{current_command_help}"
            f"Usage: {full_command_path} {full_positional_names}[{full_named_names[:-2]}]"
            "\n"
            "\n"
            f"{subcommands_available}\n"
            f"{positional_arguments}\n"
            f"{named_arguments}\n"
            f"{propagated_arguments}"
        )

        sys.exit(0)

    # =============================================
    #                Parsing methods
    # =============================================
    def _discover_command_path(
        self, args: list[str]
    ) -> tuple[list[Command], list[list[str]]]:
        """
        Returns the list of commands that need to parse the list of args that go after their index.
        Example:
            command_chain = [self, cmd1, cmd2, cmd3]
            subarg_lists = [<list1>, <list2>, <list3>, <list4>]

            self is the root -> Can parse all sublists
            cmd1 parses: subarg_lists[1:]
            cmd2 parses: subarg_lists[2:]
            cmd2 parses: subarg_lists[3:]
        """
        command_chain: list[Command] = [self]
        subarg_lists: list[list[str]] = []
        last_subcommand_pos: int = -1

        for i, a in enumerate(args):
            if _is_named_arg(a):
                if a in command_chain[-1].data.help_options:
                    command_chain[-1]._show_help()
                continue
            elif _is_positional_arg(a):
                possible_subcommand: Command | None = command_chain[
                    -1
                ].data.subcommands.get(a)
                if possible_subcommand is not None:  # Subcommand found
                    # Add arguments before command name until previous command
                    subarg_lists.append(args[last_subcommand_pos + 1 : i])
                    last_subcommand_pos = i
                    command_chain.append(possible_subcommand)

        subarg_lists.append(
            args[last_subcommand_pos + 1 :]
        )  # Add remaining args after last subcommand

        # Expand special argument forms
        subarg_lists = list(map(_expand_args, subarg_lists))

        # Assert each command has an arg_list after it
        assert len(command_chain) == len(subarg_lists)

        # Check no args on command
        for i, args_list in enumerate(subarg_lists):
            if len(args_list) == 0:
                if command_chain[i].data.no_args_requests_help:
                    command_chain[i]._show_help()
                raise ClapyParsingError(
                    f"No arguments supplied for command '{command_chain[i].data.name}'."
                )

        # Check mandatory subcommand
        if (
            command_chain[-1].data.mandatory_subcommand
            and len(command_chain[-1].data.subcommands) > 0
        ):
            options: str = ", ".join(sub for sub in command_chain[-1].data.subcommands)
            raise ClapyParsingError(
                f"Mandatory subcommand expected for command '{command_chain[-1].data.name}'. Options: {options}"
            )

        return (command_chain, subarg_lists)

    def _parse_and_consume_named_args(
        self, arg_lists: list[list[str]], *, parse_only_propagated: bool
    ) -> dict[str, ParsedArg]:
        """
        Parses the `Command` named arguments into a dict[arg_id: ParsedArg] using argument lists.
        Consumes arguments from the lists.
        """
        # Build map with arg IDs to _ArgData
        named_args_ids_map: dict[str, _ArgData] = {}
        # Build map with arg short/long alias to its _ArgData
        named_args_map: dict[str, _ArgData] = {}
        for arg in self.data.arguments:
            # Only parsing named arguments here
            if not arg.data.is_named():
                continue
            if parse_only_propagated and not arg.data.propagate:
                continue
            named_args_ids_map[arg.data.id] = arg.data
            if arg.data.long is not None:
                named_args_map[arg.data.long] = arg.data
            if arg.data.short is not None:
                named_args_map[arg.data.short] = arg.data

        consumed_values: dict[str, list[list[str]]] = defaultdict(
            list[list[str]]
        )  # Arg alias : List of lists of consumed values

        # Parse named arguments from lists
        for args in arg_lists:
            i: int = 0
            while i < len(args):
                arg: str = args[i]
                if _is_named_arg(arg):
                    possible_arg_data: _ArgData | None = named_args_map.get(arg)
                    if possible_arg_data is not None:
                        # This will consume the value(s)
                        consumed_values[arg].append(
                            _parse_and_consume_values(
                                args, i + 1, possible_arg_data, arg
                            )
                        )
                        del args[i]  # Consume arg alias
                        # 'i' doesn't need to change since we consumed the values following it
                        continue
                i += 1

        parsed_args: dict[str, ParsedArg] = {}  # Arg id : ParsedArg

        for alias in consumed_values:
            arg_data: _ArgData = named_args_map[alias]
            if arg_data.id not in named_args_ids_map:
                raise ClapyParsingError(f"Repeated argument '{alias}'.")

            parsed_arg: ParsedArg | None = None
            match arg_data.action:
                case ArgAction.StoreTrue | ArgAction.StoreFalse:
                    parsed_arg = ParsedArg(
                        arg_data.action is ArgAction.StoreTrue, arg_data.action
                    )
                case ArgAction.Count:
                    parsed_arg = ParsedArg(len(consumed_values[alias]), arg_data.action)
                case ArgAction.Set | ArgAction.Append:
                    if (
                        len(consumed_values[alias]) > 1
                        and arg_data.action is ArgAction.Set  # Doesn't apply to Append
                    ):
                        raise ClapyParsingError(f"Repeated argument '{alias}'.")
                    try:
                        flattened_values: tuple[str, ...] = tuple(
                            chain.from_iterable(consumed_values[alias])
                        )
                        parsed_values: tuple[Any, ...] = tuple(
                            map(arg_data.value_parser, flattened_values)
                        )
                        # Check for valid values
                        if arg_data.valid_values is not None:
                            valid_values: str = ", ".join(arg_data.valid_values)
                            for v in parsed_values:
                                if v not in arg_data.valid_values:
                                    raise ClapyParsingError(
                                        f"Invalid value for named argument '{alias}': '{v}'. (Valid values: {valid_values})"
                                    )
                    except ValueError:
                        values: str = ", ".join(flattened_values)
                        raise ClapyParsingError(
                            f"Wrong value{'s' if len(flattened_values) > 1 else ''} type for argument '{alias}'. Wrong values: {values}."
                        )

                    if len(parsed_values) == 1:
                        parsed_arg = ParsedArg(parsed_values[0], arg_data.action)
                    else:
                        parsed_arg = ParsedArg(parsed_values, arg_data.action)

            assert parsed_arg is not None
            parsed_args[arg_data.id] = parsed_arg
            # Remove the id so we know it was parsed
            named_args_ids_map.pop(arg_data.id)

        # Check unparsed arguments
        for arg_data in named_args_ids_map.values():
            # Manage actions default values.
            match arg_data.action:
                case ArgAction.Set | ArgAction.Append:
                    if arg_data.default is not None:
                        # Use default value if available
                        parsed_args[arg_data.id] = ParsedArg(
                            arg_data.default, arg_data.action
                        )
                        continue
                case ArgAction.StoreTrue | ArgAction.StoreFalse:
                    # If they don't appear, use negated value.
                    parsed_args[arg_data.id] = ParsedArg(
                        arg_data.action is not ArgAction.StoreTrue, arg_data.action
                    )
                    continue
                case ArgAction.Count:
                    # If none appeared, set count to 0.
                    parsed_args[arg_data.id] = ParsedArg(0, arg_data.action)
                    continue
            raise ClapyParsingError(
                f"Missing required named argument '{arg_data.long if arg_data.long is not None else ''}{'/' if arg_data.long is not None and arg_data.short is not None else ''}{arg_data.short if arg_data.short is not None else ''}'."
            )

        return parsed_args

    def _parse_and_consume_positional_args(
        self, arg_lists: list[list[str]], *, parse_only_propagated: bool
    ) -> dict[str, ParsedArg]:
        """
        Parses the `Command` positional arguments into a dict[arg_id: ParsedArg] using argument lists.
        Consumes arguments from the lists.
        """

        if len(arg_lists) == 0:
            return {}  # No arg to parse

        # Build positional _ArgData list
        positional_args_data: list[_ArgData] = []
        for arg in self.data.arguments:
            # only parsing positional arguments here
            if not arg.data.is_positional():
                continue
            if parse_only_propagated and not arg.data.propagate:
                continue
            positional_args_data.append(arg.data)

        consumed_values: list[list[str]] = []  # List of List

        positional_data_i: int = 0
        # Parse positional arguments from lists
        for args in arg_lists:
            arg_i: int = 0
            while arg_i < len(args) and positional_data_i < len(
                positional_args_data
            ):  # We also check if there are more positional arguments to parse
                arg: str = args[arg_i]
                if _is_positional_arg(arg):
                    arg_data: _ArgData = positional_args_data[positional_data_i]
                    # This will consume the value(s)
                    consumed_values.append(
                        _parse_and_consume_values(args, arg_i, arg_data, arg_data.id)
                    )
                    # 'i' doesn't need to change since we consumed the values following it
                    positional_data_i += (
                        1  # Move the index to the next positional argument definition
                    )
                arg_i += 1

        parsed_args: dict[str, ParsedArg] = {}  # Arg id : ParsedArg

        for arg_data, values in cast(
            tuple[tuple[_ArgData, list[str] | None]],
            tuple(
                zip_longest(
                    positional_args_data,
                    consumed_values,
                )
            ),
        ):
            parsed_arg: ParsedArg | None = None
            assert (
                arg_data.action is ArgAction.Set
            )  # Positional arguments must be Action.Set
            # Check if no values where consumed for the argument
            if values is None:
                if arg_data.default is not None:
                    # We use the default value if we can
                    parsed_arg = ParsedArg(arg_data.default, arg_data.action)
                else:
                    raise ClapyParsingError(
                        f"Missing required positional argument: '{arg_data.id}'."
                    )
            else:
                try:
                    parsed_values: tuple[Any, ...] = tuple(
                        map(arg_data.value_parser, values)
                    )
                except ValueError:
                    raise ClapyParsingError(
                        f"Wrong value{'s' if len(values) > 1 else ''} type for argument '{arg_data.id}'. Wrong values: {values}."
                    )

                # Check for valid values
                if arg_data.valid_values is not None:
                    valid_values: str = ", ".join(arg_data.valid_values)
                    for v in parsed_values:
                        if v not in arg_data.valid_values:
                            raise ClapyParsingError(
                                f"Invalid value for positional argument '{arg_data.id}': '{v}'. (Valid values: {valid_values})"
                            )

                if len(parsed_values) == 1:
                    parsed_arg = ParsedArg(parsed_values[0], arg_data.action)
                else:
                    parsed_arg = ParsedArg(parsed_values, arg_data.action)

            assert parsed_arg is not None
            parsed_args[arg_data.id] = parsed_arg

        return parsed_args

    def parse_from(self, args: list[str]) -> ParsedCommand:
        """
        Parses the Command using a list of arguments.
        """
        try:
            parsed: ParsedCommand | None = None
            command_chain, subarg_lists = self._discover_command_path(args)
            parsed_command_chain: list[ParsedCommand] = []

            # 1. Parse named arguments from sub -> root (We populate de parsed_command_chain here)
            for i, cmd in enumerate(command_chain[::-1]):
                parsed_cmd = ParsedCommand(cmd.data.name)
                parsed_cmd._parsed_arguments = cmd._parse_and_consume_named_args(
                    subarg_lists[-(i + 1) :], parse_only_propagated=(i != 0)
                )
                # We insert them from the front since we are going through the cmd chain in reverse order
                parsed_command_chain.insert(0, parsed_cmd)

            # 2. Parse positionals from root -> sub (We add them to the parsed_command_chain ParsedCommand objects)
            for i, cmd in enumerate(command_chain):
                parsed_command_chain[i]._parsed_arguments.update(
                    cmd._parse_and_consume_positional_args(
                        subarg_lists[i:],
                        parse_only_propagated=(i + 1 != len(command_chain)),
                    )
                )

            # 3. Check for extra unknown arguments:
            for sub_list in subarg_lists:
                if len(sub_list) > 0:
                    unknown_arguments = ", ".join(sub_list)
                    raise ClapyParsingError(
                        f"Unknown extra arguments: '{unknown_arguments}'."
                    )

            # 4. Nest all ParsedCommands
            parsed = parsed_command_chain[0]
            last_pc: ParsedCommand = parsed
            for pc in parsed_command_chain[1:]:
                last_pc._parsed_subcommand = pc
                last_pc = pc

            return parsed
        except ClapyParsingError as e:
            print(e.msg)
            # raise e  # Enable this line so pytest can catch exceptions
            sys.exit()

    def parse(self) -> ParsedCommand:
        """
        Parses the Command using sys.argv.
        """

        return self.parse_from(sys.argv)


# Helper methods
def _expand_args(args: list[str]) -> list[str]:
    expanded: list[str] = []

    for arg in args:
        # Expandable named_argument=value (--arg=value --> --arg value)
        if _is_named_arg(arg) and "=" in arg:
            name, value = arg.split("=", 1)
            expanded.append(name)
            expanded.append(value)
            continue

        # Expandable short alias named args (-vvv --> -v -v -v)
        if _is_short_expandable_arg(arg):
            for char in arg[1:]:
                expanded.append(f"-{char}")
            continue

        expanded.append(arg)

    return expanded


def _is_named_arg(arg: str) -> bool:
    return (
        _is_short_alias_arg(arg)
        or _is_long_alias_arg(arg)
        or _is_short_expandable_arg(arg)
    )


def _is_positional_arg(arg: str) -> bool:
    return not _is_named_arg(arg)


def _is_short_expandable_arg(arg: str) -> bool:
    return fullmatch(SHORT_EXPANDABLE_ALIAS_REGEX, arg) is not None


def _is_short_alias_arg(arg: str) -> bool:
    return fullmatch(SHORT_ALIAS_REGEX, arg) is not None


def _is_long_alias_arg(arg: str) -> bool:
    return fullmatch(LONG_ALIAS_REGEX, arg) is not None


def _nargs_bounds(nargs: int | Literal["+", "*"] | range) -> tuple[int, int | None]:
    """
    Returns (min, max) where max=None means infinite.
    """
    if isinstance(nargs, int):
        return nargs, nargs

    if nargs == "+":
        return 1, None
    if nargs == "*":
        return 0, None

    if isinstance(nargs, range):
        return nargs.start, nargs.stop

    raise TypeError(f"Invalid nargs: {nargs}")


def _parse_and_consume_values(
    args: list[str], start: int, arg_data: _ArgData, arg_name: str
) -> list[str]:
    """
    Consumes the values required by an arg starting from 'start'.
    """
    match arg_data.action:
        case ArgAction.StoreTrue | ArgAction.StoreFalse | ArgAction.Count:
            return ["dummy"]
        case ArgAction.Set | ArgAction.Append:
            min_n, max_n = _nargs_bounds(arg_data.nargs)

            values: list[str] = []

            i: int = start
            while i < len(args):
                arg: str = args[i]
                # If next value is a named argument or end of named arguments
                if _is_named_arg(arg) or arg == NAMED_ARGUMENTS_STOP_TOKEN:
                    # Minimum is reached -> stop consuming values
                    if len(values) >= min_n:
                        break
                    # Or minimum not reached
                    else:
                        raise ClapyParsingError(
                            f"Missing argument values for '{arg_name}'. Received {len(values)}, expected at least {min_n}."
                        )

                values.append(arg)
                i += 1

                # Check max values obtained
                if max_n is not None and len(values) == max_n:
                    break

            # Consume values from args
            del args[start:i]

            return values
