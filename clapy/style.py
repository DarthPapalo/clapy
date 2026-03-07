from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class ClapyRichStyle:
    """
    Theme used to format Clapy output when using `rich`.
    """
    command_help: str = ""
    usage: str = "b magenta"
    subcommand: str = "i hot_pink"
    subcommand_help: str = ""

    title: str = "b magenta"

    positional_arg: str = ""
    named_arg: str = ""
    arg_help: str = ""
