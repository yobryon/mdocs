# mdocs

A small CLI that recursively compiles folders of Markdown documents to PDF using [pandoc](https://pandoc.org/) with [typst](https://typst.app/) as the PDF engine.

Built for the workflow of: write a bunch of markdown, then PDF the whole lot to share or take on a reader.

## Prerequisites

You need **pandoc** (3.8 or newer) and **typst** on your PATH.

> **Note:** Older pandoc versions (e.g. 3.7 from `apt` on Debian/Ubuntu) have a buggy typst integration that fails with `error: font fallback list must not be empty` even when system fonts are properly installed. Use 3.8+.

You also need at least one system font installed — typst won't render without one. Windows and macOS ship with plenty; minimal Linux installs (servers, slim WSL, lean Docker images) often don't, in which case install something like `fonts-dejavu`, `fonts-liberation`, or `fonts-noto` and run `fc-cache -fv`.

### Linux (Debian/Ubuntu)

```bash
# pandoc — apt's version may be too old. Grab the latest .deb:
# https://github.com/jgm/pandoc/releases
# Example:
wget https://github.com/jgm/pandoc/releases/download/3.9/pandoc-3.9-1-amd64.deb
sudo dpkg -i pandoc-3.9-1-amd64.deb

# typst — download the latest release binary:
# https://github.com/typst/typst/releases
# or via cargo:
cargo install typst-cli

# fonts — minimal installs may have none; install at least one font family:
sudo apt install fonts-dejavu
```

### Windows

```powershell
winget install --id JohnMacFarlane.Pandoc
winget install --id Typst.Typst
```

### macOS

```bash
brew install pandoc typst
```

## Install

Recommended — install as an isolated CLI tool with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/yobryon/mdocs.git
```

Or with plain pip (into your active environment):

```bash
pip install git+https://github.com/yobryon/mdocs.git
```

To also get `--watch` mode (auto-recompile on file changes), include the `watch` extra:

```bash
uv tool install "git+https://github.com/yobryon/mdocs.git" --with watchdog
# or
pip install "mdocs[watch] @ git+https://github.com/yobryon/mdocs.git"
```

## Usage

```bash
# Compile everything in ./docs to ./docs_pdf/
mdocs ./docs

# Specify an output directory
mdocs ./docs -o ./pdfs

# Multiple inputs (dirs and/or .md files); -o is required when mixing.
mdocs docs/design docs/specs docs/README.md -o ./pdfs

# Bash brace expansion works — the shell expands these into separate args:
mdocs docs/{design,specs}/*.md -o ./pdfs

# Exclude subtrees (patterns are relative to each input directory).
# Repeatable, or use brace expansion to fan out:
mdocs docs -o tmp/docs -x 'reference/**' -x '**/archive/**'
mdocs docs -o tmp/docs --exclude={crossover,reference,sprint}/**

# See what would be compiled without running pandoc
mdocs ./docs --dry-run

# Verbose output (show each file as it's processed)
mdocs ./docs -v

# Clean output directory before building
mdocs ./docs --clean

# Limit parallel workers (default: CPU count)
mdocs ./docs -j 2

# Watch for changes and recompile automatically (single dir input only)
mdocs ./docs -w
```

### Behavior notes

- **Lists without preceding blank lines** are recognized as lists (pandoc's `lists_without_preceding_blankline` extension is enabled by default).
- **Long tables span pages.** mdocs ships a small typst header that makes table figures breakable — long markdown tables paginate naturally instead of overflowing.

The output directory mirrors the input directory structure:

```
docs/                    docs_pdf/
  readme.md        →      readme.pdf
  design/                  design/
    spec.md        →        spec.pdf
    sub/                    sub/
      notes.md     →          notes.pdf
```

## License

MIT
