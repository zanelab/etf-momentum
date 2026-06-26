"""akshare 数据源抽象与实现。"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class EtfMasterRow:
    """akshare 返回的单条 ETF 主数据。"""

    code: str
    name: str
    market: str
    category: str | None = None


@dataclass(frozen=True)
class DailyPriceRow:
    """akshare 返回的单条日线行情。"""

    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class AkshareClient(Protocol):
    """akshare 客户端抽象。"""

    def list_etfs(self) -> list[EtfMasterRow]:
        ...

    def fetch_etf_hist(
        self, code: str, start: date, end: date
    ) -> list[DailyPriceRow]:
        ...


class AkshareHttpClient:
    """真实 akshare HTTP 客户端。懒加载 akshare 以避免测试时副作用。"""

    def list_etfs(self) -> list[EtfMasterRow]:
        import akshare as ak  # 懒加载

        df = ak.fund_etf_spot_em()
        rows: list[EtfMasterRow] = []
        for _, r in df.iterrows():
            code = str(r["代码"]).strip()
            name = str(r["名称"]).strip()
            market = _infer_market(code)
            category = _infer_category(name)
            rows.append(EtfMasterRow(code=code, name=name, market=market, category=category))
        return rows

    def fetch_etf_hist(
        self, code: str, start: date, end: date
    ) -> list[DailyPriceRow]:
        import akshare as ak  # 懒加载

        df = ak.fund_etf_hist_em(
            symbol=code,
            period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="",
        )
        rows: list[DailyPriceRow] = []
        for _, r in df.iterrows():
            rows.append(
                DailyPriceRow(
                    date=r["日期"].date() if hasattr(r["日期"], "date") else r["日期"],
                    open=Decimal(str(r["开盘"])),
                    high=Decimal(str(r["最高"])),
                    low=Decimal(str(r["最低"])),
                    close=Decimal(str(r["收盘"])),
                    volume=int(r["成交量"]),
                )
            )
        return rows


class FakeAkshareClient:
    """测试替身：从预设 dict 返回数据。"""

    def __init__(
        self,
        etfs: list[EtfMasterRow] | None = None,
        prices: dict[str, list[DailyPriceRow]] | None = None,
    ) -> None:
        self._etfs = list(etfs or [])
        self._prices = dict(prices or {})

    def list_etfs(self) -> list[EtfMasterRow]:
        return list(self._etfs)

    def fetch_etf_hist(
        self, code: str, start: date, end: date
    ) -> list[DailyPriceRow]:
        rows = self._prices.get(code, [])
        return [r for r in rows if start <= r.date <= end]


def _infer_market(code: str) -> str:
    """从 ETF 代码前 3 位推断交易所：上海 51x/56x/58x，深圳 15x/16x/18x。"""
    if code.startswith(("51", "56", "58", "60")):
        return "SH"
    if code.startswith(("15", "16", "18")):
        return "SZ"
    return ""


def _infer_category(name: str) -> str | None:
    """从名称启发式解析分类。MVP 仅返回前 2 字。"""
    if not name:
        return None
    if "债" in name:
        return "债券"
    if "商品" in name or "黄金" in name:
        return "商品"
    if "跨境" in name or "纳斯达克" in name or "标普" in name or "恒生" in name:
        return "跨境"
    return "指数"
