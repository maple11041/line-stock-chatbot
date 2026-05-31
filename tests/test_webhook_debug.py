import base64
import hashlib
import hmac

from line_stock_chatbot.webhook_debug import verify_line_signature


def test_verify_line_signature() -> None:
    body = b'{"events":[]}'
    secret = "channel-secret"
    signature = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode(
        "ascii"
    )

    assert verify_line_signature(body, signature, secret)
    assert not verify_line_signature(body, "bad-signature", secret)

