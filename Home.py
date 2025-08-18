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
    # 例如孫輩：
    # {"name":"小明之子","relation":"孫子","age":6,"alive":True,"father":"陳小明","mother":""}
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

# =============================
# 小工具
# =============================
REL_OPTIONS = [
    "本人", "配偶(現任)", "前配偶",
    "父親", "母親",
    "祖父", "祖母",
    "兄弟", "姊妹",
    "子女", "孫子", "孫女",
    "其他"
]

GEN_BY_REL = {
    "祖父": -2, "祖母": -2,
    "父親": -1, "母親": -1,
    "本人": 0, "配偶(現任)": 0, "前配偶": 0, "兄弟": 0, "姊妹": 0, "其他": 0,
    "子女": 1,
    "孫子": 2, "孫女": 2,
}

def get_generation(rel: str) -> int:
    return GEN_BY_REL.get(rel, 0)

def normalize(s: str) -> str:
    return s.strip() if isinstance(s, str) else s

def name_exists(n: str) -> bool:
    return any(m["name"] == n for m in st.session_state["family"])

# ---- 向下相容：把舊資料的 parent 升級並做名字正規化 ----
for m in st.session_state["family"]:
    # 名字正規化
    m["name"]   = normalize(m.get("name", ""))
    m["father"] = normalize(m.get("father", ""))
    m["mother"] = normalize(m.get("mother", ""))
    # 舊 parent 轉到 father（僅在父母都空時）
    if m.get("parent"):
        p = normalize(m["parent"])
        if not (m["father"] or m["mother"]):
            m["father"] = p

# =============================
# 快捷操作：重置／載入示範
# =============================
c1, c2 = st.columns(2)
with c1:
    if st.button("🔄 重置（清空目前資料）", use_container_width=True):
        st.session_state["family"] = []
        st.session_state["assets"] = []
        st.success("已清空資料。請開始新增家族成員與資產。")
with c2:
    if st.button("🧪 載入示範資料", use_container_width=True):
        st.session_state["family"] = DEMO_FAMILY.copy()
        st.session_state["assets"] = DEMO_ASSETS.copy()
        st.info("已載入示範資料。")

st.markdown("---")

# =============================
# Step 1: 家族成員盤點（父/母可同時指定；名單永遠列出全部成員）
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

    # 刪除成員（會自動清理他人 father/mother/parent 指向）
    del_name = st.selectbox("選擇要刪除的成員", [""] + [f["name"] for f in st.session_state["family"]])
    if del_name and st.button("❌ 刪除成員"):
        del_name_norm = normalize(del_name)
        affected = 0
        for m in st.session_state["family"]:
            changed = False
            if normalize(m.get("father", "")) == del_name_norm:
                m["father"] = ""
                changed = True
            if normalize(m.get("mother", "")) == del_name_norm:
                m["mother"] = ""
                changed = True
            # 兼容舊 parent 欄位
            if normalize(m.get("parent", "")) == del_name_norm:
                m["parent"] = ""
                changed = True
            if changed:
                affected += 1
        # 刪除本人
        st.session_state["family"] = [f for f in st.session_state["family"] if normalize(f["name"]) != del_name_norm]
        st.warning(f"已刪除成員：{del_name}。提醒：有 {affected} 位成員的父/母欄位已自動清空，請視需要重新指定。")
else:
    st.info("尚無家庭成員，請先新增。")

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
        st.session_state["assets"].append({
            "owner": normalize(owner),
            "type": asset_type,
            "value": value,
            "note": note
        })
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
# Step 3: 家族樹（現任配偶用實線；父母→婚姻橫桿→子女，避免交錯）
# =============================
st.header("Step 3. 家族樹（世代清楚、上下分層）")

if st.session_state["family"]:
    dot = Digraph(format="png")
    # 直角線條 & 比較舒服的間距；預設不畫箭頭
    dot.attr(rankdir="TB", size="10", splines="ortho", nodesep="0.6", ranksep="1.0")
    dot.attr('edge', arrowhead='none')

    # 分層（僅為排版用途）
    GEN_BY_REL = {
        "祖父": -2, "祖母": -2,
        "父親": -1, "母親": -1,
        "本人": 0, "配偶(現任)": 0, "前配偶": 0, "兄弟": 0, "姊妹": 0, "其他": 0,
        "子女": 1, "孫子": 2, "孫女": 2,
    }
    def _gen(rel: str) -> int: return GEN_BY_REL.get(rel, 0)

    gens = {-2: [], -1: [], 0: [], 1: [], 2: [], 3: []}
    for m in st.session_state["family"]:
        gens.setdefault(_gen(m.get("relation","")), []).append(m["name"])

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

    # 1) 先找出「已知的父母對」（孩子同時有 father & mother）
    couple_pairs = set()   # 內容：tuple(sorted([father, mother]))
    for m in st.session_state["family"]:
        f, mo = norm(m.get("father","")), norm(m.get("mother",""))
        if f in existing and mo in existing and f and mo:
            couple_pairs.add(tuple(sorted((f, mo))))

    # 2) 把「本人 ＋ 現任配偶」也強制視為一對（即使還沒輸入孩子）
    selfs = [x for x in st.session_state["family"] if x["relation"] == "本人"]
    if selfs:
        self_name = selfs[0]["name"]
        for sp in [x for x in st.session_state["family"] if x["relation"] == "配偶(現任)"]:
            couple_pairs.add(tuple(sorted((self_name, sp["name"]))))

    # 3) 為每一對父母建立「婚姻橫桿」節點（細長小矩形），用實線把雙方橫向接在一起
    pair_to_union = {}   # frozenset({f, mo}) -> union_id
    for idx, pair in enumerate(sorted(couple_pairs)):
        union_id = f"U{idx}"
        pair_to_union[frozenset(pair)] = union_id
        f, mo = pair
        with dot.subgraph() as s:
            s.attr(rank="same")
            # 小矩形做為「婚姻橫桿」
            s.node(
                union_id, label="", shape="box",
                width="0.6", height="0.02", fixedsize="true",
                style="filled", fillcolor="black", color="black"
            )
            # 兩端用實線相連（constraint=false：不干擾整體排版，只做視覺）
            s.edge(f,  union_id, dir="none", weight="100", constraint="false")
            s.edge(union_id, mo, dir="none", weight="100", constraint="false")

    # 4) 把孩子掛到對應的婚姻橫桿；若只有單親資訊，嘗試唯一配對，否則單親直連
    for m in st.session_state["family"]:
        child = m["name"]
        f, mo = norm(m.get("father","")), norm(m.get("mother",""))
        f_ok, mo_ok = f in existing and f, mo in existing and mo

        if f_ok and mo_ok:
            key = frozenset((f, mo))
            u = pair_to_union.get(key)
            if u:
                dot.edge(u, child, weight="2", minlen="2")  # 從橫桿往下
            else:
                # 萬一沒建出婚姻節點，則退回雙親直連
                dot.edge(f, child, weight="2", minlen="2")
                dot.edge(mo, child, weight="2", minlen="2")
        else:
            # 僅有單親：若此家長只屬於一個「父母對」，就從該橫桿下接；否則保守單親直連
            parent = f if f_ok else (mo if mo_ok else "")
            if parent:
                unions = [u for pair,u in pair_to_union.items() if parent in pair]
                if len(unions) == 1:
                    dot.edge(unions[0], child, weight="2", minlen="2")
                else:
                    dot.edge(parent, child, weight="2", minlen="2")

    # ✅ 不再畫虛線伴侶連結（前一版的示意虛線已移除）

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
