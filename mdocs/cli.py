from __future__ import annotations

import os
import shutil
from pathlib import Path

import click

from mdocs import __version__
from mdocs.compiler import clean_output, compile_all


def _check_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise click.ClickException(f"'{name}' not found on PATH. Please install it first.")


@click.command()
@click.version_option(__version__, "-V", "--version", prog_name="mdocs")
@click.argument("inputs", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    "output_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory (default: <input>_pdf alongside a single dir input).",
)
@click.option(
    "-x",
    "--exclude",
    "excludes",
    multiple=True,
    metavar="PATTERN",
    help="Glob to exclude, relative to each input dir. Repeatable. e.g. -x 'reference/**'",
)
@click.option("-v", "--verbose", is_flag=True, help="Print each file as it's processed.")
@click.option("--clean", is_flag=True, help="Remove output directory before building.")
@click.option(
    "-j",
    "--jobs",
    type=int,
    default=None,
    help="Parallel pandoc processes (default: CPU count).",
)
@click.option("-w", "--watch", "watch_mode", is_flag=True, help="Watch for changes and recompile.")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be compiled without running pandoc."
)
def main(
    inputs: tuple[Path, ...],
    output_dir: Path | None,
    excludes: tuple[str, ...],
    verbose: bool,
    clean: bool,
    jobs: int | None,
    watch_mode: bool,
    dry_run: bool,
) -> None:
    """Compile Markdown files to PDF recursively via pandoc + typst.

    INPUTS may be one or more directories and/or .md files.
    """
    _check_tool("pandoc")
    _check_tool("typst")

    input_list = list(inputs)
    for p in input_list:
        if p.is_file() and p.suffix.lower() != ".md":
            raise click.ClickException(f"File input must be a .md file: {p}")

    if output_dir is None:
        if len(input_list) == 1 and input_list[0].is_dir():
            d = input_list[0]
            output_dir = d.parent / (d.name + "_pdf")
        else:
            raise click.ClickException(
                "An output directory is required (-o/--output) when passing "
                "multiple inputs or a file input."
            )

    if watch_mode and (len(input_list) != 1 or not input_list[0].is_dir()):
        raise click.ClickException("--watch requires exactly one directory input.")

    if jobs is None:
        jobs = os.cpu_count() or 1

    if clean and not dry_run:
        clean_output(output_dir)
        if verbose:
            click.echo(f"Cleaned {output_dir}")

    exclude_list = list(excludes)

    if watch_mode:
        compile_all(
            input_list,
            output_dir,
            jobs=jobs,
            verbose=verbose,
            excludes=exclude_list,
            log=click.echo,
        )
        from mdocs.watcher import watch

        # Watcher only supports a single root today; pass the first dir.
        watch(input_list[0], output_dir, verbose=verbose, log=click.echo)
    else:
        results = compile_all(
            input_list,
            output_dir,
            jobs=jobs,
            verbose=verbose,
            dry_run=dry_run,
            excludes=exclude_list,
            log=click.echo,
        )
        if any(not r.ok for r in results):
            raise SystemExit(1)
