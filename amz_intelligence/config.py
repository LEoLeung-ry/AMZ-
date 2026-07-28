from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class MarketConfig:
    code: str
    name: str
    flag: str
    currency_code: str
    currency_symbol: str
    amazon_domain: str
    source_url: str
    snapshot_label: str
    locale_name: str


MARKETS: Final[dict[str, MarketConfig]] = {
    "JP": MarketConfig(
        code="JP",
        name="日本站",
        flag="🇯🇵",
        currency_code="JPY",
        currency_symbol="¥",
        amazon_domain="amazon.co.jp",
        source_url=(
            "https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vQ0-aEMMkENn3f4WyGVbUhB0D5XPpTCC1dJCL03MBkp3yUWUoz4vLEzFQPE_"
            "MkGeRvk6DuoA7IQwn23/pub?gid=1391802072&single=true&output=csv"
        ),
        snapshot_label="当前发布快照",
        locale_name="日语",
    ),
    "US": MarketConfig(
        code="US",
        name="美国站",
        flag="🇺🇸",
        currency_code="USD",
        currency_symbol="$",
        amazon_domain="amazon.com",
        source_url=(
            "https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vQOANJBKLzLMNS74IPjQ66Ms-GnwmN0q6AiIvvd6tpmnbH3WaWn3A4J-ZS-yf4OwA/"
            "pub?output=csv"
        ),
        snapshot_label="2026-03-24 数据快照",
        locale_name="英语",
    ),
    "DE": MarketConfig(
        code="DE",
        name="德国站",
        flag="🇩🇪",
        currency_code="EUR",
        currency_symbol="€",
        amazon_domain="amazon.de",
        source_url=(
            "https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vSeGe8hIDkk5DvvjG1auCP0ZM6oIxyv2wQ_Pc9ASrKBpZN4OARzElDiNmbss_EOvg/"
            "pub?output=csv"
        ),
        snapshot_label="2026-03-24 数据快照",
        locale_name="德语",
    ),
    "UK": MarketConfig(
        code="UK",
        name="英国站",
        flag="🇬🇧",
        currency_code="GBP",
        currency_symbol="£",
        amazon_domain="amazon.co.uk",
        source_url=(
            "https://docs.google.com/spreadsheets/d/e/"
            "2PACX-1vRuk9fOKFAVhRJDh_0ov0JI6ZqCvt338d1wwc12GGEICuNEtgZd7-J0hixVwr3cSg/"
            "pub?output=csv"
        ),
        snapshot_label="2026-03-24 数据快照（源文件后续有更新）",
        locale_name="英语",
    ),
}


COLUMN_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "category_id": ("类目ID", "分类ID", "Browse Node ID", "节点ID"),
    "category_cn": ("中文名称", "中文类目", "中文解释"),
    "category_local": ("分类名称", "当地类目名", "本地名称", "类目名称"),
    "root_raw": ("根类目", "大类目", "Root Category", "root"),
    "node_path": ("Node Path", "节点路径", "类目路径"),
    "link": ("链接", "跳转", "跳转链接", "Amazon链接", "类目链接"),
    "sales": ("近12个月销量", "12个月销量", "年销量"),
    "revenue": ("近12个月净销售额", "12个月净销售额", "年销售额"),
    "search_volume": ("近12个月搜索量", "12个月搜索量", "搜索量"),
    "clicks": ("近12个月点击量", "12个月点击量", "点击量"),
    "views": ("近12个月浏览量", "12个月浏览量", "浏览量"),
    "search_conversion": ("搜索转化率", "点击产出效率"),
    "ctr": ("点击率", "CTR"),
    "asp": ("平均价格", "平均售价", "ASP"),
    "top_keyword": ("最受欢迎关键词", "热门关键词", "Top Keyword"),
    "top_keyword_value": ("最受欢迎关键词值", "热门关键词值", "Top Keyword Value"),
    "asin_count": ("ASIN数量", "ASIN数", "ASIN Count"),
    "price_band": ("价格转化率最大值", "高转化价格区间", "价格区间"),
    "rating_4_plus": ("4星及以上评分数量", "4星以上评分数量"),
    "rating_3": ("3星评分数量",),
    "rating_2": ("2星评分数量",),
    "rating_1": ("1星评分数量",),
    "source_sales_density": ("单ASIN销售密度", "单ASIN销售额"),
    "source_unit_density": ("单ASIN销量",),
    "source_search_supply": ("搜索供需比",),
    "source_price_quality": ("客单价质量",),
    "source_pain": ("产品痛点机会",),
    "snapshot_date": ("快照日期", "数据日期", "统计日期"),
}


ROOT_CATEGORY_GROUPS: Final[dict[str, tuple[str, ...]]] = {
    "电脑与周边": ("pc", "computers", "computer", "pc-accessories"),
    "电子产品": ("electronics", "ce-de", "consumer-electronics"),
    "家居厨房": (
        "kitchen",
        "home-garden",
        "home",
        "home-kitchen",
        "garden",
        "furniture",
    ),
    "办公用品": ("office-products", "officeproduct", "office"),
    "运动户外": ("sports", "sporting-goods", "outdoors", "outdoor-recreation"),
    "美妆": ("beauty", "luxury-beauty"),
    "个护健康": ("drugstore", "hpc", "health", "health-personal-care"),
    "服装配饰": ("fashion", "apparel", "clothing", "shoes", "luggage"),
    "母婴": ("baby", "baby-products"),
    "玩具儿童": ("toys", "kids", "toys-and-games"),
    "食品饮料": ("food-beverage", "grocery", "grocery-gourmet-food"),
    "汽车用品": ("automotive", "car", "motorcycles"),
    "家装工具": ("diy", "hi", "tools-home-improvement"),
    "工业科研": ("industrial-scientific", "biss", "scientific", "industrial"),
    "宠物用品": ("pet-supplies", "pets"),
    "珠宝钟表": ("jewelry", "watches"),
    "图书与内容": ("books", "kindle-store", "audible", "music", "dvd"),
    "数字软件": ("apps", "mobile-apps", "software", "digital-text", "prime-video"),
    "游戏": ("video-games", "videogames", "games"),
}


DIGITAL_HIGH_RISK_ROOTS: Final[set[str]] = {
    "apps",
    "mobile-apps",
    "software",
    "digital-text",
    "kindle-store",
    "audible",
    "prime-video",
}

DIGITAL_MEDIUM_RISK_ROOTS: Final[set[str]] = {
    "books",
    "music",
    "dvd",
    "video-games",
    "videogames",
    "games",
}

DIGITAL_HIGH_RISK_TERMS: Final[tuple[str, ...]] = (
    "software",
    "subscription",
    "digital download",
    "ebook",
    "e-book",
    "kindle",
    "streaming",
    "应用",
    "软件",
    "订阅",
    "电子书",
    "デジタル",
    "アプリ",
    "abonnement",
)


STRATEGY_PRESETS: Final[dict[str, dict[str, float]]] = {
    "大单品": {
        "MarketFactor": 0.32,
        "DemandFactor": 0.18,
        "AccessFactor": 0.18,
        "MonetizationFactor": 0.12,
        "EfficiencyFactor": 0.08,
        "PainFactor": 0.07,
        "ConfidenceFactor": 0.05,
    },
    "蓝海切入": {
        "MarketFactor": 0.10,
        "DemandFactor": 0.18,
        "AccessFactor": 0.35,
        "MonetizationFactor": 0.12,
        "EfficiencyFactor": 0.08,
        "PainFactor": 0.12,
        "ConfidenceFactor": 0.05,
    },
    "高客单精品": {
        "MarketFactor": 0.18,
        "DemandFactor": 0.10,
        "AccessFactor": 0.20,
        "MonetizationFactor": 0.32,
        "EfficiencyFactor": 0.08,
        "PainFactor": 0.07,
        "ConfidenceFactor": 0.05,
    },
    "结构性需求机会": {
        "MarketFactor": 0.10,
        "DemandFactor": 0.35,
        "AccessFactor": 0.25,
        "MonetizationFactor": 0.08,
        "EfficiencyFactor": 0.12,
        "PainFactor": 0.05,
        "ConfidenceFactor": 0.05,
    },
    "稳健优先": {
        "MarketFactor": 0.20,
        "DemandFactor": 0.15,
        "AccessFactor": 0.20,
        "MonetizationFactor": 0.15,
        "EfficiencyFactor": 0.10,
        "PainFactor": 0.05,
        "ConfidenceFactor": 0.15,
    },
}


FACTOR_LABELS: Final[dict[str, str]] = {
    "MarketFactor": "市场规模",
    "DemandFactor": "需求强度",
    "AccessFactor": "竞争可进入性",
    "MonetizationFactor": "变现质量",
    "EfficiencyFactor": "流量效率",
    "PainFactor": "痛点改良空间",
    "ConfidenceFactor": "数据置信度",
}
