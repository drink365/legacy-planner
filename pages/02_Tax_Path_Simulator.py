from __future__ import annotations
import streamlit as st
from components.lead_capture_and_pdf import lead_capture_and_pdf

st.set_page_config(page_title="路徑模擬｜顧問式體驗", page_icon="🧭", layout="wide")
st.title("🧭 傳承路徑模擬（示意版）")

st.info("此為示意專區，展示『顧問式體驗』流程與報告下載。實際稅負請以正式工具與顧問審視為準。")

with st.form("qna"):
    st.subheader("Step 1：家庭與資產")
    col1, col2, col3 = st.columns(3)
    with col1:
        members = st.multiselect("家庭成員", ["配偶", "長子", "次子", "長女", "次女", "父母"], default=["配偶", "長子", "次女"])
    with col2:
        overseas = st.selectbox("是否有海外資產", ["無", "有（中國）", "有（日本）", "有（越南）", "有（其他）"], index=0)
    with col3:
        prefer = st.radio("偏好", ["維持經營控制", "降低家族爭議", "節稅優先"], index=1)

    st.subheader("Step 2：資產概況（新台幣，萬元）")
    a1, a2, a3 = st.columns(3)
    with a1:
        realty = st.number_input("不動產", min_value=0, value=6000, step=100)
    with a2:
        stocks = st.number_input("股票/基金", min_value=0, value=2000, step=100)
    with a3:
        cash = st.number_input("現金/存款", min_value=0, value=1000, step=50)

    st.subheader("Step 3：想留給誰？")
    heirs = st.text_input("簡述（例：配偶 50%、二子女各 25%）", value="配偶 50%、二子女各 25%")

    submit = st.form_submit_button("產生模擬結果")

if submit:
    total = realty + stocks + cash
    # ⚠️ 示意算法（非真實稅額），僅用來展示 UI 與報告；請換成你的正式計算邏輯
    baseline_tax = round(total * 0.15)  # 假設基準 15% 稅負
    policy_tax = round(baseline_tax * 0.4)  # 保單規劃降低 60%
    trust_tax  = round(baseline_tax * 0.47) # 信託規劃降低 53%（示意）

    inputs_summary = {
        "家庭成員": "、".join(members) or "（未填）",
        "資產配置": f"不動產 {realty}、股票 {stocks}、現金 {cash}（萬元）",
        "海外資產": overseas,
        "偏好": prefer,
        "分配意向": heirs,
    }
    result_summary = {
        "基準稅額（示意）": f"{baseline_tax} 萬",
        "保單規劃後（示意）": f"{policy_tax} 萬",
        "信託規劃後（示意）": f"{trust_tax} 萬",
    }
    comparisons = {
        "不規劃（基準）": {"total_tax": baseline_tax, "note": "僅依法課稅（示意）"},
        "保單規劃": {"total_tax": policy_tax, "note": "以保單流動性建立稅源池（示意）"},
        "信託規劃": {"total_tax": trust_tax, "note": "加入教育/慈善條款（示意）"},
    }
    recs = {
        "短期": "先建立 2,000 萬保單稅源池，避免臨時處分資產（示意）。",
        "中期": "設置家族信託，約定教育/創業條款與受託人機制（示意）。",
        "長期": "制定家族憲章＋董事會制度，並以保單維持公平性（示意）。",
    }

    st.success("✅ 模擬完成：以下提供報告下載")
    lead_capture_and_pdf(
        inputs_summary=inputs_summary,
        result_summary=result_summary,
        comparisons=comparisons,
        recommendations=recs,
        tag="path_sim_demo",
    )
