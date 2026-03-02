# mdocs

A small CLI that recursively compiles folders of Markdown documents to PDF using [pandoc](https://pandoc.org/) with [typst](https://typst.app/) as the PDF engine.

Built for the workflow of: write a bunch of markdown, then PDF the whole lot to share or take on a reader.

## Prerequisites

You need **pandoc** and **typst** on your PATH.

### Linux (Debian/Ubuntu)

```bash
sudo apt install pandoc

# typst — download the latest release binary:
# https://github.com/typst/typst/releases
# or via cargo:
cargo install typst-cli
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

```bash
pip install git+https://github.com/<your-user>/mdocs.git
```

To also get `--watch` mode (auto-recompile on file changes):

```bash
pip install "mdocs[watch] @ git+https://github.com/<your-user>/mdocs.git"
```

## Usage

```bash
# Compile everything in ./docs to ./docs_pdf/
mdocs ./docs

# Specify an output directory
mdocs ./docs ./pdfs

# See what would be compiled without running pandoc
mdocs ./docs --dry-run

# Verbose output (show each file as it's processed)
mdocs ./docs -v

# Clean output directory before building
mdocs ./docs --clean

# Limit parallel workers (default: CPU count)
mdocs ./docs -j 2

# Watch for changes and recompile automatically
mdocs ./docs -w
```

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
