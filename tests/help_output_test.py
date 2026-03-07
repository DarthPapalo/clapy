import pytest
from clapy.argument import Arg, ArgAction
from clapy.command import Command


def test_default_help():
    cli = (
        Command("my-app")
        .arguments(
            [
                Arg("debug")
                .long("--debug")
                .action(ArgAction.StoreTrue)
                .help("Display debug information"),
                Arg("name").help("The user's name"),
                Arg("age").help("The user's age").value_parser(int),
            ]
        )
        .help("This is my-app")
        .help_print_method(print)
    )

    with pytest.raises(SystemExit):
        cli.parse_from(["--help"])


def test_rich_help():
    cli = (
        Command("my-app")
        .arguments(
            [
                Arg("debug")
                .long("--debug")
                .action(ArgAction.StoreTrue)
                .help("Display debug information"),
                # You can style the help directly
                Arg("name").help("The [blue]user's[/] name"),
                Arg("age").help("The [blue]user's[/] age").value_parser(int),
            ]
        )
        .help("This is my-app")
    )
    
    with pytest.raises(SystemExit):
        cli.parse_from(["--help"])


def test_inherit_help_print_method():
    import functools

    print_method = functools.partial(print, "Inherited print argument~")

    cli = (
            Command("my-app")
            .arguments(
                [
                    Arg("debug")
                        .long("--debug")
                        .action(ArgAction.StoreTrue)
                        .help("Display debug information"),
                    Arg("name").help("The user's name"),
                    Arg("age").help("The user's age").value_parser(int),
                ]
            )
            .help("This is my-app")
            .help_print_method(print_method)
        ).subcommand(Command("subcmd"))

    with pytest.raises(SystemExit):
        cli.parse_from(["--help"])