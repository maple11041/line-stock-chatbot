from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from .forecast import calculate_underwriting_lots, calculate_winning_rate
from .twse import PublicOffering
from .wespai import SubscriptionSnapshot


@dataclass(frozen=True)
class DailyDigest:
    target_date: date
    open_today: list[PublicOffering]
    snapshots: dict[str, SubscriptionSnapshot]

    @property
    def has_items(self) -> bool:
        return bool(self.open_today)


def build_daily_digest(
    offerings: list[PublicOffering],
    target_date: date,
    *,
    snapshots: dict[str, SubscriptionSnapshot] | None = None,
    include_bonds: bool = False,
    include_cancelled: bool = False,
) -> DailyDigest:
    live_snapshots = snapshots or {}
    filtered = [
        item
        for item in offerings
        if (include_bonds or not item.is_bond) and (include_cancelled or not item.is_cancelled)
    ]

    open_today = sorted(
        [
            item
            for item in filtered
            if item.subscribe_start
            and item.subscribe_end
            and item.subscribe_start <= target_date <= item.subscribe_end
            and _premium_rate(item, live_snapshots.get(item.code)) > Decimal("20")
        ],
        key=lambda item: (item.subscribe_end or date.max, item.code, item.name),
    )
    return DailyDigest(
        target_date=target_date,
        open_today=open_today,
        snapshots=live_snapshots,
    )


def format_digest(digest: DailyDigest) -> str:
    title_date = digest.target_date.strftime("%Y-%m-%d")
    lines = [f"台股抽籤通知 {title_date}"]

    if not digest.has_items:
        lines.append("")
        lines.append("今天沒有申購期間內且溢價率大於 20% 的台股抽籤案件。")
        return "\n".join(lines)

    if digest.open_today:
        lines.append("")
        lines.append(f"今日可申購且溢價率大於 20%（{len(digest.open_today)} 檔）")
        for item in digest.open_today:
            lines.extend(_format_item(item, digest.snapshots))

    lines.append("")
    lines.append("溢價率以最新收盤價估算；動態即時中籤率以目前累積筆數估算。")
    lines.append("以上為參考值，實際結果以證交所公告為準。")
    lines.append("資料來源：臺灣證券交易所公開申購公告、撿股讚申購彙整")
    return "\n".join(lines)


def _format_item(
    item: PublicOffering,
    snapshots: dict[str, SubscriptionSnapshot],
) -> list[str]:
    price = _prefer_actual(item.actual_underwriting_price, item.underwriting_price)
    snapshot = snapshots.get(item.code)
    premium_rate = _premium_rate(item, snapshot)
    lines = [
        f"- {item.code} {item.name}（{item.market}）",
        f"  承銷價：{price} 元；申購股數：{item.subscription_shares or '未提供'}",
        f"  最新收盤價：{snapshot.market_price if snapshot else '未提供'} 元；"
        f"溢價率：{premium_rate:.2f}%",
        f"  申購期間：{_format_date(item.subscribe_start)} - {_format_date(item.subscribe_end)}",
        f"  抽籤：{_format_date(item.draw_date)}；撥券/上市櫃：{_format_date(item.listing_date)}",
    ]
    if snapshot and snapshot.application_count > 0:
        rate = calculate_winning_rate(
            calculate_underwriting_lots(item),
            snapshot.application_count,
        )
        lines.append(
            f"  申購總筆數：{snapshot.application_count:,} 筆；動態即時中籤率：{rate:.2f}%"
        )
    else:
        lines.append("  申購總筆數：尚未有累積資料")

    return lines


def _prefer_actual(actual: str, original: str) -> str:
    if actual and actual != "未訂出":
        return actual
    return original or "未訂出"


def _premium_rate(item: PublicOffering, snapshot: SubscriptionSnapshot | None) -> Decimal:
    underwriting_price = _parse_decimal(
        _prefer_actual(
            item.actual_underwriting_price,
            item.underwriting_price,
        )
    )
    if not snapshot or snapshot.market_price is None or underwriting_price <= 0:
        return Decimal("0")

    return (snapshot.market_price - underwriting_price) / underwriting_price * Decimal("100")


def _parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "").strip())
    except InvalidOperation:
        return Decimal("0")


def _format_date(value: date | None) -> str:
    return value.strftime("%Y/%m/%d") if value else "未訂出"


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
