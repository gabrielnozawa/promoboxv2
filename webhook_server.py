"""
Servidor HTTP mínimo para expor o webhook oficial da WhatsApp Cloud API.

O Streamlit não atende requisições webhook cruas (GET de verificação da Meta
+ POST de eventos), então esse endpoint roda como um processo HTTP separado,
independente do painel. Usa apenas a biblioteca padrão do Python (sem
dependências novas).

Uso:
    python webhook_server.py
    # expõe em http://0.0.0.0:8090/webhook/whatsapp

Configure essa URL pública (atrás de HTTPS, ex: via proxy/túnel) no painel
da Meta, junto com o mesmo valor de WHATSAPP_WEBHOOK_VERIFY_TOKEN definido
no seu .env/secrets.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_PROJECT_ROOT = _Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PROJECT_ROOT))

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from app.services.whatsapp.webhook import parse_incoming_event, verify_webhook
from app.utils.logger import log_event

PORT = int(os.environ.get("WEBHOOK_PORT", "8090"))


class WhatsAppWebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/webhook/whatsapp":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        mode = params.get("hub.mode", [""])[0]
        token = params.get("hub.verify_token", [""])[0]
        challenge = params.get("hub.challenge", [""])[0]

        result = verify_webhook(mode, token, challenge)
        if result is not None:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(result.encode())
        else:
            self.send_response(403)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/webhook/whatsapp":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
            events = parse_incoming_event(payload)
            for event in events:
                log_event("integracao", f"WhatsApp webhook: evento recebido: {event}")
        except Exception as exc:
            log_event("erro", f"WhatsApp webhook: payload inválido: {exc}", level="ERROR")

        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # silencia o log padrão do http.server; usamos o logger do PromoBox


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), WhatsAppWebhookHandler)
    print(f"Webhook do WhatsApp rodando em http://0.0.0.0:{PORT}/webhook/whatsapp (Ctrl+C para parar)")
    log_event("sistema", f"Servidor de webhook do WhatsApp iniciado na porta {PORT}.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Webhook encerrado.")
