from decimal import Decimal

from line_stock_chatbot.wespai import parse_subscription_snapshots


def test_parse_subscription_snapshots() -> None:
    html = """
    <table id="example">
      <thead><tr><th>代號</th><th>公司</th><th>收盤價</th><th>總合格件</th></tr></thead>
      <tbody><tr><td>8033</td><td>雷虎</td><td>143</td><td>162,091</td></tr></tbody>
    </table>
    """

    snapshots = parse_subscription_snapshots(html)

    assert snapshots["8033"].name == "雷虎"
    assert snapshots["8033"].market_price == Decimal("143")
    assert snapshots["8033"].application_count == 162_091
