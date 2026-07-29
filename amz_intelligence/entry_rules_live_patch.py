from __future__ import annotations

from . import business_rules as rules


def install_live_rule_refinements() -> None:
    existing = {rule.code for rule in rules.BARRIER_RULES}
    additions: list[rules.BarrierRule] = []

    if "VOUCHER_STORED_VALUE" not in existing:
        additions.append(
            rules.BarrierRule(
                code="VOUCHER_STORED_VALUE",
                family="代金券/储值卡/非实体权益",
                level="D",
                terms=(
                    r"event vouchers?", r"travel vouchers?", r"experience vouchers?", r"digital vouchers?",
                    r"stored[- ]?value cards?", r"store currency cards?", r"currency cards?", r"prepaid cards?",
                    r"活动券", r"旅行券", r"体验券", r"电子券", r"存储货币卡", r"储值卡", r"代金券",
                    r"eventgutscheine", r"reisegutscheine", r"erlebnisgutscheine", r"wertkarten?", r"prepaidkarten?",
                    r"イベント券", r"旅行券", r"電子クーポン", r"プリペイドカード",
                ),
                excludes=(
                    r"holder", r"case", r"wallet", r"envelope", r"display", r"organizer", r"book", r"guide",
                    r"カードケース", r"財布", r"封筒", r"halter", r"etui", r"umschlag",
                ),
                reasons=("非实体权益、储值或兑付类目", "发行授权、支付及消费者保护要求", "不属于普通实物跨境选品"),
                resources=("平台/品牌发行授权", "支付、税务、兑付和消费者保护合规"),
            )
        )

    if "VITAMIN_WHEY_SUPPLEMENT" not in existing:
        additions.append(
            rules.BarrierRule(
                code="VITAMIN_WHEY_SUPPLEMENT",
                family="维生素/蛋白及营养补充剂",
                level="C",
                terms=(
                    r"prenatal vitamins?", r"prenatal multivitamins?", r"multivitamins?", r"whey proteins?",
                    r"whey isolate", r"whey concentrate", r"乳清蛋白", r"孕妇维生素", r"产前维生素", r"复合维生素",
                    r"ホエイプロテイン", r"マルチビタミン", r"妊婦用ビタミン",
                    r"molkenproteine?", r"molkenproteinpulver", r"multivitaminpräparate?", r"pränatale vitamine",
                ),
                excludes=(r"shaker", r"bottle", r"storage", r"container", r"book", r"guide"),
                reasons=("入口型营养补充产品", "成分、标签和功效宣称要求", "生产质量、保质期和批次追溯"),
                resources=("目标国补充剂分类确认", "配方、检测和标签资料", "进口、追溯和产品责任体系"),
                capability="supplement_compliance",
            )
        )

    if "MAJOR_ELECTRICAL_APPLIANCE" not in existing:
        additions.append(
            rules.BarrierRule(
                code="MAJOR_ELECTRICAL_APPLIANCE",
                family="电气家电/机电设备",
                level="B",
                terms=(
                    r"upright vacuums?", r"cylinder vacuums?", r"vacuum cleaners?", r"carpet cleaning machines?",
                    r"dishwashers?", r"robotic lawn mowers?", r"robot lawn mowers?", r"observation monitors?",
                    r"baby monitors?", r"display monitors?", r"立式吸尘器", r"圆筒吸尘器", r"吸尘器", r"地毯清洗机",
                    r"洗碗机", r"机器人割草机", r"观察监视器", r"监视器", r"掃除機", r"食器洗い機",
                    r"ロボット芝刈り機", r"モニター", r"staubsauger", r"teppichreiniger", r"geschirrspüler",
                    r"mähroboter", r"beobachtungsmonitore", r"babyphone",
                ),
                excludes=(
                    r"bags?", r"filters?", r"hoses?", r"brushes?", r"parts?", r"accessories?", r"stands?", r"mounts?",
                    r"吸尘器袋", r"滤网", r"软管", r"配件", r"スタンド", r"フィルター", r"beutel", r"filter", r"halterung",
                ),
                reasons=("电气安全、EMC、能效或无线电要求", "体积、售后和召回责任", "目的国插头、电压及安装适配"),
                resources=("目的国测试与认证", "稳定整机和关键零部件供应链", "售后、产品责任保险和召回预案"),
                capability="electrical_compliance",
            )
        )

    if "ORAL_CARE_FORMULATION" not in existing:
        additions.append(
            rules.BarrierRule(
                code="ORAL_CARE_FORMULATION",
                family="口腔护理配方/接触品",
                level="B",
                terms=(
                    r"mouthwash", r"oral rinses?", r"oral care supplies?", r"toothpaste", r"denture cleansers?",
                    r"漱口水", r"口腔护理用品", r"牙膏", r"义齿清洁剂", r"マウスウォッシュ", r"オーラルケア用品",
                    r"歯磨き粉", r"mundspülung", r"mundwasser", r"zahnpasta", r"mundpflegeprodukte",
                ),
                excludes=(r"holder", r"case", r"cup", r"travel bag", r"收纳", r"ケース", r"halter", r"becher"),
                reasons=("口腔接触配方、成分和标签要求", "功效宣称及误食风险", "液体运输、卫生和产品责任"),
                resources=("配方与成分安全资料", "目标国标签和宣称审核", "合规包装、检测和产品责任管理"),
                capability="cosmetics_compliance",
            )
        )

    if "MAGNETIC_WELLNESS_ACCESSORY" not in existing:
        additions.append(
            rules.BarrierRule(
                code="MAGNETIC_WELLNESS_ACCESSORY",
                family="磁疗/健康功效配件",
                level="B",
                terms=(
                    r"magnetic therapy", r"titanium germanium accessories", r"magnetic titanium germanium",
                    r"磁性/钛/锗配件", r"磁疗配件", r"磁気・チタン・ゲルマニウムアクセサリー",
                    r"磁気治療", r"magnettherapie", r"germanium accessoires",
                ),
                reasons=("健康功效宣称边界", "皮肤接触、材料与过敏风险", "部分用途可能涉及医疗器械分类"),
                resources=("目标国产品分类和宣称确认", "材料及皮肤接触测试", "说明书、证据和产品责任保险"),
                capability="medical_device",
            )
        )

    if additions:
        rules.BARRIER_RULES = rules.BARRIER_RULES + tuple(additions)
