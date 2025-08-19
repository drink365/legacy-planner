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
st.title("📦 家族盤點｜傳承圖（世代清楚、上下分層）")
st.markdown("第一步：**盤點家族成員**與**各自的資產**。本頁不做分配與繼承比例，只專注於盤點與關係圖。")

# =============================
# Demo 資料（你指定的人名）
# =============================
DEMO_FAMILY = [
    {"name": "陳志明", "relation": "本人",       "age": 65, "alive": True,  "father": "",       "mother": "", "dod": ""},
    {"name": "王春嬌", "relation": "配偶(現任)", "age": 62, "alive": True,  "father": "",       "mother": "", "dod": ""},
    {"name": "陳小明", "relation": "子女",       "age": 35, "alive": True,  "father": "陳志明", "mother": "王春嬌", "dod": ""},
    {"name": "陳小芳", "relation": "子女",       "age": 32, "alive": True,  "father": "陳志明", "mother": "王春嬌", "dod": ""},
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
    m["alive"]  = bool(m.get("alive", True))
    m["dod"]    = m.get("dod", "")
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

# 做為最後手段的文字關係→代數推測（若仍無法用親屬關係推得）
FALLBACK_GEN_BY_REL = {
    "祖父": -2, "祖母": -2,
    "父親": -1, "母親": -1,
    "本人": 0, "配偶(現任)": 0, "前配偶": 0, "兄弟": 0, "姊妹": 0, "其他": 0,
    "子女": 1, "子女之配偶": 1, "子女的配偶": 1,
    "孫子": 2, "孫女": 2, "孫輩之配偶": 2, "孫輩的配偶": 2,
}
def fallback_generation(rel: str) -> int:
    return FALLBACK_GEN_BY_REL.get(rel, 0)

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
                "mother": mother,
                "dod": ""
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
    display_cols = ["name", "relation", "age", "alive", "father", "mother", "dod"]
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

# =============================
# Step 1c: 在世狀態與逝世日期更新
# =============================
st.header("Step 1c. 在世狀態與逝世日期更新")
if st.session_state["family"]:
    names = [m["name"] for m in st.session_state["family"]]
    sel = st.selectbox("選擇成員", names, key="life_sel")
    member = next(m for m in st.session_state["family"] if m["name"] == sel)

    colu = st.columns(3)
    with colu[0]:
        new_alive = st.checkbox("在世", value=bool(member.get("alive", True)), key="life_alive")
    with colu[1]:
        new_dod = st.text_input("逝世日期（選填，YYYY-MM-DD）", member.get("dod", ""), key="life_dod")

    with colu[2]:
        if st.button("今日逝世（快速標記）"):
            from datetime import date
            new_alive = False
            new_dod = date.today().isoformat()
            st.success(f"已將「{sel}」標記為今日逝世：{new_dod}")

    if st.button("💾 儲存狀態變更"):
        member["alive"] = bool(new_alive)
        member["dod"] = new_dod.strip()
        st.success(f"已更新：{sel}（在世={member['alive']}，逝世日期='{member.get('dod','')}'）")
else:
    st.info("請先新增家庭成員，再更新狀態。")

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
# Step 3: 家族樹（任意代；夫妻橫桿→子女；無子女也畫橫線；單親直連且不穿字）
# =============================
st.header("Step 3. 家族樹（世代清楚、上下分層）")

if st.session_state["family"]:
    # --- Graphviz 初始化（圓角卡片 + 正交線 + 避免合併路徑） ---
    dot = Digraph(format="png")
    dot.attr(rankdir="TB", size="10", splines="ortho", nodesep="0.8", ranksep="1.2", concentrate="false", newrank="true")
    dot.attr('edge', arrowhead='none')
    # 全域節點風格：圓角卡片
    dot.attr('node', shape='box', style='rounded,filled', color='black', fontname="Noto Sans CJK TC, PingFang TC, Microsoft JhengHei")

    members = st.session_state["family"]
    existing = {m["name"] for m in members}

    # ---------- d.2：任何代數的自動分層（以「本人=0」做推導） ----------
    # 建立約束：父母↔子女、夫妻同層
    parent_of = defaultdict(set)  # parent -> {child,...}
    child_of  = defaultdict(set)  # child  -> {parent,...}
    for m in members:
        n, f, mo = m["name"], normalize(m.get("father","")), normalize(m.get("mother",""))
        if f in existing:  parent_of[f].add(n);  child_of[n].add(f)
        if mo in existing: parent_of[mo].add(n); child_of[n].add(mo)
    unions = [(normalize(u["a"]), normalize(u["b"])) for u in st.session_state.get("unions", [])]

    # 初始：本人=0；本人現任配偶也給0；其餘未知
    gen = {}
    for m in members:
        if m.get("relation") == "本人":
            gen[m["name"]] = 0
    for a,b in unions:
        if a in gen and b not in gen: gen[b] = gen[a]
        if b in gen and a not in gen: gen[a] = gen[b]

    # 反覆推導：父母在上、子女在下、夫妻同層
    changed = True
    loops = 0
    while changed and loops < 10 * max(1, len(members)):
        changed = False
        loops += 1
        # 父母→子女
        for p, kids in parent_of.items():
            if p in gen:
                for k in kids:
                    want = gen[p] + 1
                    if gen.get(k) != want:
                        gen[k] = want; changed = True
        # 子女→父母
        for c, parents in child_of.items():
            if c in gen:
                for p in parents:
                    want = gen[c] - 1
                    if gen.get(p) != want:
                        gen[p] = want; changed = True
        # 夫妻同層
        for a,b in unions:
            if a in gen and b not in gen:
                gen[b] = gen[a]; changed = True
            if b in gen and a not in gen:
                gen[a] = gen[b]; changed = True

    # 仍未知的，以關係名稱做保底
    for m in members:
        if m["name"] not in gen:
            gen[m["name"]] = fallback_generation(m.get("relation",""))

    # --- 分層畫節點 ---
    def node_style(mem):
        alive = bool(mem.get('alive', True))
        dod   = (mem.get('dod') or "").strip()
        if alive:
            fill  = "khaki" if mem["relation"] == "本人" else "lightgrey"
            style = "rounded,filled"
            color = "black"
            suffix = ""
        else:
            fill  = "#eeeeee"
            style = "rounded,filled,dashed"
            color = "#666666"
            suffix = f"・✝{dod}" if dod else "・不在世"
        label = f"{mem['name']} ({mem['relation']}{suffix})"
        return label, fill, style, color

    gens_sorted = sorted(set(gen.values()))
    for g in gens_sorted:
        with dot.subgraph() as s:
            s.attr(rank="same")
            for mem in members:
                if gen[mem["name"]] != g: 
                    continue
                label, fill, style, color = node_style(mem)
                s.node(mem["name"], label, fillcolor=fill, style=style, color=color, fontcolor="#333333")

    # --- 工具 ---
    def norm(s): return s.strip() if isinstance(s, str) else ""
    def age_of(name: str) -> int:
        m = next((x for x in members if x["name"] == name), None)
        return int(m.get("age", 0)) if m else 0

    # (0) 提醒未配對的「子女之/的配偶」
    dangling = []
    for m in members:
        if m.get("relation") in {"子女之配偶","子女的配偶"}:
            name = m["name"]
            linked = any(name in {u["a"], u["b"]} for u in st.session_state.get("unions", []))
            if not linked:
                dangling.append(name)
    if dangling:
        st.warning("以下『子女之配偶』尚未與子女配對： " + "、".join(dangling) +
                   "。請在上方「伴侶關係」建立配對，或於新增成員時選『配偶對象（子女）』。")

    # (a) 由孩子蒐集「父母對」→ 適用任意代；只放孩子本人（不含配偶）
    children_by_pair = defaultdict(list)  # key=frozenset({f,mo}) -> [child1, child2...]
    for m in members:
        f, mo = norm(m.get("father","")), norm(m.get("mother",""))
        if f and mo and f in existing and mo in existing:
            children_by_pair[frozenset((f, mo))].append(m["name"])

    # (b) 夫妻對（含 unions & 本人＋現任配偶）→ 任意代
    couple_pairs = set(children_by_pair.keys())
    for u in st.session_state.get("unions", []):
        a, b = norm(u.get("a","")), norm(u.get("b",""))
        if a and b and a in existing and b in existing:
            couple_pairs.add(frozenset((a, b)))
    selfs = [x for x in members if x["relation"] == "本人"]
    if selfs:
        me = selfs[0]["name"]
        for sp in [x for x in members if x["relation"] == "配偶(現任)"]:
            couple_pairs.add(frozenset((me, sp["name"])))

    # (c) 讓配偶可以貼在對應子女旁（不參與排序）
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

    # (d) 夫妻橫桿 → 直接連每位子女（無子女也畫橫線，參與佈局）—— 適用每一代
    pair_to_union = {}  # frozenset({f,mo}) -> union_id
    for idx, pair in enumerate(sorted(couple_pairs, key=lambda p: sorted(list(p)))):
        f, mo = sorted(list(pair))
        union_id = f"U{idx}"
        pair_to_union[pair] = union_id
        kids = children_by_pair.get(pair, [])

        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(union_id, label="", shape="box",
                   width="0.8", height="0.02", fixedsize="true",
                   style="filled", fillcolor="black", color="black")
            if kids:
                s.edge(f,  union_id, weight="20", minlen="1")
                s.edge(union_id, mo, weight="20", minlen="1")
            else:
                s.edge(f,  union_id, weight="12", minlen="1")
                s.edge(union_id, mo, weight="12", minlen="1")

        if kids:
            # 子女依年齡（左→右），但只排序子女本人
            kids_sorted = sorted(kids, key=lambda n: age_of(n), reverse=True)
            with dot.subgraph() as s:
                s.attr(rank="same", ordering="out")
                for c in kids_sorted: s.node(c)
                for i in range(len(kids_sorted)-1):
                    s.edge(kids_sorted[i], kids_sorted[i+1], style="invis", constraint="false", weight="100")
            for c in kids_sorted:
                dot.edge(union_id, c, tailport="s", headport="n", weight="5", minlen="2")
            # 子女的配偶僅貼齊（不參與排序）
            for c in kids_sorted:
                mates = [sp for sp in spouse_map.get(c, []) 
                         if next((m for m in members if m["name"] == sp and m["relation"] in {"子女之配偶","子女的配偶"}), None)]
                if mates:
                    dot.edge(c, mates[0], style="invis", constraint="false", weight="200")

    # (e) 單親資訊：只有「父+母都存在」才掛到夫妻橫線；
    #     否則一律由已知的那位父/母直接往下連（適用婚外所生、未知另一方等）
    #     並加「錨點」確保線從框外緣垂直落下，不穿過文字
    parent_anchors = {}  # name -> anchor_id
    for m in members:
        child = m["name"]
        f, mo = norm(m.get("father","")), norm(m.get("mother",""))
        f_ok = bool(f) and f in existing
        mo_ok = bool(mo) and mo in existing

        if f_ok and mo_ok:
            continue  # 已在 (d) 掛到夫妻橫桿

        parent = f if f_ok else (mo if mo_ok else "")
        if not parent:
            continue  # 父母都未知就跳過

        if parent not in parent_anchors:
            anchor_id = f"PA_{len(parent_anchors)}"
            parent_anchors[parent] = anchor_id
            dot.node(anchor_id, label="", shape="point", width="0.01")
            dot.edge(parent, anchor_id, tailport="s", headport="n", weight="6", minlen="1")
        dot.edge(parent_anchors[parent], child, tailport="s", headport="n", weight="4", minlen="2")

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
