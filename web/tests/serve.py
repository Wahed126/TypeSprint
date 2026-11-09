"""Serve the built site under a GitHub Pages-style project subpath for QA."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith('/TypeSprint/'):
            self.send_error(404)
            return
        self.path = self.path[len('/TypeSprint'):]
        super().do_GET()

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    directory = Path(__file__).resolve().parent.parent / 'dist'
    ThreadingHTTPServer(('127.0.0.1', 4173), partial(Handler, directory=str(directory))).serve_forever()
