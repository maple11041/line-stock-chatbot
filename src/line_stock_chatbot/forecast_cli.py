from __future__ import annotations

import argparse
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .cli import load_dotenv
from .forecast import build_deadline_forecast, format_forecast
from .line_api import push_text_messages
from .notify import split_message
from .twse import fetch_public_offerings
from .wespai import fetch_subscription_snapshots

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


def main() -> None:
    load_dotenv(Path(".env"))

    args = parse_args()
    target_date = args.date or _env_date("TARGET_DATE") or datetime.now(TAIPEI_TZ).date()
    dry_run = args.dry_run or _env_bool("DRY_RUN")
    send_empty = args.send_empty or _env_bool("SEND_EMPTY")

    offerings = fetch_public_offerings(args.year or target_date.year)
    snapshots = fetch_subscription_snapshots()
    forecast = build_deadline_forecast(offerings, snapshots, target_date)
    text = format_forecast(forecast)
    messages = split_message(text)

    if dry_run:
        print(text)
        return

    if not forecast.has_items and not send_empty:
        print(text)
        print("No LINE forecast sent because there are no deadline items with application counts.")
        return

    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    to = os.environ.get("LINE_TO_ID")
    if not token or not to:
        raise SystemExit(
            "LINE_CHANNEL_ACCESS_TOKEN and LINE_TO_ID are required unless DRY_RUN=true."
        )

    push_text_messages(channel_access_token=token, to=to, messages=messages)
    print(f"Sent {len(messages)} LINE forecast message(s) for {target_date.isoformat()}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a LINE deadline lottery forecast.")
    parser.add_argument("--date", type=_parse_date, help="Target date in YYYY-MM-DD.")
    parser.add_argument("--year", type=int, help="TWSE data year. Defaults to target date year.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the forecast instead of sending LINE.",
    )
    parser.add_argument(
        "--send-empty",
        action="store_true",
        help="Send a LINE message even when no forecast items exist.",
    )
    return parser.parse_args()


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _env_date(name: str) -> date | None:
    value = os.environ.get(name)
    return _parse_date(value) if value else None


def _env_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


if __name__ == "__main__":
    main()

