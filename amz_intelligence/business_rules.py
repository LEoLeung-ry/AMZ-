from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from .fx import apply_cny_conversion


ENTRY_LABELS: dict[str, str] = {
    "A": "A 普通可进入",
    "B": "B 有条件可进入",
    "C": "C 高门槛",
    "D": "D 默认排除",
}

ENTRY_MULTIPLIERS: dict[str, float] = {"A": 1.00, "B": 0.75, "C": 0.30, "D": 0.00}
ENTRY_SEVERITY: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3}


@dataclass(frozen=True)
class BarrierRule:
    code: str
    family: str
    level: str
    terms: tuple[str, ...]
    reasons: tuple[str, ...]
    resources: tuple[str, ...]
    capability: str | None = None
    root_groups: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()
    confidence: str = "高"


# Multilingual commercial triage rules. They are decision support, not legal advice.
BARRIER_RULES: tuple[BarrierRule, ...] = (
    BarrierRule(
        code="ALCOHOL",
        family="酒类",
        level="D",
        terms=(
            r"\bbeer\b", r"\bale\b", r"\blager\b", r"\bwine\b", r"\bvodka\b", r"\bwhisk(?:y|ey)\b",
            r"\bspirits?\b", r"\bliquor\b", r"\bcider\b", r"alcoholic beverage", r"啤酒", r"葡萄酒",
            r"烈酒", r"白酒", r"清酒", r"焼酎", r"ビール", r"ワイン", r"酒類", r"bier", r"wein",
            r"spirituosen", r"schnaps",
        ),
        excludes=(r"glass", r"mug", r"cup", r"rack", r"holder", r"coaster", r"sign", r"shirt", r"costume", r"accessor"),
        reasons=("酒类经营与进口许可", "税务及标签要求", "跨境与仓储限制"),
        resources=("当地持证进口/销售主体", "酒类税务与标签合规", "可承运酒类的物流仓储"),
        capability="alcohol_license",
    ),
    BarrierRule(
        code="PET_MED_PESTICIDE",
        family="宠物药/农药杀虫",
        level="D",
        terms=(
            r"flea", r"tick treatment", r"flea & tick", r"deworm", r"wormer", r"veterinary medicine",
            r"animal drug", r"pesticide", r"insecticide", r"rodenticide", r"herbicide", r"fungicide",
            r"跳蚤", r"蜱", r"驱虫药", r"宠物药", r"兽药", r"杀虫剂", r"农药", r"除草剂", r"ノミ", r"ダニ",
            r"駆虫", r"動物用医薬品", r"殺虫剤", r"農薬", r"floh", r"zecke", r"tierarznei", r"insektizid",
            r"schädlingsbekämpfung",
        ),
        reasons=("动物药品或农药注册", "有效成分与功效宣称监管", "高产品责任及平台审核"),
        resources=("目的国持证主体", "产品注册/批准文件", "成分、标签与批次追溯体系"),
        capability="pet_medicine_pesticide",
    ),
    BarrierRule(
        code="HUMAN_MEDICINE",
        family="人用药品/准药品",
        level="D",
        terms=(
            r"prescription", r"over[- ]?the[- ]?counter", r"\botc\b", r"medicine", r"medication", r"drug product",
            r"analgesic", r"antibiotic", r"antifungal treatment", r"医薬品", r"药品", r"藥品", r"处方药", r"非处方药",
            r"解熱鎮痛", r"育毛剤", r"発毛剤", r"薬用", r"arzneimittel", r"medikament", r"apothekenpflichtig",
        ),
        excludes=(r"medicine cabinet", r"pill box", r"storage", r"book", r"textbook"),
        reasons=("药品或准药品许可/注册", "功效宣称与标签监管", "当地持证经营要求"),
        resources=("持证主体与产品批准", "GMP/质量与批次追溯", "药品合规和不良事件处理能力"),
        capability="human_medicine",
    ),
    BarrierRule(
        code="TOBACCO_NICOTINE",
        family="烟草/尼古丁",
        level="D",
        terms=(r"tobacco", r"cigarette", r"cigar", r"nicotine", r"vape", r"e-cig", r"烟草", r"香烟", r"雪茄", r"尼古丁", r"電子タバコ", r"たばこ"),
        excludes=(r"case", r"holder", r"ashtray", r"accessor"),
        reasons=("年龄限制与专门许可", "广告销售限制", "跨境运输和平台政策风险"),
        resources=("当地许可与年龄验证", "税务及平台合规体系"),
        capability="tobacco_license",
    ),
    BarrierRule(
        code="INFANT_FORMULA",
        family="婴幼儿配方/特殊食品",
        level="D",
        terms=(r"infant formula", r"baby formula", r"follow[- ]?on formula", r"婴儿配方", r"婴幼儿配方", r"粉ミルク", r"乳児用調製乳", r"säuglingsnahrung"),
        reasons=("特殊食品注册与严格标签要求", "婴幼儿产品高责任", "保质期与批次追溯"),
        resources=("食品进口与特殊食品合规能力", "稳定配方和批次追溯", "产品责任与召回体系"),
        capability="special_food",
    ),
    BarrierRule(
        code="MEDICAL_DEVICE",
        family="医疗器械/医用防护",
        level="C",
        terms=(
            r"medical device", r"surgical mask", r"medical mask", r"diagnostic", r"blood pressure monitor", r"glucose meter",
            r"pulse oximeter", r"hearing aid", r"medical thermometer", r"医療機器", r"医用口罩", r"外科口罩", r"医疗器械",
            r"血圧計", r"血糖", r"パルスオキシメータ", r"補聴器", r"medizinprodukt", r"blutdruckmessgerät",
        ),
        reasons=("医疗器械分类与注册", "当地责任主体/上市后责任", "临床、性能与标签资料"),
        resources=("目的国医疗器械合规路径", "当地责任主体", "技术文档、质量体系与产品责任保险"),
        capability="medical_device",
    ),
    BarrierRule(
        code="SUPPLEMENT",
        family="膳食补充剂/营养品",
        level="C",
        terms=(
            r"protein powder", r"whey protein", r"soy protein", r"dietary supplement", r"food supplement", r"sports nutrition",
            r"amino acid supplement", r"creatine", r"collagen supplement", r"vitamin supplement", r"l[- ]?lysine",
            r"citrulline", r"arginine", r"\bbcaa\b", r"\beaa\b", r"mineral supplement", r"zinc supplement",
            r"蛋白粉", r"蛋白质粉", r"大豆蛋白", r"膳食补充剂", r"营养补充剂", r"保健食品", r"维生素补充剂",
            r"プロテイン", r"サプリメント", r"健康食品", r"アミノ酸", r"クレアチン", r"イソフラボン", r"レシチン",
            r"シトルリン", r"アルギニン", r"亜鉛", r"瓜氨酸", r"精氨酸", r"锌补充剂",
            r"nahrungsergänzung", r"proteinpulver", r"eiweißpulver", r"vitaminpräparat",
        ),
        reasons=("入口产品与原料安全责任", "配方、标签及功效宣称监管", "生产质量和批次追溯"),
        resources=("食品/补充剂进口合规", "合格工厂与检测资料", "当地标签审核和产品责任体系"),
        capability="supplement_compliance",
    ),
    BarrierRule(
        code="FOOD_BEVERAGE",
        family="食品饮料",
        level="C",
        terms=(r"food", r"beverage", r"drink", r"snack", r"coffee", r"tea", r"食品", r"饮料", r"飲料", r"食品・飲料", r"lebensmittel", r"getränke"),
        root_groups=("食品饮料",),
        reasons=("食品进口、标签与原料要求", "保质期及批次追溯", "仓储温度与召回责任"),
        resources=("食品进口/经营主体", "成分和标签合规", "批次追溯、保质期与召回体系"),
        capability="food_import",
        confidence="中",
    ),
    BarrierRule(
        code="COLD_CHAIN",
        family="冷链/生鲜",
        level="C",
        terms=(r"frozen", r"fresh meat", r"fresh seafood", r"refrigerated", r"ice cream", r"生鲜", r"冷冻", r"冷蔵", r"鲜肉", r"冷凍", r"gekühlt", r"tiefkühl"),
        reasons=("冷链和保质期要求", "检疫/食品安全责任", "高损耗和退货风险"),
        resources=("目的国冷链仓储", "检疫和食品安全合规", "保质期及损耗管理"),
        capability="cold_chain",
    ),
    BarrierRule(
        code="COSMETIC_CLAIMS",
        family="强功效化妆品/外用治疗",
        level="C",
        terms=(r"hair growth", r"regrowth", r"acne treatment", r"eczema treatment", r"whitening treatment", r"育毛", r"発毛", r"養毛", r"祛痘治疗", r"美白治疗", r"治療", r"haarwuchs", r"aknebehandlung"),
        reasons=("强功效宣称可能触及药品/准药品", "成分与标签要求", "皮肤接触产品责任"),
        resources=("当地法规分类确认", "配方安全与检测", "责任主体和功效证据"),
        capability="cosmetics_compliance",
    ),
    BarrierRule(
        code="COSMETICS",
        family="化妆品/皮肤接触品",
        level="B",
        terms=(r"cosmetic", r"makeup", r"skin care", r"serum", r"cream", r"lotion", r"toner", r"化妆品", r"护肤", r"精华", r"面霜", r"美容液", r"化粧品", r"スキンケア", r"kosmetik", r"hautpflege"),
        root_groups=("美妆",),
        reasons=("配方、成分和标签合规", "当地责任主体要求可能存在", "皮肤接触和过敏责任"),
        resources=("合格配方与安全资料", "目的国标签审核", "产品责任与不良反应处理"),
        capability="cosmetics_compliance",
        confidence="中",
    ),
    BarrierRule(
        code="BATTERY_DG",
        family="锂电池/危险品运输",
        level="B",
        terms=(r"power bank", r"portable charger", r"lithium battery", r"battery pack", r"充电宝", r"移动电源", r"锂电池", r"モバイルバッテリー", r"リチウム", r"powerbank", r"lithium-ionen"),
        reasons=("锂电运输与危险品审核", "电池安全和召回风险", "目的国电气合规"),
        resources=("UN38.3等运输资料", "电池与整机检测", "危险品物流及产品责任保险"),
        capability="battery_dg",
    ),
    BarrierRule(
        code="ELECTRICAL",
        family="电气电子产品",
        level="B",
        terms=(r"charger", r"adapter", r"electric", r"electronic", r"powered", r"usb-c", r"充电器", r"适配器", r"电动", r"电子", r"電動", r"充電器", r"電気", r"elektrisch", r"ladegerät", r"netzteil"),
        root_groups=("电子产品", "电脑与周边"),
        excludes=(r"case", r"cover", r"stand", r"holder", r"bag", r"収納", r"ケース"),
        reasons=("电气安全、EMC及能效要求", "插头/电压适配", "产品责任和召回风险"),
        resources=("目的国认证与测试", "稳定电气供应链", "产品责任保险和召回预案"),
        capability="electrical_compliance",
        confidence="中",
    ),
    BarrierRule(
        code="PERSONAL_CARE_DEVICE",
        family="电动个护",
        level="B",
        terms=(r"shaver", r"trimmer", r"electric toothbrush", r"epilator", r"hair clipper", r"nose trimmer", r"剃须刀", r"剃毛器", r"电动牙刷", r"理发器", r"鼻毛器", r"シェーバー", r"トリマー", r"電動歯ブラシ", r"rasierer", r"haarschneider", r"elektrische zahnbürste"),
        reasons=("电气安全和皮肤接触责任", "电池/充电合规", "刀头、卫生与售后风险"),
        resources=("整机和电池测试", "刀头耗材与质量管理", "产品责任和售后体系"),
        capability="personal_care_device",
    ),
    BarrierRule(
        code="CHILDREN",
        family="儿童/母婴用品",
        level="B",
        terms=(r"baby", r"infant", r"toddler", r"children", r"kids", r"儿童", r"婴儿", r"婴幼儿", r"ベビー", r"子供", r"キッズ", r"babyartikel", r"kinder"),
        root_groups=("母婴", "玩具儿童"),
        excludes=(r"book", r"衣服", r"clothing", r"服", r"shoe"),
        reasons=("儿童安全标准与材料限制", "年龄分级和警示标签", "高产品责任"),
        resources=("儿童产品测试与合规文件", "材料及小部件风险控制", "产品责任保险"),
        capability="children_compliance",
        confidence="中",
    ),
    BarrierRule(
        code="CHEMICAL_AEROSOL",
        family="化学品/喷雾/易燃液体",
        level="B",
        terms=(r"aerosol", r"spray paint", r"solvent", r"adhesive", r"flammable", r"chemical cleaner", r"喷雾", r"溶剂", r"胶黏剂", r"易燃", r"エアゾール", r"スプレー塗料", r"lösungsmittel", r"entzündlich"),
        reasons=("危险品运输和仓储审核", "化学品标签/SDS要求", "泄漏与产品责任"),
        resources=("SDS及危险品分类", "合规包装和危险品物流", "成分及标签审核"),
        capability="chemical_dg",
    ),
    BarrierRule(
        code="AUTOMOTIVE_SAFETY",
        family="汽车安全/关键部件",
        level="B",
        terms=(r"brake", r"airbag", r"seat belt", r"steering", r"suspension", r"刹车", r"安全气囊", r"安全带", r"转向", r"ブレーキ", r"エアバッグ", r"sicherheitsgurt"),
        reasons=("车辆安全责任", "车型适配和安装风险", "认证与召回风险"),
        resources=("车型数据库与安装说明", "产品测试和责任保险", "稳定汽配质量体系"),
        capability="automotive_safety",
    ),
)


PROFILE_DEFAULTS: dict[str, dict[str, object]] = {
    "当前公司画像": {
        "label": "当前公司画像（日用品 / 电池 / 电动个护）",
        "base_fit": 68,
        "family_fit": {
            "普通消费品": 90,
            "电气电子产品": 82,
            "锂电池/危险品运输": 86,
            "电动个护": 88,
            "化妆品/皮肤接触品": 55,
            "强功效化妆品/外用治疗": 18,
            "儿童/母婴用品": 45,
            "汽车安全/关键部件": 55,
            "食品饮料": 10,
            "膳食补充剂/营养品": 8,
            "酒类": 0,
            "宠物药/农药杀虫": 0,
            "人用药品/准药品": 0,
            "医疗器械/医用防护": 15,
            "冷链/生鲜": 0,
            "烟草/尼古丁": 0,
        },
        "target_terms": (
            r"umbrella", r"parasol", r"雨伞", r"日伞", r"傘", r"fan", r"扇風機", r"风扇",
            r"power bank", r"charger", r"充电宝", r"充电器", r"モバイルバッテリー", r"充電器",
            r"shaver", r"trimmer", r"toothbrush", r"剃须刀", r"剃毛器", r"电动牙刷", r"シェーバー",
            r"mask", r"口罩", r"マスク", r"packaging", r"bag", r"包装", r"袋", r"garbage bag", r"垃圾袋",
            r"face towel", r"擦脸巾", r"storage", r"收纳",
        ),
    },
    "普通跨境卖家": {
        "label": "普通跨境卖家",
        "base_fit": 65,
        "family_fit": {
            "普通消费品": 82,
            "电气电子产品": 55,
            "锂电池/危险品运输": 42,
            "电动个护": 55,
            "化妆品/皮肤接触品": 40,
            "强功效化妆品/外用治疗": 10,
            "儿童/母婴用品": 38,
            "汽车安全/关键部件": 30,
            "食品饮料": 8,
            "膳食补充剂/营养品": 5,
            "酒类": 0,
            "宠物药/农药杀虫": 0,
            "人用药品/准药品": 0,
            "医疗器械/医用防护": 8,
            "冷链/生鲜": 0,
            "烟草/尼古丁": 0,
        },
        "target_terms": (),
    },
    "成熟合规团队": {
        "label": "具备当地合规和进口资源的团队",
        "base_fit": 78,
        "family_fit": {
            "普通消费品": 90,
            "电气电子产品": 82,
            "锂电池/危险品运输": 80,
            "电动个护": 82,
            "化妆品/皮肤接触品": 75,
            "强功效化妆品/外用治疗": 48,
            "儿童/母婴用品": 72,
            "汽车安全/关键部件": 68,
            "食品饮料": 55,
            "膳食补充剂/营养品": 52,
            "酒类": 25,
            "宠物药/农药杀虫": 18,
            "人用药品/准药品": 15,
            "医疗器械/医用防护": 48,
            "冷链/生鲜": 35,
            "烟草/尼古丁": 5,
        },
        "target_terms": (),
    },
}


CAPABILITY_LABELS: dict[str, str] = {
    "electrical_compliance": "可处理电气认证 / EMC / 能效",
    "battery_dg": "可处理锂电危险品运输与电池资料",
    "personal_care_device": "具备电动个护供应链与售后",
    "cosmetics_compliance": "具备化妆品责任主体和配方标签能力",
    "children_compliance": "可处理儿童用品测试与责任保险",
    "automotive_safety": "具备安全关键汽配质量体系",
    "chemical_dg": "可处理化学品 / 喷雾危险品",
    "food_import": "具备食品进口、标签和追溯体系",
    "supplement_compliance": "具备补充剂配方、标签和质量体系",
    "special_food": "具备婴幼儿或特殊食品资质",
    "cold_chain": "具备冷链仓储和履约",
    "medical_device": "具备医疗器械注册与责任主体",
    "human_medicine": "具备药品经营与产品批准体系",
    "pet_medicine_pesticide": "具备宠物药 / 农药注册与经营体系",
    "alcohol_license": "具备酒类进口、税务及销售许可",
    "tobacco_license": "具备烟草 / 尼古丁经营许可",
}


PROFILE_CAPABILITY_DEFAULTS: dict[str, dict[str, bool]] = {
    "当前公司画像": {
        "electrical_compliance": True,
        "battery_dg": True,
        "personal_care_device": True,
        "cosmetics_compliance": False,
        "children_compliance": False,
        "automotive_safety": False,
        "chemical_dg": False,
        "food_import": False,
        "supplement_compliance": False,
        "special_food": False,
        "cold_chain": False,
        "medical_device": False,
        "human_medicine": False,
        "pet_medicine_pesticide": False,
        "alcohol_license": False,
        "tobacco_license": False,
    },
    "普通跨境卖家": {key: False for key in CAPABILITY_LABELS},
    "成熟合规团队": {
        "electrical_compliance": True,
        "battery_dg": True,
        "personal_care_device": True,
        "cosmetics_compliance": True,
        "children_compliance": True,
        "automotive_safety": True,
        "chemical_dg": True,
        "food_import": True,
        "supplement_compliance": True,
        "special_food": False,
        "cold_chain": True,
        "medical_device": True,
        "human_medicine": False,
        "pet_medicine_pesticide": False,
        "alcohol_license": False,
        "tobacco_license": False,
    },
}


def _safe_text_series(frame: pd.DataFrame) -> pd.Series:
    columns = ["Category", "CategoryCN", "CategoryLocal", "TopKeyword", "NodePath", "RootStandard"]
    text = pd.Series("", index=frame.index, dtype="string")
    for column in columns:
        if column in frame:
            part = frame[column].astype("string").fillna("").str.casefold()
            text = text.str.cat(part, sep=" ")
    return text.str.replace(r"\s+", " ", regex=True).str.strip()


def _contains_any(text: pd.Series, patterns: Sequence[str]) -> pd.Series:
    if not patterns:
        return pd.Series(False, index=text.index, dtype=bool)
    regex = "(?:" + "|".join(patterns) + ")"
    return text.str.contains(regex, regex=True, na=False, case=False)


def _append_tag(series: pd.Series, mask: pd.Series, value: str) -> pd.Series:
    safe_mask = mask.fillna(False).astype(bool)
    current = series.astype("string").fillna("")
    return current.where(~safe_mask, current.where(current.eq(""), current + "；") + value)


def enrich_entry_rules(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy(deep=False)
    text = _safe_text_series(result)
    root = result.get("RootStandard", pd.Series("未分类", index=result.index)).astype("string").fillna("未分类")

    result["BusinessText"] = text
    result["RegulatoryFamily"] = "普通消费品"
    result["BaseEntryClass"] = "A"
    result["BaseEntryLabel"] = ENTRY_LABELS["A"]
    result["BarrierReasons"] = "无明显特殊准入；仍需核验具体产品材料、标签和平台要求"
    result["RequiredResources"] = "常规供应链、质检、标签和产品责任管理"
    result["BarrierRuleCode"] = "GENERAL"
    result["BarrierRuleConfidence"] = "中"
    result["RequiredCapability"] = ""
    severity = pd.Series(0, index=result.index, dtype="int64")
    confidence_rank = pd.Series(1, index=result.index, dtype="int64")
    confidence_values = {"低": 0, "中": 1, "高": 2}

    digital_mask = result.get("DigitalRisk", pd.Series("低", index=result.index)).astype("string").eq("高")
    if digital_mask.any():
        result.loc[digital_mask, "RegulatoryFamily"] = "数字内容/软件"
        result.loc[digital_mask, "BaseEntryClass"] = "D"
        result.loc[digital_mask, "BaseEntryLabel"] = ENTRY_LABELS["D"]
        result.loc[digital_mask, "BarrierReasons"] = "非实体商品或数字内容，不属于当前跨境实物选品范围"
        result.loc[digital_mask, "RequiredResources"] = "数字内容授权和平台发行体系"
        result.loc[digital_mask, "BarrierRuleCode"] = "DIGITAL"
        result.loc[digital_mask, "BarrierRuleConfidence"] = "高"
        severity.loc[digital_mask] = ENTRY_SEVERITY["D"]
        confidence_rank.loc[digital_mask] = confidence_values["高"]

    for rule in BARRIER_RULES:
        match = _contains_any(text, rule.terms)
        if rule.root_groups:
            match = match | root.isin(rule.root_groups)
        if rule.excludes:
            match &= ~_contains_any(text, rule.excludes)
        rule_severity = ENTRY_SEVERITY[rule.level]
        rule_confidence = confidence_values.get(rule.confidence, 1)
        eligible = match & severity.le(rule_severity)
        if not eligible.any():
            continue
        overwrite = eligible & (
            severity.lt(rule_severity)
            | (severity.eq(rule_severity) & confidence_rank.lt(rule_confidence))
        )
        same = eligible & severity.eq(rule_severity) & ~overwrite
        result.loc[overwrite, "RegulatoryFamily"] = rule.family
        result.loc[overwrite, "BaseEntryClass"] = rule.level
        result.loc[overwrite, "BaseEntryLabel"] = ENTRY_LABELS[rule.level]
        result.loc[overwrite, "BarrierReasons"] = "；".join(rule.reasons)
        result.loc[overwrite, "RequiredResources"] = "；".join(rule.resources)
        result.loc[overwrite, "BarrierRuleCode"] = rule.code
        result.loc[overwrite, "BarrierRuleConfidence"] = rule.confidence
        result.loc[overwrite, "RequiredCapability"] = rule.capability or ""
        if same.any():
            result["BarrierReasons"] = _append_tag(result["BarrierReasons"], same, "；".join(rule.reasons))
            result["RequiredResources"] = _append_tag(result["RequiredResources"], same, "；".join(rule.resources))
        severity.loc[eligible] = rule_severity
        confidence_rank.loc[overwrite] = rule_confidence
    return result


def profile_capabilities(profile: str, overrides: Mapping[str, bool] | None = None) -> dict[str, bool]:
    base = dict(PROFILE_CAPABILITY_DEFAULTS.get(profile, PROFILE_CAPABILITY_DEFAULTS["普通跨境卖家"]))
    for key, value in (overrides or {}).items():
        if key in CAPABILITY_LABELS:
            base[key] = bool(value)
    return base


def _promote_entry_class(base: pd.Series, capability: pd.Series) -> pd.Series:
    original = base.astype("string").fillna("D")
    result = original.copy()
    result = result.mask(capability & original.eq("D"), "C")
    result = result.mask(capability & original.eq("C"), "B")
    return result


def _company_fit(frame: pd.DataFrame, profile: str, capabilities: Mapping[str, bool]) -> pd.Series:
    profile_data = PROFILE_DEFAULTS.get(profile, PROFILE_DEFAULTS["普通跨境卖家"])
    family_fit = profile_data.get("family_fit", {})
    base_fit = float(profile_data.get("base_fit", 60))
    family = frame["RegulatoryFamily"].astype("string").fillna("普通消费品")
    fit = family.map(family_fit).fillna(base_fit).astype("float64")
    target_terms = profile_data.get("target_terms", ())
    if target_terms:
        fit += np.where(_contains_any(frame["BusinessText"].astype("string"), target_terms), 8.0, 0.0)
    required = frame["RequiredCapability"].astype("string").fillna("")
    cap_match = pd.Series(False, index=frame.index, dtype=bool)
    for key, enabled in capabilities.items():
        if enabled:
            cap_match |= required.eq(key)
    fit += np.where(cap_match, 12.0, 0.0)
    fit -= np.where(required.ne("") & ~cap_match, 8.0, 0.0)
    return fit.clip(0, 100).round(1)


def apply_business_model(
    frame: pd.DataFrame,
    *,
    profile: str = "当前公司画像",
    capability_overrides: Mapping[str, bool] | None = None,
    fx_rates: Mapping[str, float] | None = None,
    fx_reference_date: str | None = None,
    fx_source: str | None = None,
) -> pd.DataFrame:
    result = frame if "BaseEntryClass" in frame.columns else enrich_entry_rules(frame)
    result = result.copy()
    capabilities = profile_capabilities(profile, capability_overrides)
    required = result["RequiredCapability"].astype("string").fillna("")
    capability_match = pd.Series(False, index=result.index, dtype=bool)
    for key, enabled in capabilities.items():
        if enabled:
            capability_match |= required.eq(key)

    result["SellerProfile"] = profile
    result["CapabilityMatched"] = capability_match
    result["EntryClass"] = _promote_entry_class(result["BaseEntryClass"], capability_match)
    result["EntryLabel"] = result["EntryClass"].map(ENTRY_LABELS).fillna(ENTRY_LABELS["D"])
    result["EntryMultiplier"] = result["EntryClass"].map(ENTRY_MULTIPLIERS).fillna(0.0).astype("float64")
    result.loc[capability_match & result["EntryClass"].eq("B"), "EntryMultiplier"] = 0.85
    result.loc[capability_match & result["EntryClass"].eq("C"), "EntryMultiplier"] = 0.40

    result["CompanyFitScore"] = _company_fit(result, profile, capabilities)
    base_friendliness = result["EntryClass"].map({"A": 92.0, "B": 66.0, "C": 28.0, "D": 0.0}).astype("float64")
    result["CrossBorderFriendliness"] = (
        base_friendliness + np.where(capability_match, 10.0, 0.0)
    ).clip(0, 100).round(1)

    opportunity = pd.to_numeric(result.get("OpportunityScore"), errors="coerce").fillna(0).clip(0, 100)
    fit_multiplier = pd.to_numeric(result["CompanyFitScore"], errors="coerce").fillna(0).clip(0, 100) / 100
    result["FinalPriorityScore"] = (opportunity * result["EntryMultiplier"] * fit_multiplier).clip(0, 100).round(1)
    result["DefaultBusinessEligible"] = (
        result.get("EligiblePhysical", pd.Series(False, index=result.index)).fillna(False).astype(bool)
        & result["EntryClass"].isin(["A", "B"])
        & result["CompanyFitScore"].ge(35)
    ).astype(bool)

    conditions = [
        result["EntryClass"].eq("D"),
        result["EntryClass"].eq("C"),
        result["FinalPriorityScore"].ge(70),
        result["FinalPriorityScore"].ge(55),
        result["FinalPriorityScore"].ge(35),
    ]
    result["BusinessDecision"] = np.select(
        conditions,
        ["默认排除", "受监管研究", "优先研究", "进入验证", "有条件推进"],
        default="暂缓",
    )
    result["FinalPriorityLevel"] = pd.cut(
        result["FinalPriorityScore"],
        bins=[-np.inf, 10, 35, 55, 70, np.inf],
        labels=["排除/低适配", "观察", "B级", "A级", "S级"],
        right=False,
    ).astype("string")
    return apply_cny_conversion(
        result,
        fx_rates,
        reference_date=fx_reference_date,
        source_name=fx_source,
    )
