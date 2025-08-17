# pages/02_Tax_Path_Simulator.py
from __future__ import annotations
import re
from typing import Dict, Any, Tuple

import streamlit as st
import pandas as pd

from components.lead_capture_and_pdf import lead_capture_and_pdf
from src.tax.tw_estate import calculate_estate_tax_2025  # 依照你剛新增的模組

# ────────────────────────────────────────────────────────────────────────────────
# 基本設定
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="🧭 傳承路徑模擬", page_icon="🧭", layout="wide")
st.title("🧭 傳承路徑模擬（顧問式體驗）")
st.caption("說明：本頁為教育示意；稅額採 2025 年正式三級距累進與扣除邏輯，實務仍需由顧問審視與調整。")

# ────────────────────────────────────────────────────────────────────────────────
# 小工具
# ────────────────────────────────────────────────────────────────────────────────
def sanitize_plus(s: str) -> str:
    """將『配偶＋二子女』等 +/＋ 改成頓號，避免誤讀"""
    return re.sub(r"[+＋]", "、", s)

def derive_kpi(comparisons: Dict[str, Dict[str, Any]]) -> Tuple[str, int, int, str]:
    """從情境比較推 KPI：最佳方案 / 節省金額 / 基準稅額 / 降幅%"""
    # 找 baseline
    base_key = None
    for k in comparisons:
        if "不規劃" in k or "基準" in k:
            base_key = k
            break
    if base_key is None:
        base_key = max(comparisons, key=lambda x: comparisons[x].get("total_tax", 0))

    base_tax = int(comparisons[base_key].get("total_tax", 0))
    # 找最低
    best_key = min(comparisons, key=lambda x: comparisons[x].get("total_tax", 10**9))
    best_tax = int(comparisons[best_key].get("total_tax", 0))
    saved = max(base_tax - best_tax, 0)
    pct = f"{round(saved / base_tax * 100)}%" if base_tax > 0 else "-"
    return best_key, saved, base_tax, pct

def liquidity_gap(tax_need_10k: int, cash_10k: int) -> Tuple[int, str]:
    """流動性缺口（需要稅源 - 現金），<0 表足額"""
    gap = tax_need_10k - cash_10k
    if gap <= 0:
        return 0, "現金足以覆蓋稅款"
    return gap, f"現金不足 {gap} 萬，建議規劃稅源池（保單/信託）"

# ────────────────────────────────────────────────────────────────────────────────
# 表單：家庭與資產
# ────────────────────────────────────────────────────────────────────────────────
with st.form("qna_form"):
    st.subheader("Step 1｜家庭與偏好")
    c1, c2, c3 = st.columns(3)
    with c1:
        members = st.multiselect(
            "家庭成員",
            ["配偶", "長子", "次子", "長女", "次女", "父母", "其他"],
            default=["配偶", "長子", "次女"],
        )
    with c2:
        overseas = st.selectbox(
            "是否有海外資產",
            ["無", "有（中國）", "有（日本）", "有（新加坡）", "有（越南）", "有（其他）"],
            index=0,
        )
    with c3:
        prefer = st.radio("規劃偏好", ["維持經營控制", "降低家族爭議", "節稅優先"], index=1, horizontal=True)

    st.subheader("Step 1.1｜家庭人數細項（影響扣除額）")
    f1, f2, f3, f4, f5 = st.columns(5)
    with f1:
        has_spouse = st.checkbox("有配偶", value=True)
    with f2:
        adult_children = st.number_input("成年子女數", min_value=0, max_value=10, value=2, step=1)
    with f3:
        parents = st.number_input("父母人數（最多2）", min_value=0, max_value=2, value=0, step=1)
    with f4:
        disabled_people = st.number_input("重度身心障礙者數", min_value=0, max_value=5, value=0, step=1)
    with f5:
        other_dependents = st.number_input("其他受扶養（兄弟姊妹/祖父母）", min_value=0, max_value=5, value=0, step=1)

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
# 模擬計算（正式：2025 遺產稅三級距＋扣除）
# ────────────────────────────────────────────────────────────────────────────────
total_10k = int(realty + equities + cash)
if total_10k <= 0:
    st.error("資產總額需大於 0。")
    st.stop()

taxable_10k, base_tax_10k, deduct_10k = calculate_estate_tax_2025(
    total_10k,
    has_spouse=has_spouse,
    adult_children=int(adult_children),
    parents=int(parents),
    disabled_people=int(disabled_people),
    other_dependents=int(other_dependents),
)

# 三情境（先用效果係數表達方向；後續可逐步替換為精算）
def simulate_scenarios(prefer: str, overseas: str, base_tax_10k: int) -> Dict[str, Dict[str, Any]]:
    save_policy = 0.55
    save_trust  = 0.48
    if prefer == "節稅優先":
        save_policy += 0.03; save_trust += 0.02
    elif prefer == "降低家族爭議":
        save_trust  += 0.03
    if overseas != "無":
        save_trust  += 0.03

    policy_tax = max(int(round(base_tax_10k * (1 - save_policy))), 0)
    trust_tax  = max(int(round(base_tax_10k * (1 - save_trust))),  0)

    return {
        "不規劃（基準）": {"total_tax": base_tax_10k, "note": "依法課稅（2025 正式級距，含免稅與扣除）。"},
        "保單規劃":       {"total_tax": policy_tax,   "note": "以保單現金價值預留稅源池、提升流動性（示意）。"},
        "信託規劃":       {"total_tax": trust_tax,    "note": "信託條款可納教育/慈善與跨境合規（示意）。"},
    }

comparisons = simulate_scenarios(prefer, overseas, base_tax_10k)
best_key, saved_10k, base_tax_show_10k, pct = derive_kpi(comparisons)
gap_10k, gap_note = liquidity_gap(base_tax_show_10k, int(cash))

# ────────────────────────────────────────────────────────────────────────────────
# 顯示結果（KPI + 圖表 + 計算基礎）
# ────────────────────────────────────────────────────────────────────────────────
st.success("✅ 模擬完成：以下是您的差距與建議")

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("最佳方案（示意）", best_key)
with k2:
    st.metric("基準稅額", f"{base_tax_show_10k} 萬")
with k3:
    st.metric("預估可節省", f"{saved_10k} 萬", pct)
with k4:
    st.metric("現金稅源缺口", f"{gap_10k} 萬")

df = pd.DataFrame(
    {"情境": list(comparisons.keys()),
     "稅費合計_萬元": [v["total_tax"] for v in comparisons.values()]}
)
st.bar_chart(df, x="情境", y="稅費合計_萬元", use_container_width=True)

with st.expander("🧾 計算基礎（免稅與扣除）", expanded=False):
    st.write(
        f"- 課稅遺產淨額：{taxable_10k} 萬\n"
        f"- 總扣除額：{deduct_10k} 萬（含免稅 1333 萬、喪葬 138 萬、配偶/子女/父母/身障/其他受扶養等）"
    )

# ────────────────────────────────────────────────────────────────────────────────
# 報告下載（Email 留存 → PDF）
# ────────────────────────────────────────────────────────────────────────────────
inputs_summary = {
    "家庭成員": "、".join(members) if members else "（未填）",
    "資產配置": f"不動產 {realty}、股票 {equities}、現金 {cash}（萬元）",
    "海外資產": overseas,
    "偏好": prefer,
    "分配意向": sanitize_plus(heirs),
    "扣除摘要": f"配偶:{'有' if has_spouse else '無'}、成子女:{int(adult_children)}、父母:{int(parents)}、"
               f"身障:{int(disabled_people)}、其他受扶養:{int(other_dependents)}",
}
result_summary = {
    "最佳方案（示意）": best_key,
    "基準稅額": f"{base_tax_show_10k} 萬",
    "預估可節省": f"{saved_10k} 萬（{pct}）",
    "現金稅源檢視": gap_note,
}
recommendations = {
    "短期": "先建立可支用之稅源池（如：具有現金價值之保單），避免臨時處分核心資產（示意）。",
    "中期": "導入家族信託（含教育/創業/慈善條款），提升治理與跨境合規（示意）。",
    "長期": "制定家族憲章與董事會制度，結合股權安排維持控制與公平（示意）。",
}

pdf_comparisons = {k: {"total_tax": int(v["total_tax"]), "note": v.get("note", "")} for k, v in comparisons.items()}

st.markdown("---")
st.subheader("📄 下載您的顧問級報告（免費）")
lead_capture_and_pdf(
    inputs_summary=inputs_summary,
    result_summary=result_summary,
    comparisons=pdf_comparisons,
    recommendations=recommendations,
    tag="path_sim_v2",
)
