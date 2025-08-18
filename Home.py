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
st.markdown("這是傳承規劃的第一步：**盤點人 & 盤點資產 → 自動生成傳承圖**（依《民法》第1138、1140、1144 條計算）")

# =============================
# Demo（已用您指定的姓名，並標示現任配偶）
# =============================
DEMO_FAMILY = [
    {"name": "陳志明", "relation": "本人",       "age": 65, "alive": True,  "partner": "",       "child_type": "",           "parent": ""},
    {"name": "王春嬌", "relation": "配偶(現任)", "age": 62, "alive": True,  "partner": "",       "child_type": "",           "parent": ""},
    {"name": "陳小明", "relation": "子女",       "age": 35, "alive": True,  "partner": "",       "child_type": "親生",        "parent": ""},
    {"name": "陳小芳", "relation": "子女",       "age": 32, "alive": True,  "partner": "",       "child_type": "親生",        "parent": ""},
    # 範例：前配偶與與前配偶所生子女（若要測試，可解除註解）
    # {"name": "林美惠", "relation": "前配偶",     "age": 60, "alive": True,  "partner": "",       "child_type": "",           "parent": ""},
    # {"name": "陳小華", "relation": "子女",       "age": 30, "alive": True,  "partner": "",       "child_type": "親生",        "parent": ""},  # 視為本人之子女（與前配偶所生）
    # 代位繼承示例：子女亡故 + 其名下孫子女（parent 指向該子女）
    # {"name": "陳小明", "relation": "子女",       "age": 35, "alive": False, "partner": "",       "child_type": "親生",        "parent": ""},
    # {"name": "阿明之子", "relation": "孫子",     "age": 6,  "alive": True,  "partner": "",       "child_type": "親生",        "parent": "陳小明"},
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
# 常數與工具
# =============================
REL_OPTIONS = ["本人", "配偶(現任)", "前配偶", "父親", "母親", "祖父", "祖母", "子女", "孫子", "孫女", "兄弟", "姊妹", "其他"]
CHILD_TYPES = ["（不適用）", "親生", "非婚生已認領", "收養", "繼子女(未收養)"]  # 具第一順位資格：親生、非婚生已認領、收養

def get_member(name: str):
    for m in st.session_state["family"]:
        if m["name"] == name:
            return m
    return None

def list_names_by_relation(rel: str, alive_only=True):
    return [m["name"] for m in st.session_state["family"] if m["relation"] == rel and (m.get("alive", True) or not alive_only)]

def eligible_child(m):
    """子女是否具第一順位資格"""
    return m["relation"] == "子女" and m.get("child_type") in ["親生", "非婚生已認領", "收養"]

def current_spouse_for(core_rel: str):
    # 目前僅處理「本人」的現任配偶
    if core_rel == "本人":
        cands = list_names_by_relation("配偶(現任)")
        return cands[0] if cands else None
    return None

def compute_heirs_by_law(core_name: str):
    """
    依 1138（順位）、1140（代位）、1144（配偶應繼分）計算。
    完整支援：以「本人」為被繼承人之情境（含代位、多伴侶、多型態子女）。
    """
    heirs, notes = {}, []
    core = get_member(core_name)
    if not core:
        return heirs, ["找不到被繼承人"]

    spouse = current_spouse_for(core.get("relation",""))

    # ---- 第一順位：直系卑親屬（子女；子女亡故 → 孫輩代位）----
    children_alive = [m for m in st.session_state["family"] if eligible_child(m) and m.get("alive", True)]
    children_dead  = [m for m in st.session_state["family"] if eligible_child(m) and not m.get("alive", True)]

    branches = []       # 每位合格子女形成一個分支；亡故者由其孫輩代位承受該分支
    branch_members = [] # 分支中實際承受者名單（子女本人或其存活之孫輩）

    for c in children_alive:
        branches.append(c["name"])
        branch_members.append([c["name"]])

    for d in children_dead:
        reps = [m["name"] for m in st.session_state["family"]
                if m["relation"] in ["孫子", "孫女"] and m.get("alive", True) and m.get("parent","") == d["name"]]
        if reps:
            branches.append(d["name"] + "_branch")
            branch_members.append(reps)

    if branches:
        denom = len(branches) + (1 if spouse else 0)
        if denom == 0:
            return heirs, ["資料不足無法計算"]
        branch_share = 1.0 / denom
        if spouse:
            heirs[spouse] = heirs.get(spouse, 0) + (1.0 / denom)
        for members in branch_members:
            if len(members) == 1:
                heirs[members[0]] = heirs.get(members[0], 0) + branch_share
            else:
                per = branch_share / len(members)
                for who in members:
                    heirs[who] = heirs.get(who, 0) + per
        notes.append("第一順位成立：子女（含非婚生已認領、收養）。亡故子女由其直系卑親屬代位；配偶與第一順位平均（§1144 I）。")
        return heirs, notes

    # ---- 第二順位：父母 ----
    parents = [n for n in list_names_by_relation("父親") + list_names_by_relation("母親")]
    if parents:
        if spouse:
            heirs[spouse] = heirs.get(spouse, 0) + 0.5
            per = 0.5 / len(parents)
            for p in parents:
                heirs[p] = heirs.get(p, 0) + per
            notes.append("第二順位成立：父母。配偶 1/2，父母均分 1/2（§1144 II）。")
        else:
            per = 1.0 / len(parents)
            for p in parents:
                heirs[p] = heirs.get(p, 0) + per
            notes.append("第二順位成立：父母均分。")
        return heirs, notes

    # ---- 第三順位：兄弟姊妹 ----
    siblings = [n for n in list_names_by_relation("兄弟") + list_names_by_relation("姊妹")]
    if siblings:
        if spouse:
            heirs[spouse] = heirs.get(spouse, 0) + 0.5
            per = 0.5 / len(siblings)
            for s in siblings:
                heirs[s] = heirs.get(s, 0) + per
            notes.append("第三順位成立：兄弟姊妹。配偶 1/2，兄弟姊妹均分 1/2（§1144 II）。")
        else:
            per = 1.0 / len(siblings)
            for s in siblings:
                heirs[s] = heirs.get(s, 0) + per
            notes.append("第三順位成立：兄弟姊妹均分。")
        return heirs, notes

    # ---- 第四順位：祖父母 ----
    grands = [n for n in list_names_by_relation("祖父") + list_names_by_relation("祖母")]
    if grands:
        if spouse:
            heirs[spouse] = heirs.get(spouse, 0) + (2.0/3.0)
            per = (1.0/3.0) / len(grands)
            for g in grands:
                heirs[g] = heirs.get(g, 0) + per
            notes.append("第四順位成立：祖父母。配偶 2/3，祖父母均分 1/3（§1144 III）。")
        else:
            per = 1.0 / len(grands)
            for g in grands:
                heirs[g] = heirs.get(g, 0) + per
            notes.append("第四順位成立：祖父母均分。")
        return heirs, notes

    # ---- 無第一至四順位 ----
    if spouse:
        heirs[spouse] = heirs.get(spouse, 0) + 1.0
        notes.append("無第1-4順位，配偶取得全部（§1144 IV）。")
    else:
        notes.append("無第1-4順位與配偶：本工具不處理歸公庫情形。")
    return heirs, notes

# =============================
# 快捷操作：重置／載入示範（JSON 下載移到進階）
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

with st.expander("⚙️ 進階功能（可選）"):
    scenario = {"family": st.session_state["family"], "assets": st.session_state["assets"]}
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
    df_family = pd.DataFrame(st.session_state["family"])
    st.table(df_family)

    # 刪除成員
    del_name = st.selectbox("選擇要刪除的成員", [""] + [f["name"] for f in st.session_state["family"]])
    if del_name and st.button("❌ 刪除成員"):
        st.session_state["family"] = [f for f in st.session_state["family"] if f["name"] != del_name]
        st.success(f"已刪除成員：{del_name}")
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
    df_assets = pd.DataFrame(st.session_state["assets"])
    st.table(df_assets)

    label_choices = [""] + [f"{i}｜{a['type']}｜{a['value']:,}" for i, a in enumerate(st.session_state["assets"])]
    chosen = st.selectbox("選擇要刪除的資產", label_choices)
    if chosen and st.button("❌ 刪除資產"):
        idx = int(chosen.split("｜", 1)[0])
        removed = st.session_state["assets"].pop(idx)
        st.success(f"已刪除資產：{removed['type']} (金額 {removed['value']:,})")
else:
    st.info("尚無資產，請先新增。")

# =============================
# Step 3: 法定繼承人自動判定
# =============================
st.header("Step 3. 法定繼承人自動判定（民法）")

all_names = [m["name"] for m in st.session_state["family"]]
default_core = [m["name"] for m in st.session_state["family"] if m["relation"] == "本人"]
core_name = st.selectbox("選擇被繼承人（核心人物）", default_core + [n for n in all_names if n not in default_core])

heirs, law_notes = compute_heirs_by_law(core_name)

if heirs:
    df_heirs = pd.DataFrame(
        [{"繼承人": k, "比例(%)": round(v * 100, 2)} for k, v in sorted(heirs.items(), key=lambda x: -x[1])]
    )
    st.subheader("📑 法定繼承名單與比例")
    st.table(df_heirs)
else:
    st.info("目前無可計算之法定繼承人（請檢查成員關係、子女類型與在世狀態）。")

for n in law_notes:
    st.caption("📌 " + n)

# =============================
# Step 4: 傳承圖（高亮本人、標示法定繼承人）
# =============================
st.header("Step 4. 傳承圖")

if st.session_state["family"]:
    dot = Digraph(format="png")
    dot.attr(rankdir="TB", size="8")

    heirs_set = set(heirs.keys())

    for f in st.session_state["family"]:
        name = f["name"]
        rel = f.get("relation", "")
        alive = f.get("alive", True)

        style = "filled"
        fillcolor = "lightgrey"
        color = "black"
        penwidth = "1"

        if rel == "本人":
            fillcolor = "khaki"
            penwidth = "2"

        if name in heirs_set:
            color = "darkgreen"
            penwidth = "3"

        label = f"{name} ({rel}{'' if alive else '・不在世'})"
        dot.node(name, label, shape="ellipse", style=style, fillcolor=fillcolor, color=color, penwidth=penwidth)

    # 現況規劃資產流向（非法律分配）
    for idx, a in enumerate(st.session_state["assets"]):
        asset_label = f"{a['type']} | {a['value']:,}"
        node_id = f"asset{idx}"
        dot.node(node_id, asset_label, shape="box", style="filled", fillcolor="lightblue")
        dot.edge(node_id, a["heir"])

    st.graphviz_chart(dot)
else:
    st.info("請先新增 **家庭成員**。")

# =============================
# Step 5: 匯出法定繼承比例（CSV）
# =============================
if heirs:
    csv_buffer = io.StringIO()
    pd.DataFrame(
        [{"繼承人": k, "比例(%)": round(v * 100, 2)} for k, v in sorted(heirs.items(), key=lambda x: -x[1])]
    ).to_csv(csv_buffer, index=False)
    st.download_button(
        label="📥 下載法定繼承比例 (CSV)",
        data=csv_buffer.getvalue(),
        file_name=f"heirs_{core_name}.csv",
        mime="text/csv"
    )

st.markdown("---")
st.markdown("""
《影響力》傳承策略平台｜永傳家族辦公室  
🌐 gracefo.com  
📩 聯絡信箱：123@gracefo.com
""")
