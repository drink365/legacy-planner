# pages/99_Copilot.py
import time
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import OpenAI, RateLimitError
from src.repos.leads_repo import log_event

# ====== 基本設定 ======
st.set_page_config(page_title="永傳顧問 AI", page_icon="🤖", layout="wide")
st.title("🧭 永傳顧問 AI")

# 只用 gpt-5-nano
MODEL_NAME = "gpt-5-nano"

# 使用者體驗與穩定性參數
COOLDOWN_SECONDS = 8      # 兩次送出間最短間隔（避免連點造成限流）
HISTORY_TURNS = 6         # 僅保留最近 N 輪對話（壓 token）
MAX_TOKENS = 512          # 回覆上限（避免過長）

# 內部除錯訊息開關（在 Secrets 設 app_env="dev" 才顯示）
APP_ENV = st.secrets.get("app_env", "").lower()

# 系統提示（顧問式語氣）
SYS_PROMPT = (
    "你是永傳家族辦公室的顧問 AI。用語要溫暖、專業、簡潔。"
    "聚焦台灣高資產族群的退休與傳承，回答時要：\n"
    "1) 先釐清情境（家庭結構、資產配置、跨境、偏好）\n"
    "2) 提供 3 步行動建議（含保單/信託/贈與的方向）\n"
    "3) 結尾給 CTA：下載顧問報告 / 預約諮詢。\n"
)

# ====== 狀態初始化 ======
if "chat" not in st.session_state:
    st.session_state.chat = []  # list[tuple(role, content)]
if "last_call_ts" not in st.session_state:
    st.session_state.last_call_ts = 0.0

# ====== 顯示歷史訊息 ======
for role, content in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(content)

# ====== 輔助：組裝 messages 並裁切歷史 ======
def build_messages():
    messages = [{"role": "system", "content": SYS_PROMPT}]
    # 只帶入最近 N 輪對話（每輪包含 user+assistant 兩則）
    recent = st.session_state.chat[-(HISTORY_TURNS * 2):] if HISTORY_TURNS > 0 else st.session_state.chat
    for r, c in recent:
        messages.append({"role": r, "content": c})
    return messages

# ====== 指數退避重試（針對 RateLimitError） ======
@retry(
    reraise=True,
    stop=stop_after_attempt(5),                   # 最多重試 5 次
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(RateLimitError),
)
def call_openai(client: OpenAI, messages):
    return client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        max_tokens=MAX_TOKENS,
    )

# ====== 冷卻倒數（送出前提示） ======
now = time.time()
remain = int(max(0, COOLDOWN_SECONDS - (now - st.session_state.get("last_call_ts", 0))))
if remain > 0:
    st.info(f"為確保穩定回覆，請 {remain} 秒後再送。")
st.caption("提示：輸入完成後請按 Enter 送出，送出後請稍候片刻讓顧問 AI 思考。")

# ====== 使用者輸入 ======
user_msg = st.chat_input("想問的情境或問題，例如：先贈與還是用保單？有海外資產要注意什麼？")
if user_msg:
    # 節流：避免短時間重複呼叫
    now = time.time()
    delta = now - st.session_state.last_call_ts
    if delta < COOLDOWN_SECONDS:
        with st.chat_message("assistant"):
            st.info(f"訊息已收到，為避免限流，請 {int(COOLDOWN_SECONDS - delta)} 秒後再送 🙏")
        st.stop()

    # 顯示使用者訊息
    st.session_state.chat.append(("user", user_msg))
    with st.chat_message("user"):
        st.markdown(user_msg)

    # 準備 OpenAI Client（若你的帳戶需要 organization，請在 Secrets 設 openai.organization）
    api_key = st.secrets["openai"]["api_key"]
    org     = st.secrets["openai"].get("organization", None)
    client_kwargs = {"api_key": api_key}
    if org:
        client_kwargs["organization"] = org
    client = OpenAI(**client_kwargs)

    messages = build_messages()

    with st.chat_message("assistant"):
        try:
            st.session_state.last_call_ts = time.time()  # 記錄節流時間點
            resp = call_openai(client, messages)
            ans = resp.choices[0].message.content
            st.markdown(ans)
            st.session_state.chat.append(("assistant", ans))
            log_event("chat", payload={"q": user_msg, "a": ans, "model": MODEL_NAME})

        except RateLimitError:
            st.error("目前顧問 AI 較忙或達到速率上限，系統已自動重試。請稍後再問一次，或將問題整合後再送。")
        except Exception as e:
            st.error("⚠️ 無法取得回覆。請確認 `openai.api_key` 有效，且帳戶對 gpt-5-nano 具有使用權。")
            if APP_ENV == "dev":
                st.caption(f"DEBUG：{e}")

# ====== 頁尾說明 ======
st.divider()
st.info("小提醒：此對話僅供教育與初步規劃參考，實際方案仍需顧問審視。")
