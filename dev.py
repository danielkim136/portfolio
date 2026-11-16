"""Local preview server with auto-refresh.

Run:  python3 dev.py
Open: http://localhost:3000

Every time you save a file in this folder, the browser reloads by itself.
This file is only for previewing on your computer. It is not part of the website.
"""
import http.server
import os
import time

PORT = 3000
ROOT = os.path.dirname(os.path.abspath(__file__))
SNIPPET = b"<script>new EventSource('/__reload').onmessage=()=>location.reload()</script>"


def latest_change():
    newest = 0
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            try:
                newest = max(newest, os.path.getmtime(os.path.join(folder, name)))
            except OSError:
                pass
    return newest


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path == "/__reload":
            return self.watch()
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        if path.endswith(".html") and os.path.isfile(path):
            with open(path, "rb") as f:
                body = f.read().replace(b"</body>", SNIPPET + b"</body>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def watch(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        seen = latest_change()
        try:
            while True:
                time.sleep(0.4)
                now = latest_change()
                if now != seen:
                    self.wfile.write(b"data: reload\n\n")
                    self.wfile.flush()
                    return
                self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    http.server.ThreadingHTTPServer.daemon_threads = True
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Previewing at http://localhost:{PORT}  (Ctrl+C to stop)")
    server.serve_forever()
