from __future__ import annotations

import os
import shutil
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path, PurePath

_TYPST_HEADER = Path(__file__).parent / "templates" / "breakable.typ"


@dataclass
class BuildResult:
    src: Path
    dest: Path
    ok: bool
    elapsed: float
    error: str = ""


def _matches_any(rel: PurePath, patterns: list[str]) -> bool:
    rel_posix = rel.as_posix()
    for pat in patterns:
        if rel.match(pat):
            return True
        # PurePath.match doesn't traverse `**` across multiple segments the way
        # most users expect; fall back to fnmatch on the posix string for those.
        if "**" in pat:
            from fnmatch import fnmatch

            # Translate `**` into fnmatch's `*` (which already matches across /).
            if fnmatch(rel_posix, pat.replace("**", "*")):
                return True
    return False


def discover(inputs: list[Path], excludes: list[str] | None = None) -> list[Path]:
    """Find all .md files across the given inputs (dirs and/or files).

    Excludes are glob patterns matched against paths relative to each input
    directory's root. Patterns do not apply to explicit file inputs.
    """
    excludes = excludes or []
    found: list[Path] = []
    seen: set[Path] = set()

    for entry in inputs:
        if entry.is_dir():
            for md in entry.rglob("*.md"):
                rel = md.relative_to(entry)
                if _matches_any(rel, excludes):
                    continue
                resolved = md.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                found.append(md)
        elif entry.is_file():
            resolved = entry.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(entry)

    return sorted(found)


def common_root(inputs: list[Path]) -> Path:
    """Compute the common parent dir for a set of input paths.

    Files contribute their parent; dirs contribute themselves.
    """
    roots = [str(p if p.is_dir() else p.parent) for p in inputs]
    return Path(os.path.commonpath(roots))


def output_path_for(src: Path, root: Path, output_dir: Path) -> Path:
    """Map a source .md path to its mirrored .pdf output path."""
    rel = src.relative_to(root)
    return output_dir / rel.with_suffix(".pdf")


def build_file(src: Path, root: Path, output_dir: Path) -> BuildResult:
    """Compile a single .md file to PDF via pandoc + typst."""
    dest = output_path_for(src, root, output_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()
    try:
        subprocess.run(
            [
                "pandoc",
                str(src),
                "--from=markdown+lists_without_preceding_blankline",
                "--pdf-engine=typst",
                f"--include-in-header={_TYPST_HEADER}",
                "-o",
                str(dest),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return BuildResult(src=src, dest=dest, ok=True, elapsed=time.monotonic() - t0)
    except subprocess.CalledProcessError as exc:
        return BuildResult(
            src=src,
            dest=dest,
            ok=False,
            elapsed=time.monotonic() - t0,
            error=exc.stderr.strip(),
        )


def clean_output(output_dir: Path) -> None:
    """Remove the output directory if it exists."""
    if output_dir.exists():
        shutil.rmtree(output_dir)


def compile_all(
    inputs: list[Path],
    output_dir: Path,
    *,
    jobs: int = 1,
    verbose: bool = False,
    dry_run: bool = False,
    excludes: list[str] | None = None,
    log=print,
) -> list[BuildResult]:
    """Discover and compile all .md files across inputs, returning results."""
    sources = discover(inputs, excludes)
    if not sources:
        log("No .md files found.")
        return []

    root = common_root(inputs)

    if dry_run:
        for src in sources:
            dest = output_path_for(src, root, output_dir)
            log(f"  {src} -> {dest}")
        log(f"\n{len(sources)} file(s) would be compiled.")
        return []

    results: list[BuildResult] = []
    t0 = time.monotonic()

    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(build_file, src, root, output_dir): src for src in sources}
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            if verbose:
                status = "ok" if r.ok else "FAIL"
                log(f"  [{status}] {r.src} ({r.elapsed:.2f}s)")

    total = time.monotonic() - t0
    ok = sum(1 for r in results if r.ok)
    failed = sum(1 for r in results if not r.ok)

    log(f"\n{ok} compiled, {failed} failed ({total:.2f}s)")

    for r in results:
        if not r.ok:
            log(f"  FAIL: {r.src}\n        {r.error}")

    return results
