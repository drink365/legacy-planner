# pages/02_Tax_Path_Simulator.py
from __future__ import annotations
import re
import time
from typing import Dict, Any, Tuple

import streamlit as st
import pandas as pd

from components.lead_capture_and_pdf import lead_capture_and_pdf

# ────────────────────────────────────────────────────────────────────────────────
# 基本設定
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="🧭 傳承路徑模擬", page_icon="🧭", layout="wide")
st.title("🧭 傳承路徑模擬（顧問式體驗）")
st.caption("說明：本頁為教育示意，稅額公式採簡化模型，實務仍需由顧問審視與調整。")

# 小工具
def sanitize_plus(s: str) -> str:
    """將『配偶＋二子女』等 +/＋ 改成頓號，避免誤讀"""
    return re.sub(r"[+＋]", "、", s)

def tw_progressive_tax(total_10k: float) -> int:
    """
    超簡化示意級距（單位：萬元）：
      - 0 ~ 1,200 萬：10%
      - 1,200 ~ 3,200 萬：15%
      - 3,200 萬以上：20%
    目的：讓使用者看得懂『不規劃 vs. 規劃』的差距，實務稅額請接你的正式邏輯。
    """
    t = total_10k
    tax = 0.0
    # 0~1200
    a = min(t, 1200)
    tax += a * 0.10
    t -= a
    if t <= 0:
        return round(tax)

    # 1200~3200
    b = min(t, 2000)
    tax += b * 0.15
    t -= b
    if t <= 0:
        return round(tax)

    # 3200+
    tax += t * 0.20
    return round(tax)

def simulate_scenarios(total_10k: int, prefer: str, overseas: str) -> Dict[str, Dict[str, Any]]:
    """
    回傳三情境（示意）：不規劃 / 保單規劃 / 信託規劃
    可依偏好、海外資產微調降幅。
    """
    base_tax = tw_progressive_tax(total_10k)

    # 預設降幅（示意）
    save_policy = 0.55   # 保單規劃節省 55%
    save_trust  = 0.48   # 信託規劃節省 48%

    # 依偏好微調（示意）
    if prefer == "節稅優先":
        save_policy += 0.03
        save_trust  += 0.02
    elif prefer == "降低家族爭議":
        save_trust  += 0.03

    # 海外資產 → 多半需要信託/合規 → 信託方案效果略佳
    if overseas != "無":
        save_trust += 0.03

    policy_tax = max(round(base_tax * (1 - save_policy)), 0)
    trust_tax  = max(round(base_tax * (1 - save_trust)),  0)

    return {
        "不規劃（基準）": {"total_tax": base_tax, "note": "依法課稅（示意）。"},
        "保單規劃":       {"total_tax": policy_tax, "note": "以保單現金價值建立稅源池、流動性（示意）。"},
        "信託規劃":       {"total_tax": trust_tax,  "note": "可納入教育/慈善條款、跨境資產治理（示意）。"},
    }

def derive_kpi(comparisons: Dict[str, Dict[str, Any]]) -> Tuple[str, int, int, str]:
    """
    KPI：最佳方案 / 節省金額 / 基準稅額 / 降幅%
    """
    # 找 baseline
    base_key = None
    for k in comparisons:
        if "不規劃" in k or "基準" in k:
            base_key = k
            break
    if base_key is None:
        base_key = max(comparisons, key=lambda x: comparisons[x].get("total_tax", 0))

    base_tax = int(comparisons[base_key].get("total_tax", 0))

    # 找最低稅
    best_key = min(comparisons, key=lambda x: comparisons[x].get("total_tax", 10**9))
    best_tax = int(comparisons[best_key].get("total_tax", 0))

    saved = max(base_tax - best_tax, 0)
    pct = f"{round(saved / base_tax * 100)}%" if base_tax > 0 else "-"

    return best_key, saved, base_tax, pct

def liquidity_gap(tax_need_10k: int, cash_10k: int) -> Tuple[int, str]:
    """流動性缺口（需要稅源 - 現金），<0 表示足額"""
    gap = tax_need_10k - cash_10k
    if gap <= 0:
        return 0, "現金足以覆蓋稅款"
    return gap, f"現金不足 {gap} 萬，建議規劃稅源池（保單/信託）"

# ────────────────────────────────────────────────────────────────────────────────
# Step 1：基本情境
# ────────────────────────────────────────────────────────────────────────────────
with st.form("qna_form"):
    st.subheader("Step 1｜家庭與偏好")
    c1, c2, c3 = st.columns(3)
    with c1:
        members = st.multiselect(
            "家庭成員",
            ["配偶", "長子", "次子", "長女", "次女", "父母", "其他"],
            default=["配偶", "長子", "次女"]
        )
    with c2:
        overseas = st.selectbox(
            "是否有海外資產",
            ["無", "有（中國）", "有（日本）", "有（新加坡）", "有（越南）", "有（其他）"],
            index=0
        )
    with c3:
        prefer = st.radio("規劃偏好", ["維持經營控制", "降低家族爭議", "節稅優先"], index=1, horizontal=True)

    st.subheader("Step 2｜資產概況（新台幣，萬元）")
    a1, a2, a3 = st.columns(3)
    with a1:
        realty = st.number_input("不動產", min_value=0, value=6000, step=100)
    with a2:
        equities = st.number_input("股票/基金", min_value=0, value=2000, step=100)
    with a3:
        cash = st.number_input("現金/存款", min_value=0, value=1000, step=50)

    st.subheader("Step 3｜想留給誰？（文字）")
    heirs = st.text_input("簡述（例：配偶 50%、二子女各 25%）", value="配偶 50%、二子女各 25%")

    submitted = st.form_submit_button("⚙️ 產生模擬結果")

if not submitted:
    st.info("請完成上方 3 個步驟後，按下「⚙️ 產生模擬結果」。")
    st.stop()

# ────────────────────────────────────────────────────────────────────────────────
# 模擬計算（示意算法）
# ────────────────────────────────────────────────────────────────────────────────
total_10k = int(realty + equities + cash)
if total_10k <= 0:
    st.error("資產總額需大於 0。")
    st.stop()

comparisons = simulate_scenarios(total_10k, prefer, overseas)
best_key, saved_10k, base_tax_10k, pct = derive_kpi(comparisons)
gap_10k, gap_note = liquidity_gap(base_tax_10k, int(cash))

# ────────────────────────────────────────────────────────────────────────────────
# 結果區塊（圖表 + KPI + 文字）
# ────────────────────────────────────────────────────────────────────────────────
st.success("✅ 模擬完成：以下是您的差距與建議")

# 1) KPI 區
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("最佳方案（示意）", best_key)
with k2:
    st.metric("基準稅額", f"{base_tax_10k} 萬")
with k3:
    st.metric("預估可節省", f"{saved_10k} 萬", pct)
with k4:
    st.metric("現金稅源缺口", f"{gap_10k} 萬")

# 2) 長條圖（三情境稅額比較）
df = pd.DataFrame(
    {
        "情境": list(comparisons.keys()),
        "稅費合計_萬元": [v["total_tax"] for v in comparisons.values()],
    }
)
st.bar_chart(df, x="情境", y="稅費合計_萬元", use_container_width=True)

# 3) 風險/提醒
with st.expander("📌 風險與提醒（示意）", expanded=True):
    bullets = []
    if overseas != "無":
        bullets.append("您提到有海外資產：請特別留意 CRS 申報與跨境遺贈稅協定，建議納入信託或控股架構。")
    if gap_10k > 0:
        bullets.append(f"現金不足以覆蓋基準稅額（缺口 {gap_10k} 萬），建議建立可支用之稅源池（保單/信託）。")
    if prefer == "維持經營控制":
        bullets.append("可透過雙層股權 / 信託條款維持控制，同時做好股權流動性安排。")
    if prefer == "降低家族爭議":
        bullets.append("建議訂定家族憲章與分配條款（教育/創業基金），降低爭議風險。")
    if prefer == "節稅優先":
        bullets.append("在合規前提下評估保單與信託的搭配，兼顧節稅與資金調度。")
    if not bullets:
        bullets.append("初步看起來風險可控，仍建議安排顧問會談進一步確認。")
    for b in bullets:
        st.write(f"- {b}")
    st.caption("以上為系統根據輸入條件產生之示意提醒，並非正式顧問意見。")

# ────────────────────────────────────────────────────────────────────────────────
# 報告下載（Email 留存 → PDF）
# ────────────────────────────────────────────────────────────────────────────────
inputs_summary = {
    "家庭成員": "、".join(members) if members else "（未填）",
    "資產配置": f"不動產 {realty}、股票 {equities}、現金 {cash}（萬元）",
    "海外資產": overseas,
    "偏好": prefer,
    "分配意向": sanitize_plus(heirs),
}
result_summary = {
    "最佳方案（示意）": best_key,
    "基準稅額": f"{base_tax_10k} 萬",
    "預估可節省": f"{saved_10k} 萬（{pct}）",
    "現金稅源檢視": gap_note,
}
reco
