import streamlit as st

st.set_page_config(page_title="永傳｜數位傳承顧問", page_icon="🏛️", layout="centered")

brand = st.secrets.get("brand", {})
TITLE = brand.get("title", "Grace Family Office｜永傳家族辦公室")

st.markdown(f"# {TITLE}")
st.markdown(
    "**高資產家族的數位傳承顧問**  
"
    "**30 年專業 × AI 智能** — 以情境化路徑模擬，讓您看見『不規劃 vs. 規劃』的差距。"
)

c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("pages/02_Tax_Path_Simulator.py", label="開始路徑模擬", icon="🧭")
with c2:
    st.page_link("pages/09_Demo_Lead_and_Report.py", label="顧問報告下載（Demo）", icon="📄")
with c3:
    st.page_link("pages/99_Copilot.py", label="永傳顧問 AI", icon="🤖")

st.caption("本平台提供初步規劃建議與教育資訊，實際仍需顧問審視後決定。")
