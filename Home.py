import streamlit as st
import pandas as pd
from graphviz import Digraph
from collections import defaultdict

# =============== 基本設定 ===============
st.set_page_config(page_title="家族盤點｜傳承樹", page_icon="🌳", layout="wide")
st.title("Step 3. 家族樹（世代清楚、上下分層）")

# =============== Demo 初始資料 ===============
DEMO_FAMILY = [
    {"name": "陳志明", "relation": "本人",       "age": 65, "alive": True,  "father": "",       "mother": "", "dod": ""},
    {"name": "王春嬌", "relation": "配偶(現任)", "age": 62, "alive": True,  "father": "",       "mother": "", "dod": ""},
    {"name": "陳小明", "relation": "子女",       "age": 35, "alive": True,  "father": "陳志明", "mother": "王春嬌", "dod": ""},
    {"name": "陳小芳", "relation": "子女",       "age": 32, "alive": True,  "father": "陳志明", "mother": "王春嬌", "dod": ""},
]
DEMO_ASSETS = [
    {"owner": "陳志明", "type": "公司股權", "value": 100_000_000, "note": ""},
    {"owner": "陳志明", "type": "不動產",   "value": 50_000_000,  "note": "台北市某處"},
]

# =============== Session State ===============
if "family" not in st.session_state:
    st.session_state.family = DEMO_FAMILY.copy()
if "assets" not in st.session_state:
    st.session_state.assets = DEMO_ASSETS.copy()
if "unions" not in st.session_state:
    # {"a":姓名, "b":姓名, "type":"現任配偶/前配偶/伴侶"}
    st.session_state.unions = []

# =============== 工具函式 ===============
def N(s): return s.strip() if isinstance(s, str) else ""

def pair_key(a, b):
    a, b = N(a), N(b)
    if not a or not b or a == b:
        return None
    return tuple(sorted([a, b]))

def age_of(name):
    m = next((x for x in st.session_state.family if x["name"] == name), None)
    return int(m.get("age", 0)) if m else 0

def label_of(mem):
    # 只顯示姓名；往生加記號
    if mem.get("alive", True):
        return mem["name"]
    dod = N(mem.get("dod", ""))
    mark = f" ✝{dod}" if dod else " ✝不在世"
    return f"{mem['name']}{mark}"

# =============== 快捷：載入/清空 ===============
c1, c2 = st.columns(2)
with c1:
    if st.button("🧪 載入示範資料", use_container_width=True):
        st.session_state.family = DEMO_FAMILY.copy()
        st.session_state.assets = DEMO_ASSETS.copy()
        st.session_state.unions = []
with c2:
    if st.button("🔄 清空所有資料", use_container_width=True):
        st.session_state.family = []
        st.session_state.assets = []
        st.session_state.unions = []

st.markdown("---")

# =============== Step 1：家族成員（簡化版） ===============
st.header("Step 1. 家族成員")
all_names = [m["name"] for m in st.session_state.family]

with st.form("add_member"):
    c = st.columns(6)
    name     = c[0].text_input("姓名")
    relation = c[1].selectbox("關係", ["本人","配偶(現任)","前配偶","子女","孫子","孫女","其他"], index=3)
    age      = c[2].number_input("年齡", 0, 120, 30)
    alive    = c[3].checkbox("在世", True)
    father   = c[4].selectbox("父（選填）", [""] + all_names)
    mother   = c[5].selectbox("母（選填）", [""] + all_names)
    ok = st.form_submit_button("➕ 新增")
    if ok:
        name = N(name)
        if not name:
            st.error("請輸入姓名")
        elif any(m["name"] == name for m in st.session_state.family):
            st.error("姓名重複，請加註稱謂或別名")
        elif relation in {"子女","孫子","孫女"} and not (N(father) or N(mother)):
            st.error("子女/孫輩至少需指定父或母")
        else:
            st.session_state.family.append({
                "name": name, "relation": relation, "age": age, "alive": alive,
                "father": N(father), "mother": N(mother), "dod": ""
            })
            st.success(f"已新增：{name}")

if st.session_state.family:
    st.dataframe(pd.DataFrame(st.session_state.family), use_container_width=True)

st.markdown("---")

# =============== Step 1b：伴侶關係 ===============
st.header("Step 1b. 伴侶關係")
names = [m["name"] for m in st.session_state.family]
with st.form("add_union"):
    c = st.columns(4)
    a = c[0].selectbox("成員 A", names)
    b = c[1].selectbox("成員 B", names)
    t = c[2].selectbox("類型", ["現任配偶","前配偶","伴侶"])
    ok = c[3].form_submit_button("建立配對")
    if ok:
        k = pair_key(a, b)
        if not k:
            st.error("請選不同的兩人")
        elif any(pair_key(u["a"], u["b"]) == k for u in st.session_state.unions):
            st.warning("配對已存在")
        else:
            st.session_state.unions.append({"a": k[0], "b": k[1], "type": t})
            st.success(f"已配對：{k[0]} ↔ {k[1]}")

if st.session_state.unions:
    st.table(pd.DataFrame(st.session_state.unions))

st.markdown("---")

# =============== Step 1c：在世/逝世 ===============
st.header("Step 1c. 在世 / 逝世")
if st.session_state.family:
    who = st.selectbox("選擇成員", names, key="life_sel")
    m = next(x for x in st.session_state.family if x["name"] == who)
    c = st.columns(3)
    alive = c[0].checkbox("在世", value=bool(m.get("alive", True)))
    dod   = c[1].text_input("逝世日期(YYYY-MM-DD/可空)", value=m.get("dod", ""))
    if c[2].button("儲存"):
        m["alive"] = alive
        m["dod"] = N(dod)
        st.success("已更新")
st.markdown("---")

# =============== Step 3：畫圖（核心） ===============
st.header("Step 3. 家族樹（只顯示姓名）")

def build_graph():
    fam = st.session_state.family
    if not fam:
        return None

    people = {m["name"]: m for m in fam}
    existing = set(people.keys())

    # ---- 推導世代：本人=0；父母-1；子女+1；夫妻同層（迭代） ----
    parent_of = defaultdict(set)
    child_of  = defaultdict(set)
    for m in fam:
        n, f, mo = m["name"], N(m.get("father","")), N(m.get("mother",""))
        if f in existing:  parent_of[f].add(n);  child_of[n].add(f)
        if mo in existing: parent_of[mo].add(n); child_of[n].add(mo)

    unions = [(N(u["a"]), N(u["b"])) for u in st.session_state.unions]
    gen = {}
    for m in fam:
        if m.get("relation") == "本人":
            gen[m["name"]] = 0
    for a, b in unions:
        if a in gen and b not in gen: gen[b] = gen[a]
        if b in gen and a not in gen: gen[a] = gen[b]

    changed = True; loops = 0
    while changed and loops < 10 * max(1, len(fam)):
        changed = False; loops += 1
        for p, kids in parent_of.items():
            if p in gen:
                for k in kids:
                    want = gen[p] + 1
                    if gen.get(k) != want: gen[k] = want; changed = True
        for c, parents in child_of.items():
            if c in gen:
                for p in parents:
                    want = gen[c] - 1
                    if gen.get(p) != want: gen[p] = want; changed = True
        for a, b in unions:
            if a in gen and b not in gen: gen[b] = gen[a]; changed = True
            if b in gen and a not in gen: gen[a] = gen[b]; changed = True

    fallback = {"祖父":-2,"祖母":-2,"父親":-1,"母親":-1,"本人":0,"配偶(現任)":0,"前配偶":0,"子女":1,"孫子":2,"孫女":2}
    for m in fam:
        gen.setdefault(m["name"], fallback.get(m.get("relation","其他"), 0))

    # ---- Graphviz 設定 ----
    dot = Digraph(format="png")
    dot.attr(rankdir="TB", splines="ortho", nodesep="0.8", ranksep="1.2",
             concentrate="false", newrank="true")
    dot.attr('edge', arrowhead='none')
    dot.attr('node', shape='box', style='rounded,filled',
             fontname="Noto Sans CJK TC, PingFang TC, Microsoft JhengHei")

    # ---- 節點（姓名＋往生樣式） ----
    for g in sorted(set(gen.values())):
        with dot.subgraph() as s:
            s.attr(rank="same")
            for m in fam:
                if gen[m["name"]] != g: 
                    continue
                alive = bool(m.get("alive", True))
                fill  = "khaki" if (m["relation"]=="本人" and alive) else ("#eeeeee" if not alive else "lightgrey")
                style = "rounded,filled" + (",dashed" if not alive else "")
                color = "#666666" if not alive else "black"
                s.node(m["name"], label_of(m), fillcolor=fill, style=style, color=color, fontcolor="#333333")

    # ---- 雙親組合 → 子女（任何代）----
    children_by_pair = defaultdict(list)  # key=frozenset({f,mo}) -> [child...]
    for m in fam:
        f, mo = N(m.get("father","")), N(m.get("mother",""))
        if f and mo and (f in existing) and (mo in existing):
            children_by_pair[frozenset((f, mo))].append(m["name"])

    # ---- 夫妻橫桿（可見極薄黑條） ----
    marriage_id = {}  # pair -> bar id
    def ensure_marriage(a, b):
        key = frozenset((a, b))
        if key in marriage_id:
            return marriage_id[key]
        mid = f"MB_{len(marriage_id)}"
        marriage_id[key] = mid
        with dot.subgraph() as s:
            s.attr(rank="same")
            s.node(mid, label="", shape="box",
                   width="0.8", height="0.02", fixedsize="true",
                   style="filled", fillcolor="black", color="black")
            s.node(a); s.node(b)  # 同層幫定位
        dot.edge(a, mid, tailport="s", headport="n", weight="20", minlen="1")
        dot.edge(b, mid, tailport="s", headport="n", weight="20", minlen="1")
        return mid

    # 5a) 自然形成的夫妻（有共同子女）
    for pair, kids in children_by_pair.items():
        a, b = sorted(list(pair))
        mid = ensure_marriage(a, b)
        kids_sorted = sorted(kids, key=lambda n: age_of(n), reverse=True)
        for c in kids_sorted:
            dot.edge(mid, c, tailport="s", headport="n", weight="8", minlen="2")

    # 5b) 手動配對（即使無子女也畫橫桿，綁在一起）
    for u in st.session_state.unions:
        a, b = N(u.get("a","")), N(u.get("b",""))
        if a in existing and b in existing:
            ensure_marriage(a, b)

    # ---- 單親：每位家長一條單親橫桿（極薄黑條） ----
    single_children = defaultdict(list)  # parent -> [child...]
    for m in fam:
        child = m["name"]
        f, mo = N(m.get("father","")), N(m.get("mother",""))
        both = f and mo and (f in existing) and (mo in existing)
        if not both:
            parent = f if f in existing else (mo if mo in existing else "")
            if parent:
                single_children[parent].append(child)

    sp_bar = {}  # parent -> bar id
    for parent, kids in single_children.items():
        # 過濾掉「其實雙親皆存在」者（已在婚姻橫桿下）
        filtered = []
        for c in kids:
            f, mo = N(people[c].get("father","")), N(people[c].get("mother",""))
            if not (f and mo and (f in existing) and (mo in existing)):
                filtered.append(c)
        if not filtered:
            continue

        if parent not in sp_bar:
            sid = f"SPB_{len(sp_bar)}"
            sp_bar[parent] = sid
            with dot.subgraph() as s:
                s.attr(rank="same")
                s.node(sid, label="", shape="box",
                       width="0.8", height="0.02", fixedsize="true",
                       style="filled", fillcolor="black", color="black")
                s.node(parent)
            dot.edge(parent, sid, tailport="s", headport="n", weight="16", minlen="1")

        for c in sorted(filtered, key=lambda n: age_of(n), reverse=True):
            dot.edge(sp_bar[parent], c, tailport="s", headport="n", weight="10", minlen="2")

    return dot

dot = build_graph()
if dot:
    st.graphviz_chart(dot)
else:
    st.info("請先新增家庭成員。")

# =============== 頁尾 ===============
st.markdown("---")
st.markdown("🌐 [gracefo.com](https://gracefo.com) 　｜　《影響力》傳承策略平台｜永傳家族辦公室")
