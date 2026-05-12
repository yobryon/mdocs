from __future__ import annotations

import os
import shutil
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

_TYPST_HEADER = Path(__file__).parent / "templates" / "breakable.typ"


@dataclass
class BuildResult:
    src: Path
    dest: Path
    ok: bool
    elapsed: float
    error: str = ""


def _matches_any(candidates: list[str], patterns: list[str]) -> bool:
    """True if any candidate path string matches any pattern.

    Candidates typically include both the input-relative path (`reference/foo.md`)
    and the path as the user typed it on the command line (`docs/reference/foo.md`),
    so either pattern style works.
    """
    from fnmatch import fnmatch

    for pat in patterns:
        # Translate `**` into fnmatch's `*` (which already matches across /).
        translated = pat.replace("**", "*")
        for cand in candidates:
            if fnmatch(cand, translated):
                return True
            # Also match against any tail of the path so a pattern like
            # `reference/**` matches even when the candidate is the full
            # `docs/reference/foo.md` form.
            parts = cand.split("/")
            for i in range(1, len(parts)):
                if fnmatch("/".join(parts[i:]), translated):
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
                rel = md.relative_to(entry).as_posix()
                as_typed = md.as_posix()
                if _matches_any([rel, as_typed], excludes):
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

    # Resolve referenced resources (images, etc.) from the md file's directory
    # first, then fall back to the input root for shared assets/.
    resource_dirs = [str(src.parent)]
    if src.parent != root:
        resource_dirs.append(str(root))
    resource_path = os.pathsep.join(resource_dirs)

    t0 = time.monotonic()
    try:
        subprocess.run(
            [
                "pandoc",
                str(src),
                "--from=markdown+lists_without_preceding_blankline",
                "--pdf-engine=typst",
                f"--resource-path={resource_path}",
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
