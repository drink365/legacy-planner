import streamlit as st
import pandas as pd
from graphviz import Digraph
import io
import json

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
DEMO_FAMILY = [
    {"name": "陳志明", "relation": "父親", "age": 65},
    {"name": "王春嬌", "relation": "母親", "age": 62},
    {"name": "陳小明", "relation": "子女", "age": 35},
    {"name": "陳小芳", "relation": "子女", "age": 32}
]

DEMO_ASSETS = [
    {"type": "公司股權", "value": 100_000_000, "heir": "陳小明"},
    {"type": "不動產", "value": 50_000_000, "heir": "陳小芳"},
    {"type": "保單",   "value": 30_000_000, "heir": "王春嬌"}
]

# =============================
# 初始化 Session State
# =============================
if "family" not in st.session_state:
    st.session_state["family"] = DEMO_FAMILY.copy()
if "assets" not in st.session_state:
    st.session_state["assets"] = DEMO_ASSETS.copy()

# =============================
# 快捷操作列：重置／載入示範／匯出JSON
# =============================
ops_col1, ops_col2, ops_col3 = st.columns([1,1,2])

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

with ops_col3:
    scenario = {
        "family": st.session_state["family"],
        "assets": st.session_state["assets"]
    }
    json_bytes = json.dumps(scenario, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        label="📥 下載目前情境（JSON）",
        data=json_bytes,
        file_name="legacy_scenario.json",
        mime="application/json",
        use_container_width=True
    )

st.markdown("---")

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
    df_family = pd.DataFrame(st.session_state["family"])
    st.table(df_family)

    # 刪除成員
    delete_member = st.selectbox("選擇要刪除的成員", [""] + [f["name"] for f in st.session_state["family"]])
    if delete_member and st.button("❌ 刪除成員"):
        st.session_state["family"] = [f for f in st.session_state["family"] if f["name"] != delete_member]
        st.success(f"已刪除成員：{delete_member}")
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
        heir = st.selectbox("分配給", members if members else ["尚未新增成員"])

    submitted_asset = st.form_submit_button("➕ 新增資產")
    if submitted_asset and value > 0 and heir != "尚未新增成員":
        st.session_state["assets"].append({"type": asset_type, "value": value, "heir": heir})

if st.session_state["assets"]:
    st.subheader("💰 資產清單")
    df_assets = pd.DataFrame(st.session_state["assets"])
    st.table(df_assets)

    # 刪除資產
    delete_asset_idx = st.selectbox("選擇要刪除的資產", [""] + list(range(len(st.session_state["assets"]))))
    if delete_asset_idx != "" and st.button("❌ 刪除資產"):
        removed = st.session_state["assets"].pop(int(delete_asset_idx))
        st.success(f"已刪除資產：{removed['type']} (金額 {removed['value']:,})")
else:
    st.info("尚無資產，請先新增。")

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

    total = summary["value"].sum()
    for _, row in summary.iterrows():
        percent = row["value"] / total * 100
        if percent > 50:
            st.warning(f"⚠️ {row['heir']} 佔比 {percent:.1f}%，可能引起公平性疑慮")

    # =============================
    # Step 5: 匯出功能（CSV）
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
🌐 gracefo.com  
📩 聯絡信箱：123@gracefo.com
""")
