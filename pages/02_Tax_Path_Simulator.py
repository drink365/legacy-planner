# 置頂 import 區域新增：
from src.tax.tw_estate import calculate_estate_tax_2025

# … Step 1（家庭與偏好）之後，新增家庭人數與身障/其他受扶養輸入 …
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

# … 模擬計算（把原本 base 稅額的示意級距換成正式級距+扣除） …
taxable_10k, base_tax_10k, deduct_10k = calculate_estate_tax_2025(
    total_10k,
    has_spouse=has_spouse,
    adult_children=int(adult_children),
    parents=int(parents),
    disabled_people=int(disabled_people),
    other_dependents=int(other_dependents),
)

# 原有的 simulate_scenarios 改成只產出三情境，但以 base_tax_10k 為基準（其餘可保留你的係數）
def simulate_scenarios(total_10k: int, prefer: str, overseas: str, base_tax_10k: int) -> Dict[str, Dict[str, Any]]:
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
        "不規劃（基準）": {"total_tax": base_tax_10k, "note": "依法課稅（2025 正式級距，含各項扣除）。"},
        "保單規劃":       {"total_tax": policy_tax,   "note": "以保單現金價值預留稅源池、提升流動性（示意）。"},
        "信託規劃":       {"total_tax": trust_tax,    "note": "信託條款可納教育/慈善與跨境合規（示意）。"},
    }

comparisons = simulate_scenarios(total_10k, prefer, overseas, base_tax_10k)

# KPI 與報表顯示區：建議把扣除資訊也露出，強化「專業感」
with st.expander("🧾 計算基礎（免稅與扣除）", expanded=False):
    st.write(
        f"- 課稅遺產淨額：{taxable_10k} 萬\n"
        f"- 總扣除額：{deduct_10k} 萬（含免稅 1333 萬、喪葬 138 萬、配偶/子女/父母/身障/其他受扶養等）"
    )
