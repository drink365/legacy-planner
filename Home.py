import streamlit as st
import pandas as pd
from graphviz import Digraph
from collections import defaultdict

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
# Demo 資料（你指定的人名）
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
    # 伴侶關係：{"a":姓名, "b":姓名, "type":"現任配偶"/"前配偶"/"伴侶"}
    st.session_state["unions"] = []

# =============================
# 小工具與常數
# =============================
def normalize(s: str) -> str:
    return s.strip() if isinstance(s, str) else s

def pair_key(a: str, b: str):
    if not a or not b: return None
    a, b = normalize(a), normalize(b)
    return tuple(sorted([a, b])) if a != b else None

# 舊資料相容（若舊版只有 parent）
for m in st.session_state["family"]:
    m["name"]   = normalize(m.get("name", ""))
    m["father"] = normalize(m.get("father", ""))
    m["mother"] = normalize(m.get("mother", ""))
    if m.get("parent") and not (m["father"] or m["mother"]):
        m["father"] = normalize(m["parent"])

REL_OPTIONS = [
    "本人", "配偶(現任)", "前配偶",
    "父親", "母親",
    "祖父", "祖母",
    "兄弟", "姊妹",
    "子女", "子女之配偶", "子女的配偶",
    "孫子", "孫女", "孫輩之配偶", "孫輩的配偶",
    "其他"
]
SPOUSE_REL_CHILD = {"子女之配偶", "子女的配偶"}
SPOUSE_REL_GRAND = {"孫輩之配偶", "孫輩的配偶"}

GEN_BY_REL = {
    "祖父": -2, "祖母": -2,
    "父親": -1, "母親": -1,
    "本人": 0, "配偶(現任)": 0, "前配偶": 0, "兄弟": 0, "姊妹": 0, "其他": 0,
    "子女": 1, "子女之配偶": 1, "子女的配偶": 1,
    "孫子": 2, "孫女": 2, "孫輩之配偶": 2, "孫輩的配偶": 2,
}
def get_generation(rel: str) -> int:
    return GEN_BY_REL.get(rel, 0)

# =============================
# 快捷：重置／載入示範
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
# Step 1: 家族成員（可直接指定子女/孫輩的配偶對象）
# =============================
st.header("Step 1. 家族成員")

all_names = [m["name"] for m in st.session_state["family"]]
children_names = [m["name"] for m in st.session_state["family"] if m.get("relation") == "子女"]
grand_names = [m["name"] for m in st.session_state["family"] if m.get("relation") in ["孫子", "孫女"]]

with st.form("add_family"):
    cols = st.columns(9)
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

    # 永遠顯示（避免 form 同輪不重繪），不需要時禁用
    with cols[6]:
        spouse_target_child = st.selectbox(
            "配偶對象（子女）",
            [""] + children_names,
            disabled=(relation not in SPOUSE_REL_CHILD),
            key="spouse_target_child"
        )
    with cols[7]:
        spouse_target_grand = st.selectbox(
            "配偶對象（孫輩）",
            [""] + grand_names,
            disabled=(relation not in SPOUSE_REL_GRAND),
            key="spouse_target_grand"
        )
    with cols[8]:
        submitted = st.form_submit_button("➕ 新增成員")

    # ---- 驗證 & 寫入 ----
    def _norm(x): return x.strip() if isinstance(x, str) else x
    def _pair_key(a, b):
        if not a or not b: return None
        a, b = _norm(a), _norm(b)
        return tuple(sorted([a, b])) if a != b else None
    def _name_exists(n: str) -> bool:
        return any(m["name"] == n for m in st.session_state["family"])

    if submitted:
        name   = _norm(name)
        father = _norm(father)
        mother = _norm(mother)
        spouse_target_child = _norm(spouse_target_child)
        spouse_target_grand = _norm(spouse_target_grand)

        if not name:
            st.error("請輸入姓名。")
        elif _name_exists(name):
            st.error(f"成員「{name}」已存在，為避免混淆請改用不同名稱（或加註稱謂）。")
        elif relation in ["子女", "孫子", "孫女"] and (not father and not mother):
            st.error("子女/孫輩至少需指定一位父或母，才能正確掛在家族樹下。")
        elif relation in SPOUSE_REL_CHILD and not spouse_target_child:
            st.error("請選擇『配偶對象（子女）』，才能與指定子女連線。")
        elif relation in SPOUSE_REL_GRAND and not spouse_target_grand:
            st.error("請選擇『配偶對象（孫輩）』，才能與指定孫輩連線。")
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

            # 自動建立伴侶配對（夫妻橫桿）
            if relation in SPOUSE_REL_CHILD and spouse_target_child:
                key = _pair_key(name, spouse_target_child)
                if key and not any(_pair_key(u["a"], u["b"]) == key for u in st.session_state["unions"]):
                    st.session_state["unions"].append({"a": key[0], "b": key[1], "type": "現任配偶"})
                    st.info(f"已自動配對：{key[0]} ↔ {key[1]}（現任配偶）")
            if relation in SPOUSE_REL_GRAND and spouse_target_grand:
                key = _pair_key(name, spouse_target_grand)
                if key and not any(_pair_key(u["a"], u["b"]) == key for u in st.session_state["unions"]):
                    st.session_state["unions"].append({"a": key[0], "b": key[1], "type": "現任配偶"})
                    st.info(f"已自動配對：{key[0]} ↔ {key[1]}（現任配偶）")

# 成員清單 & 刪除
if st.session_state["family"]:
    st.subheader("👨‍👩‍👧 家庭成員清單")
    df_family = pd.DataFrame(st.session_state["family"])
    display_cols = ["name", "relation", "age", "alive", "father", "mother"]
    df_family = df_family.reindex(columns=[c for c in display_cols if c in df_family.columns])
    st.table(df_family)

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

        st.session_state["family"] = [f for f in st.session_state["family"] if normalize(f["name"]) != del_name_norm]
        st.warning(f"已刪除成員：{del_name}。提醒：有 {affected} 位成員的父/母欄位已自動清空，並同步移除相關的伴侶關係。")
else:
    st.info("尚無家庭成員，請先新增。")

# =============================
# Step 1b: 伴侶關係（手動新增/刪除）
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
# Step 3: 家族樹（乾淨連線；夫妻橫桿→子女；無子女也畫橫線）
# =============================
st.header("Step 3. 家族樹（世代清楚、上下分層）")

if st.session_state["family"]:
    # --- Graphviz 初始化（圓角卡片 + 正交線 + 避免合併路徑） ---
    dot = Digraph(format="png")
    dot.attr(
        rankdir="TB",
        size="10",
        splines="ortho",
        nodesep="0.8",
        ranksep="1.2",
        concentrate="false",
        newrank="true"
    )
    dot.attr('edge', arrowhead='none')
    # 全域節點風格：圓角卡片
    dot.attr('node', shape='box', style='rounded,filled', color='black', fontname="Noto Sans CJK TC, PingFang TC, Microsoft JhengHei")

    # --- 分層（純排版） ---
    gens = {-2: [], -1: [], 0: [], 1: [], 2: [], 3: []}
    for m in st.session_state["family"]:
        gens.setdefault(get_generation(m.get("relation","")), []).append(m["name"])
    for _, names in sorted(gens.items()):
        if not names:
            continue
        with dot.subgraph() as s:
            s.attr(rank="same")
            for n in names:
                mem = next((x for x in st.session_state["family"] if x["name"] == n), None)
                if not mem:
                    continue
                alive_mark = "" if mem.get('alive', True) else "・不在世"
                label = f"{mem['name']} ({mem['relation']}{alive_mark})"
                fill  = "khaki" if mem["relation"] == "本人" else "lightgrey"
                s.node(mem["name"], label, fillcolor=fill)

    def norm(s): return s.strip() if isinstance(s, str) else ""
    def age_of(name: str) -> int:
        m = next((x for x in st.session_state["family"] if x["name"] == name), None)
        return int(m.get("age", 0)) if m else 0

    existing = {m["name"] for m in st.session_state["family"]}

    # (0) 提醒：未與子女配對的「子女之/的配偶」
    dangling = []
    for m in st.session_state["family"]:
        if m.get("relation") in {"子女之配偶","子女的配偶"}:
            name = m["name"]
            linked = any(name in {u["a"], u["b"]} for u in st.session_state.get("unions", []))
            if not linked:
                dangling.append(name)
    if dangling:
        st.warning("以下『子女之配偶』尚未與子女配對： " + "、".join(dangling) +
                   "。請在上方「伴侶關係」建立配對，或於新增成員時選『配偶對象（子女）』。")

    # (a) 由孩子蒐集「父母對」→ 只放孩子本人（不含配偶）
    children_by_pair = defaultdict(list)  # key=frozenset({f,mo}) -> [child1, child2...]
    for m in st.session_state["family"]:
        f, mo = norm(m.get("father","")), norm(m.get("mother",""))
        if f and mo and f in existing and mo in existing:
            children_by_pair[frozenset((f, mo))].append(m["name"])

    # (b) 夫妻對（含 unions & 本人＋現任配偶）
    couple_pairs = set(children_by_pair.keys())
    for u in st.session_state.get("unions", []):
        a, b = norm(u.get("a","")), norm(u.get("b",""))
        if a and b and a in existing and b in existing:
            couple_pairs.add(frozenset((a, b)))
    selfs = [x for x in st.session_state["family"] if x["relation"] == "本人"]
    if selfs:
        me = selfs[0]["name"]
        for sp in [x for x in st.session_state["family"] if x["relation"] == "配偶(現任)"]:
            couple_pairs.add(frozenset((me, sp["name"])))

    # (c) 讓配偶可以貼在子女旁（不參與排序）
    spouse_map = {}
    for u in st.session_state.get("unions", []):
        a, b = norm(u.get("a","")), norm(u.get("b",""))
        if a in existing and b in existing:
            spouse_map.setdefault(a, []).append(b)
            spouse_map.setdefault(b, []).append(a)
    for pair in couple_pairs:
        f, mo = list(pair)
        spouse_map.setdefault(f, []).append(mo)
        spouse_map.setdefault(mo, []).append(f)

    # (d) 夫妻橫桿 → 直接連每位子女（無子女也畫橫線，參與佈局）
    pair_to_union = {}  # frozenset({f,mo}) -> union_id
    for idx, pair in enumerate(sorted(couple_pairs, key=lambda p: sorted(list(p)))):
        f, mo = sorted(list(pair))
        union_id = f"U{idx}"
        pair_to_union[pair] = union_id
        kids = children_by_pair.get(pair, [])

        # 橫桿（小黑盒）與父母連線
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(union_id, label="", shape="box",
                   width="0.8", height="0.02", fixedsize="true",
                   style="filled", fillcolor="black", color="black")
            if kids:
                s.edge(f,  union_id, weight="20", minlen="1")
                s.edge(union_id, mo, weight="20", minlen="1")
            else:
                # ✅ 沒有子女也要把夫妻黏在一起，橫線要參與佈局（就會畫出來）
                s.edge(f,  union_id, weight="12", minlen="1")   # constraint 預設 True
                s.edge(union_id, mo, weight="12", minlen="1")

        if kids:
            # 子女依年齡（左→右），但只排序子女本人
            kids_sorted = sorted(kids, key=lambda n: age_of(n), reverse=True)

            # 把兄弟姊妹放同一 rank，並用「不影響佈局的隱形邊」鎖左右順序
            with dot.subgraph() as s:
                s.attr(rank="same", ordering="out")
                for c in kids_sorted:
                    s.node(c)  # 已建立；強化 rank 相同
                for i in range(len(kids_sorted)-1):
                    s.edge(kids_sorted[i], kids_sorted[i+1], style="invis", constraint="false", weight="100")

            # 橫桿 → 每位子女：由上往下
            for c in kids_sorted:
                dot.edge(union_id, c, tailport="s", headport="n", weight="5", minlen="2")

            # 子女的配偶僅貼齊（用不影響佈局的隱形邊）
            for c in kids_sorted:
                mates = [sp for sp in spouse_map.get(c, []) 
                         if next((m for m in st.session_state["family"] if m["name"] == sp and m["relation"] in {"子女之配偶","子女的配偶"}), None)]
                if mates:
                    dot.edge(c, mates[0], style="invis", constraint="false", weight="200")

    # (e) 單親資訊：若能唯一對應到某組父母，就用「那組橫桿」直連；否則由單親直連
    for m in st.session_state["family"]:
        child = m["name"]
        f, mo = norm(m.get("father","")), norm(m.get("mother",""))
        f_ok, mo_ok = f in existing and f, mo in existing and mo
        if f_ok and mo_ok:
            continue
        parent = f if f_ok else (mo if mo_ok else "")
        if not parent:
            continue
        candidates = [uid for pair, uid in pair_to_union.items() if parent in pair]
        if len(candidates) == 1:
            dot.edge(candidates[0], child, tailport="s", headport="n", weight="4", minlen="2")
        else:
            dot.edge(parent, child, tailport="s", headport="n", weight="3", minlen="2")

    st.graphviz_chart(dot)
else:
    st.info("請先新增 **家庭成員**。")

# =============================
# 頁尾（可點擊連結）
# =============================
st.markdown("---")
st.markdown("""
《影響力》傳承策略平台｜永傳家族辦公室  
🌐 [gracefo.com](https://gracefo.com)  
📩 [123@gracefo.com](mailto:123@gracefo.com)
""")
