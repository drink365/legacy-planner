from graphviz import Digraph
from collections import defaultdict

def build_graph_union(fam, unions):
    """
    目標：
    1) 配偶一定相鄰（rank=same）
    2) 以「夫妻中介點」承接所有子女線（避免孩子拉兩條線）
    3) 上下分層：父母在上一層、孩子在下一層；配偶同層
    4) 線條盡量直且不交錯
    """
    if not fam: 
        return None

    # 構建索引
    people = {p["name"]: p for p in fam}
    existing = set(people.keys())

    # Graph 全域設定
    dot = Digraph("FamilyTree", graph_attr={
        "rankdir": "TB",           # 由上而下
        "splines": "ortho",        # 直角線，較整齊
        "nodesep": "0.3",
        "ranksep": "0.6",
        "dpi": "120"
    }, node_attr={
        "shape": "box",
        "fontsize": "10",
        "height": "0.35",
        "width": "1.4",
        "style": "rounded,filled",
        "fillcolor": "white",
    }, edge_attr={
        "penwidth": "1.2"
    })

    # 畫節點（只顯示姓名；若過世可在這裡加小十字或灰階）
    for name, m in people.items():
        label = name if m.get("alive", True) else f"{name} ✝"
        dot.node(name, label=label)

    # —— 1) 配偶相鄰：用 rank=same 限制，並加一條極短的虛線連起來（或實線）
    # 並為每對配偶建立一個「夫妻中介點」union_x，孩子只接這個點
    couple_union = {}  # (a,b) 排序後為 key → union_id
    for i, u in enumerate(unions or []):
        a, b = u.get("a"), u.get("b")
        if not a or not b or a not in existing or b not in existing:
            continue
        key = tuple(sorted((a, b)))
        uid = couple_union.get(key) or f"U{i}"
        couple_union[key] = uid

        # 同層
        with dot.subgraph() as same:
            same.attr(rank="same")
            same.node(a)
            same.node(b)

        # 夫妻中介點（很小很小）
        dot.node(uid, label="", shape="point", width="0.01", height="0.01")

        # 夫↔妻連到中介點（不佔層級，僅為幾何定位）
        style = "solid" if u.get("type") != "前配偶" else "dashed"
        dot.edge(a, uid, style=style, weight="10")
        dot.edge(b, uid, style=style, weight="10")

    # —— 2) 父母 → 子女：只從「夫妻中介點」往下接
    # 若只有單親，則由該單親本人建立一個臨時的 union 點，仍以 union → 子女
    # 先按照 (father, mother) 分群（若你的欄位名稱不同，請相應修改）
    groups = defaultdict(list)  # key: (f or "", m or "") → [child...]
    for m in fam:
        c = m["name"]
        f = (m.get("father") or "").strip()
        mo = (m.get("mother") or "").strip()
        groups[(f if f in existing else "", mo if mo in existing else "")].append(c)

    for (f, mo), kids in groups.items():
        if not kids:
            continue

        # 取得/建立 union 點
        if f and mo:
            key = tuple(sorted((f, mo)))
            uid = couple_union.get(key)
            if not uid:
                # 若沒在 unions 明確登記，也臨時建立
                uid = f"U_auto_{f}_{mo}"
                couple_union[key] = uid
                dot.node(uid, label="", shape="point", width="0.01", height="0.01")
                with dot.subgraph() as same:
                    same.attr(rank="same"); same.node(f); same.node(mo)
                dot.edge(f, uid, weight="10"); dot.edge(mo, uid, weight="10")
        else:
            # 單親：用單親建立一個臨時 union
            p = f or mo
            uid = f"U_single_{p}"
            dot.node(uid, label="", shape="point", width="0.01", height="0.01")
            dot.edge(p, uid, weight="8")

        # 把所有孩子接到 union → child（往下一層）
        for child in kids:
            dot.edge(uid, child, weight="20", minlen="1")

        # 同父母的孩子之間用不可見邊，保持左右順序（避免交錯）
        ordered = sorted(kids, key=lambda n: people[n].get("age", 0), reverse=True)
        for a, b in zip(ordered, ordered[1:]):
            dot.edge(a, b, style="invis", constraint="false")

    return dot
