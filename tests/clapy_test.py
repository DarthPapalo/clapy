import pytest
from clapy.argument import Arg, ArgAction
from clapy.command import Command, ParsedCommand, ClapyParsingError


def test_basic_cli():
    cli: Command = (
        Command("test-prog")
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
        Command("lists-test")
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

    with pytest.raises(ClapyParsingError):
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

    with pytest.raises(ClapyParsingError):
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

    cli = (
        Command("my-app")
        .arguments(
            [
                Arg("verbose").long("--verbose").short("-v").count().propagate(True),
                Arg("config")
                .long("--config")
                .propagate(True)
                .value_parser(Path)
                .default(""),
                Arg("tag").long("--tag").propagate(True).action(ArgAction.Append),
                Arg("input").value_parser(Path).propagate(True),
            ]
        )
        .subcommand(
            Command("build")
            .arguments(
                [
                    Arg("release")
                    .long("--release")
                    .action(ArgAction.StoreTrue)
                    .propagate(True),
                    Arg("opt-level").long("--opt-level").flag().propagate(True),
                    Arg("targets").nargs("+").propagate(True),
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
