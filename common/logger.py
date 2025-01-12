import sys
from logging import Logger, getLogger, StreamHandler
from colorlog import ColoredFormatter
from colorama import Fore, Style

logger: Logger = getLogger()


# https://github.com/borntyping/python-colorlog
def configure_logger(level: int):
    """Initialize the logger configuration."""
    handler: StreamHandler = StreamHandler(sys.stdout)
    handler.setFormatter(ColoredFormatter(
        # fmt='%(log_color)s%(levelname)-8s %(message)s%(reset)s',
        fmt='%(log_color)s%(message)s%(reset)s',
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'white',  # 'cyan',
            'INFO': 'light_white',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_light_white',
        },
        secondary_log_colors={},
        style='%',
    ))
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)


def get_logger() -> Logger:
    """Returns the global logger."""
    return logger


def __flush_logger():
    logger.handlers[0].flush()


def print_interactive(string: str):
    """Prints the message to stdout with color."""
    __flush_logger()
    print(Fore.CYAN + Style.BRIGHT + string + Style.RESET_ALL)


def input_interactive(string: str) -> str:
    """Prints the message to stdout with color, and returns the user message.
    If the message could not be Unicode decoded, raises KeyboardInterrupt."""
    __flush_logger()
    print(Fore.CYAN + Style.BRIGHT + string + Style.RESET_ALL, end='')
    try:
        result = input().strip().upper()
    except UnicodeDecodeError as exc:
        raise KeyboardInterrupt() from exc
    return result
