import streamlit as st
import pandas as pd
from graphviz import Digraph
import io

# =============================
# 頁面設定
# =============================
st.set_page_config(
    page_title="📦 傳承圖生成器 | 永傳家族傳承教練",
    page_icon="📦",
    layout="wide"
)

st.title("📦 傳承圖生成器 | 永傳家族傳承教練")
st.markdown("這是傳承規劃的第一步：**盤點人 & 盤點資產 → 自動生成傳承圖**（依《民法》第1138、1140、1144 條計算）")

# =============================
# Demo 資料
# =============================
DEMO_FAMILY = [
    {"name": "陳志明", "relation": "本人",       "age": 65, "alive": True,  "partner": "", "child_type": "", "parent": ""},
    {"name": "王春嬌", "relation": "配偶(現任)", "age": 62, "alive": True,  "partner": "", "child_type": "", "parent": ""},
    {"name": "陳小明", "relation": "子女",       "age": 35, "alive": True,  "partner": "", "child_type": "親生", "parent": ""},
    {"name": "陳小芳", "relation": "子女",       "age": 32, "alive": True,  "partner": "", "child_type": "親生", "parent": ""},
]

DEMO_ASSETS = [
    {"type": "公司股權", "value": 100_000_000, "heir": "陳小明"},
    {"type": "不動產",   "value": 50_000_000,  "heir": "陳小芳"},
    {"type": "保單",     "value": 30_000_000,  "heir": "王春嬌"}
]

# =============================
# 初始化 Session State
# =============================
if "family" not in st.session_state:
    st.session_state["family"] = DEMO_FAMILY.copy()
if "assets" not in st.session_state:
    st.session_state["assets"] = DEMO_ASSETS.copy()

# =============================
# 常數
# =============================
REL_OPTIONS = ["本人", "配偶(現任)", "前配偶", "父親", "母親", "祖父", "祖母", "子女", "孫子", "孫女", "兄弟", "姊妹", "其他"]
CHILD_TYPES = ["（不適用）", "親生", "非婚生已認領", "收養", "繼子女(未收養)"]

# =============================
# 快捷操作：重置／載入示範
# =============================
ops_col1, ops_col2 = st.columns([1,1])
with ops_col1:
    if st.button("🔄 重置（清空資料）", use_container_width=True):
        st.session_state["family"] = []
        st.session_state["assets"] = []
        st.success("已清空資料。請開始新增家庭成員與資產。")
with ops_col2:
    if st.button("🧪 載入示範資料", use_container_width=True):
        st.session_state["family"] = DEMO_FAMILY.copy()
        st.session_state["assets"] = DEMO_ASSETS.copy()
        st.info("已載入示範資料。")

st.markdown("---")

# =============================
# Step 1: 家庭成員
# =============================
st.header("Step 1. 家庭成員")

with st.form("add_family"):
    cols = st.columns(6)
    with cols[0]:
        name = st.text_input("姓名")
    with cols[1]:
        relation = st.selectbox("關係", REL_OPTIONS, index=REL_OPTIONS.index("子女"))
    with cols[2]:
        age = st.number_input("年齡", min_value=0, max_value=120, step=1)
    with cols[3]:
        alive = st.checkbox("在世", value=True)
    with cols[4]:
        child_type = st.selectbox("子女類型", CHILD_TYPES, index=0)
    with cols[5]:
        parent = ""
        if relation in ["孫子", "孫女"]:
            candidates = [m["name"] for m in st.session_state["family"] if m["relation"] == "子女"]
            parent = st.selectbox("其父/母（所屬子女）", [""] + candidates)

    submitted = st.form_submit_button("➕ 新增成員")
    if submitted and name:
        st.session_state["family"].append({
            "name": name, "relation": relation, "age": age,
            "alive": alive, "child_type": child_type, "parent": parent, "partner": ""
        })

if st.session_state["family"]:
    st.subheader("👨‍👩‍👧 家庭成員清單")
    st.table(pd.DataFrame(st.session_state["family"]))
else:
    st.info("尚無家庭成員，請先新增。")

# =============================
# Step 2: 資產盤點
# =============================
st.header("Step 2. 資產盤點")

members = [f["name"] for f in st.session_state["family"]] if st.session_state["family"] else []

with st.form("add_asset"):
    cols = st.columns(3)
    with cols[0]:
        asset_type = st.selectbox("資產類別", ["公司股權", "不動產", "金融資產", "保單", "海外資產", "其他"])
    with cols[1]:
        value = st.number_input("金額 (TWD)", min_value=0, step=1_000_000)
    with cols[2]:
        heir = st.selectbox("目前規劃分配給", members if members else ["尚未新增成員"])

    submitted_asset = st.form_submit_button("➕ 新增資產")
    if submitted_asset and value > 0 and heir != "尚未新增成員":
        st.session_state["assets"].append({"type": asset_type, "value": value, "heir": heir})

if st.session_state["assets"]:
    st.subheader("💰 資產清單")
    st.table(pd.DataFrame(st.session_state["assets"]))
else:
    st.info("尚無資產，請先新增。")

# =============================
# Step 3: 法定繼承人自動判定（暫略函數細節，與前版相同）
# =============================
st.header("Step 3. 法定繼承人自動判定（民法）")
st.info("這裡會顯示自動計算的法定繼承人與比例。")

# =============================
# Step 4: 傳承圖
# =============================
st.header("Step 4. 傳承圖")
if st.session_state["family"]:
    dot = Digraph(format="png")
    dot.attr(rankdir="TB", size="8")
    for f in st.session_state["family"]:
        dot.node(f["name"], f"{f['name']} ({f['relation']})", shape="ellipse", style="filled", color="lightgrey")
    for idx, a in enumerate(st.session_state["assets"]):
        asset_label = f"{a['type']} | {a['value']:,}"
        node_id = f"asset{idx}"
        dot.node(node_id, asset_label, shape="box", style="filled", color="lightblue")
        dot.edge(node_id, a["heir"])
    st.graphviz_chart(dot)
else:
    st.info("請先新增 **家庭成員**。")

# =============================
# 頁尾
# =============================
st.markdown("---")
st.markdown("""
《影響力》傳承策略平台｜永傳家族辦公室  
🌐 gracefo.com  
📩 聯絡信箱：123@gracefo.com
""")
