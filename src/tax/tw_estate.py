# src/tax/tw_estate.py
from __future__ import annotations
from typing import Tuple

# 常數（單位：萬元）
EXEMPT_10K                = 1333   # 免稅額
FUNERAL_10K               = 138    # 喪葬費扣除
SPOUSE_DEDUCT_10K         = 553    # 配偶扣除
ADULT_CHILD_DEDUCT_10K    = 56     # 直系卑親屬（成年子女等）每人
PARENTS_DEDUCT_10K        = 138    # 父母每人
DISABLED_DEDUCT_10K       = 693    # 重度以上身心障礙每人
OTHER_DEPENDENTS_10K      = 56     # 其他受扶養（兄弟姊妹、祖父母）每人

# 級距（轉為「元」後算更精準），門檻金額（元）
B1 = 56_210_000
B2 = 112_420_000

def _progressive_tax_from_net_10k(net_10k: int) -> int:
    """
    將課稅遺產淨額（萬元）換算為元後按 10% / 15% / 20% 級距計稅，再換回萬元（四捨五入）。
    """
    taxable = max(net_10k, 0) * 10_000
    if taxable <= 0:
        tax = 0
    elif taxable <= B1:
        tax = taxable * 0.10
    elif taxable <= B2:
        tax = 5_621_000 + (taxable - B1) * 0.15
    else:
        tax = 14_052_500 + (taxable - B2) * 0.20
    return int(round(tax / 10_000))  # 回傳萬元

def calculate_estate_tax_2025(
    total_assets_10k: int,
    *,
    has_spouse: bool = False,
    adult_children: int = 0,
    parents: int = 0,
    disabled_people: int = 0,
    other_dependents: int = 0
) -> Tuple[int, int, int]:
    """
    回傳 (課稅遺產淨額_萬元, 應納遺產稅_萬元, 扣除總額_萬元)
    """
    deduct_10k = FUNERAL_10K
    if has_spouse:
        deduct_10k += SPOUSE_DEDUCT_10K
    deduct_10k += adult_children * ADULT_CHILD_DEDUCT_10K
    deduct_10k += parents * PARENTS_DEDUCT_10K
    deduct_10k += disabled_people * DISABLED_DEDUCT_10K
    deduct_10k += other_dependents * OTHER_DEPENDENTS_10K

    taxable_net_10k = max(total_assets_10k - EXEMPT_10K - deduct_10k, 0)
    tax_10k = _progressive_tax_from_net_10k(taxable_net_10k)
    return taxable_net_10k, tax_10k, deduct_10k
