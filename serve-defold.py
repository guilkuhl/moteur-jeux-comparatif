import http.server
import os

os.chdir(r'C:/Users/kuhle/source/repos/moteur-jeux-comparatif/defold-build-web/Defold Benchmark')

class COOPHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        super().end_headers()

    def log_message(self, format, *args):
        pass

print('Defold COOP/COEP server on port 8090', flush=True)
http.server.HTTPServer(('', 8090), COOPHandler).serve_forever()
