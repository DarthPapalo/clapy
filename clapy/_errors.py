"Clapy error messages."

from enum import Enum, auto
import importlib.util


ARGUMENT_RICH_ERROR_PREFIX = "[bright_red]Argument error:[/bright_red] "
ARGUMENT_ERROR_PREFIX = "Argument error: "
PARSING_RICH_ERROR_PREFIX = "[bright_red]Parsing error:[/bright_red] "
PARSING_ERROR_PREFIX = "Parsing error: "

class ClapyErrors(Enum):
    # Parsing errors
    NO_ARGUMENTS = auto()
    MISSING_MANDATORY_SUBCOMMAND = auto()
    REPEATED_ARGUMENT = auto()
    INVALID_NAMED_ARGUMENT_VALUES = auto()
    WRONG_VALUE_TYPE = auto()
    MISSING_REQUIRED_NAMED_ARGUMENT = auto()
    MISSING_REQUIRED_POSITIONAL_ARGUMENT = auto()
    INVALID_POSITIONAL_ARGUMENT_VALUES = auto()
    UNKNOWN_EXTRA_ARGUMENTS = auto()
    MISSING_VALUES = auto()
    # Argument errors
    NEGATIVE_VALUES_AMOUNT = auto()
    TOO_HIGH_VALUES_AMOUNT = auto()
    INVALID_SHORT_ALIAS = auto()
    INVALID_LONG_ALIAS = auto()


using_rich: bool = False

try:
    using_rich = importlib.util.find_spec("rich") is not None
except ValueError:
    # Error is raised if rich is imported but is not Accessible
    using_rich = False

ERROR_MSGS: dict[ClapyErrors, str] = {}

if using_rich:
    # Error msgs WITH rich implementation
    ERROR_MSGS = {
        ClapyErrors.NO_ARGUMENTS: "No arguments supplied for command [yellow]'{}'",
        ClapyErrors.MISSING_MANDATORY_SUBCOMMAND: (
            "Missing mandatory subcommand for command [yellow]'{}'[/yellow]. Options: [cyan]{}[/cyan]\n"
            "[bright_black]Note: Use [grey78]{}[/grey78] to show command help[/bright_black]"
        ),
        ClapyErrors.REPEATED_ARGUMENT: "Repeated argument [yellow]'{}'",
        ClapyErrors.INVALID_NAMED_ARGUMENT_VALUES: "Invalid value for named argument [yellow]'{}'[/yellow]: [bright_red]'{}'[/bright_red]. Valid values: [cyan]{}",
        ClapyErrors.WRONG_VALUE_TYPE: "Wrong value type{} for argument [yellow]'{}'[/yellow]. Wrong values: [cyan]{}",
        ClapyErrors.MISSING_REQUIRED_NAMED_ARGUMENT: "Missing required named argument [yellow]'{}{}{}'",
        ClapyErrors.MISSING_REQUIRED_POSITIONAL_ARGUMENT: "Missing required positional argument: [yellow]'{}'",
        ClapyErrors.INVALID_POSITIONAL_ARGUMENT_VALUES: "Invalid value for positional argument [yellow]'{}'[/yellow]: [bright_red]'{}'[/bright_red]. Valid values: [cyan]{}",
        ClapyErrors.UNKNOWN_EXTRA_ARGUMENTS: "Unknown extra arguments: [yellow]'{}'",
        ClapyErrors.MISSING_VALUES: "Missing argument values for [yellow]'{}'[/yellow]. Received [bright_red]{}[/bright_red], expected at least [cyan]{}",
        ClapyErrors.NEGATIVE_VALUES_AMOUNT: "Argument [yellow]'{}'[/yellow] can't have a negative number of associated values: [bright_red]{}",
        ClapyErrors.TOO_HIGH_VALUES_AMOUNT: "Argument [yellow]'{}'[/yellow] can't have multiple associated values with [cyan]StoreTrue, StoreFalse or Count[/cyan] actions",
        ClapyErrors.INVALID_SHORT_ALIAS: "Short argument alias can only be a single character: [bright_red]{}",
        ClapyErrors.INVALID_LONG_ALIAS: "Long argument alias should start with -- and have at least 2 characters: [bright_red]{}",
    }
else:
    # Error msgs WITHOUT rich implementation
    ERROR_MSGS = {
        ClapyErrors.NO_ARGUMENTS: "No arguments supplied for command '{}'",
        ClapyErrors.MISSING_MANDATORY_SUBCOMMAND: (
            "Missing mandatory subcommand for command '{}'. Options: {}\n"
            "Note: Use {} to show command help"
        ),
        ClapyErrors.REPEATED_ARGUMENT: "Repeated argument '{}'",
        ClapyErrors.INVALID_NAMED_ARGUMENT_VALUES: "Invalid value for named argument '{}': '{}' (Valid values: {})",
        ClapyErrors.WRONG_VALUE_TYPE: "Wrong value type{} for argument '{}'. Wrong values: {}",
        ClapyErrors.MISSING_REQUIRED_NAMED_ARGUMENT: "Missing required named argument '{}{}{}'",
        ClapyErrors.INVALID_POSITIONAL_ARGUMENT_VALUES: "Invalid value for positional argument '{}': '{}'. Valid values: {}",
        ClapyErrors.UNKNOWN_EXTRA_ARGUMENTS: "Unknown extra arguments: '{}'",
        ClapyErrors.MISSING_VALUES: "Missing argument values for '{}'. Received {}, expected at least {}",
        ClapyErrors.NEGATIVE_VALUES_AMOUNT: "Argument '{}' can't have a negative number of associated values: {}",
        ClapyErrors.TOO_HIGH_VALUES_AMOUNT: "Argument '{}' can't have multiple associated values with StoreTrue, StoreFalse or Count actions",
        ClapyErrors.INVALID_SHORT_ALIAS: "Short argument alias can only be a single character: {}",
        ClapyErrors.INVALID_LONG_ALIAS: "Long argument alias should start with -- and have at least 2 characters: {}",
    }
