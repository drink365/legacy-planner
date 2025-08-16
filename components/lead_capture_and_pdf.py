from __future__ import annotations
from typing import Dict, Any, Optional
import streamlit as st
from src.repos.leads_repo import save_lead, log_event
from src.report.report_builder import build_pdf

def lead_capture_and_pdf(*, inputs_summary: Dict[str, Any], result_summary: Dict[str, Any], comparisons: Optional[Dict[str, Any]], recommendations: Dict[str, Any], tag: str = "tax_tool", case_id: Optional[str] = None):
    brand = st.secrets.get("brand", {})
    invite_code_cfg = brand.get("invite_code", "")

    # 邀請碼（若設定）
    if invite_code_cfg:
        code = st.text_input("邀請碼（必填）", type="password")
        if code.strip() != invite_code_cfg:
            st.info("請輸入有效邀請碼以解鎖下載報告。")
            st.stop()

    with st.expander("🔎 結果重點（點我展開/收合）", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("您的基本情境")
            st.json(inputs_summary, expanded=False)
        with c2:
            st.subheader("計算結果摘要")
            st.json(result_summary, expanded=False)
        if comparisons:
            st.subheader("情境比較（基準 vs. 規劃）")
            st.json(comparisons, expanded=False)

    st.markdown("---")
    st.subheader("下載您的顧問級報告（免費）")
    st.caption("輸入 Email 後即可下載 PDF。此報告僅供教育與初步規劃參考，實際以專家諮詢為準。")

    with st.form("lead_form"):
        cols = st.columns([1,1])
        name = cols[0].text_input("姓名（選填）")
        email = cols[1].text_input("Email（必填）")
        cols2 = st.columns([1,1])
        phone = cols2[0].text_input("手機（選填）")
        agree = cols2[1].checkbox("我同意接收報告與後續規劃建議（可隨時取消）", value=True)
        submitted = st.form_submit_button("產生專屬 PDF")

    if submitted:
        if not email or "@" not in email:
            st.error("請輸入有效的 Email。")
            return
        payload = {
            "inputs": inputs_summary,
            "result": result_summary,
            "comparisons": comparisons,
            "recommendations": recommendations,
        }
        lead_id = save_lead(name=name or None, email=email.strip(), phone=phone or None, case_id=case_id, tag=tag, payload=payload)
        st.success(f"已建立報告（Lead #{lead_id}）。")
        log_event("submit_form", ref_id=lead_id, payload=payload)

        pdf_bytes = build_pdf(inputs_summary=inputs_summary, result_summary=result_summary, comparisons=comparisons, recommendations=recommendations)
        log_event("download_pdf", ref_id=lead_id, payload={"bytes": len(pdf_bytes)})

        st.download_button(
            label="⬇️ 下載 PDF 報告",
            data=pdf_bytes,
            file_name="永傳_顧問建議報告.pdf",
            mime="application/pdf",
        )
