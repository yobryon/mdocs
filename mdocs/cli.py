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
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("output_dir", type=click.Path(path_type=Path), required=False, default=None)
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
    input_dir: Path,
    output_dir: Path | None,
    verbose: bool,
    clean: bool,
    jobs: int | None,
    watch_mode: bool,
    dry_run: bool,
) -> None:
    """Compile Markdown files to PDF recursively via pandoc + typst."""
    _check_tool("pandoc")
    _check_tool("typst")

    if output_dir is None:
        output_dir = input_dir.parent / (input_dir.name + "_pdf")

    if jobs is None:
        jobs = os.cpu_count() or 1

    if clean and not dry_run:
        clean_output(output_dir)
        if verbose:
            click.echo(f"Cleaned {output_dir}")

    if watch_mode:
        # Do an initial full compile, then watch
        compile_all(input_dir, output_dir, jobs=jobs, verbose=verbose, log=click.echo)
        from mdocs.watcher import watch

        watch(input_dir, output_dir, verbose=verbose, log=click.echo)
    else:
        results = compile_all(
            input_dir, output_dir, jobs=jobs, verbose=verbose, dry_run=dry_run, log=click.echo
        )
        if any(not r.ok for r in results):
            raise SystemExit(1)
