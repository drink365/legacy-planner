from __future__ import annotations
import streamlit as st
from supabase import create_client

@st.cache_resource(show_spinner=False)
def get_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    except KeyError as e:
        st.error("讀取 Secrets 失敗：請到 Streamlit Cloud 的 Secrets 設定 supabase.url / supabase.key")
        raise

    try:
        return create_client(url, key)
    except Exception as e:
        st.error("連線 Supabase 失敗：請檢查 url 是否為 https://<專案>.supabase.co 與 key 是否為 Service role key。")
        raise
