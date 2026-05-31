from __future__ import annotations

import argparse
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .line_api import push_text_messages
from .notify import build_daily_digest, format_digest, split_message
from .twse import fetch_public_offerings

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def main() -> None:
    load_dotenv(Path(".env"))

    args = parse_args()
    target_date = args.date or _env_date("TARGET_DATE") or datetime.now(TAIPEI_TZ).date()
    dry_run = args.dry_run or _env_bool("DRY_RUN")
    include_bonds = args.include_bonds or _env_bool("INCLUDE_BONDS")
    send_empty = args.send_empty or _env_bool("SEND_EMPTY")

    offerings = fetch_public_offerings(args.year or target_date.year)
    digest = build_daily_digest(offerings, target_date, include_bonds=include_bonds)
    text = format_digest(digest)
    messages = split_message(text)

    if dry_run:
        print(text)
        return

    if not digest.has_items and not send_empty:
        print(text)
        print("No LINE message sent because SEND_EMPTY=false.")
        return

    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    to = os.environ.get("LINE_TO_ID")
    if not token or not to:
        raise SystemExit(
            "LINE_CHANNEL_ACCESS_TOKEN and LINE_TO_ID are required unless DRY_RUN=true."
        )

    push_text_messages(channel_access_token=token, to=to, messages=messages)
    print(f"Sent {len(messages)} LINE message(s) for {target_date.isoformat()}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Notify LINE with daily Taiwan stock subscription info."
    )
    parser.add_argument("--date", type=_parse_date, help="Target date in YYYY-MM-DD.")
    parser.add_argument("--year", type=int, help="TWSE data year. Defaults to target date year.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the message instead of sending LINE.",
    )
    parser.add_argument(
        "--send-empty",
        action="store_true",
        help="Send a LINE message even when no items exist.",
    )
    parser.add_argument(
        "--include-bonds",
        action="store_true",
        help="Include central government bonds.",
    )
    return parser.parse_args()


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _env_date(name: str) -> date | None:
    value = os.environ.get(name)
    return _parse_date(value) if value else None


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        if line.startswith("export "):
            line = line.removeprefix("export ").strip()

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


if __name__ == "__main__":
    main()
