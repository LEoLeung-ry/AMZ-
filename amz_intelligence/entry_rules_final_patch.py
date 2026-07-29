from __future__ import annotations

from . import business_rules as rules


def install_final_entry_refinements() -> None:
    existing = {rule.code for rule in rules.BARRIER_RULES}
    additions: list[rules.BarrierRule] = []

    if "CONDOM_MEDICAL_DEVICE" not in existing:
        additions.append(
            rules.BarrierRule(
                code="CONDOM_MEDICAL_DEVICE",
                family="避孕/医疗接触产品",
                level="C",
                terms=(
                    r"\bcondoms?\b", r"male condoms?", r"female condoms?", r"安全套", r"避孕套",
                    r"コンドーム", r"kondome?", r"präservative?",
                ),
                excludes=(r"case", r"holder", r"storage", r"dispenser", r"ケース", r"halter"),
                reasons=("避孕及医疗接触产品的注册/分类要求", "材料、破损率和性能标准", "高产品责任和标签要求"),
                resources=("目标国医疗器械或相关产品分类确认", "性能、材料和稳定性测试", "责任主体、追溯和产品责任保险"),
                capability="medical_device",
            )
        )

    if "DISINFECTANT_BIOCIDE" not in existing:
        additions.append(
            rules.BarrierRule(
                code="DISINFECTANT_BIOCIDE",
                family="消毒/杀菌/生物杀灭产品",
                level="C",
                terms=(
                    r"disinfectants?", r"sanitizers?", r"surface disinfectants?", r"antibacterial disinfectants?",
                    r"消毒液", r"消毒剂", r"杀菌剂", r"除菌剂", r"除菌剤", r"消毒剤", r"殺菌剤",
                    r"desinfektionsmittel", r"flächendesinfektion", r"händedesinfektion",
                ),
                excludes=(r"dispenser", r"bottle", r"holder", r"wipe container", r"容器", r"ディスペンサー", r"spender"),
                reasons=("消毒/杀菌功效可能触及生物杀灭剂、农药、药品或准药品规则", "有效成分、浓度和标签要求", "化学品运输及产品责任"),
                resources=("成分和用途分类确认", "注册/批准或豁免路径", "SDS、功效测试、标签和合规物流"),
                capability="chemical_dg",
            )
        )

    if "SMOKING_CESSATION" not in existing:
        additions.append(
            rules.BarrierRule(
                code="SMOKING_CESSATION",
                family="戒烟/尼古丁或治疗产品",
                level="D",
                terms=(
                    r"smoking cessation", r"stop smoking aids?", r"nicotine replacement", r"nicotine gums?", r"nicotine patches?",
                    r"戒烟", r"戒煙", r"尼古丁替代", r"禁煙補助", r"禁煙用品", r"rauchentwöhnung",
                    r"nikotinersatz", r"nikotinpflaster", r"nikotinkaugummi",
                ),
                excludes=(r"book", r"guide", r"poster", r"sign", r"戒烟书", r"禁煙本", r"ratgeber"),
                reasons=("可能涉及尼古丁、药品或治疗宣称", "年龄限制、平台和广告政策", "当地批准、标签和药物警戒责任"),
                resources=("目标国产品分类和批准确认", "持证经营/责任主体", "标签、追溯和不良事件处理体系"),
                capability="human_medicine",
            )
        )

    if "DIGESTIVE_AIDS" not in existing:
        additions.append(
            rules.BarrierRule(
                code="DIGESTIVE_AIDS",
                family="消化/胃肠支持产品",
                level="C",
                terms=(
                    r"digestive aids?", r"digestion aids?", r"digestive support", r"indigestion remedies?",
                    r"助消化", r"消化辅助", r"胃肠支持", r"消化サポート", r"胃腸薬",
                    r"verdauungshilfen?", r"verdauungsunterstützung", r"magen[- ]?darm mittel",
                ),
                excludes=(r"book", r"guide", r"tea infuser", r"storage", r"本", r"ratgeber"),
                reasons=("入口型补充剂、食品或药品分类可能性", "成分、剂量和功效宣称要求", "生产质量、标签和批次追溯"),
                resources=("目标国产品分类确认", "配方、检测和标签资料", "进口、追溯和产品责任体系"),
                capability="supplement_compliance",
            )
        )

    if "HEAT_PUMP_DRYER" not in existing:
        additions.append(
            rules.BarrierRule(
                code="HEAT_PUMP_DRYER",
                family="大型电气家电",
                level="B",
                terms=(
                    r"heat pump dryers?", r"tumble dryers?", r"clothes dryers?", r"热泵烘干机", r"热泵干衣机",
                    r"ヒートポンプ乾燥機", r"衣類乾燥機", r"wärmepumpentrockner", r"wäschetrockner",
                ),
                excludes=(r"parts?", r"filters?", r"hoses?", r"accessories?", r"配件", r"フィルター", r"ersatzteile"),
                reasons=("大型家电电气安全、EMC和能效要求", "安装、电压和售后责任", "体积、退货和召回风险"),
                resources=("目的国认证和能效资料", "安装与售后服务能力", "产品责任、备件和召回预案"),
                capability="electrical_compliance",
            )
        )

    if "FITNESS_BIKE_EQUIPMENT" not in existing:
        additions.append(
            rules.BarrierRule(
                code="FITNESS_BIKE_EQUIPMENT",
                family="大型健身器材",
                level="B",
                terms=(
                    r"exercise bikes?", r"fitness bikes?", r"stationary bikes?", r"spin bikes?", r"健身自行车",
                    r"动感单车", r"室内自行车", r"フィットネスバイク", r"エアロバイク",
                    r"fitnessbikes?", r"heimtrainer", r"spinning bikes?",
                ),
                excludes=(r"covers?", r"mats?", r"parts?", r"pedals?", r"seats?", r"accessories?", r"配件", r"マット", r"ersatzteile"),
                reasons=("承重、结构稳定和人身安全责任", "大件物流、安装和退货成本", "电气/无线连接功能可能需要额外合规"),
                resources=("结构和耐久测试", "大件物流、安装和售后方案", "产品责任保险和备件体系"),
            )
        )

    if "GENERIC_CONTROLLER_HARDWARE" not in existing:
        additions.append(
            rules.BarrierRule(
                code="GENERIC_CONTROLLER_HARDWARE",
                family="电子控制器/兼容硬件",
                level="B",
                terms=(
                    r"\bcontrollers\b", r"\bcontroller\b", r"\bconsoles\b", r"\bconsole\b",
                    r"控制器", r"控制台", r"游戏主机", r"コントローラー", r"ゲーム機",
                    r"steuergeräte?", r"steuerungen?", r"spielkonsolen?",
                ),
                excludes=(
                    r"financial controller", r"controller job", r"temperature controller book", r"console table", r"car console",
                    r"management console", r"管理人员", r"财务", r"本", r"家具", r"autokonsole",
                ),
                reasons=("电气、无线电或兼容性要求", "品牌授权和知识产权风险", "固件、售后和产品责任"),
                resources=("用途和产品类型确认", "电气/无线电及兼容性测试", "知识产权、售后和召回能力"),
                capability="electrical_compliance",
            )
        )

    if additions:
        rules.BARRIER_RULES = rules.BARRIER_RULES + tuple(additions)
