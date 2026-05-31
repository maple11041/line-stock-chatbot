from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .cli import load_dotenv

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def main() -> None:
    load_dotenv(Path(".env"))
    args = parse_args()

    server = ThreadingHTTPServer(
        (args.host, args.port),
        build_handler(channel_secret=os.environ.get("LINE_CHANNEL_SECRET")),
    )

    print(f"Webhook debug server listening on http://{args.host}:{args.port}")
    print("Set LINE Developers webhook URL to your public tunnel URL + /callback")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping webhook debug server.")
    finally:
        server.server_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print LINE webhook source IDs.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Defaults to 127.0.0.1.")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind. Defaults to 8000.")
    return parser.parse_args()


def build_handler(channel_secret: str | None) -> type[BaseHTTPRequestHandler]:
    class LineWebhookHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/healthz":
                self._write_json(HTTPStatus.OK, {"ok": True})
                return

            self._write_json(HTTPStatus.NOT_FOUND, {"message": "Not found"})

        def do_POST(self) -> None:
            if self.path != "/callback":
                self._write_json(HTTPStatus.NOT_FOUND, {"message": "Not found"})
                return

            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if channel_secret and not verify_line_signature(
                body,
                self.headers.get("X-Line-Signature", ""),
                channel_secret,
            ):
                self._write_json(HTTPStatus.UNAUTHORIZED, {"message": "Invalid LINE signature"})
                return

            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                self._write_json(HTTPStatus.BAD_REQUEST, {"message": "Invalid JSON"})
                return

            print_webhook_summary(payload)
            self._write_json(HTTPStatus.OK, {"ok": True})

        def log_message(self, format: str, *args: object) -> None:
            timestamp = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {self.address_string()} - {format % args}")

        def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return LineWebhookHandler


def verify_line_signature(body: bytes, signature: str, channel_secret: str) -> bool:
    digest = hmac.new(channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, signature)


def print_webhook_summary(payload: dict[str, Any]) -> None:
    events = payload.get("events", [])
    timestamp = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d %H:%M:%S")

    print("")
    print(f"LINE webhook received at {timestamp}")
    if not events:
        print("No events in payload.")
        return

    for index, event in enumerate(events, start=1):
        source = event.get("source", {})
        message = event.get("message", {})
        print(f"Event #{index}")
        print(f"  type: {event.get('type', 'unknown')}")
        print(f"  source.type: {source.get('type', 'unknown')}")
        print(f"  source.userId: {source.get('userId', '(not present)')}")
        print(f"  source.groupId: {source.get('groupId', '(not present)')}")
        print(f"  source.roomId: {source.get('roomId', '(not present)')}")
        if message:
            print(f"  message.type: {message.get('type', 'unknown')}")
            if message.get("type") == "text":
                print(f"  message.text: {message.get('text', '')}")

