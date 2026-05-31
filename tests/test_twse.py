from datetime import date

from line_stock_chatbot.twse import PublicOffering, parse_roc_date


def test_parse_roc_date() -> None:
    assert parse_roc_date("115/06/11") == date(2026, 6, 11)
    assert parse_roc_date("未訂出") is None


def test_public_offering_from_twse_row_handles_trailing_cancel_field_space() -> None:
    fields = ["序號", "抽籤日期", "證券名稱", "證券代號", "發行市場", "取消公開抽籤 "]
    row = ["1", "115/06/11", "立弘", "1780", "初上櫃", "取消"]

    offering = PublicOffering.from_twse_row(fields, row)

    assert offering.draw_date == date(2026, 6, 11)
    assert offering.name == "立弘"
    assert offering.cancel_reason == "取消"
    assert offering.is_cancelled

