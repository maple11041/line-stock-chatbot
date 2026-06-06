from datetime import date

import requests

from line_stock_chatbot.twse import PublicOffering, fetch_public_offerings, parse_roc_date


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


def test_fetch_public_offerings_falls_back_after_non_json_response() -> None:
    session = _FakeSession(
        [
            _response("<html>temporarily unavailable</html>", content_type="text/html"),
            _response(
                '{"stat":"OK","fields":["序號","證券名稱"],"data":[["1","測試公司"]]}',
                content_type="application/json",
            ),
        ]
    )

    offerings = fetch_public_offerings(2026, session=session, attempts=1, retry_delay=0)

    assert offerings[0].name == "測試公司"
    assert len(session.urls) == 2


def test_fetch_public_offerings_reports_non_json_response_details() -> None:
    session = _FakeSession(
        [
            _response("<html>blocked</html>", content_type="text/html"),
            _response("", content_type="text/plain"),
        ]
    )

    try:
        fetch_public_offerings(2026, session=session, attempts=1, retry_delay=0)
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected TWSE fetch to fail")

    assert "content-type=text/html" in message
    assert "blocked" in message


class _FakeSession:
    def __init__(self, responses: list[requests.Response]) -> None:
        self.responses = iter(responses)
        self.urls: list[str] = []

    def get(self, url: str, **_: object) -> requests.Response:
        self.urls.append(url)
        return next(self.responses)


def _response(text: str, *, content_type: str) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response._content = text.encode()
    response.headers["Content-Type"] = content_type
    return response
