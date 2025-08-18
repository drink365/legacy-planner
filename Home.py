# =============================
# Step 3: 家族樹（鎖定由上而下的連線；兄弟姊妹依年齡排序；配偶貼齊但不排序；無子女的夫妻不下拉）
# =============================
st.header("Step 3. 家族樹（世代清楚、上下分層）")

if st.session_state["family"]:
    from collections import defaultdict

    dot = Digraph(format="png")
    # 直角線＋舒適間距；所有邊預設不畫箭頭
    dot.attr(rankdir="TB", size="10", splines="ortho", nodesep="0.7", ranksep="1.1")
    dot.attr('edge', arrowhead='none')

    # ---- 分層（純排版）----
    GEN_BY_REL = {
        "祖父": -2, "祖母": -2,
        "父親": -1, "母親": -1,
        "本人": 0, "配偶(現任)": 0, "前配偶": 0, "兄弟": 0, "姊妹": 0, "其他": 0,
        "子女": 1, "子女之配偶": 1, "子女的配偶": 1,
        "孫子": 2, "孫女": 2, "孫輩之配偶": 2, "孫輩的配偶": 2,
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
    def age_of(name: str) -> int:
        m = next((x for x in st.session_state["family"] if x["name"] == name), None)
        return int(m.get("age", 0)) if m else 0

    existing = {m["name"] for m in st.session_state["family"]}

    # (a) 由孩子蒐集「父母對」→只放孩子本人（不含配偶）
    children_by_pair = defaultdict(list)  # key=frozenset({f,mo}) -> [child1, child2...]
    for m in st.session_state["family"]:
        f, mo = norm(m.get("father","")), norm(m.get("mother",""))
        if f in existing and mo in existing and f and mo:
            children_by_pair[frozenset((f, mo))].append(m["name"])

    # (b) 蒐集所有夫妻對（含 unions 與 本人+現任配偶），用來畫橫線
    couple_pairs = set(children_by_pair.keys())
    for u in st.session_state.get("unions", []):
        a, b = norm(u.get("a","")), norm(u.get("b",""))
        if a in existing and b in existing and a and b:
            couple_pairs.add(frozenset((a, b)))
    selfs = [x for x in st.session_state["family"] if x["relation"] == "本人"]
    if selfs:
        self_name = selfs[0]["name"]
        for sp in [x for x in st.session_state["family"] if x["relation"] == "配偶(現任)"]:
            couple_pairs.add(frozenset((self_name, sp["name"])))

    # (c) 每對夫妻：畫橫桿；有子女才畫「垂直幹線」
    pair_to_trunk = {}  # frozenset({f,mo}) -> trunk_id
    for idx, pair in enumerate(sorted(couple_pairs, key=lambda p: sorted(list(p)))):
        f, mo = sorted(list(pair))
        union_id = f"U{idx}"
        kids     = children_by_pair.get(pair, [])  # 只有孩子本人，不含配偶

        with dot.subgraph() as s:
            s.attr(rank="same")
            # 夫妻橫桿（小矩形）
            s.node(union_id, label="", shape="box",
                   width="0.8", height="0.02", fixedsize="true",
                   style="filled", fillcolor="black", color="black")

            if kids:
                # 讓橫桿與雙親參與版面計算
                s.edge(f,  union_id, weight="100")
                s.edge(union_id, mo, weight="100")
            else:
                # 沒子女：只示意橫線，不干擾整體排序
                s.edge(f,  union_id, weight="1", constraint="false")
                s.edge(union_id, mo, weight="1", constraint="false")

        if kids:
            trunk_id = f"T{idx}"
            pair_to_trunk[pair] = trunk_id
            dot.node(trunk_id, label="", shape="point", width="0.01")
            # ✅ 橫桿 → 幹線：由上往下（south -> north）
            dot.edge(union_id, trunk_id, weight="60", minlen="2", tailport="s", headport="n")

            # 兄弟姊妹依年齡由大到小（左→右），配偶不參與排序
            kids_sorted = sorted(kids, key=lambda n: age_of(n), reverse=True)

            # ✅ 幹線 → 每個孩子：由上往下（south -> north），避免長方形繞線
            for c in kids_sorted:
                dot.edge(trunk_id, c, weight="4", minlen="1", tailport="s", headport="n")

            # 用隱形邊固定兄弟姊妹左右順序（不連到配偶）
            if len(kids_sorted) > 1:
                for i in range(len(kids_sorted)-1):
                    dot.edge(kids_sorted[i], kids_sorted[i+1],
                             style="invis", weight="200", constraint="true")

    # (d) 單親資訊的孩子：若能唯一對應到某組父母就掛到該幹線，否則以單親直連（同樣鎖定方向）
    for m in st.session_state["family"]:
        child = m["name"]
        f, mo = norm(m.get("father","")), norm(m.get("mother",""))
        f_ok, mo_ok = f in existing and f, mo in existing and mo
        if f_ok and mo_ok:
            continue  # 雙親情況已在上方處理
        parent = f if f_ok else (mo if mo_ok else "")
        if parent:
            candidates = [tr for pair, tr in pair_to_trunk.items() if parent in pair]
            if len(candidates) == 1:
                dot.edge(candidates[0], child, weight="3", minlen="1", tailport="s", headport="n")
            else:
                dot.edge(parent, child, weight="3", minlen="2", tailport="s", headport="n")

    st.graphviz_chart(dot)
else:
    st.info("請先新增 **家庭成員**。")
