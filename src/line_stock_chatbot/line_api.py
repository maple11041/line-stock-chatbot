from __future__ import annotations

import requests

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def push_text_messages(
    *,
    channel_access_token: str,
    to: str,
    messages: list[str],
    timeout: float = 20,
) -> None:
    if not messages:
        return

    response = requests.post(
        LINE_PUSH_URL,
        json={
            "to": to,
            "messages": [{"type": "text", "text": message} for message in messages],
        },
        headers={
            "Authorization": f"Bearer {channel_access_token}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"LINE push API failed with {response.status_code}: {response.text}"
        ) from exc
