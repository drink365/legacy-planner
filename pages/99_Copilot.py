import streamlit as st
from openai import OpenAI
from src.repos.leads_repo import log_event

st.set_page_config(page_title="永傳顧問 AI", page_icon="🤖", layout="wide")
st.title("🧭 永傳顧問 AI")

sys_prompt = (
    "你是永傳家族辦公室的顧問 AI。用語要溫暖、專業、簡潔。"
    "聚焦台灣高資產族群的退休與傳承，回答時要：\n"
    "1) 先釐清情境（家庭結構、資產配置、跨境、偏好）\n"
    "2) 提供3步行動建議（含保單/信託/贈與的方向）\n"
    "3) 結尾給CTA：下載顧問報告 / 預約諮詢。\n"
)

if "chat" not in st.session_state:
    st.session_state.chat = []

for role, content in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(content)

user_msg = st.chat_input("想問的情境或問題，例如：先贈與還是用保單？有海外資產要注意什麼？")
if user_msg:
    st.session_state.chat.append(("user", user_msg))
    with st.chat_message("user"):
        st.markdown(user_msg)

    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    model = st.secrets["openai"].get("model", "gpt-5-nano")
    messages = [{"role": "system", "content": sys_prompt}] + [
        {"role": r, "content": c} for r, c in st.session_state.chat
    ]
    with st.chat_message("assistant"):
        with st.spinner("思考中…"):
            resp = client.chat.completions.create(model=model, messages=messages, temperature=0.2)
            ans = resp.choices[0].message.content
            st.markdown(ans)
            st.session_state.chat.append(("assistant", ans))
            log_event("chat", payload={"q": user_msg, "a": ans})

st.divider()
st.info("小提醒：此對話僅供教育與初步規劃參考，實際方案仍需顧問審視。")
