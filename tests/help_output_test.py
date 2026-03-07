from io import StringIO

import pytest
from rich.console import Console

from clapy.argument import Arg, ArgAction
from clapy.command import Command
from clapy.style import ClapyRichStyle


# Helper methods
def rich_to_ansi(markup: str) -> str:
    buffer = StringIO()
    console = Console(
        file=buffer,
        force_terminal=True,
    )
    console.print(
        markup, highlight=False, end=""
    )  # No end since we add it the assert statement
    return buffer.getvalue()


# Tests
def test_help_triggering():
    cli: Command = (
        Command("my-app")
        .arguments([Arg("debug").short("-d").flag().propagate()])
        .subcommand(
            Command("download-data").arguments(
                [Arg("output").short("-o"), Arg("additional").short("-a")]
            )
        )
        .mandatory_subcommand(False)
    )

    with pytest.raises(SystemExit) as ex:
        cli.parse_from(["download-data", "-o", "test"])
    assert ex.value.code == 1

    with pytest.raises(SystemExit) as ex:
        cli.parse_from(["download-data"])
    assert ex.value.code == 0

    with pytest.raises(SystemExit) as ex:
        cli.parse_from([])
    assert ex.value.code == 0


def test_default_help(capsys: pytest.CaptureFixture[str]):
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

    with pytest.raises(SystemExit) as ex:
        cli.parse_from(["--help"])
        assert ex.value.code == 0

    captured = capsys.readouterr()
    assert captured.out == (
        "Usage: my-app <NAME> <AGE> [--debug]\n"
        "This is my-app\n"
        "\n"
        "Positional arguments:\n"
        "    NAME: The user's name\n"
        "    AGE: The user's age\n"
        "\n"
        "Named arguments:\n"
        "    --debug: Display debug information\n"
        "\n"
    )


def test_rich_help(capsys: pytest.CaptureFixture[str]):
    cli = (
        Command("my-app")
        .help("This is my-app")
        .arguments(
            [
                Arg("debug")
                .long("--debug")
                .action(ArgAction.StoreTrue)
                .help("Display debug information"),
                Arg("name")
                # You can style the help text directly
                .help("The [blue]user's[/] name"),
                Arg("age").help("The [blue]user's[/] age").value_parser(int),
            ]
        )
    )

    with pytest.raises(SystemExit) as ex:
        cli.parse_from(["--help"])
        assert ex.value.code == 0

    captured = capsys.readouterr()
    assert captured.out == rich_to_ansi(
        (
            "[b magenta]Usage:[/b magenta] my-app <NAME> <AGE> [--debug]\n"
            "This is my-app\n"
            "\n"
            "[b magenta]Positional arguments:[/b magenta]\n"
            "    NAME: The [blue]user's[/] name\n"
            "    AGE: The [blue]user's[/] age\n"
            "\n"
            "[b magenta]Named arguments:[/b magenta]\n"
            "    --debug: Display debug information\n"
            "\n"
        )
    )


def test_inherit_help_print_method(capsys: pytest.CaptureFixture[str]):
    import functools

    print_method = functools.partial(print, "Inherited print argument~")

    cli: Command = (Command("my-app").help_print_method(print_method)).subcommand(
        Command("subcmd")
    )

    with pytest.raises(SystemExit) as ex:
        cli.parse_from(["subcmd", "--help"])
        assert ex.value.code == 0

    captured = capsys.readouterr()
    assert captured.out == ("Inherited print argument~ Usage: my-app subcmd\n\n")


def test_rich_style(capsys: pytest.CaptureFixture[str]):
    my_style = ClapyRichStyle(
        arg_help="cyan i", title="green b", usage="green b i", subcommand_help="red"
    )

    cli = (
        Command("my-app")
        .arguments(
            [
                Arg("name").help("This is the user's name"),
                Arg("age").help("This is the user's age").value_parser(int),
            ]
        )
        .help("This is my awesome command")
        .style(my_style)
        .subcommand(
            Command("subcmd")
            .help("My subcommand help")
            .argument(Arg("option").long("--option").help("My option"))
        )
    )

    with pytest.raises(SystemExit):
        cli.parse_from(["--help"])

    print("separator\n")
    # Test style inheritance
    with pytest.raises(SystemExit) as ex:
        cli.parse_from(["subcmd", "--help"])
        assert ex.value.code == 0

    captured = capsys.readouterr()
    assert captured.out == rich_to_ansi(
        (
            "[green b i]Usage:[/green b i] my-app <NAME> <AGE>\n"
            "This is my awesome command\n"
            "\n"
            "[green b]Subcommands:[/green b]\n"
            "    [i hot_pink]subcmd:[/i hot_pink] [red]My subcommand help[/red]\n"
            "\n"
            "[green b]Positional arguments:[/green b]\n"
            "    NAME: [cyan i]This is the user's name[/cyan i]\n"
            "    AGE: [cyan i]This is the user's age[/cyan i]\n"
            "\n"
            "separator\n"
            "\n"
            "[green b i]Usage:[/green b i] my-app subcmd [--option]\n"
            "My subcommand help\n"
            "\n"
            "[green b]Named arguments:[/green b]\n"
            "    --option: [cyan i]My option[/cyan i]\n"
            "\n"
        )
    )
