##########################################################################
# File:         utils.py                                                 #
# Purpose:      Automatically send batch of mails                        #
# Last changed: 2015/06/21                                               #
# Author:       zhuang-jia-xu                                            #
# Edited:                                                                #
# Copyleft:     (ɔ)NTUEE                                                 #
##########################################################################
import typer
from rich import print
from rich.progress import Progress, TextColumn
from rich.prompt import Confirm
from configparser import ConfigParser
from cerberus.errors import ValidationError, ErrorList

import logging
import time
from pathlib import Path

from .globals import *


def richError(
    *objects: any, end: str = "\n", prefix: str = "Error: ", terminate: bool = True
) -> None:
    print(f"[red]{prefix}", end="")
    for o in objects:
        print(f"[red]{o}", end="")
    print("", end=end)
    if terminate:
        exit(1)


def richWarning(text: str, end: str = "\n", prefix: bool = True) -> None:
    if prefix:
        print(f"[yellow]Warning: [/yellow]", end="")
    print(f"[yellow]{text}[/yellow]", end=end)


def richSuccess(text: str, end: str = "\n") -> None:
    print(f"[green]{text}[/green]", end=end)


def parse_validation_error(errors: ErrorList) -> None:
    def _parse(error: ValidationError, indent: int = 1) -> None:
        if type(error) == ErrorList:
            for e in error:
                _parse(e, indent)
            return

        tabs = " " * 4 * indent

        if error.rule == "schema":
            richError(
                f"{tabs}{'/'.join(error.document_path)}: missing entry",
                terminate=False,
                prefix=False,
            )
        elif error.rule == "type":
            richError(
                f"{tabs}{'/'.join(error.document_path)}: should be {error.constraint}",
                terminate=False,
                prefix=False,
            )
        elif error.rule == "coerce":
            richError(
                f"{tabs}{'/'.join(error.document_path)}: ",
                *error.info,
                terminate=False,
                prefix=False,
            )
        elif error.rule == "required":
            richError(
                f"{tabs}{'/'.join(error.document_path)}: required",
                terminate=False,
                prefix=False,
            )
        else:
            richError(
                f"{tabs}{'/'.join(error.document_path)}: ",
                *error.info,
                terminate=False,
                prefix=False,
            )

        if type(error.info) == tuple and len(error.info) > 0:
            for e in error.info:
                if type(e) != str:
                    _parse(e, indent + 1)

    _parse(errors)


def complete_school_email(email_addr) -> list:
    """
    Autocomplete school email addresss
    """
    if type(email_addr) == list:
        return [complete_school_email(addr) for addr in email_addr]

    if "@" not in email_addr:
        return f"{email_addr}@ntu.edu.tw"
    else:
        return email_addr


def typerSelect(message: str, options: list) -> str:
    def process_options(n):
        n = int(n)
        if n < 0 or n >= len(options):
            raise typer.BadParameter("invalid letter index")
        return options[n]

    prompt_message = (
        "\n"
        + "\n".join(
            [
                f"{'> ' if i == 0 else '  '}[{i}] {option}"
                for i, option in enumerate(options)
            ]
        )
        + "\n\n"
        + message
    )

    result = typer.prompt(
        prompt_message,
        value_proc=process_options,
        default=0,
    )
    print()
    return result


def countdownConfirm(message: str, default=True, countdown: int = 0) -> bool:
    prompt_message = f"\n{message}"
    if countdown == 0:
        result = Confirm.ask(prompt_message, default=default)
    else:
        with Progress(
            TextColumn("[bold blue]{task.description}"), transient=True
        ) as progress:
            countdown_task = progress.add_task("", total=countdown)
            for i in range(countdown + 1):
                progress.update(
                    countdown_task,
                    total=i + 1,
                    description=f' {countdown - i}{" ." * (countdown - i)}',
                )
                time.sleep(1)
        result = Confirm.ask(prompt_message, default=default)
    print()
    return result


DEBUG_LEVELS = [
    logging.NOTSET,
    logging.DEBUG,
    logging.INFO,
    logging.WARNING,
    logging.ERROR,
    logging.CRITICAL,
]


def setup_logger(file_path, level):
    # create log file if it doesn't exist
    if not Path(file_path).is_file():
        with open(file_path, "w") as f:
            pass

    logging.basicConfig(
        level=DEBUG_LEVELS[level],
        filename=file_path,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y/%m/%d %I:%M:%S %p",
    )


if __name__ == "__main__":
    richSuccess("Success")
    richWarning("Warning")
    richError("Error")
