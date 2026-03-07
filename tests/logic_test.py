import pytest

from clapy.argument import Arg, ArgAction
from clapy.command import Command, ParsedCommand


def test_basic_cli():
    cli: Command = (
        Command("my-app")
        .argument(Arg("positional"))
        .argument(Arg("option").default(5).value_parser(int))
    )

    parsed: ParsedCommand = cli.parse_from(["hello"])

    assert parsed.get_one("positional") == "hello"
    assert parsed.get_one("option") == 5


def test_lists_args():
    from pathlib import Path

    POSSIBLE_SOURCES: list[str] = ["Source1", "Source2", "Source3"]
    POSSIBLE_DATA_TYPES: list[str] = ["Genome", "Gene"]

    cli: Command = (
        Command("my-app")
        .argument(
            Arg("programs-paths")
            .long("--programs-paths")
            .value_parser(Path)
            .default(None)
        )
        .argument(
            Arg("data-sources")
            .long("--sources")
            .nargs(range(1, len(POSSIBLE_SOURCES)))
            .valid_values(POSSIBLE_SOURCES)
        )
        .argument(
            Arg("data-types")
            .long("--data-types")
            .nargs(range(1, len(POSSIBLE_DATA_TYPES)))
            .valid_values(POSSIBLE_DATA_TYPES)
        )
        .argument(
            Arg("keep-individuals")
            .long("--keep-individuals")
            .action(ArgAction.StoreTrue)
        )
        .argument(Arg("debug").long("--debug").short("-d").action(ArgAction.StoreTrue))
    )

    with pytest.raises(SystemExit) as ex:
        cli.parse_from(
            [
                "--programs-paths",
                "file.txt",
                "--sources",
                "Source1",
                "Source2",
                "Source3",
                "Source3",
                "--data-types",
                "Genome",
                "--keep-individuals",
                "--debug",
            ]
        )
        assert ex.value.code == 1

    with pytest.raises(SystemExit) as ex:
        cli.parse_from(
            [
                "--programs-paths",
                "file.txt",
                "--sources",
                "Source1",
                "BadSource",
                "--data-types",
                "Genome",
                "--keep-individuals",
                "--debug",
            ]
        )
        assert ex.value.code == 1

    parsed = cli.parse_from(
        [
            "--programs-paths",
            "file.txt",
            "--sources",
            "Source1",
            "Source2",
            "Source3",
            "--data-types",
            "Genome",
            "--keep-individuals",
            "--debug",
        ]
    )
    assert parsed.get_one("programs-paths") == Path("file.txt")
    assert parsed.get_many("data-sources") == ("Source1", "Source2", "Source3")
    assert parsed.get_many("data-types", force=True) == ("Genome",)
    assert parsed.get_flag("keep-individuals")
    assert parsed.get_flag("debug")


def test_complex_subcommands():
    from pathlib import Path

    cli: Command = (
        Command("my-app")
        .arguments(
            [
                Arg("verbose").long("--verbose").short("-v").count().propagate(),
                Arg("config")
                .long("--config")
                .propagate()
                .value_parser(Path)
                .default(""),
                Arg("tag").long("--tag").propagate().action(ArgAction.Append),
                Arg("input").value_parser(Path).propagate(),
            ]
        )
        .subcommand(
            Command("build")
            .arguments(
                [
                    Arg("release")
                    .long("--release")
                    .action(ArgAction.StoreTrue)
                    .propagate(),
                    Arg("opt-level").long("--opt-level").flag().propagate(),
                    Arg("targets").nargs("+").propagate(),
                ]
            )
            .subcommand(
                Command("image").arguments(
                    [
                        Arg("platform").long("--platform").nargs("+"),
                        Arg("label").long("--label").action(ArgAction.Append),
                        Arg("name"),
                    ]
                )
            )
        )
        .subcommand(
            Command("run").arguments(
                [
                    Arg("env").long("--env").action(ArgAction.Append),
                    Arg("rml").long("--rm").flag(),
                    Arg("command"),
                    Arg("args").nargs("*"),
                ]
            )
        )
    )

    parsed: ParsedCommand = cli.parse_from(
        [
            "input.txt",
            "-vv",
            "--tag",
            "alpha",
            "--tag",
            "beta",
            "build",
            "--opt-level",
            "--release",
            "core",
            "utils",
            "image",
            "myimg",
            "--platform",
            "linux",
            "arm64",
            "--label",
            "stage=prod",
            "--label",
            "commit=abc",
        ]
    )

    assert parsed.get_count("verbose") == 2
    assert parsed.get_one("config") == ""
    assert parsed.get_many("tag") == ("alpha", "beta")
    assert parsed.get_one("input") == Path("input.txt")

    sub_cmd: ParsedCommand | None = parsed.subcommand()
    assert sub_cmd is not None
    assert sub_cmd.get_flag("release")
    assert sub_cmd.get_flag("opt-level")
    assert sub_cmd.get_many("targets") == ("core", "utils")

    sub_sub_cmd: ParsedCommand | None = sub_cmd.subcommand()
    assert sub_sub_cmd is not None
    assert sub_sub_cmd.get_one("name") == "myimg"
    assert sub_sub_cmd.get_many("platform") == ("linux", "arm64")
    assert sub_sub_cmd.get_many("label") == ("stage=prod", "commit=abc")


def test_default_argument_values():
    cli: Command = Command("my-app").arguments(
        [
            Arg("mandatory"),
            Arg("option1").long("--option-one").default("Option_one_value"),
            Arg("option2").long("--option-two").default("Option_two_value"),
        ]
    )

    parsed = cli.parse_from(["mandatory_value"])

    assert parsed.get_one("mandatory") == "mandatory_value"
    assert parsed.get_one("option1") == "Option_one_value"
    assert parsed.get_one("option2") == "Option_two_value"

    with pytest.raises(SystemExit) as ex:
        cli.parse_from(["--option-one", "value_1"])
        assert ex.value.code == 1


def test_flag_arguments():
    cli: Command = Command("my-app").arguments(
        [
            Arg("verbose").long("--verbose").short("-v").flag(),
            Arg("debug").long("--debug").flag(),
            Arg("no-execute").long("--no-execute").flag(False),
        ]
    )

    parsed: ParsedCommand = cli.parse_from(["--verbose", "--no-execute"])

    assert parsed.get_flag("verbose")
    assert not parsed.get_flag("debug")
    assert not parsed.get_flag("no-execute")
