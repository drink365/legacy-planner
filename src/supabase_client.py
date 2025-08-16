from __future__ import annotations
import streamlit as st
from supabase import create_client

@st.cache_resource(show_spinner=False)
def get_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)
