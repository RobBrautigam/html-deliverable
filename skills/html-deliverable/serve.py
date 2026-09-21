"""Serve an HTML deliverable over local HTTP so its embedded live-reload script activates.

Usage:
    python serve.py <file-or-dir> [--port N] [--open]

- Given a FILE: serves its parent directory and prints/opens the file's URL.
- Given a DIR:  serves that directory and prints the root URL.
- Every response carries Cache-Control: no-store so the 2s self-poll in the
  deliverable template always sees fresh bytes.
- Binds 127.0.0.1 only. Ctrl+C to stop. No dependencies beyond the stdlib.

The screen-share helper: edit the HTML file on disk and the browser tab (shared on
a call) reloads itself within about 2s of each save. Opening the same file from disk
(file://) stays a plain static snapshot.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:  # noqa: N802 (stdlib naming)
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # keep the console quiet
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="HTML file or directory to serve")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="open the URL in the default browser")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"not found: {target}", file=sys.stderr)
        return 1

    directory = target if target.is_dir() else target.parent
    handler = partial(NoCacheHandler, directory=str(directory))

    port = args.port
    httpd = None
    for candidate in range(port, port + 20):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", candidate), handler)
            port = candidate
            break
        except OSError:
            continue
    if httpd is None:
        print(f"no free port in {args.port}-{args.port + 19}", file=sys.stderr)
        return 1

    if target.is_dir():
        url = f"http://127.0.0.1:{port}/"
    else:
        url = f"http://127.0.0.1:{port}/{quote(target.name)}"

    print(f"serving {directory}")
    print(f"open:    {url}")
    if args.open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
