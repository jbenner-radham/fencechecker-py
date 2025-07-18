import os
from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from fencechecker.config import default_python_binary
from fencechecker.file import process_file, report_processed_file
from fencechecker.venv import (
    autodiscover_venv_path,
    get_activate_this_path_and_code_prefix,
    validate_activate_this_path,
)

app = typer.Typer()


def version_callback(show_version: bool) -> None:
    if show_version:
        Console().print(f"fencechecker {metadata.version('fencechecker')}")

        raise typer.Exit(code=0)


@app.command(context_settings={"help_option_names": ["--help", "-h"]})
def main(
    filepaths: Annotated[
        list[Path],
        typer.Argument(
            help="Check these Markdown files.",
            show_default=False,
            exists=True,
            file_okay=True,
            readable=True,
        ),
    ],
    autodiscover_venv: Annotated[
        bool, typer.Option(help="Autodiscover and activate a virtual environment.")
    ] = True,
    only_report_errors: Annotated[
        bool,
        typer.Option(
            "--only-report-errors", "-e", help="Only include errors when reporting."
        ),
    ] = False,
    python_binary: Annotated[
        str,
        typer.Option(
            "--python-binary",
            "-p",
            help="Use this Python binary to execute code.",
        ),
    ] = default_python_binary,
    venv_path: Annotated[
        Path | None,
        typer.Option(
            "--venv-path",
            "-V",
            help="Operate within this virtual environment.",
            show_default=False,
            exists=True,
            dir_okay=True,
            readable=True,
        ),
    ] = None,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Print version info and exit.",
            callback=version_callback,
        ),
    ] = False,
) -> None:
    """Check Python fenced code blocks in Markdown files."""
    console = Console()
    err_console = Console(stderr=True)
    total_errors = 0
    code_prefix: str | None = None

    if venv_path:
        activate_this_path, code_prefix = get_activate_this_path_and_code_prefix(
            venv_path
        )

        if error := validate_activate_this_path(activate_this_path):
            err_console.print(error)

            raise typer.Exit(code=-1)

    # TODO: Check that filepath is a Markdown file?

    # TODO: Implement asyncio to make it faster to run MD files with lots of code blocks.

    for filepath in filepaths:
        if not venv_path and autodiscover_venv:
            discovered_venv_path = autodiscover_venv_path(filepath)

            if not discovered_venv_path:
                err_console.print(
                    "[bold red]✘ Error[/bold red]"
                    + " (Could not autodiscover a virtual environment for the filepath"
                    + f" [link=file://{filepath.absolute()}]{filepath}[/link])"
                )
                raise typer.Exit(code=-1)
            else:
                activate_this_path, code_prefix = (
                    get_activate_this_path_and_code_prefix(discovered_venv_path)
                )

                if error := validate_activate_this_path(activate_this_path):
                    err_console.print(error)

                    raise typer.Exit(code=-1)

        processed_file = process_file(
            filepath, python_binary=python_binary, code_prefix=code_prefix
        )
        total_errors += processed_file["error_count"]

        report_processed_file(
            processed_file,
            console=console,
            err_console=err_console,
            only_report_errors=only_report_errors,
        )

    total_errors_message = f"{os.linesep}[bold]Total Errors: {total_errors}"

    console.print(total_errors_message) if total_errors == 0 else err_console.print(
        total_errors_message
    )

    raise typer.Exit(code=total_errors)


if __name__ == "__main__":
    app()
