from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

import requests

WESPAI_DRAW_URL = "https://stock.wespai.com/draw"


@dataclass(frozen=True)
class SubscriptionSnapshot:
    code: str
    name: str
    application_count: int


def fetch_subscription_snapshots(
    *,
    timeout: float = 20,
    session: requests.Session | None = None,
) -> dict[str, SubscriptionSnapshot]:
    """Fetch preliminary application counts from the public Wespai lottery table."""
    http = session or requests.Session()
    response = http.get(
        WESPAI_DRAW_URL,
        timeout=timeout,
        headers={"User-Agent": "line-stock-chatbot/0.1"},
    )
    response.raise_for_status()
    return parse_subscription_snapshots(response.text)


def parse_subscription_snapshots(html: str) -> dict[str, SubscriptionSnapshot]:
    parser = _DrawTableParser()
    parser.feed(html)

    if not parser.headers:
        raise RuntimeError("Wespai response does not contain the expected draw table")

    try:
        code_index = parser.headers.index("代號")
        name_index = parser.headers.index("公司")
        count_index = parser.headers.index("總合格件")
    except ValueError as exc:
        raise RuntimeError("Wespai draw table is missing expected columns") from exc

    snapshots: dict[str, SubscriptionSnapshot] = {}
    for row in parser.rows:
        if len(row) <= max(code_index, name_index, count_index):
            continue

        code = row[code_index]
        if not code:
            continue

        snapshots[code] = SubscriptionSnapshot(
            code=code,
            name=row[name_index],
            application_count=_parse_int(row[count_index]),
        )

    return snapshots


def _parse_int(value: str) -> int:
    normalized = value.strip().replace(",", "")
    return int(normalized) if normalized else 0


class _DrawTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_target_table = False
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.current_row: list[str] = []
        self.headers: list[str] = []
        self.rows: list[list[str]] = []
        self.current_cell_tag = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "table" and attributes.get("id") == "example":
            self.in_target_table = True
            return

        if self.in_target_table and tag in {"th", "td"}:
            self.in_cell = True
            self.current_cell_tag = tag
            self.cell_parts = []

    def handle_endtag(self, tag: str) -> None:
        if not self.in_target_table:
            return

        if tag in {"th", "td"} and self.in_cell:
            value = "".join(self.cell_parts).strip()
            if self.current_cell_tag == "th":
                self.headers.append(value)
            else:
                self.current_row.append(value)
            self.in_cell = False
            return

        if tag == "tr" and self.current_row:
            self.rows.append(self.current_row)
            self.current_row = []
            return

        if tag == "table":
            self.in_target_table = False

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_parts.append(data)

