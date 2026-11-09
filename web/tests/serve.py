"""Serve artifact or branch publishing under a GitHub Pages-style project path."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PUBLIC_FILES = {'index.html', 'styles.css', 'app.js', 'engine.js', 'storage.js',
                'data/exercises.json', 'icon.svg', 'manifest.webmanifest', 'sw.js'}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith('/TypeSprint/'):
            self.send_error(404)
            return
        self.path = self.path[len('/TypeSprint'):]
        if urlsplit(self.path).path not in self.allowed:
            self.send_error(404)
            return
        super().do_GET()

    def log_message(self, *_):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', action='store_true')
    parser.add_argument('--port', type=int, default=4173)
    args = parser.parse_args()
    web = Path(__file__).resolve().parent.parent
    directory = web.parent if args.branch else web / 'dist'
    Handler.allowed = {'/', '/index.html'} | ({'/web/'} | {'/web/' + name for name in PUBLIC_FILES}
                                           if args.branch else {'/web/', '/web/index.html'} | {'/' + name for name in PUBLIC_FILES})
    ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(directory))).serve_forever()
