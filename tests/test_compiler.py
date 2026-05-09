from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from mdocs.compiler import (
    build_file,
    clean_output,
    common_root,
    compile_all,
    discover,
    output_path_for,
)


def _make_tree(tmp_path: Path) -> Path:
    """Create a sample directory tree with .md and non-.md files."""
    root = tmp_path / "docs"
    (root / "sub").mkdir(parents=True)
    (root / "readme.md").write_text("# Hello")
    (root / "sub" / "notes.md").write_text("# Notes")
    (root / "sub" / "image.png").write_bytes(b"\x89PNG")
    (root / "ignore.txt").write_text("not markdown")
    return root


def test_discover(tmp_path):
    root = _make_tree(tmp_path)
    found = discover([root])
    names = [p.name for p in found]
    assert "readme.md" in names
    assert "notes.md" in names
    assert "image.png" not in names
    assert "ignore.txt" not in names


def test_discover_empty(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert discover([empty]) == []


def test_discover_excludes(tmp_path):
    root = _make_tree(tmp_path)
    (root / "reference").mkdir()
    (root / "reference" / "huge.md").write_text("# huge")
    (root / "reference" / "deep").mkdir()
    (root / "reference" / "deep" / "x.md").write_text("# x")

    found = discover([root], excludes=["reference/**"])
    names = [p.name for p in found]
    assert "huge.md" not in names
    assert "x.md" not in names
    assert "readme.md" in names


def test_discover_excludes_cwd_style(tmp_path, monkeypatch):
    """Patterns like `docs/reference/**` (the form users actually type) should match."""
    root = _make_tree(tmp_path)
    (root / "reference").mkdir()
    (root / "reference" / "huge.md").write_text("# huge")

    monkeypatch.chdir(tmp_path)
    found = discover([Path("docs")], excludes=["docs/reference/**"])
    names = [p.name for p in found]
    assert "huge.md" not in names
    assert "readme.md" in names


def test_discover_multiple_inputs_dedupes(tmp_path):
    root = _make_tree(tmp_path)
    explicit = root / "readme.md"
    found = discover([root, explicit])
    # readme.md should appear exactly once
    assert sum(1 for p in found if p.name == "readme.md") == 1


def test_discover_file_input_bypasses_excludes(tmp_path):
    root = _make_tree(tmp_path)
    (root / "draft.md").write_text("# draft")
    found = discover([root / "draft.md"], excludes=["**/*.md"])
    assert [p.name for p in found] == ["draft.md"]


def test_common_root_single_dir(tmp_path):
    root = _make_tree(tmp_path)
    assert common_root([root]) == root


def test_common_root_mixed(tmp_path):
    root = _make_tree(tmp_path)
    assert common_root([root / "sub", root / "readme.md"]) == root


def test_output_path_for(tmp_path):
    input_dir = tmp_path / "docs"
    output_dir = tmp_path / "out"
    src = input_dir / "sub" / "notes.md"
    result = output_path_for(src, input_dir, output_dir)
    assert result == output_dir / "sub" / "notes.pdf"


def test_build_file_success(tmp_path):
    root = tmp_path / "docs"
    root.mkdir()
    md = root / "hello.md"
    md.write_text("# Hello")
    out = tmp_path / "out"

    with patch("mdocs.compiler.subprocess.run") as mock_run:
        mock_run.return_value = None
        result = build_file(md, root, out)

    assert result.ok
    assert result.dest == out / "hello.pdf"
    mock_run.assert_called_once()


def test_build_file_failure(tmp_path):
    import subprocess

    root = tmp_path / "docs"
    root.mkdir()
    md = root / "bad.md"
    md.write_text("# Bad")
    out = tmp_path / "out"

    with patch("mdocs.compiler.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "pandoc", stderr="something went wrong"
        )
        result = build_file(md, root, out)

    assert not result.ok
    assert "something went wrong" in result.error


def test_compile_all_dry_run(tmp_path):
    root = _make_tree(tmp_path)
    out = tmp_path / "out"
    lines: list[str] = []

    results = compile_all([root], out, jobs=1, dry_run=True, log=lines.append)

    assert results == []
    text = "\n".join(lines)
    assert "readme.md" in text
    assert "notes.md" in text
    assert "2 file(s) would be compiled" in text


def test_compile_all_dry_run_with_excludes(tmp_path):
    root = _make_tree(tmp_path)
    out = tmp_path / "out"
    lines: list[str] = []

    results = compile_all([root], out, jobs=1, dry_run=True, excludes=["sub/**"], log=lines.append)

    assert results == []
    text = "\n".join(lines)
    assert "readme.md" in text
    assert "notes.md" not in text
    assert "1 file(s) would be compiled" in text


def test_compile_all_no_files(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    out = tmp_path / "out"
    lines: list[str] = []

    results = compile_all([empty], out, jobs=1, log=lines.append)

    assert results == []
    assert "No .md files found." in lines


def test_clean_output(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "old.pdf").write_text("old")
    assert out.exists()

    clean_output(out)

    assert not out.exists()


def test_clean_output_nonexistent(tmp_path):
    out = tmp_path / "nope"
    clean_output(out)  # should not raise
