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
                    r"生发",
                    r"生髮",
                    r"育发",
                    r"育髮",
                    r"防脱",
                    r"防脫",
                    r"脱发治疗",
                    r"脱髮治療",
                    r"hair growth",
                    r"hair regrowth",
                    r"hair tonic",
                    r"育毛",
                    r"発毛",
                    r"養毛",
                    r"haarwuchs",
                    r"haarwuchsmittel",
                ),
                reasons=("强功效生发/防脱宣称可能触及药品或准药品", "活性成分、功效证据与标签要求", "皮肤接触和不良反应责任"),
                resources=("目标国法规分类确认", "配方安全及功效资料", "当地责任主体和产品责任体系"),
                capability="cosmetics_compliance",
            )
        )

    if "WEAPONS_EXPLOSIVES" not in existing:
        additions.append(
            rules.BarrierRule(
                code="WEAPONS_EXPLOSIVES",
                family="武器/爆炸物/高限制品",
                level="D",
                terms=(
                    r"firearm",
                    r"ammunition",
                    r"gun parts",
                    r"explosive",
                    r"fireworks",
                    r"stun gun",
                    r"switchblade",
                    r"枪械",
                    r"弹药",
                    r"爆炸物",
                    r"烟花",
                    r"電気ショック",
                    r"schusswaffe",
                    r"munition",
                    r"feuerwerk",
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
