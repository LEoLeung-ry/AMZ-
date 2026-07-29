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

    if additions:
        rules.BARRIER_RULES = rules.BARRIER_RULES + tuple(additions)
