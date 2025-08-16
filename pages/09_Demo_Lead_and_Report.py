import streamlit as st
from components.lead_capture_and_pdf import lead_capture_and_pdf

st.set_page_config(page_title="顧問報告下載 Demo", page_icon="📄", layout="wide")
st.title("📄 顧問報告下載 Demo")

inputs_summary = {
    "家庭成員": "配偶＋二子女",
    "資產配置": "房產 6,000 萬、股票 2,000 萬、現金 1,000 萬",
    "偏好": "保留經營權、降低繼承糾紛",
}
result_summary = {
    "基準稅額": "4,700 萬（示意）",
    "保單規劃後": "降至 1,900 萬（示意）",
    "信託規劃後": "降至 2,200 萬（示意）",
}
comparisons = {
    "不規劃（基準）": {"total_tax": 4700, "note": "僅依法課稅（示意）"},
    "保單規劃": {"total_tax": 1900, "note": "以保單流動性作為稅源（示意）"},
    "信託規劃": {"total_tax": 2200, "note": "配置慈善與教育子女條款（示意）"},
}
recommendations = {
    "短期": "以 2,000 萬保單建立稅源池，並分批贈與股權（示意）。",
    "中期": "設置家族信託，約定教育/創業條款（示意）。",
    "長期": "建立董事會/家族憲章，以保單維持公平性（示意）。",
}

lead_capture_and_pdf(
    inputs_summary=inputs_summary,
    result_summary=result_summary,
    comparisons=comparisons,
    recommendations=recommendations,
)
