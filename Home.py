import streamlit as st
import pandas as pd
from graphviz import Digraph

# =============================
# 頁面設定
# =============================
st.set_page_config(
    page_title="📦 家族盤點｜傳承圖（世代樹）",
    page_icon="📦",
    layout="wide"
)

st.title("📦 家族盤點｜傳承圖（世代樹）")
st.markdown("第一步：**盤點家族成員**與**各自的資產**。本頁不做分配與繼承比例，只專注於盤點與關係圖。")

# =============================
# Demo 資料（您指定的人名）
# =============================
DEMO_FAMILY = [
    {"name": "陳志明", "relation": "本人",       "age": 65, "alive": True,  "father": "",       "mother": ""},
    {"name": "王春嬌", "relation": "配偶(現任)", "age": 62, "alive": True,  "father": "",       "mother": ""},
    {"name": "陳小明", "relation": "子女",       "age": 35, "alive": True,  "father": "陳志明", "mother": "王春嬌"},
    {"name": "陳小芳", "relation": "子女",       "age": 32, "alive": True,  "father": "陳志明", "mother": "王春嬌"},
]
DEMO_ASSETS = [
    {"owner": "陳志明", "type": "公司股權", "value": 100_000_000, "note": ""},
    {"owner": "陳志明", "type": "不動產",   "value": 50_000_000,  "note": "台北市某處"},
    {"owner": "王春嬌", "type": "保單",     "value": 30_000_000,  "note": ""},
    {"owner": "陳小明", "type": "金融資產", "value": 10_000_000,  "note": ""},
]

# =============================
# 初始化 Session State
# =============================
if "family" not in st.session_state:
    st.session_state["family"] = DEMO_FAMILY.copy()
if "assets" not in st.session_state:
    st.session_state["assets"] = DEMO_ASSETS.copy()
if "unions" not in st.session_state:
    # 伴侶關係清單：每筆 {"a":姓名, "b":姓名, "type":"現任配偶" 或 "前配偶" 或 "伴侶"}
    st.session_state["unions"] = []

# ----------------- 小工具 -----------------
REL_OPTIONS = [
    "本人", "配偶(現任)", "前配偶",
    "父親", "母親",
    "祖父", "祖母",
    "兄弟", "姊妹",
    "子女", "子女之配偶",   # 新增：第二代配偶
    "孫子", "孫女", "孫輩之配偶",  # 選填：若要放第三代配偶
    "其他"
]

# 世代分層（單純為排版；若要更準確可改用 BFS 推算）
GEN_BY_REL = {
    "祖父": -2, "祖母": -2,
    "父親": -1, "母親": -1,
    "本人": 0, "配偶(現任)": 0, "前配偶": 0, "兄弟": 0, "姊妹": 0, "其他": 0,
    "子女": 1, "子女之配偶": 1,
    "孫子": 2, "孫女": 2, "孫輩之配偶": 2,
}
def get_generation(rel: str) -> int:
    return GEN_BY_REL.get(rel, 0)

def normalize(s: str) -> str:
    return s.strip() if isinstance(s, str) else s

def name_exists(n: str) -> bool:
    return any(m["name"] == n for m in st.session_state["family"])

def pair_key(a: str, b: str):
    if not a or not b: return None
    a, b = normalize(a), normalize(b)
    return tuple(sorted([a, b])) if a != b else None

# =============================
# 快捷操作：重置／載入示範
# =============================
c1, c2 = st.columns(2)
with c1:
    if st.button("🔄 重置（清空目前資料）", use_container_width=True):
        st.session_state["family"] = []
        st.session_state["assets"] = []
        st.session_state["unions"] = []
        st.success("已清空資料。請開始新增家族成員、伴侶關係與資產。")
with c2:
    if st.button("🧪 載入示範資料", use_container_width=True):
        st.session_state["family"] = DEMO_FAMILY.copy()
        st.session_state["assets"] = DEMO_ASSETS.copy()
        st.session_state["unions"] = []
        st.info("已載入示範資料。")

st.markdown("---")

# =============================
# Step 1: 家族成員
# =============================
st.header("Step 1. 家族成員")

all_names = [m["name"] for m in st.session_state["family"]]

with st.form("add_family"):
    cols = st.columns(7)
    with cols[0]:
        name = st.text_input("姓名")
    with cols[1]:
        relation = st.selectbox("關係", REL_OPTIONS, index=REL_OPTIONS.index("子女"))
    with cols[2]:
        age = st.number_input("年齡", min_value=0, max_value=120, step=1)
    with cols[3]:
        alive = st.checkbox("在世", value=True)
    with cols[4]:
        father = st.selectbox("父親（可留空）", [""] + all_names)
    with cols[5]:
        mother = st.selectbox("母親（可留空）", [""] + all_names)
    with cols[6]:
        st.write("")  # 佔位

    submitted = st.form_submit_button("➕ 新增成員")

    if submitted:
        name   = normalize(name)
        father = normalize(father)
        mother = normalize(mother)
        if not name:
            st.error("請輸入姓名。")
        elif name_exists(name):
            st.error(f"成員「{name}」已存在，為避免混淆請改用不同名稱（或加註稱謂）。")
        elif relation in ["子女", "孫子", "孫女"] and (not father and not mother):
            st.error("子女/孫輩至少需指定一位父或母，才能正確掛在家族樹下。")
        else:
            st.session_state["family"].append({
                "name": name,
                "relation": relation,
                "age": age,
                "alive": alive,
                "father": father,
                "mother": mother
            })
            st.success(f"已新增：{name}")

if st.session_state["family"]:
    st.subheader("👨‍👩‍👧 家庭成員清單")
    df_family = pd.DataFrame(st.session_state["family"])
    display_cols = ["name", "relation", "age", "alive", "father", "mother"]
    df_family = df_family.reindex(columns=[c for c in display_cols if c in df_family.columns])
    st.table(df_family)

    # 刪除成員（會清理他人 father/mother 指向；同時清理伴侶配對）
    del_name = st.selectbox("選擇要刪除的成員", [""] + [f["name"] for f in st.session_state["family"]])
    if del_name and st.button("❌ 刪除成員"):
        del_name_norm = normalize(del_name)
        affected = 0
        for m in st.session_state["family"]:
            changed = False
            if normalize(m.get("father", "")) == del_name_norm:
                m["father"] = ""; changed = True
            if normalize(m.get("mother", "")) == del_name_norm:
                m["mother"] = ""; changed = True
            if changed: affected += 1
        # 清理配對
        st.session_state["unions"] = [u for u in st.session_state["unions"]
                                      if del_name_norm not in (normalize(u["a"]), normalize(u["b"]))]
        # 刪除本人
        st.session_state["family"] = [f for f in st.session_state["family"] if normalize(f["name"]) != del_name_norm]
        st.warning(f"已刪除成員：{del_name}。提醒：有 {affected} 位成員的父/母欄位已自動清空，並同步移除相關的伴侶關係。")
else:
    st.info("尚無家庭成員，請先新增。")

# =============================
# Step 1b: 伴侶關係（可建立第二代配偶）
# =============================
st.header("Step 1b. 伴侶關係（含第二代配偶）")

member_names = [m["name"] for m in st.session_state["family"]]
with st.form("add_union"):
    c = st.columns(4)
    with c[0]:
        ua = st.selectbox("成員 A", member_names if member_names else ["（請先新增成員）"])
    with c[1]:
        ub = st.selectbox("成員 B", member_names if member_names else ["（請先新增成員）"])
    with c[2]:
        utype = st.selectbox("關係類型", ["現任配偶", "前配偶", "伴侶"])
    with c[3]:
        submitted_u = st.form_submit_button("➕ 新增配對")

    if submitted_u:
        if not member_names or ua == "（請先新增成員）" or ub == "（請先新增成員）":
            st.error("請先新增成員，再建立配對。")
        else:
            key = pair_key(ua, ub)
            if not key:
                st.error("成員 A 與成員 B 需為兩位不同的人。")
            elif any(pair_key(u["a"], u["b"]) == key for u in st.session_state["unions"]):
                st.error("這兩位的配對已存在。")
            else:
                st.session_state["unions"].append({"a": key[0], "b": key[1], "type": utype})
                st.success(f"已建立配對：{key[0]} ↔ {key[1]}（{utype}）")

if st.session_state["unions"]:
    st.subheader("💞 伴侶關係清單")
    st.table(pd.DataFrame(st.session_state["unions"]))
    # 刪除配對
    label_pairs = [""] + [f"{i}｜{u['a']} ↔ {u['b']}｜{u['type']}" for i, u in enumerate(st.session_state["unions"])]
    chosen_pair = st.selectbox("選擇要刪除的配對", label_pairs)
    if chosen_pair and st.button("❌ 刪除配對"):
        idx = int(chosen_pair.split("｜", 1)[0])
        removed = st.session_state["unions"].pop(idx)
        st.success(f"已刪除配對：{removed['a']} ↔ {removed['b']}（{removed['type']}）")

st.markdown("---")

# =============================
# Step 2: 各自資產盤點（不做分配）
# =============================
st.header("Step 2. 各自資產盤點（不做分配）")

member_names = [f["name"] for f in st.session_state["family"]] if st.session_state["family"] else []
with st.form("add_asset"):
    cols = st.columns(4)
    with cols[0]:
        owner = st.selectbox("資產擁有者", member_names if member_names else ["（請先新增成員）"])
    with cols[1]:
        asset_type = st.selectbox("資產類別", ["公司股權", "不動產", "金融資產", "保單", "海外資產", "其他"])
    with cols[2]:
        value = st.number_input("金額 (TWD)", min_value=0, step=1_000_000)
    with cols[3]:
        note = st.text_input("備註（選填）")

    submitted_asset = st.form_submit_button("➕ 新增資產")
    if submitted_asset and member_names and owner != "（請先新增成員）" and value > 0:
        st.session_state["assets"].append({"owner": normalize(owner), "type": asset_type, "value": value, "note": note})
        st.success(f"已新增資產：{owner}｜{asset_type}｜{value:,}")

if st.session_state["assets"]:
    st.subheader("💰 資產清單（依筆列示）")
    st.table(pd.DataFrame(st.session_state["assets"]))
    df_assets = pd.DataFrame(st.session_state["assets"])
    by_owner = df_assets.groupby("owner")["value"].sum().reset_index().sort_values("value", ascending=False)
    by_owner.columns = ["擁有者", "合計金額"]
    st.subheader("📊 各成員資產合計")
    st.table(by_owner)

    labels = [""] + [f"{i}｜{a['owner']}｜{a['type']}｜{a['value']:,}" for i, a in enumerate(st.session_state["assets"])]
    chosen = st.selectbox("選擇要刪除的資產", labels)
    if chosen and st.button("❌ 刪除資產"):
        idx = int(chosen.split("｜", 1)[0])
        removed = st.session_state["assets"].pop(idx)
        st.success(f"已刪除資產：{removed['owner']}｜{removed['type']}｜{removed['value']:,}")
else:
    st.info("尚無資產，請先新增。")

# =============================
# Step 3: 家族樹（夫妻橫桿＋單一垂直幹線→子女）
# =============================
st.header("Step 3. 家族樹（世代清楚、上下分層）")

if st.session_state["family"]:
    dot = Digraph(format="png")
    # 直角線條、實線、較舒適的間距；預設不畫箭頭
    dot.attr(rankdir="TB", size="10", splines="ortho", nodesep="0.7", ranksep="1.1")
    dot.attr('edge', arrowhead='none')

    # 1) 分層（純排版用途）
    gens = {-2: [], -1: [], 0: [], 1: [], 2: [], 3: []}
    for m in st.session_state["family"]:
        gens.setdefault(get_generation(m.get("relation","")), []).append(m["name"])

    for g, names in sorted(gens.items()):
        if not names: 
            continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            for n in names:
                member = next((x for x in st.session_state["family"] if x["name"] == n), None)
                if not member: 
                    continue
                label = f"{member['name']} ({member['relation']}{'' if member.get('alive', True) else '・不在世'})"
                fill  = "khaki" if member["relation"] == "本人" else "lightgrey"
                s.node(member["name"], label, shape="ellipse", style="filled", fillcolor=fill)

    def norm(s): return s.strip() if isinstance(s, str) else ""
    existing = {m["name"] for m in st.session_state["family"]}

    # 2) 蒐集父母對：來自 (a) 伴侶關係清單 unions、(b) 由孩子的 father/mother 推導、(c) 本人 +「配偶(現任)」
    couple_pairs = set()
    # (a) unions
    for u in st.session_state["unions"]:
        key = pair_key(u["a"], u["b"])
        if key and key[0] in existing and key[1] in existing:
            couple_pairs.add(key)
    # (b) 有同時標父/母的孩子
    for m in st.session_state["family"]:
        f, mo = norm(m.get("father","")), norm(m.get("mother",""))
        key = pair_key(f, mo)
        if key and key[0] in existing and key[1] in existing:
            couple_pairs.add(key)
    # (c) 本人 + 現任配偶（保險起見）
    selfs = [x for x in st.session_state["family"] if x["relation"] == "本人"]
    if selfs:
        self_name = selfs[0]["name"]
        for sp in [x for x in st.session_state["family"] if x["relation"] == "配偶(現任)"]:
            couple_pairs.add(pair_key(self_name, sp["name"]))

    # 3) 建立：每對父母 => 夫妻橫桿 + 垂直幹線
    pair_to_trunk = {}  # frozenset({f, mo}) -> trunk_id
    for idx, pair in enumerate(sorted(couple_pairs)):
        f, mo = pair
        if not f or not mo: 
            continue
        union_id = f"U{idx}"      # 橫桿
        trunk_id = f"T{idx}"      # 垂直幹線（point）
        pair_to_trunk[frozenset(pair)] = trunk_id

        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(union_id, label="", shape="box",
                   width="0.8", height="0.02", fixedsize="true",
                   style="filled", fillcolor="black", color="black")
            s.edge(f,  union_id, weight="100")
            s.edge(union_id, mo, weight="100")

        dot.node(trunk_id, label="", shape="point", width="0.01")
        dot.edge(union_id, trunk_id, weight="50", minlen="2")

    # 4) 接子女：優先接到對應幹線；單親時若能「唯一配對」則接該幹線，否則單親直連
    for m in st.session_state["family"]:
        child = m["name"]
        f, mo = norm(m.get("father","")), norm(m.get("mother",""))
        f_ok, mo_ok = f in existing and f, mo in existing and mo

        if f_ok and mo_ok:
            key = frozenset((f, mo))
            trunk = pair_to_trunk.get(key)
            if trunk:
                dot.edge(trunk, child, weight="2", minlen="1")
            else:
                dot.edge(f, child, weight="2", minlen="2")
                dot.edge(mo, child, weight="2", minlen="2")
        else:
            parent = f if f_ok else (mo if mo_ok else "")
            if parent:
                candidates = [tr for pair,tr in pair_to_trunk.items() if parent in pair]
                if len(candidates) == 1:
                    dot.edge(candidates[0], child, weight="2", minlen="1")
                else:
                    dot.edge(parent, child, weight="2", minlen="2")

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
