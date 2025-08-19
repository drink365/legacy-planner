import streamlit as st
import pandas as pd
from collections import defaultdict
import html

# ---------- 共用 ----------
st.set_page_config(page_title="家族盤點｜傳承樹", page_icon="🌳", layout="wide")
st.title("家族樹（穩定版：婚姻/單親橫桿）")

DEMO_FAMILY = [
    {"name":"陳志明","relation":"本人","age":65,"alive":True,"father":"","mother":"","dod":""},
    {"name":"王春嬌","relation":"配偶(現任)","age":62,"alive":True,"father":"","mother":"","dod":""},
    {"name":"陳小明","relation":"子女","age":35,"alive":True,"father":"陳志明","mother":"王春嬌","dod":""},
    {"name":"陳小芳","relation":"子女","age":32,"alive":True,"father":"陳志明","mother":"王春嬌","dod":""},
]
DEMO_ASSETS = []

def N(s): return s.strip() if isinstance(s,str) else ""

if "family" not in st.session_state: st.session_state.family = DEMO_FAMILY.copy()
if "assets" not in st.session_state: st.session_state.assets = DEMO_ASSETS.copy()
if "unions" not in st.session_state: st.session_state.unions = []  # {"a","b","type"}

def age_of(name):
    m = next((x for x in st.session_state.family if x["name"]==name), None)
    return int(m.get("age",0)) if m else 0

def label_of(mem):
    if mem.get("alive",True):
        return mem["name"]
    return f'{mem["name"]} ✝{N(mem.get("dod","")) or "不在世"}'

# ---------- 快捷 ----------
c1,c2 = st.columns(2)
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

st.divider()

# ---------- Step 1 成員 ----------
st.header("Step 1. 家族成員")
all_names = [m["name"] for m in st.session_state.family]
with st.form("add_member"):
    c = st.columns(6)
    name     = c[0].text_input("姓名")
    relation = c[1].selectbox("關係",["本人","配偶(現任)","前配偶","伴侶","子女","子女之配偶","孫子","孫女","孫輩之配偶","其他"], index=4)
    age      = c[2].number_input("年齡",0,120,30)
    alive    = c[3].checkbox("在世",True)
    father   = c[4].selectbox("父（選填）",[""]+all_names)
    mother   = c[5].selectbox("母（選填）",[""]+all_names)
    ok = st.form_submit_button("➕ 新增")
    if ok:
        name=N(name)
        if not name:
            st.error("請輸入姓名")
        elif any(m["name"]==name for m in st.session_state.family):
            st.error("姓名重複，請加註稱謂或別名")
        elif relation in {"子女","孫子","孫女"} and not (N(father) or N(mother)):
            st.error("子女/孫輩至少要有父或母")
        else:
            st.session_state.family.append({
                "name":name,"relation":relation,"age":age,"alive":alive,
                "father":N(father),"mother":N(mother),"dod":""
            })
            st.success(f"已新增：{name}")

if st.session_state.family:
    st.dataframe(pd.DataFrame(st.session_state.family), use_container_width=True)

st.divider()

# ---------- Step 1b 伴侶 ----------
st.header("Step 1b. 伴侶關係")
names = [m["name"] for m in st.session_state.family]
with st.form("add_union"):
    c = st.columns(4)
    a = c[0].selectbox("成員 A", names)
    b = c[1].selectbox("成員 B", names)
    t = c[2].selectbox("類型",["現任配偶","前配偶","伴侶"])
    ok = c[3].form_submit_button("建立配對")
    if ok:
        a,b=N(a),N(b)
        if not a or not b or a==b:
            st.error("請選擇不同的兩人")
        elif any({u["a"],u["b"]}=={a,b} for u in st.session_state.unions):
            st.warning("配對已存在")
        else:
            st.session_state.unions.append({"a":a,"b":b,"type":t})
            st.success(f"已配對：{a} ↔ {b}")

if st.session_state.unions:
    st.table(pd.DataFrame(st.session_state.unions))

st.divider()

# ---------- Step 1c 在世/逝世 ----------
st.header("Step 1c. 在世 / 逝世")
if st.session_state.family:
    who = st.selectbox("選擇成員", names, key="life_sel")
    m = next(x for x in st.session_state.family if x["name"]==who)
    c = st.columns(3)
    alive = c[0].checkbox("在世", value=bool(m.get("alive", True)))
    dod   = c[1].text_input("逝世日期(YYYY-MM-DD/可空)", value=m.get("dod",""))
    if c[2].button("儲存"):
        m["alive"] = alive
        m["dod"] = N(dod)
        st.success("已更新")

st.divider()

# ===================== 新：決定式 SVG 畫家族樹 =====================
st.header("Step 3. 家族樹（只顯示姓名｜穩定佈局）")

# 參數（外觀）
CELL_W, CELL_H = 160, 84      # 人名框寬高
H_GAP, V_GAP   = 36, 70       # 同代水平間距、代與代之間距
BAR_W          = 46           # 婚姻/單親橫桿長度
RADIUS         = 12           # 人名框圓角

def build_generations(fam):
    """本人=0；父母-1；子女+1（收斂）"""
    people={m["name"]:m for m in fam}; existing=set(people)
    parent_of=defaultdict(set); child_of=defaultdict(set)
    for m in fam:
        n=m["name"]; f,mo=N(m.get("father","")),N(m.get("mother",""))
        if f in existing: parent_of[f].add(n); child_of[n].add(f)
        if mo in existing: parent_of[mo].add(n); child_of[n].add(mo)
    gen={}
    for m in fam:
        if m.get("relation")=="本人": gen[m["name"]]=0
    changed=True; loops=0
    while changed and loops<10*max(1,len(fam)):
        changed=False; loops+=1
        for p,kids in parent_of.items():
            if p in gen:
                for k in kids:
                    want=gen[p]+1
                    if gen.get(k)!=want: gen[k]=want; changed=True
        for c,ps in child_of.items():
            if c in gen:
                for p in ps:
                    want=gen[c]-1
                    if gen.get(p)!=want: gen[p]=want; changed=True
    FALLBACK={"本人":0,"配偶(現任)":0,"前配偶":0,"伴侶":0,"子女":1,"子女之配偶":1,"孫子":2,"孫女":2}
    for m in fam: gen.setdefault(m["name"], FALLBACK.get(m.get("relation","其他"),0))
    return gen

def compute_blocks(fam, unions):
    """
    回傳：
      pairs: { (a,b) 冰凍集合 : {"parents":[a,b], "gen":g, "children":[...]} }
      singles: { p : {"parent":p, "gen":g, "children":[...]} }
    孩子只會出現在其中一種：雙親已知 -> pairs；否則 -> singles[已知父或母]
    """
    people={m["name"]:m for m in fam}; existing=set(people)
    gen = build_generations(fam)

    # 顯式配對（現任/前配偶/伴侶），也視為一組 parents 區塊
    pair_type = {}
    for u in unions:
        a,b = N(u["a"]), N(u["b"])
        if a in existing and b in existing and a!=b:
            key=frozenset((a,b))
            pair_type[key]=u.get("type","伴侶")

    # 由孩子推論的生父母配對
    for m in fam:
        f,mo=N(m.get("father","")),N(m.get("mother",""))
        if f in existing and mo in existing and f and mo:
            key=frozenset((f,mo))
            pair_type.setdefault(key,"生物父母")

    # collect children
    pairs = {}
    singles = defaultdict(lambda: {"children":[],"gen":0})
    for key, typ in pair_type.items():
        a,b = tuple(key)
        g = min(gen.get(a,0), gen.get(b,0))
        pairs[key] = {"parents":[a,b],"gen":g,"children":[],"type":typ}

    for m in fam:
        c=m["name"]; f,mo=N(m.get("father","")),N(m.get("mother",""))
        if f and mo and f in existing and mo in existing:
            key=frozenset((f,mo))
            if key in pairs: pairs[key]["children"].append(c)
        else:
            if f in existing: 
                singles[f]["children"].append(c); singles[f]["gen"]=gen.get(f,0)
            if mo in existing:
                singles[mo]["children"].append(c); singles[mo]["gen"]=gen.get(mo,0)

    # 排序孩子（歲大在左）
    for p in pairs.values():
        p["children"].sort(key=lambda n: age_of(n), reverse=True)
    for s in singles.values():
        s["children"].sort(key=lambda n: age_of(n), reverse=True)

    return gen, pairs, singles

def layout_and_svg(fam, unions):
    if not fam: return "<p>尚無資料</p>"

    people={m["name"]:m for m in fam}
    gen, pairs, singles = compute_blocks(fam, unions)

    # 每一代的「父母區塊順序」：以本人所在區塊優先，其餘依父母姓名、再依長子年齡排序
    blocks_by_gen = defaultdict(list)
    def eldest_age(children): return max((age_of(x) for x in children), default=-1)

    # 生成所有區塊（pair、single）
    for k,p in pairs.items():
        blocks_by_gen[p["gen"]].append(("pair", tuple(sorted(p["parents"])), p))
    for parent,s in singles.items():
        blocks_by_gen[s["gen"]].append(("single", (parent,), s))

    # 找到「本人」
    me = next((m["name"] for m in fam if m.get("relation")=="本人"), None)

    for g in blocks_by_gen:
        def key_func(item):
            kind, parents, data = item
            score0 = 0
            if me and me in parents: score0 = -999999  # 本人優先
            # 第二排序：父/母姓名（穩定且可預期）
            name_key = ",".join(parents)
            # 第三排序：孩子最大年齡（歲大靠左）
            eldest = -eldest_age(data["children"])
            return (score0, name_key, eldest)
        blocks_by_gen[g].sort(key=key_func)

    # 佈局座標（欄位）
    pos = {}           # person -> (col,row)
    bars = []          # [(x,y,kind,width,parents,children)]
    max_col = 0
    min_g = min(gen.values() or [0]); max_g = max(gen.values() or [0])

    # 為每一代從左到右排區塊；孩子直接落在下代連續欄位
    next_child_col = defaultdict(int)  # g+1 的下一個可用欄位

    for g in range(min_g, max_g+1):
        col_cursor = 0
        for kind, parents, data in blocks_by_gen.get(g, []):
            # 區塊中心（以孩子數量決定寬度，至少 1）
            kids = data["children"]
            width_k = max(1, len(kids))
            x_start_child = next_child_col[g+1]
            next_child_col[g+1] += width_k
            col_center = x_start_child + (width_k-1)/2

            # 放父母人名（相鄰）
            if kind=="pair":
                a,b = parents
                # 左右各佔 0.5 欄（視覺靠近）
                pos.setdefault(a, (col_center-0.3, g))
                pos.setdefault(b, (col_center+0.3, g))
                # 婚姻橫桿
                bars.append((col_center, g+0.35, "pair", BAR_W, parents, kids))
            else:
                p = parents[0]
                pos.setdefault(p, (col_center, g))
                bars.append((col_center, g+0.35, "single", BAR_W*0.7, parents, kids))

            # 放孩子
            for i, c in enumerate(kids):
                pos.setdefault(c, (x_start_child+i, g+1))
            col_cursor = max(col_cursor, next_child_col[g+1])
            max_col = max(max_col, col_cursor)

    # 若某些人沒有孩子也沒有被任何區塊覆蓋到（例如另一支系），也排入該代右側
    placed = set(pos.keys())
    leftovers_by_gen = defaultdict(list)
    for n,m in people.items():
        if n not in placed:
            leftovers_by_gen[gen.get(n,0)].append(n)
    for g, arr in leftovers_by_gen.items():
        arr.sort(key=lambda n:(n!="本人",-age_of(n),n))
        for n in arr:
            x = next_child_col[g]
            pos[n]=(x,g); next_child_col[g]+=1; max_col=max(max_col, next_child_col[g])

    # ---------- 輸出 SVG ----------
    # 計算畫布大小
    cols = max_col+1
    rows = (max_g - min_g + 1) + 1  # 可能用到 g+1
    W = int(cols*CELL_W + (cols+1)*H_GAP)
    H = int(rows*CELL_H + (rows+1)*V_GAP)

    def to_xy(col,row):
        x = int(H_GAP + col*CELL_W + col*H_GAP)
        y = int(V_GAP + (row-min_g)*CELL_H + (row-min_g)*V_GAP)
        return x,y

    def person_rect(name):
        m = people[name]
        x,y = to_xy(*pos[name])
        w,h = CELL_W, CELL_H
        rx,ry = RADIUS, RADIUS
        alive = bool(m.get("alive",True))
        is_me = (m.get("relation")=="本人")
        fill = "#f7e08c" if is_me and alive else ("#eeeeee" if not alive else "#e7e7e7")
        stroke = "#a0a0a0" if not alive else "#333"
        dash = ' stroke-dasharray="6,5"' if not alive else ""
        label = html.escape(label_of(m))
        return f'''
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>
  <text x="{x+w/2}" y="{y+h/2+6}" text-anchor="middle" font-family="Noto Sans CJK TC, PingFang TC, Microsoft JhengHei" font-size="18" fill="#222">{label}</text>
'''

    def hline(x1,y1,x2):
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y1}" stroke="#222" stroke-width="2"/>'
    def vline(x1,y1,y2):
        return f'<line x1="{x1}" y1="{y1}" x2="{x1}" y2="{y2}" stroke="#222" stroke-width="2"/>'

    svg = [f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg">']

    # 先畫連線（由上到下）
    # 1) 父母人名框到底部（到婚姻/單親桿）
    for cx, gy, kind, barw, parents, kids in bars:
        bx, by = to_xy(cx, gy)
        # 直線：父/母 -> 桿
        if kind=="pair":
            a,b = parents
            ax,ay = to_xy(*pos[a]); bx1, by1 = ax + CELL_W/2, ay + CELL_H
            bx2, by2 = bx, by
            svg.append(vline(bx1, by1, by2))
            ax,ay = to_xy(*pos[b]); bx1, by1 = ax + CELL_W/2, ay + CELL_H
            svg.append(vline(bx1, by1, by2))
            # 橫桿
            svg.append(hline(bx - barw/2, by, bx + barw/2))
        else:
            p = parents[0]
            ax,ay = to_xy(*pos[p]); bx1, by1 = ax + CELL_W/2, ay + CELL_H
            svg.append(vline(bx1, by1, by))
            svg.append(hline(bx - barw/2, by, bx + barw/2))

        # 2) 桿 -> 每個孩子頂部
        for c in kids:
            cx2, cy2 = to_xy(*pos[c])
            svg.append(vline(bx, by, cy2))  # 垂直到孩子那一列
            # 再短水平接到孩子中線
            svg.append(hline(min(bx, cx2 + CELL_W/2), cy2, max(bx, cx2 + CELL_W/2)))

    # 3) 畫人名框（在連線之上）
    for name in sorted(pos, key=lambda n:(pos[n][1], pos[n][0])):
        svg.append(person_rect(name))

    # 頁尾
    svg.append('</svg>')
    return "\n".join(svg)

svg = layout_and_svg(st.session_state.family, st.session_state.unions)
st.markdown(svg, unsafe_allow_html=True)

st.divider()
st.markdown("🌐 [gracefo.com](https://gracefo.com) 　｜　《影響力》傳承策略平台｜永傳家族辦公室")
