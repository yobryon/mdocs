from __future__ import annotations

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


def discover(input_dir: Path) -> list[Path]:
    """Recursively find all .md files under input_dir."""
    return sorted(input_dir.rglob("*.md"))


def output_path_for(src: Path, input_dir: Path, output_dir: Path) -> Path:
    """Map a source .md path to its mirrored .pdf output path."""
    rel = src.relative_to(input_dir)
    return output_dir / rel.with_suffix(".pdf")


def build_file(src: Path, input_dir: Path, output_dir: Path) -> BuildResult:
    """Compile a single .md file to PDF via pandoc + typst."""
    dest = output_path_for(src, input_dir, output_dir)
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
    input_dir: Path,
    output_dir: Path,
    *,
    jobs: int = 1,
    verbose: bool = False,
    dry_run: bool = False,
    log=print,
) -> list[BuildResult]:
    """Discover and compile all .md files, returning results."""
    sources = discover(input_dir)
    if not sources:
        log("No .md files found.")
        return []

    if dry_run:
        for src in sources:
            dest = output_path_for(src, input_dir, output_dir)
            log(f"  {src} -> {dest}")
        log(f"\n{len(sources)} file(s) would be compiled.")
        return []

    results: list[BuildResult] = []
    t0 = time.monotonic()

    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(build_file, src, input_dir, output_dir): src for src in sources}
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
