from __future__ import annotations

from . import business_rules as rules


def install_supplemental_entry_rules() -> None:
    existing = {rule.code for rule in rules.BARRIER_RULES}
    additions: list[rules.BarrierRule] = []

    if "HAIR_GROWTH_TREATMENT" not in existing:
        additions.append(
            rules.BarrierRule(
                code="HAIR_GROWTH_TREATMENT",
                family="强功效化妆品/外用治疗",
                level="C",
                terms=(
                    r"生发", r"生髮", r"育发", r"育髮", r"防脱", r"防脫", r"脱发治疗", r"脱髮治療",
                    r"hair growth", r"hair regrowth", r"hair tonic", r"育毛", r"発毛", r"養毛",
                    r"haarwuchs", r"haarwuchsmittel",
                ),
                reasons=("强功效生发/防脱宣称可能触及药品或准药品", "活性成分、功效证据与标签要求", "皮肤接触和不良反应责任"),
                resources=("目标国法规分类确认", "配方安全及功效资料", "当地责任主体和产品责任体系"),
                capability="cosmetics_compliance",
            )
        )

    if "CPAP_RESPIRATORY_MEDICAL" not in existing:
        additions.append(
            rules.BarrierRule(
                code="CPAP_RESPIRATORY_MEDICAL",
                family="医疗器械/呼吸治疗配件",
                level="C",
                terms=(
                    r"\bcpap\b", r"\bbipap\b", r"sleep apnea", r"positive airway pressure",
                    r"oxygen concentrator", r"respiratory therapy", r"breathing machine",
                    r"睡眠呼吸暂停", r"呼吸机配件", r"呼吸器治疗", r"人工呼吸器", r"酸素濃縮器",
                    r"schlafapnoe", r"atemtherapie", r"sauerstoffkonzentrator",
                ),
                reasons=("呼吸治疗器械或其配件可能属于医疗器械", "兼容性、卫生和患者安全责任", "平台及目的国注册要求"),
                resources=("医疗器械分类确认", "制造商授权/兼容性资料", "责任主体、质量体系和产品责任保险"),
                capability="medical_device",
            )
        )

    if "RESPIRATORY_PPE" not in existing:
        additions.append(
            rules.BarrierRule(
                code="RESPIRATORY_PPE",
                family="呼吸防护/PPE",
                level="C",
                terms=(
                    r"reusable respirator", r"full face respirator", r"half mask respirator", r"respirator mask",
                    r"respiratory protective", r"powered air purifying respirator", r"\bpapr\b",
                    r"可重复使用的呼吸器", r"呼吸防护器", r"防毒面具", r"全面罩呼吸器", r"半面罩呼吸器",
                    r"再使用可能な防毒マスク", r"防毒マスク", r"呼吸用保護具",
                    r"atemschutzmaske", r"atemschutzgerät", r"halbmaske", r"vollmaske",
                ),
                reasons=("PPE/呼吸防护认证和性能标准", "错误防护宣称可能造成人身伤害", "平台、进口及产品责任风险"),
                resources=("目的国PPE认证/批准", "性能检测和技术文档", "责任主体与产品责任保险"),
                capability="medical_device",
            )
        )

    if "NUTRITION_BARS_COLLAGEN" not in existing:
        additions.append(
            rules.BarrierRule(
                code="NUTRITION_BARS_COLLAGEN",
                family="食品/营养补充剂",
                level="C",
                terms=(
                    r"protein bar", r"protein bars", r"energy bar", r"energy bars", r"nutrition bar",
                    r"meal replacement bar", r"sports nutrition bar", r"collagen", r"kollagen",
                    r"蛋白棒", r"能量棒", r"营养棒", r"代餐棒", r"胶原蛋白", r"膠原蛋白",
                    r"プロテインバー", r"栄養バー", r"コラーゲン", r"kollagenpräparat",
                ),
                excludes=(r"collagen mask", r"collagen cream", r"collagen serum", r"コラーゲンマスク", r"胶原面膜", r"胶原面霜"),
                reasons=("入口食品/补充剂合规", "配方、过敏原、营养与功效标签要求", "保质期和批次追溯"),
                resources=("食品/补充剂进口主体", "合格工厂与检测资料", "当地标签审核、批次和召回体系"),
                capability="supplement_compliance",
            )
        )

    if "SUPPLEMENT_EXTENDED" not in existing:
        additions.append(
            rules.BarrierRule(
                code="SUPPLEMENT_EXTENDED",
                family="膳食补充剂/营养及情绪支持",
                level="C",
                terms=(
                    r"electrolyte replacements?", r"electrolyte supplements?", r"oral rehydration",
                    r"\bomega[- ]?3\b", r"fish oil supplements?", r"lactobacillus", r"probiotics?", r"prebiotics?",
                    r"diet shakes?", r"weight loss shakes?", r"meal replacement shakes?",
                    r"relaxants?\s*&?\s*anxiety relief", r"anxiety relief supplements?", r"calming supplements?",
                    r"电解质替代", r"电解质补充", r"欧米茄3", r"鱼油补充剂", r"乳酸菌", r"益生菌", r"益生元",
                    r"减肥奶昔", r"代餐奶昔", r"放松剂", r"焦虑缓解", r"情绪舒缓",
                    r"電解質補給", r"オメガ[- ]?3", r"乳酸菌", r"プロバイオティクス", r"ダイエットシェイク",
                    r"beruhigungsmittel", r"angstlinderung", r"elektrolytersatz", r"laktobazillus", r"probiotika",
                    r"diät[- ]?shake", r"mahlzeitenersatz[- ]?shake",
                ),
                excludes=(
                    r"bottle", r"shaker", r"container", r"storage", r"holder", r"mixer", r"blender",
                    r"electrolyte analyzer", r"test strip", r"book", r"guide",
                ),
                reasons=("入口型营养或情绪支持产品", "成分、标签和功效宣称要求", "生产质量、保质期与批次追溯"),
                resources=("目标国食品/补充剂分类确认", "配方、检测和标签资料", "当地进口、追溯和产品责任体系"),
                capability="supplement_compliance",
            )
        )

    if "PET_FOOD_FEED" not in existing:
        additions.append(
            rules.BarrierRule(
                code="PET_FOOD_FEED",
                family="宠物食品/饲料",
                level="C",
                terms=(
                    r"cat food", r"dog food", r"pet food", r"animal feed", r"dry cat food", r"dry dog food",
                    r"wet cat food", r"wet dog food", r"cat treats?", r"dog treats?",
                    r"猫粮", r"狗粮", r"宠物食品", r"宠物饲料", r"猫零食", r"狗零食",
                    r"キャットフード", r"ドッグフード", r"ペットフード", r"猫用フード", r"犬用フード",
                    r"katzenfutter", r"hundefutter", r"tierfutter", r"trockenfutter", r"nassfutter",
                ),
                excludes=(
                    r"storage", r"container", r"bowl", r"mat", r"scoop", r"feeder", r"dispenser",
                    r"保存容器", r"食器", r"ボウル", r"futterautomat", r"futternapf",
                ),
                reasons=("宠物食品/饲料进口与标签要求", "原料、动物源成分和检疫风险", "保质期、批次与召回责任"),
                resources=("目标国宠物食品/饲料分类确认", "合格工厂、成分和检测资料", "进口、追溯及召回体系"),
                capability="food_import",
            )
        )

    if "GIFT_CARD_NONPHYSICAL" not in existing:
        additions.append(
            rules.BarrierRule(
                code="GIFT_CARD_NONPHYSICAL",
                family="储值卡/非实体发行",
                level="D",
                terms=(
                    r"gift cards?", r"gift certificates?", r"digital gift cards?", r"e[- ]?gift cards?",
                    r"prepaid store cards?", r"store credit", r"礼品卡", r"礼券", r"储值卡",
                    r"ギフトカード", r"商品券", r"geschenkkarte", r"gutscheinkarte", r"gutschein",
                ),
                excludes=(
                    r"holder", r"box", r"envelope", r"display", r"rack", r"case", r"wallet", r"organizer",
                    r"カードケース", r"封筒", r"収納", r"halter", r"umschlag",
                ),
                reasons=("非实体或储值发行类目", "平台发行授权和金融/消费者保护要求", "不属于普通实物跨境选品"),
                resources=("平台或品牌发行授权", "支付、税务与消费者保护合规"),
            )
        )

    if "EMS_MUSCLE_STIMULATION" not in existing:
        additions.append(
            rules.BarrierRule(
                code="EMS_MUSCLE_STIMULATION",
                family="电气健身/功效设备",
                level="B",
                terms=(
                    r"\bems\b", r"electrical muscle stimulation", r"muscle stimulators?", r"ab belts?", r"abdominal belts?",
                    r"腹肌贴", r"腹肌带", r"肌肉刺激器", r"电脉冲健身", r"腹筋ベルト", r"EMS・腹筋ベルト",
                    r"ems trainer", r"muskelstimulator", r"bauchmuskelgürtel",
                ),
                excludes=(r"replacement pads?", r"electrode pads?", r"替换贴片", r"交換パッド", r"ersatzpads"),
                reasons=("电气和皮肤接触安全", "健身/治疗功效宣称边界", "电池、EMC和产品责任"),
                resources=("目标国产品分类确认", "电气、EMC和皮肤接触测试", "功效证据、说明书和责任保险"),
                capability="electrical_compliance",
            )
        )

    if "FERTILIZER_AGRICULTURAL_INPUT" not in existing:
        additions.append(
            rules.BarrierRule(
                code="FERTILIZER_AGRICULTURAL_INPUT",
                family="肥料/农业投入品",
                level="B",
                terms=(
                    r"fertili[sz]ers?", r"lawn fertili[sz]ers?", r"plant food", r"soil nutrients?",
                    r"草坪肥", r"肥料", r"植物营养剂", r"园艺肥", r"園芸肥料",
                    r"rasendünger", r"pflanzendünger", r"dünger", r"bodennährstoff",
                ),
                excludes=(r"spreader", r"applicator", r"storage", r"container", r"撒布机", r"施肥器", r"streuwagen"),
                reasons=("成分、用途和标签可能受农业/化学品规则约束", "运输、储存和环境责任", "不同国家配方准入差异"),
                resources=("目标国肥料/化学品分类确认", "成分、SDS和标签资料", "合规包装、运输与产品责任管理"),
                capability="chemical_dg",
            )
        )

    if "PEST_CONTROL_REPELLENT" not in existing:
        additions.append(
            rules.BarrierRule(
                code="PEST_CONTROL_REPELLENT",
                family="害虫防治/驱避产品",
                level="B",
                terms=(
                    r"pest control", r"moth repellents?", r"moth killers?", r"moth traps?", r"insect repellents?", r"insect killers?",
                    r"防蛾", r"飞蛾防治", r"灭蛾", r"害虫防治", r"驱虫剂", r"防虫剂",
                    r"防虫", r"蛾駆除", r"害虫駆除", r"mottenmittel", r"mottenfalle", r"schädlingsabwehr",
                ),
                excludes=(r"book", r"toy", r"costume", r"poster", r"sticker", r"jewelry", r"図鑑", r"玩具"),
                reasons=("驱避/杀虫功效可能触及农药或生物杀灭剂规则", "有效成分和标签要求", "危险品运输及产品责任"),
                resources=("成分和作用机理确认", "目标国注册/豁免判断", "SDS、标签和合规物流"),
                capability="pet_medicine_pesticide",
            )
        )

    if "SAFETY_DETECTOR" not in existing:
        additions.append(
            rules.BarrierRule(
                code="SAFETY_DETECTOR",
                family="安全报警/探测器",
                level="B",
                terms=(
                    r"smoke detector", r"smoke alarm", r"carbon monoxide detector", r"co alarm", r"gas detector",
                    r"烟雾探测器", r"烟雾报警器", r"一氧化碳报警器", r"燃气报警器",
                    r"煙感知器", r"火災警報器", r"一酸化炭素警報器",
                    r"rauchmelder", r"brandmelder", r"kohlenmonoxidmelder", r"gasmelder",
                ),
                reasons=("生命安全相关性能和认证要求", "安装、误报/漏报及召回责任", "电池和无线电合规可能存在"),
                resources=("目的国安全认证和性能测试", "安装说明及质量追溯", "产品责任保险和召回预案"),
                capability="electrical_compliance",
            )
        )

    if "ELECTRICAL_APPLIANCE_SECURITY" not in existing:
        additions.append(
            rules.BarrierRule(
                code="ELECTRICAL_APPLIANCE_SECURITY",
                family="电气家电/安防电子",
                level="B",
                terms=(
                    r"tower fans?", r"pedestal fans?", r"table fans?", r"desk fans?", r"industrial fans?",
                    r"handheld fans?", r"portable electric fans?", r"electric fans?",
                    r"塔扇", r"落地扇", r"台扇", r"工厂风扇", r"工业风扇", r"手持风扇", r"电风扇",
                    r"扇風機", r"工場扇", r"ハンディファン", r"卓上扇風機",
                    r"turmventilator", r"standventilator", r"tischventilator", r"ventilator",
                    r"coffee machines?", r"coffee makers?", r"espresso machines?", r"bean-to-cup",
                    r"全自动咖啡机", r"全自動咖啡機", r"咖啡机", r"咖啡機", r"意式咖啡机",
                    r"コーヒーメーカー", r"全自動コーヒーマシン", r"エスプレッソマシン",
                    r"kaffeevollautomat", r"kaffeemaschine", r"espressomaschine",
                    r"surveillance cameras?", r"security cameras?", r"cctv", r"ip cameras?",
                    r"监控摄像头", r"監控攝像頭", r"安防摄像头", r"防犯カメラ", r"監視カメラ",
                    r"überwachungskamera", r"sicherheitskamera",
                ),
                excludes=(r"fan cover", r"fan guard", r"fan blade", r"camera case", r"camera mount", r"camera bag", r"coffee filter paper"),
                reasons=("电气安全、EMC或无线电合规", "插头、电压、能效和电池要求", "安防隐私、产品责任及召回风险"),
                resources=("目的国电气/无线电测试与认证", "稳定整机和关键零部件供应链", "产品责任保险、售后和召回预案"),
                capability="electrical_compliance",
            )
        )

    if "WEAPONS_EXPLOSIVES" not in existing:
        additions.append(
            rules.BarrierRule(
                code="WEAPONS_EXPLOSIVES",
                family="武器/爆炸物/高限制品",
                level="D",
                terms=(
                    r"firearm", r"ammunition", r"gun parts", r"explosive", r"fireworks", r"stun gun",
                    r"switchblade", r"枪械", r"弹药", r"爆炸物", r"烟花", r"電気ショック",
                    r"schusswaffe", r"munition", r"feuerwerk",
                ),
                excludes=(r"toy", r"玩具", r"おもちゃ", r"costume", r"book"),
                reasons=("武器或爆炸物法规限制", "平台禁限售及运输风险", "刑事与产品责任风险"),
                resources=("专业持证经营体系", "目标国法律及平台专项审核"),
            )
        )

    if "CONTROLLED_CANNABINOID" not in existing:
        additions.append(
            rules.BarrierRule(
                code="CONTROLLED_CANNABINOID",
                family="受控物质/CBD",
                level="D",
                terms=(r"\bcbd\b", r"cannabis", r"marijuana", r"thc", r"大麻", r"カンナビス", r"cannabidiol", r"hanföl"),
                excludes=(r"book", r"shirt", r"costume", r"poster"),
                reasons=("受控物质及成分合法性差异", "平台禁限售", "跨境进口和刑事风险"),
                resources=("目标国专项法律意见", "成分检测、许可及平台书面确认"),
            )
        )

    if additions:
        rules.BARRIER_RULES = rules.BARRIER_RULES + tuple(additions)
