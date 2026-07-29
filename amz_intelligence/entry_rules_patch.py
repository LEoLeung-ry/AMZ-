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
