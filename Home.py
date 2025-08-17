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
st.markdown("這是傳承規劃的第一步：**盤點人 & 盤點資產 → 自動生成傳承圖**")

# =============================
# Demo 資料
# =============================
demo_family = [
    {"name": "王大明", "relation": "父親", "age": 65},
    {"name": "李淑芬", "relation": "母親", "age": 62},
    {"name": "王小華", "relation": "子女", "age": 35},
    {"name": "王小美", "relation": "子女", "age": 32}
]

demo_assets = [
    {"type": "公司股權", "value": 100000000, "heir": "王小華"},
    {"type": "不動產", "value": 50000000, "heir": "王小美"},
    {"type": "保單", "value": 30000000, "heir": "李淑芬"}
]

# 初始化 Session State
if "family" not in st.session_state:
    st.session_state["family"] = demo_family.copy()
if "assets" not in st.session_state:
    st.session_state["assets"] = demo_assets.copy()

# =============================
# Step 1: 家庭成員
# =============================
st.header("Step 1. 家庭成員")

with st.form("add_family"):
    cols = st.columns(3)
    with cols[0]:
        name = st.text_input("姓名")
    with cols[1]:
        relation = st.selectbox("關係", ["父親", "母親", "配偶", "子女", "其他"])
    with cols[2]:
        age = st.number_input("年齡", min_value=0, max_value=120, step=1)

    submitted = st.form_submit_button("➕ 新增成員")
    if submitted and name:
        st.session_state["family"].append({"name": name, "relation": relation, "age": age})

if st.session_state["family"]:
    st.subheader("👨‍👩‍👧 家庭成員清單")
    st.table(pd.DataFrame(st.session_state["family"]))

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
        value = st.number_input("金額 (TWD)", min_value=0, step=1000000)
    with cols[2]:
        heir = st.selectbox("分配給", members if members else ["尚未新增成員"])

    submitted_asset = st.form_submit_button("➕ 新增資產")
    if submitted_asset and value > 0 and heir != "尚未新增成員":
        st.session_state["assets"].append({"type": asset_type, "value": value, "heir": heir})

if st.session_state["assets"]:
    st.subheader("💰 資產清單")
    st.table(pd.DataFrame(st.session_state["assets"]))

# =============================
# Step 3: 傳承圖生成
# =============================
st.header("Step 3. 傳承圖")

if st.session_state["family"] and st.session_state["assets"]:
    dot = Digraph(format="png")
    dot.attr(rankdir="TB", size="8")

    # 家庭成員節點
    for f in st.session_state["family"]:
        dot.node(f["name"], f"{f['name']} ({f['relation']})", shape="ellipse", style="filled", color="lightgrey")

    # 資產節點與箭頭
    for idx, a in enumerate(st.session_state["assets"]):
        asset_label = f"{a['type']} | {a['value']:,}"
        node_id = f"asset{idx}"
        dot.node(node_id, asset_label, shape="box", style="filled", color="lightblue")
        dot.edge(node_id, a["heir"])

    st.graphviz_chart(dot)

    # =============================
    # Step 4: 公平性檢測
    # =============================
    df = pd.DataFrame(st.session_state["assets"])
    summary = df.groupby("heir")["value"].sum().reset_index()
    st.subheader("📊 分配總覽")
    summary["比例 (%)"] = summary["value"] / summary["value"].sum() * 100
    st.table(summary)

    # 公平性提示
    total = summary["value"].sum()
    for _, row in summary.iterrows():
        percent = row["value"] / total * 100
        if percent > 50:
            st.warning(f"⚠️ {row['heir']} 佔比 {percent:.1f}%，可能引起公平性疑慮")

    # =============================
    # Step 5: 匯出功能
    # =============================
    csv_buffer = io.StringIO()
    summary.to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 下載分配摘要 (CSV)",
        data=csv_buffer.getvalue(),
        file_name="inheritance_summary.csv",
        mime="text/csv"
    )

else:
    st.info("請先新增 **家庭成員** 與 **資產**，再生成傳承圖。")

# =============================
# 頁尾品牌資訊
# =============================
st.markdown("---")
st.markdown("""
《影響力》傳承策略平台｜永傳家族辦公室  
🌐 [gracefo.com](https://gracefo.com)  
📩 聯絡信箱：123@gracefo.com
""")
