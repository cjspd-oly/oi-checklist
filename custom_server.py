import http.server
import socketserver
import os
import urllib

PORT = 5501
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        # Decode URL path
        url_path = urllib.parse.unquote(self.path)

        # 0) root: serve index.html
        if url_path in ('/', ''):
            index_file = os.path.join(BASE_DIR, 'index.html')
            if os.path.isfile(index_file):
                return self._serve_file(index_file)

        # 1) exact file?
        fs_path = os.path.join(BASE_DIR, url_path.lstrip('/'))
        if os.path.isfile(fs_path):
            return self._serve_file(fs_path)

        # 2) try .html
        html_path = fs_path + '.html'
        if os.path.isfile(html_path):
            return self._serve_file(html_path)

        # 3) fallback to 404.html
        not_found = os.path.join(BASE_DIR, '404.html')
        if os.path.isfile(not_found):
            self.send_response(404)
            return self._serve_file(not_found)

        # Default behavior if nothing matches
        return super().send_head()

    def _serve_file(self, path):
        # send headers
        status = 200 if self.command in ('GET', 'HEAD') else 200
        self.send_response(status)
        self.send_header('Content-type', self.guess_type(path))
        fs = os.stat(path)
        self.send_header('Content-Length', str(fs.st_size))
        self.end_headers()
        return open(path, 'rb')

    def log_message(self, format, *args):
        print(f"{self.command} {self.path} -> {format % args}")

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == '__main__':
    os.chdir(BASE_DIR)
    with ReusableTCPServer(('', PORT), CustomHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            httpd.server_close()
