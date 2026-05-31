from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .twse import PublicOffering


@dataclass(frozen=True)
class DailyDigest:
    target_date: date
    draw_today: list[PublicOffering]
    open_today: list[PublicOffering]

    @property
    def has_items(self) -> bool:
        return bool(self.draw_today or self.open_today)


def build_daily_digest(
    offerings: list[PublicOffering],
    target_date: date,
    *,
    include_bonds: bool = False,
    include_cancelled: bool = False,
) -> DailyDigest:
    filtered = [
        item
        for item in offerings
        if (include_bonds or not item.is_bond) and (include_cancelled or not item.is_cancelled)
    ]

    draw_today = sorted(
        [item for item in filtered if item.draw_date == target_date],
        key=lambda item: (item.code, item.name),
    )
    open_today = sorted(
        [
            item
            for item in filtered
            if item.subscribe_start
            and item.subscribe_end
            and item.subscribe_start <= target_date <= item.subscribe_end
        ],
        key=lambda item: (item.subscribe_end or date.max, item.code, item.name),
    )
    return DailyDigest(target_date=target_date, draw_today=draw_today, open_today=open_today)


def format_digest(digest: DailyDigest) -> str:
    title_date = digest.target_date.strftime("%Y-%m-%d")
    lines = [f"台股抽籤通知 {title_date}"]

    if not digest.has_items:
        lines.append("")
        lines.append("今天沒有台股公開申購或抽籤案件。")
        return "\n".join(lines)

    if digest.draw_today:
        lines.append("")
        lines.append(f"今日抽籤（{len(digest.draw_today)} 檔）")
        for item in digest.draw_today:
            lines.extend(_format_item(item))

    if digest.open_today:
        lines.append("")
        lines.append(f"今日可申購（{len(digest.open_today)} 檔）")
        for item in digest.open_today:
            lines.extend(_format_item(item))

    lines.append("")
    lines.append("資料來源：臺灣證券交易所公開申購公告")
    return "\n".join(lines)


def _format_item(item: PublicOffering) -> list[str]:
    price = _prefer_actual(item.actual_underwriting_price, item.underwriting_price)
    return [
        f"- {item.code} {item.name}（{item.market}）",
        f"  承銷價：{price} 元；申購股數：{item.subscription_shares or '未提供'}",
        f"  申購期間：{_format_date(item.subscribe_start)} - {_format_date(item.subscribe_end)}",
        f"  抽籤：{_format_date(item.draw_date)}；撥券/上市櫃：{_format_date(item.listing_date)}",
        f"  中籤率：{_format_rate(item.winning_rate)}；主辦券商：{item.broker or '未提供'}",
    ]


def _prefer_actual(actual: str, original: str) -> str:
    if actual and actual != "未訂出":
        return actual
    return original or "未訂出"


def _format_date(value: date | None) -> str:
    return value.strftime("%Y/%m/%d") if value else "未訂出"


def _format_rate(value: str) -> str:
    if not value:
        return "未提供"
    return value if value.endswith("%") else f"{value}%"


def split_message(text: str, *, max_chars: int = 4500) -> list[str]:
    """Split LINE text messages while preserving whole lines where possible."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in text.splitlines():
        extra_len = len(line) + (1 if current else 0)
        if current and current_len + extra_len > max_chars:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += extra_len

    if current:
        chunks.append("\n".join(current))

    return chunks

