from dataclasses import dataclass


@dataclass(slots=True)
class ClapyRichStyle:
    command_help: str = ""
    usage: str = "b magenta"
    subcommand: str = "magenta"
    sub_command: str = "i hot_pink"

    title: str = "b magenta"

    positional_arg: str = ""
    named_arg: str = ""
    arg_help: str = ""
