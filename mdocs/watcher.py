from __future__ import annotations

from pathlib import Path

from mdocs.compiler import build_file


def watch(input_dir: Path, output_dir: Path, *, verbose: bool = False, log=print) -> None:
    """Watch input_dir for .md changes and recompile on save."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        log("watchdog is not installed. Install it with:  pip install mdocs[watch]")
        raise SystemExit(1)

    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.is_directory:
                return
            path = Path(event.src_path)
            if path.suffix == ".md":
                log(f"  changed: {path}")
                r = build_file(path, input_dir, output_dir)
                status = "ok" if r.ok else "FAIL"
                log(f"  [{status}] {r.dest} ({r.elapsed:.2f}s)")
                if not r.ok:
                    log(f"        {r.error}")

    observer = Observer()
    observer.schedule(Handler(), str(input_dir), recursive=True)
    observer.start()
    log(f"Watching {input_dir} for changes... (Ctrl+C to stop)")
    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
