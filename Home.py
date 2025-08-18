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
st.markdown("這是傳承規劃的第一步：**盤點人 & 盤點資產 → 自動生成傳承圖**（依《民法》第1138條與第1144條計算）")

# =============================
# Demo 資料（您指定的人名）
# =============================
DEMO_FAMILY = [
    {"name": "陳志明", "relation": "本人", "age": 65, "alive": True, "parent": ""},
    {"name": "王春嬌", "relation": "配偶", "age": 62, "alive": True, "parent": ""},
    {"name": "陳小明", "relation": "子女", "age": 35, "alive": True, "parent": ""},
    {"name": "陳小芳", "relation": "子女", "age": 32, "alive": True, "parent": ""},
    # 若要示範代位繼承，可把某位子女 alive 改為 False，並新增其名下孫輩（parent 指向該子女）
    # {"name": "陳小華", "relation": "子女", "age": 30, "alive": False, "parent": ""},
    # {"name": "陳小華之子", "relation": "孫子", "age": 5, "alive": True, "parent": "陳小華"},
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
# 工具函式
# =============================
REL_OPTIONS = ["本人", "配偶", "父親", "母親", "祖父", "祖母", "子女", "孫子", "孫女", "兄弟", "姊妹", "其他"]

def get_member(name: str):
    for m in st.session_state["family"]:
        if m["name"] == name:
            return m
    return None

def list_names_by_relation(rel: str, alive_only=True):
    res = [m["name"] for m in st.session_state["family"] if m["relation"] == rel and (m.get("alive", True) or not alive_only)]
    return res

def choose_spouse_for_core(core_rel: str):
    # 簡化邏輯：以常見場景對應
    if core_rel == "本人":
        return list_names_by_relation("配偶")
    if core_rel == "父親":
        return list_names_by_relation("母親")
    if core_rel == "母親":
        return list_names_by_relation("父親")
    # 其他關係無法從「本人相對關係」安全推導
    return []

def compute_statutory_heirs(core_name: str):
    """
    依《民法》第1138條（順位）＋第1140條（第一順位之代位）＋第1144條（配偶應繼分）計算。
    目前完整支援：以「本人」為被繼承人。
    若核心人物非本人，僅嘗試以可推導之關係估算（可能不含代位），並顯示提醒。
    回傳：heirs: {name: share_ratio_float_0_to_1}, notes: [str]
    """
    notes = []
    heirs = {}
    core = get_member(core_name)
    if not core:
        return heirs, ["找不到被繼承人"]

    # 找配偶
    spouse_candidates = choose_spouse_for_core(core.get("relation", ""))
    spouse_alive = [n for n in spouse_candidates if get_member(n) and get_member(n).get("alive", True)]
    spouse_name = spouse_alive[0] if spouse_alive else None

    # 以核心人物為「本人」情境：可精準計算代位
    if core.get("relation") == "本人":
        # 第一順位：直系卑親屬（子女；子女死亡或喪失繼承權，孫輩代位）
        children_alive = [m for m in st.session_state["family"] if m["relation"] == "子女" and m.get("alive", True)]
        children_dead = [m for m in st.session_state["family"] if m["relation"] == "子女" and not m.get("alive", True)]

        # 代位：以「parent == 該子女姓名」承接，僅處理一層（孫子女）
        branches = []  # 每一個 child-branch 為一份
        branch_members = []  # 與 branches 同長度：每個分支中的實際承受者名單
        # 活著的子女各自成一個分支
        for c in children_alive:
            branches.append(c["name"])
            branch_members.append([c["name"]])

        # 已亡子女 → 由其名下孫輩（alive）平分該分支
        for d in children_dead:
            reps = [m["name"] for m in st.session_state["family"]
                    if m["relation"] in ["孫子", "孫女"] and m.get("alive", True) and m.get("parent", "") == d["name"]]
            if reps:
                branches.append(d["name"] + "_branch")
                branch_members.append(reps)

        # 決定是否有第一順位
        has_first_order = len(branches) > 0

        if has_first_order:
            # 配偶與第一順位平均（1144 I）
            denom = len(branches) + (1 if spouse_name else 0)
            if denom == 0:
                return heirs, ["資料不足無法計算"]

            # 每個子女分支所占比例
            branch_share = 1.0 / denom
            # 配偶
            if spouse_name:
                heirs[spouse_name] = heirs.get(spouse_name, 0) + (1.0 / denom)

            # 分支內部分配（代位）
            for members in branch_members:
                if len(members) == 1:
                    heirs[members[0]] = heirs.get(members[0], 0) + branch_share
                else:
                    # 同一分支孫輩平分
                    per = branch_share / len(members)
                    for who in members:
                        heirs[who] = heirs.get(who, 0) + per

            notes.append("依第1138條：第一順位（直系卑親屬）。依第1144條：配偶與第一順位平均。若有亡故子女，依第1140條由其直系卑親屬（孫輩）代位。")
            return heirs, notes

        # 沒有第一順位 → 檢視第二順位：父母
        parents_alive = [n for n in list_names_by_relation("父親") + list_names_by_relation("母親")]
        if parents_alive:
            if spouse_name:
                # 配偶 1/2，其餘父母均分 1/2（1144 II）
                heirs[spouse_name] = heirs.get(spouse_name, 0) + 0.5
                per = 0.5 / len(parents_alive)
                for p in parents_alive:
                    heirs[p] = heirs.get(p, 0) + per
                notes.append("第二順位（父母）。依第1144條：配偶 1/2，其餘由父母均分 1/2。")
            else:
                per = 1.0 / len(parents_alive)
                for p in parents_alive:
                    heirs[p] = heirs.get(p, 0) + per
                notes.append("第二順位（父母）。無配偶，共同繼承人均分。")
            return heirs, notes

        # 沒有父母 → 第三順位：兄弟姊妹（不處理其代位）
        siblings_alive = [n for n in list_names_by_relation("兄弟") + list_names_by_relation("姊妹")]
        if siblings_alive:
            if spouse_name:
                heirs[spouse_name] = heirs.get(spouse_name, 0) + 0.5
                per = 0.5 / len(siblings_alive)
                for s in siblings_alive:
                    heirs[s] = heirs.get(s, 0) + per
                notes.append("第三順位（兄弟姊妹）。依第1144條：配偶 1/2，其餘由兄弟姊妹均分 1/2。")
            else:
                per = 1.0 / len(siblings_alive)
                for s in siblings_alive:
                    heirs[s] = heirs.get(s, 0) + per
                notes.append("第三順位（兄弟姊妹）。無配偶，共同繼承人均分。")
            return heirs, notes

        # 無兄弟姊妹 → 第四順位：祖父母（不分內外）
        grands_alive = [n for n in list_names_by_relation("祖父") + list_names_by_relation("祖母")]
        if grands_alive:
            if spouse_name:
                heirs[spouse_name] = heirs.get(spouse_name, 0) + (2.0 / 3.0)
                per = (1.0 / 3.0) / len(grands_alive)
                for g in grands_alive:
                    heirs[g] = heirs.get(g, 0) + per
                notes.append("第四順位（祖父母）。依第1144條：配偶 2/3，祖父母均分 1/3。")
            else:
                per = 1.0 / len(grands_alive)
                for g in grands_alive:
                    heirs[g] = heirs.get(g, 0) + per
                notes.append("第四順位（祖父母）。無配偶，共同繼承人均分。")
            return heirs, notes

        # 若第1-4順位均無 → 配偶全拿；再無則（法律上歸公庫，這裡不處理）
        if spouse_name:
            heirs[spouse_name] = heirs.get(spouse_name, 0) + 1.0
            notes.append("無第1-4順位繼承人，配偶取得全部（1144 IV）。")
        else:
            notes.append("無第1-4順位與配偶：本工具不處理歸公庫情形。")
        return heirs, notes

    # 若核心人物非「本人」：提示限制並盡力估算
    notes.append("目前版本以『本人』為被繼承人可完整計算代位。您選擇的核心人物非『本人』，將以可推導親屬（配偶、子女、父母、兄弟姊妹、祖父母）做近似估算，可能不含代位。")
    # 嘗試以常見對應估算第一順位（以『本人』視角逆推）
    # 例如核心=父親 → 第一順位= 本人 + 兄弟姊妹； 配偶=母親
    rel = core.get("relation", "")
    approx_children = []
    if rel in ["父親", "母親"]:
        approx_children = [n for n in list_names_by_relation("子女")] + [n for n in list_names_by_relation("兄弟")] + [n for n in list_names_by_relation("姊妹")]
    elif rel in ["子女"]:
        # 其子女= 孫輩，需以 parent 對應
        approx_children = [m["name"] for m in st.session_state["family"] if m["relation"] in ["孫子", "孫女"] and m.get("parent", "") == core_name and m.get("alive", True)]
    else:
        approx_children = []

    approx_children = [n for n in approx_children if get_member(n) and get_member(n).get("alive", True)]
    if approx_children:
        denom = len(approx_children) + (1 if spouse_name else 0)
        share = 1.0 / denom if denom else 0
        if spouse_name:
            heirs[spouse_name] = heirs.get(spouse_name, 0) + share
        for c in approx_children:
            heirs[c] = heirs.get(c, 0) + share
        notes.append("以近似方式視為有第一順位：配偶與子女平均。")
        return heirs, notes

    # 否則退回檢視父母、兄弟姊妹、祖父母
    parents = []
    if rel in ["子女"]:
        parents = [n for n in list_names_by_relation("本人")]  # 若有標記『本人』即為其父/母之一；此近似不嚴謹
    parents += [n for n in list_names_by_relation("父親")] + [n for n in list_names_by_relation("母親")]
    parents = [n for n in parents if get_member(n) and get_member(n).get("alive", True)]
    if parents:
        if spouse_name:
            heirs[spouse_name] = heirs.get(spouse_name, 0) + 0.5
            per = 0.5 / len(parents)
            for p in parents:
                heirs[p] = heirs.get(p, 0) + per
            notes.append("近似第二順位：配偶 1/2，其餘父母均分。")
        else:
            per = 1.0 / len(parents)
            for p in parents:
                heirs[p] = heirs.get(p, 0) + per
            notes.append("近似第二順位：無配偶，父母均分。")
        return heirs, notes

    siblings = [n for n in list_names_by_relation("兄弟")] + [n for n in list_names_by_relation("姊妹")]
    siblings = [n for n in siblings if get_member(n) and get_member(n).get("alive", True)]
    if siblings:
        if spouse_name:
            heirs[spouse_name] = heirs.get(spouse_name, 0) + 0.5
            per = 0.5 / len(siblings)
            for s in siblings:
                heirs[s] = heirs.get(s, 0) + per
            notes.append("近似第三順位：配偶 1/2，兄弟姊妹均分 1/2。")
        else:
            per = 1.0 / len(siblings)
            for s in siblings:
                heirs[s] = heirs.get(s, 0) + per
            notes.append("近似第三順位：無配偶，兄弟姊妹均分。")
        return heirs, notes

    grands = [n for n in list_names_by_relation("祖父")] + [n for n in list_names_by_relation("祖母")]
    grands = [n for n in grands if get_member(n) and get_member(n).get("alive", True)]
    if grands:
        if spouse_name:
            heirs[spouse_name] = heirs.get(spouse_name, 0) + (2.0/3.0)
            per = (1.0/3.0) / len(grands)
            for g in grands:
                heirs[g] = heirs.get(g, 0) + per
            notes.append("近似第四順位：配偶 2/3，祖父母均分 1/3。")
        else:
            per = 1.0 / len(grands)
            for g in grands:
                heirs[g] = heirs.get(g, 0) + per
            notes.append("近似第四順位：無配偶，祖父母均分。")
        return heirs, notes

    if spouse_name:
        heirs[spouse_name] = heirs.get(spouse_name, 0) + 1.0
        notes.append("無第1-4順位，配偶取得全部。")
    else:
        notes.append("無可推導之繼承人，本工具不處理歸公庫。")
    return heirs, notes

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
    cols = st.columns(5)
    with cols[0]:
        name = st.text_input("姓名")
    with cols[1]:
        relation = st.selectbox("關係", REL_OPTIONS, index=REL_OPTIONS.index("子女") if "子女" in REL_OPTIONS else 0)
    with cols[2]:
        age = st.number_input("年齡", min_value=0, max_value=120, step=1)
    with cols[3]:
        alive = st.checkbox("在世", value=True)
    with cols[4]:
        parent = ""
        if relation in ["孫子", "孫女"]:
            # 指定其父/母（必須是「子女」）
            candidates = list_names_by_relation("子女", alive_only=False)
            parent = st.selectbox("其父/母（所屬子女）", [""] + candidates)
        else:
            st.write("　")

    submitted = st.form_submit_button("➕ 新增成員")
    if submitted and name:
        st.session_state["family"].append({"name": name, "relation": relation, "age": age, "alive": alive, "parent": parent})

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
        heir = st.selectbox("目前規劃分配給", members if members else ["尚未新增成員"])

    submitted_asset = st.form_submit_button("➕ 新增資產")
    if submitted_asset and value > 0 and heir != "尚未新增成員":
        st.session_state["assets"].append({"type": asset_type, "value": value, "heir": heir})

if st.session_state["assets"]:
    st.subheader("💰 資產清單")
    df_assets = pd.DataFrame(st.session_state["assets"])
    st.table(df_assets)

    # 刪除資產（以清單索引顯示類型與金額，較直覺）
    label_choices = [""] + [f"{i}｜{a['type']}｜{a['value']:,}" for i, a in enumerate(st.session_state["assets"])]
    choice = st.selectbox("選擇要刪除的資產", label_choices)
    if choice and st.button("❌ 刪除資產"):
        idx = int(choice.split("｜", 1)[0])
        removed = st.session_state["assets"].pop(idx)
        st.success(f"已刪除資產：{removed['type']} (金額 {removed['value']:,})")
else:
    st.info("尚無資產，請先新增。")

# =============================
# Step 3: 以民法自動判定法定繼承人（1138, 1140, 1144）
# =============================
st.header("Step 3. 法定繼承人自動判定（民法）")

all_names = [m["name"] for m in st.session_state["family"]]
default_core = list_names_by_relation("本人", alive_only=False)
core_name = st.selectbox("選擇被繼承人（核心人物）", default_core + [n for n in all_names if n not in default_core])

heirs, law_notes = compute_statutory_heirs(core_name)

if heirs:
    df_heirs = pd.DataFrame([
        {"繼承人": k, "比例(%)": round(v * 100, 2)}
        for k, v in sorted(heirs.items(), key=lambda x: -x[1])
    ])
    st.subheader("📑 法定繼承名單與比例")
    st.table(df_heirs)
else:
    st.info("目前無可計算之法定繼承人（請檢查成員關係與在世狀態）。")

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

    # 成員節點：本人高亮；法定繼承人描邊加粗
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

    # 資產節點與箭頭（展示規劃現況，非法律分配）
    for idx, a in enumerate(st.session_state["assets"]):
        asset_label = f"{a['type']} | {a['value']:,}"
        node_id = f"asset{idx}"
        dot.node(node_id, asset_label, shape="box", style="filled", fillcolor="lightblue")
        dot.edge(node_id, a["heir"])

    st.graphviz_chart(dot)
else:
    st.info("請先新增 **家庭成員**。")

# =============================
# Step 5: 匯出摘要
# =============================
if heirs:
    csv_buffer = io.StringIO()
    df_export = pd.DataFrame([
        {"繼承人": k, "比例(%)": round(v * 100, 2)}
        for k, v in sorted(heirs.items(), key=lambda x: -x[1])
    ])
    df_export.to_csv(csv_buffer, index=False)
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
