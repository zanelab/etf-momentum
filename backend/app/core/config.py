"""应用配置（数据库 URL 等）。"""

import os

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./etf_momentum.db")
