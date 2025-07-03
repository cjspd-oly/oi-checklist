import http.server
import socketserver
import os

PORT = 5501
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def send_error(self, code, message=None, explain=None):
        if code == 404:
            self.path = '/404.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        else:
            return super().send_error(code, message, explain)

    def translate_path(self, path):
        # Ensure files are served relative to your project directory
        path = super().translate_path(path)
        relpath = os.path.relpath(path, os.getcwd())
        return os.path.join(DIRECTORY, relpath)

if __name__ == "__main__":
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()
