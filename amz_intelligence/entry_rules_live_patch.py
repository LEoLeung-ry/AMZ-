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

    if "ADULT_SEXUAL_PRODUCT" not in existing:
        additions.append(
            rules.BarrierRule(
                code="ADULT_SEXUAL_PRODUCT",
                family="成人性用品/年龄限制品",
                level="D",
                terms=(
                    r"sex toys?", r"adult toys?", r"male masturbators?", r"female masturbators?", r"masturbation sleeves?",
                    r"vibrators?", r"dildos?", r"penis sleeves?", r"成人性用品", r"男士自慰用品", r"女士自慰用品",
                    r"自慰器", r"飞机杯", r"アダルト用ホール", r"オナホール", r"バイブレーター",
                    r"sexspielzeug", r"masturbatoren?", r"masturbationshilfen?",
                ),
                excludes=(r"condoms?", r"lubricants?", r"book", r"education", r"storage case", r"cleaner"),
                reasons=("年龄限制及平台成人品政策", "广告、支付和跨境销售限制", "卫生、材料与产品责任风险"),
                resources=("目标国年龄限制和平台政策确认", "合规材料、标签及隐私履约体系"),
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
                    r"whey isolate", r"whey concentrate", r"multi[- ]?component proteins?", r"protein blends?",
                    r"creatine", r"\bkreatin\b", r"乳清蛋白", r"多组分蛋白质", r"复合蛋白", r"肌酸",
                    r"孕妇维生素", r"产前维生素", r"复合维生素", r"ホエイプロテイン", r"マルチビタミン",
                    r"妊婦用ビタミン", r"クレアチン", r"molkenproteine?", r"molkenproteinpulver",
                    r"mehrkomponenten proteine", r"multivitaminpräparate?", r"pränatale vitamine",
                ),
                excludes=(r"shaker", r"bottle", r"storage", r"container", r"book", r"guide"),
                reasons=("入口型营养补充产品", "成分、标签和功效宣称要求", "生产质量、保质期和批次追溯"),
                resources=("目标国补充剂分类确认", "配方、检测和标签资料", "进口、追溯和产品责任体系"),
                capability="supplement_compliance",
            )
        )

    if "FOOD_SNACK_SHAKE" not in existing:
        additions.append(
            rules.BarrierRule(
                code="FOOD_SNACK_SHAKE",
                family="食品/零食/饮品",
                level="C",
                terms=(
                    r"chips?\s*&\s*crisps?", r"potato chips?", r"crisps?", r"snack foods?", r"soft snacks?",
                    r"pet snacks?", r"cat soft snacks?", r"dog soft snacks?", r"\bshakes\b", r"milkshakes?",
                    r"薯片", r"零食", r"猫用.*零食", r"狗用.*零食", r"宠物零食", r"奶昔",
                    r"ソフトスナック", r"猫用.*スナック", r"犬用.*スナック", r"ポテトチップス", r"スナック菓子",
                    r"shakes", r"kartoffelchips", r"knabberartikel",
                ),
                excludes=(
                    r"shaker", r"mixer", r"blender", r"machine", r"maker", r"bowl", r"container", r"storage",
                    r"toy", r"book", r"シェイカー", r"ミキサー", r"容器", r"maschine", r"gerät",
                ),
                reasons=("入口食品、原料与标签要求", "过敏原、保质期和批次追溯", "进口、仓储和召回责任"),
                resources=("目标国食品/宠物食品分类确认", "合格工厂、成分和检测资料", "进口、标签、追溯及召回体系"),
                capability="food_import",
            )
        )

    if "PET_FEED_EXTENDED" not in existing:
        additions.append(
            rules.BarrierRule(
                code="PET_FEED_EXTENDED",
                family="宠物食品/饲料",
                level="C",
                terms=(
                    r"grain feed", r"seed feed", r"bird feed", r"small animal feed", r"soft cat snacks?", r"soft dog snacks?",
                    r"谷物饲料", r"种子饲料", r"鸟粮", r"小动物饲料", r"猫用软质零食", r"狗用软质零食",
                    r"körnerfutter", r"vogelfutter", r"kleintierfutter", r"猫用ソフトスナック", r"犬用ソフトスナック",
                ),
                excludes=(r"feeder", r"bowl", r"container", r"storage", r"dispenser", r"toy", r"食器", r"容器", r"futterautomat"),
                reasons=("宠物食品/饲料进口和标签要求", "动物源或植物源原料及检疫风险", "保质期、批次和召回责任"),
                resources=("目标国宠物食品/饲料分类确认", "成分、检测及原产地资料", "进口、追溯和召回体系"),
                capability="food_import",
            )
        )

    if "EYE_SKIN_REMEDY" not in existing:
        additions.append(
            rules.BarrierRule(
                code="EYE_SKIN_REMEDY",
                family="眼用/外用治疗产品",
                level="C",
                terms=(
                    r"eye drops?", r"ophthalmic drops?", r"lubricating eye drops?", r"moisturizing eye drops?",
                    r"itch remedies?", r"anti[- ]?itch remedies?", r"itch relief treatments?", r"眼药水", r"滴眼液",
                    r"保湿眼药水", r"止痒药", r"止痒治疗", r"目薬", r"点眼薬", r"かゆみ止め",
                    r"augentropfen", r"juckreizmittel", r"juckreizlinderung",
                ),
                excludes=(r"bottle", r"case", r"holder", r"storage", r"eyewash cup", r"容器", r"ケース"),
                reasons=("眼用或治疗类产品可能属于药品、医疗器械或准药品", "无菌、成分和功效宣称要求", "高产品责任和不良反应风险"),
                resources=("目标国产品分类与批准路径确认", "无菌/配方、检测和标签资料", "持证主体、追溯和不良事件处理体系"),
                capability="human_medicine",
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

    if "GAMING_HARDWARE" not in existing:
        additions.append(
            rules.BarrierRule(
                code="GAMING_HARDWARE",
                family="游戏主机/电子控制器",
                level="B",
                terms=(
                    r"game consoles?", r"gaming consoles?", r"video game controllers?", r"gaming controllers?",
                    r"handheld consoles?", r"控制台", r"游戏主机", r"游戏控制器", r"手柄",
                    r"ゲーム機", r"ゲームコントローラー", r"spielkonsolen?", r"gamecontroller",
                ),
                excludes=(r"console table", r"car console", r"center console", r"furniture", r"机柜", r"家具", r"autokonsole"),
                reasons=("电气、无线电和电池合规", "品牌兼容、授权和知识产权风险", "售后、固件及产品责任"),
                resources=("目标国电气/无线电测试", "兼容性和知识产权核验", "售后、固件和召回能力"),
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
