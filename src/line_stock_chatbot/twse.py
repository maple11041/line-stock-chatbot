from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from time import sleep
from typing import Any

import requests

TWSE_PUBLIC_FORM_URLS = (
    "https://www.twse.com.tw/rwd/zh/announcement/publicForm",
    "https://www.twse.com.tw/announcement/publicForm",
)


def parse_roc_date(value: str | None) -> date | None:
    """Parse TWSE ROC date strings such as 115/06/11 into Gregorian dates."""
    if not value:
        return None

    normalized = value.strip().replace(".", "/").replace("-", "/")
    if not normalized or normalized in {"未訂出", "--", "-"}:
        return None

    parts = normalized.split("/")
    if len(parts) != 3:
        raise ValueError(f"Unsupported ROC date format: {value!r}")

    roc_year, month, day = (int(part) for part in parts)
    return date(roc_year + 1911, month, day)


@dataclass(frozen=True)
class PublicOffering:
    sequence: str
    draw_date: date | None
    name: str
    code: str
    market: str
    subscribe_start: date | None
    subscribe_end: date | None
    underwriting_shares: str
    actual_underwriting_shares: str
    underwriting_price: str
    actual_underwriting_price: str
    listing_date: date | None
    broker: str
    subscription_shares: str
    total_amount: str
    qualified_count: str
    winning_rate: str
    cancel_reason: str

    @property
    def is_cancelled(self) -> bool:
        return bool(self.cancel_reason.strip())

    @property
    def is_bond(self) -> bool:
        return self.market == "中央登錄公債"

    @classmethod
    def from_twse_row(cls, fields: list[str], row: list[str]) -> PublicOffering:
        values = {field.strip(): value.strip() for field, value in zip(fields, row, strict=False)}
        return cls(
            sequence=values.get("序號", ""),
            draw_date=parse_roc_date(values.get("抽籤日期")),
            name=values.get("證券名稱", ""),
            code=values.get("證券代號", ""),
            market=values.get("發行市場", ""),
            subscribe_start=parse_roc_date(values.get("申購開始日")),
            subscribe_end=parse_roc_date(values.get("申購結束日")),
            underwriting_shares=values.get("承銷股數", ""),
            actual_underwriting_shares=values.get("實際承銷股數", ""),
            underwriting_price=values.get("承銷價(元)", ""),
            actual_underwriting_price=values.get("實際承銷價(元)", ""),
            listing_date=parse_roc_date(values.get("撥券日期(上市、上櫃日期)")),
            broker=values.get("主辦券商", ""),
            subscription_shares=values.get("申購股數", ""),
            total_amount=values.get("總承銷金額(元)", ""),
            qualified_count=values.get("總合格件", ""),
            winning_rate=values.get("中籤率(%)", ""),
            cancel_reason=values.get("取消公開抽籤", "") or values.get("取消公開抽籤 ", ""),
        )


def fetch_public_offerings(
    year: int,
    *,
    timeout: float = 20,
    session: requests.Session | None = None,
    attempts: int = 3,
    retry_delay: float = 2,
) -> list[PublicOffering]:
    """Fetch TWSE public subscription entries for a Gregorian year."""
    http = session or requests.Session()
    errors: list[str] = []

    for attempt in range(attempts):
        for url in TWSE_PUBLIC_FORM_URLS:
            response: requests.Response | None = None
            try:
                response = http.get(
                    url,
                    params={"response": "json", "yy": str(year)},
                    timeout=timeout,
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "Referer": "https://www.twse.com.tw/",
                        "User-Agent": "line-stock-chatbot/0.1",
                    },
                )
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                return _parse_public_offerings_payload(payload)
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                errors.append(_describe_fetch_error(url, response, exc))

        if attempt < attempts - 1 and retry_delay > 0:
            sleep(retry_delay * (attempt + 1))

    details = " | ".join(errors[-4:])
    raise RuntimeError(f"Unable to fetch valid TWSE public offering JSON after retries: {details}")


def _parse_public_offerings_payload(payload: dict[str, Any]) -> list[PublicOffering]:
    if not isinstance(payload, dict):
        raise RuntimeError("TWSE JSON response is not an object")
    if payload.get("stat") != "OK":
        raise RuntimeError(f"TWSE returned non-OK status: {payload.get('stat')!r}")

    fields = payload.get("fields")
    rows = payload.get("data")
    if not isinstance(fields, list) or not isinstance(rows, list):
        raise RuntimeError("TWSE response does not contain expected fields/data arrays")

    return [PublicOffering.from_twse_row(fields, row) for row in rows]


def _describe_fetch_error(
    url: str,
    response: requests.Response | None,
    error: Exception,
) -> str:
    if response is None:
        return f"{url}: {type(error).__name__}: {error}"

    content_type = response.headers.get("Content-Type", "unknown")
    preview = response.text[:120].replace("\n", " ").replace("\r", " ")
    return (
        f"{url}: {type(error).__name__}: {error}; "
        f"status={response.status_code}; content-type={content_type}; body={preview!r}"
    )
