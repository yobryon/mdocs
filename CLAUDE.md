# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**mdocs** is a CLI tool that recursively compiles folders of Markdown documents to PDF using pandoc with typst as the PDF engine.

Core command: `pandoc <input.md> --pdf-engine=typst -o <output.pdf>`

## Build & Development

```bash
# Install in development mode (include dev deps)
pip install -e ".[dev]"

# Run the CLI
mdocs <input-dir> [output-dir]

# Run tests
pytest

# Run a single test
pytest tests/test_compiler.py::test_discover

# Lint + format
ruff check . && ruff format --check .
```

## Architecture

Python CLI using `click`. Single-package structure:

- `mdocs/cli.py` — click entry point (`main`). Validates pandoc/typst on PATH, parses args, dispatches to compiler or watcher.
- `mdocs/compiler.py` — core logic: `discover()` finds `.md` files, `build_file()` runs pandoc for one file, `compile_all()` orchestrates parallel builds via `ProcessPoolExecutor`.
- `mdocs/watcher.py` — optional `--watch` mode using `watchdog`. Lazily imported; gracefully errors if watchdog isn't installed.
- Tests mock `subprocess.run` to avoid requiring pandoc/typst in CI.

## Key Design Decisions

- **pandoc + typst**: All PDF rendering goes through `pandoc --pdf-engine=typst`. Both must be available on PATH.
- **Directory mirroring**: Output directory structure mirrors the input. Default output dir is `<input_dir>_pdf/` alongside the input.
- **Parallel by default**: Uses `ProcessPoolExecutor` with CPU count workers. Override with `-j`.
- **Minimal dependencies**: click for CLI, subprocess for pandoc. watchdog is an optional extra (`pip install mdocs[watch]`).
