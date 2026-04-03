"""Local HTTP server for the login flow: serves landing page, userscript, and receives token callback."""
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from m365.auth import token_store
from m365.auth.userscript import USERSCRIPT_JS

_token_received = threading.Event()

LANDING_HTML = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>m365-cli Login</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif; max-width: 600px; margin: 60px auto; padding: 0 20px; color: #333; }
  h1 { font-size: 1.4em; }
  .status { padding: 16px; border-radius: 8px; margin: 24px 0; font-size: 1.1em; }
  .waiting { background: #fff3cd; border: 1px solid #ffc107; }
  .success { background: #d4edda; border: 1px solid #28a745; }
  code { background: #f1f1f1; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
  ol { line-height: 1.8; }
  a { color: #0366d6; }
</style>
</head>
<body>
<h1>m365-cli Login</h1>

<div class="status waiting" id="status">
  ⏳ Waiting for token...
</div>

<h3>First-time setup</h3>
<ol>
  <li>Install <a href="https://addons.mozilla.org/en-US/firefox/addon/tampermonkey/" target="_blank">Tampermonkey</a> (Firefox) or <a href="https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo" target="_blank">Tampermonkey</a> (Chrome)</li>
  <li>Click to install the helper userscript: <a href="/userscript.user.js">m365-cli Token Helper</a></li>
  <li>Navigate to <a href="https://teams.microsoft.com" target="_blank">teams.microsoft.com</a> or <a href="https://outlook.office.com" target="_blank">outlook.office.com</a></li>
</ol>

<p>Already installed? Just open Teams or Outlook — the token will be captured automatically.</p>

<script>
  async function poll() {
    try {
      const resp = await fetch('/poll');
      const data = await resp.json();
      if (data.done) {
        document.getElementById('status').className = 'status success';
        document.getElementById('status').textContent = '✓ Token captured! You can close this tab.';
        return;
      }
    } catch (e) {}
    setTimeout(poll, 1500);
  }
  poll();
</script>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._respond(200, "text/html", LANDING_HTML)
        elif self.path == "/userscript.user.js":
            self._respond(200, "application/javascript", USERSCRIPT_JS)
        elif self.path == "/poll":
            done = _token_received.is_set()
            self._respond(200, "application/json", json.dumps({"done": done}))
        else:
            self._respond(404, "text/plain", "Not found")

    def do_POST(self):
        if self.path == "/callback":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                if "access_token" in data:
                    token_store.save(data)
                    _token_received.set()
                    self._respond(200, "application/json", '{"ok": true}')
                else:
                    self._respond(400, "application/json", '{"error": "missing access_token"}')
            except json.JSONDecodeError:
                self._respond(400, "application/json", '{"error": "invalid json"}')
        else:
            self._respond(404, "text/plain", "Not found")

    def _respond(self, code: int, content_type: str, body: str):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        from m365.fmt import console
        console.print(f"  [dim]{self.address_string()} {format % args}[/dim]")


def run_login_server(port: int = 9365, timeout: int = 300) -> bool:
    """Start the login server, block until token received or timeout. Returns True if token captured."""
    _token_received.clear()
    server = HTTPServer(("127.0.0.1", port), _Handler)
    server.timeout = 1

    def serve():
        while not _token_received.is_set():
            server.handle_request()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    _token_received.wait(timeout=timeout)
    server.server_close()
    return _token_received.is_set()
