from datetime import date

from line_stock_chatbot.notify import build_daily_digest, format_digest, split_message
from line_stock_chatbot.twse import PublicOffering


def test_build_daily_digest_excludes_bonds_by_default() -> None:
    target = date(2026, 6, 5)
    stock = _offering(
        code="7839",
        name="達人網",
        market="初上櫃",
        draw_date=date(2026, 6, 9),
        subscribe_start=date(2026, 6, 3),
        subscribe_end=date(2026, 6, 5),
    )
    bond = _offering(
        code="A151FA",
        name="115央債甲06",
        market="中央登錄公債",
        draw_date=date(2026, 6, 9),
        subscribe_start=date(2026, 6, 1),
        subscribe_end=date(2026, 6, 5),
    )

    digest = build_daily_digest([stock, bond], target)

    assert digest.open_today == [stock]


def test_format_digest_includes_daily_sections() -> None:
    target = date(2026, 6, 5)
    stock = _offering(
        code="7839",
        name="達人網",
        market="初上櫃",
        draw_date=target,
        subscribe_start=date(2026, 6, 3),
        subscribe_end=target,
    )

    text = format_digest(build_daily_digest([stock], target))

    assert "今日抽籤" in text
    assert "今日可申購" in text
    assert "7839 達人網" in text


def test_split_message_respects_max_chars() -> None:
    text = "a\nbb\nccc"

    assert split_message(text, max_chars=4) == ["a\nbb", "ccc"]


def _offering(
    *,
    code: str,
    name: str,
    market: str,
    draw_date: date,
    subscribe_start: date,
    subscribe_end: date,
) -> PublicOffering:
    return PublicOffering(
        sequence="1",
        draw_date=draw_date,
        name=name,
        code=code,
        market=market,
        subscribe_start=subscribe_start,
        subscribe_end=subscribe_end,
        underwriting_shares="1,000",
        actual_underwriting_shares="1,000",
        underwriting_price="36",
        actual_underwriting_price="未訂出",
        listing_date=date(2026, 6, 15),
        broker="福邦",
        subscription_shares="1,000",
        total_amount="未訂出",
        qualified_count="0",
        winning_rate="0",
        cancel_reason="",
    )

