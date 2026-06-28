"""Seed default configuration data on first startup."""
from __future__ import annotations

import json
from datetime import datetime

from sqlmodel import select

from app import db as db_module
from app.models.static_pool import StaticPool
from app.models.strategy_param import StrategyParam
from app.models.theme_keyword import ThemeKeyword

# Static core pool from main.py (curated subset).
DEFAULT_STATIC_POOL: list[str] = [
    "159206.XSHE", "159218.XSHE", "159227.XSHE", "159256.XSHE", "159323.XSHE",
    "159326.XSHE", "159363.XSHE", "159378.XSHE", "159502.XSHE", "159509.XSHE",
    "159516.XSHE", "159518.XSHE", "159529.XSHE", "159550.XSHE", "159566.XSHE",
    "159583.XSHE", "159605.XSHE", "159611.XSHE", "159637.XSHE", "159638.XSHE",
    "159667.XSHE", "159732.XSHE", "159755.XSHE", "159766.XSHE", "159819.XSHE",
    "159825.XSHE", "159840.XSHE", "159851.XSHE", "159852.XSHE", "159865.XSHE",
    "159869.XSHE", "159870.XSHE", "159883.XSHE", "159892.XSHE", "159915.XSHE",
    "159919.XSHE", "159922.XSHE", "159928.XSHE", "159949.XSHE", "159967.XSHE",
    "159980.XSHE", "159981.XSHE", "159985.XSHE", "159992.XSHE", "159995.XSHE",
    "159998.XSHE", "161226.XSHE", "501018.XSHG", "510050.XSHG", "510180.XSHG",
    "510300.XSHG", "510410.XSHG", "510500.XSHG", "510760.XSHG", "510880.XSHG",
    "510900.XSHG", "511260.XSHG", "511380.XSHG", "512000.XSHG", "512010.XSHG",
    "512050.XSHG", "512070.XSHG", "512100.XSHG", "512170.XSHG", "512200.XSHG",
    "512400.XSHG", "512480.XSHG", "512660.XSHG", "512670.XSHG", "512690.XSHG",
    "512710.XSHG", "512800.XSHG", "512880.XSHG", "512890.XSHG", "512980.XSHG",
    "513030.XSHG", "513050.XSHG", "513090.XSHG", "513100.XSHG", "513120.XSHG",
    "513130.XSHG", "513180.XSHG", "513190.XSHG", "513290.XSHG", "513300.XSHG",
    "513310.XSHG", "513330.XSHG", "513350.XSHG", "513360.XSHG", "513400.XSHG",
    "513500.XSHG", "513520.XSHG", "513630.XSHG", "513690.XSHG", "513750.XSHG",
    "513920.XSHG", "513970.XSHG", "515000.XSHG", "515030.XSHG", "515050.XSHG",
    "515120.XSHG", "515170.XSHG", "515210.XSHG", "515220.XSHG", "515250.XSHG",
    "515400.XSHG", "515650.XSHG", "515790.XSHG", "515880.XSHG", "515980.XSHG",
    "516010.XSHG", "516150.XSHG", "516160.XSHG", "516190.XSHG", "516510.XSHG",
    "516520.XSHG", "517520.XSHG", "518880.XSHG", "520830.XSHG", "560860.XSHG",
    "561330.XSHG", "561360.XSHG", "561980.XSHG", "562500.XSHG", "562590.XSHG",
    "562800.XSHG", "563300.XSHG", "588080.XSHG", "588120.XSHG", "588170.XSHG",
    "588200.XSHG", "588220.XSHG", "588790.XSHG",
]

DEFAULT_THEMES: dict[str, list[str]] = {
    "半导体": ["半导体", "芯片", "集成电路"],
    "医药": ["医药", "医疗", "创新药", "生物", "疫苗", "健康"],
    "消费": ["消费", "食品", "白酒", "家电", "零售", "酒"],
    "新能源": ["新能源", "光伏", "锂电", "风电", "碳中和", "电池", "储能"],
    "电力公用": ["电力", "绿电", "绿色电力", "公用事业", "水务", "燃气"],
    "军工": ["军工", "国防"],
    "金融": ["银行", "券商", "保险", "金融", "证券", "非银"],
    "科技信息": ["科技", "人工智能", "软件", "计算机", "互联网", "信息", "数据", "云计算"],
    "宽基": ["沪深300", "中证500", "中证1000", "上证50", "创业板", "科创",
             "中证A50", "MSCI", "红利", "价值", "成长", "龙头"],
    "跨境": ["纳斯达克", "纳指", "标普", "恒生", "日经", "德国", "法国",
             "印度", "越南", "亚太", "美国", "港股", "中概"],
    "资源能源": ["有色", "钢铁", "煤炭", "石油", "黄金", "白银", "铜", "稀土",
                 "矿业", "资源", "豆粕", "能源化工", "油气", "天然气", "原油"],
    "地产基建": ["地产", "房地产", "建材", "基建", "建筑"],
    "通信": ["通信", "5G"],
    "汽车": ["汽车", "智能驾驶", "新能车", "电动车"],
    "机器人": ["机器人", "机械", "自动化", "智能制造"],
    "传媒": ["传媒", "游戏", "动漫", "影视"],
    "农业": ["农业", "养殖", "畜牧"],
    "环保": ["环保", "碳排放", "环境"],
}

DEFAULT_STRATEGY_PARAMS: dict[str, object] = {
    "stock_sum": 1,
    "min_money": 500,
    "momentum_days": 25,
    "enable_volume_check": True,
    "volume_lookback": 5,
    "volume_threshold": 2.5,
    "ma_short": 20,
    "ma_long": 60,
    "enable_ma_filter": True,
    "stop_loss_ratio": 0.92,
    "defensive_etf": "511880.XSHG",
    "enable_industry_diverse": False,
    "dynamic_pool_size": 150,
    "dynamic_pool_min_money": 50_000_000,
}


def seed_if_empty() -> None:
    """Populate defaults if any of the three tables is empty."""
    with db_module.session_scope() as session:
        pool_empty = session.exec(select(StaticPool).limit(1)).first() is None
        themes_empty = session.exec(select(ThemeKeyword).limit(1)).first() is None
        strategy_empty = session.exec(select(StrategyParam).limit(1)).first() is None

        if not (pool_empty or themes_empty or strategy_empty):
            return

        if pool_empty:
            now = datetime.utcnow()
            for code in DEFAULT_STATIC_POOL:
                session.add(
                    StaticPool(
                        code=code,
                        display_name=None,
                        enabled=True,
                        created_at=now,
                        updated_at=now,
                    )
                )

        if themes_empty:
            for theme, keywords in DEFAULT_THEMES.items():
                for kw in keywords:
                    session.add(ThemeKeyword(theme=theme, keyword=kw))

        if strategy_empty:
            now = datetime.utcnow()
            for key, value in DEFAULT_STRATEGY_PARAMS.items():
                session.add(
                    StrategyParam(key=key, value_json=json.dumps(value), updated_at=now)
                )