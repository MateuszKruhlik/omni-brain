#!/usr/bin/env python3
"""Brain HTML edit server — optional served mode with in-place md editing.

Stdlib-only. Serves the repo root on 127.0.0.1 and exposes POST /save that
writes an edited markdown file back to disk (path-validated, atomic) and
rebuilds brain.html. Self-terminating: exits when the parent process dies
or after IDLE_LIMIT seconds without requests (pattern: make-pages-interactive).

Usage: python3 tools/brain/serve.py [--port 8643] [--no-open]
"""
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PORT = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8643
IDLE_LIMIT = 600  # seconds without any request -> shut down
PARENT_PID = os.getppid()

_last_activity = time.time()


def _touch():
    global _last_activity
    _last_activity = time.time()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def guess_type(self, path):
        ctype = super().guess_type(path)
        # force utf-8 on text types — without it browsers fall back to Latin-1
        if ctype.startswith("text/") and "charset" not in ctype:
            ctype += "; charset=utf-8"
        return ctype

    def do_GET(self):
        _touch()
        if self.path in ("/", "/index.html"):
            self.path = "/brain.html"
        super().do_GET()

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        _touch()
        if self.path != "/save":
            self._json(404, {"ok": False, "error": "unknown endpoint"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            rel, md = data["path"], data["md"]
            target = (ROOT / rel).resolve()
            if (
                not str(target).startswith(str(ROOT) + os.sep)
                or target.suffix != ".md"
                or not target.is_file()
            ):
                raise ValueError(f"invalid path: {rel}")
            tmp = target.with_name(target.name + ".tmp")
            tmp.write_text(md, encoding="utf-8")
            tmp.replace(target)  # atomic write
            subprocess.run(
                [sys.executable, str(HERE / "build.py")],
                check=True, capture_output=True, text=True,
            )
            self._json(200, {"ok": True})
            print(f"[save] {rel} ({len(md)} B) + rebuild")
        except Exception as e:  # noqa: BLE001 — report any failure to the client
            self._json(400, {"ok": False, "error": str(e)})


def watchdog():
    while True:
        time.sleep(5)
        if os.getppid() != PARENT_PID:
            os._exit(0)  # parent (terminal/agent) died — don't linger
        if time.time() - _last_activity > IDLE_LIMIT:
            print("[idle] no requests for 10 min — shutting down")
            os._exit(0)


def main():
    subprocess.run([sys.executable, str(HERE / "build.py")], check=True)
    threading.Thread(target=watchdog, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/brain.html"
    print(f"Brain edit mode: {url}  (auto-stops after 10 min idle, Ctrl+C to quit)")
    if "--no-open" not in sys.argv:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
