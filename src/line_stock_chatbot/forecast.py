from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from .twse import PublicOffering
from .wespai import SubscriptionSnapshot

SHARES_PER_LOT = Decimal("1000")


@dataclass(frozen=True)
class ForecastItem:
    offering: PublicOffering
    application_count: int
    underwriting_lots: Decimal
    estimated_winning_rate: Decimal


@dataclass(frozen=True)
class DeadlineForecast:
    target_date: date
    items: list[ForecastItem]

    @property
    def has_items(self) -> bool:
        return bool(self.items)


def build_deadline_forecast(
    offerings: list[PublicOffering],
    snapshots: dict[str, SubscriptionSnapshot],
    target_date: date,
    *,
    include_cancelled: bool = False,
) -> DeadlineForecast:
    items: list[ForecastItem] = []
    for offering in offerings:
        if offering.subscribe_end != target_date or offering.is_bond:
            continue
        if offering.is_cancelled and not include_cancelled:
            continue

        snapshot = snapshots.get(offering.code)
        if not snapshot or snapshot.application_count <= 0:
            continue

        underwriting_lots = calculate_underwriting_lots(offering)
        if underwriting_lots <= 0:
            continue

        estimated_rate = calculate_winning_rate(underwriting_lots, snapshot.application_count)
        items.append(
            ForecastItem(
                offering=offering,
                application_count=snapshot.application_count,
                underwriting_lots=underwriting_lots,
                estimated_winning_rate=estimated_rate,
            )
        )

    items.sort(key=lambda item: (item.offering.code, item.offering.name))
    return DeadlineForecast(target_date=target_date, items=items)


def format_forecast(forecast: DeadlineForecast) -> str:
    title_date = forecast.target_date.strftime("%Y-%m-%d")
    lines = [f"台股抽籤賽況預報 {title_date}"]

    if not forecast.has_items:
        lines.append("")
        lines.append("今天沒有可發布的申購截止賽況。")
        return "\n".join(lines)

    lines.append("")
    lines.append(f"今日申購截止（{len(forecast.items)} 檔）")
    for item in forecast.items:
        offering = item.offering
        lines.extend(
            [
                f"- {offering.code} {offering.name}（{offering.market}）",
                f"  承銷張數：{_format_decimal(item.underwriting_lots)} 張",
                f"  申購總筆數：{item.application_count:,} 筆",
                f"  預估中籤率：{item.estimated_winning_rate:.2f}%",
                f"  抽籤：{_format_date(offering.draw_date)}；主辦券商：{offering.broker}",
            ]
        )

    lines.append("")
    lines.append("預估值依截止日晚間公開彙整筆數計算，實際結果以證交所公告為準。")
    lines.append("資料來源：臺灣證券交易所公開申購公告、撿股讚申購彙整")
    return "\n".join(lines)


def calculate_underwriting_lots(offering: PublicOffering) -> Decimal:
    shares = _parse_decimal(
        offering.actual_underwriting_shares
        if offering.actual_underwriting_shares not in {"", "未訂出"}
        else offering.underwriting_shares
    )
    return shares / SHARES_PER_LOT


def calculate_winning_rate(underwriting_lots: Decimal, application_count: int) -> Decimal:
    if application_count <= 0:
        return Decimal("0")

    return min(
        Decimal("100"),
        underwriting_lots / Decimal(application_count) * Decimal("100"),
    )


def _parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "").strip())
    except InvalidOperation:
        return Decimal("0")


def _format_decimal(value: Decimal) -> str:
    if value == value.to_integral():
        return f"{int(value):,}"
    return f"{value:,}"


def _format_date(value: date | None) -> str:
    return value.strftime("%Y/%m/%d") if value else "未訂出"
