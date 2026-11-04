"""Explicit one-time LAN transfers over TLS. No discovery, background sync or uploads."""
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import html
import ipaddress
from pathlib import Path
import secrets
import ssl
import tempfile
import threading
import time
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from clipo.security.vault import private_write


class ShareSession:
    def __init__(self, host, data: bytes, kind="text", lifetime=60):
        address = ipaddress.ip_address(host)
        if address.version != 4 or not (address.is_private or address.is_loopback) or address.is_unspecified or address.is_multicast:
            raise ValueError("Choose a private IPv4 address on your local network")
        if kind not in ("text", "image") or not 10 <= lifetime <= 600 or not data or len(data) > 16 * 1024 * 1024:
            raise ValueError("Transfer requires text/image data up to 16 MiB and a 10–600 second lifetime")
        self.data, self.kind = data, kind
        self.token = secrets.token_urlsafe(32)
        self.deadline = time.monotonic() + lifetime
        self.lock = threading.Lock()
        self.closed = False
        self.temporary = tempfile.TemporaryDirectory(prefix="clipo-share-")
        root = Path(self.temporary.name)
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Clipo temporary local transfer")])
        now = datetime.now(timezone.utc)
        certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(address)]), critical=False).sign(key, hashes.SHA256()))
        self.fingerprint = certificate.fingerprint(hashes.SHA256()).hex(":").upper()
        self.certificate = certificate.public_bytes(serialization.Encoding.PEM)
        private_write(root / "certificate.pem", self.certificate)
        private_write(root / "key.pem", key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(root / "certificate.pem", root / "key.pem")
        session = self

        class Server(ThreadingHTTPServer):
            daemon_threads = True
            def get_request(self):
                connection, peer = super().get_request()
                connection.settimeout(3)
                try:
                    return context.wrap_socket(connection, server_side=True), peer
                except Exception:
                    connection.close()
                    raise

            def handle_error(self, request, client_address):
                pass  # No token/content or peer information is logged.

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def respond(self, status, body, mime="text/html; charset=utf-8"):
                self.send_response(status)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)

            def authorized(self):
                return secrets.compare_digest(self.path, "/s/" + session.token)

            def do_GET(self):
                if not self.authorized():
                    return self.respond(404, b"Not found")
                with session.lock:
                    available = session.data is not None and time.monotonic() < session.deadline
                if not available:
                    return self.respond(410, b"This transfer expired or was already received.")
                # Link previews do not consume or expose clipboard contents.
                self.respond(200, b'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Receive from Clipo</title><h1>Receive from Clipo</h1><p>This local transfer can be received once.</p><form method="post"><button type="submit">Receive item</button></form>')

            def do_POST(self):
                if not self.authorized():
                    return self.respond(404, b"Not found")
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    return self.respond(400, b"Invalid request")
                if not 0 <= length <= 1024:
                    return self.respond(413, b"Request too large")
                if length:
                    self.rfile.read(length)
                with session.lock:
                    if session.data is None or time.monotonic() >= session.deadline:
                        return self.respond(410, b"Transfer expired or already received")
                    payload, session.data = session.data, None
                if session.kind == "image":
                    self.respond(200, payload, "image/png")
                else:
                    body = ('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Clipo item</title><h1>Your clipboard item</h1><p>Long-press the text to select and copy.</p><textarea readonly style="width:95%;height:70vh">' + html.escape(payload.decode("utf-8")) + '</textarea>').encode()
                    self.respond(200, body)

        try:
            self.server = Server((host, 0), Handler)
        except OSError:
            self.temporary.cleanup()
            raise ValueError("Could not listen on that local interface. Check your network and firewall.") from None
        self.url = f"https://{host}:{self.server.server_port}/s/{self.token}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="clipo-local-transfer")
        self.thread.start()
        self.timer = threading.Timer(lifetime, self.close)
        self.timer.daemon = True
        self.timer.start()

    def close(self):
        with self.lock:
            if self.closed:
                return
            self.closed, self.data = True, None
        self.timer.cancel()
        def shutdown():
            self.server.shutdown()
            self.server.server_close()
            self.temporary.cleanup()
        threading.Thread(target=shutdown, daemon=True).start()
