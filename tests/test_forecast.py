from datetime import date
from decimal import Decimal

from line_stock_chatbot.forecast import build_deadline_forecast, format_forecast
from line_stock_chatbot.twse import PublicOffering
from line_stock_chatbot.wespai import SubscriptionSnapshot


def test_build_deadline_forecast_converts_shares_to_lots() -> None:
    target = date(2026, 5, 29)
    offering = _offering(code="8033", name="雷虎", subscribe_end=target, shares="1,020,000")
    snapshots = {
        "8033": SubscriptionSnapshot(code="8033", name="雷虎", application_count=162_091)
    }

    forecast = build_deadline_forecast([offering], snapshots, target)

    assert len(forecast.items) == 1
    assert forecast.items[0].underwriting_lots == Decimal("1020")
    assert forecast.items[0].estimated_winning_rate.quantize(Decimal("0.01")) == Decimal("0.63")


def test_build_deadline_forecast_skips_zero_application_counts() -> None:
    target = date(2026, 5, 29)
    offering = _offering(code="8033", name="雷虎", subscribe_end=target, shares="1,020,000")
    snapshots = {"8033": SubscriptionSnapshot(code="8033", name="雷虎", application_count=0)}

    assert not build_deadline_forecast([offering], snapshots, target).has_items


def test_format_forecast_marks_rate_as_estimated() -> None:
    target = date(2026, 5, 29)
    offering = _offering(code="8033", name="雷虎", subscribe_end=target, shares="1,020,000")
    snapshots = {
        "8033": SubscriptionSnapshot(code="8033", name="雷虎", application_count=162_091)
    }

    text = format_forecast(build_deadline_forecast([offering], snapshots, target))

    assert "台股抽籤賽況預報" in text
    assert "申購總筆數：162,091 筆" in text
    assert "預估中籤率：0.63%" in text
    assert "實際結果以證交所公告為準" in text


def _offering(*, code: str, name: str, subscribe_end: date, shares: str) -> PublicOffering:
    return PublicOffering(
        sequence="1",
        draw_date=date(2026, 6, 2),
        name=name,
        code=code,
        market="上市增資",
        subscribe_start=date(2026, 5, 27),
        subscribe_end=subscribe_end,
        underwriting_shares=shares,
        actual_underwriting_shares=shares,
        underwriting_price="108",
        actual_underwriting_price="108",
        listing_date=date(2026, 6, 10),
        broker="福邦",
        subscription_shares="1,000",
        total_amount="110,160,000",
        qualified_count="0",
        winning_rate="0",
        cancel_reason="",
    )

