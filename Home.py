# Home.py  — 家族樹（穩定版：婚姻/單親橫桿｜決定式 SVG 佈局 + 性別底色）
import math
import html
import streamlit as st
import pandas as pd
from collections import defaultdict

# ===== 站點與聯絡資訊（可自行修改） =====
FOOTER_SITE  = "https://gracefo.com"
FOOTER_EMAIL = "service@gracefo.com"   # ← 換成你的 email

# ===== Streamlit 基本設定 =====
st.set_page_config(page_title="家族盤點｜傳承樹", page_icon="🌳", layout="wide")
st.title("Step 3. 家族樹（只顯示姓名｜穩定佈局）")

# ===== Demo 初始資料（加上 gender） =====
# gender: "男" / "女" / "其他/未知"
DEMO_FAMILY = [
    {"name":"陳志明","gender":"男","relation":"本人","age":65,"alive":True,"father":"","mother":"","dod":""},
    {"name":"王春嬌","gender":"女","relation":"配偶(現任)","age":62,"alive":True,"father":"","mother":"","dod":""},
    {"name":"陳小明","gender":"男","relation":"子女","age":35,"alive":True,"father":"陳志明","mother":"王春嬌","dod":""},
    {"name":"陳小芳","gender":"女","relation":"子女","age":32,"alive":True,"father":"陳志明","mother":"王春嬌","dod":""},
]
DEMO_ASSETS = []

# ===== 小工具 =====
def N(s): return s.strip() if isinstance(s,str) else ""

def age_of(name):
    m = next((x for x in st.session_state.family if x["name"]==name), None)
    return int(m.get("age",0)) if m else 0

def label_of(mem):
    if mem.get("alive",True):
        return mem["name"]
    return f'{mem["name"]} ✝{N(mem.get("dod","")) or "不在世"}'

# ===== Session State =====
if "family" not in st.session_state: st.session_state.family = DEMO_FAMILY.copy()
if "assets" not in st.session_state: st.session_state.assets = DEMO_ASSETS.copy()
if "unions" not in st.session_state: st.session_state.unions = []  # {"a","b","type"}

# 舊資料若沒有 gender，補上預設
for m in st.session_state.family:
    if "gender" not in m:
        m["gender"] = "其他/未知"

# ===== 快捷按鈕 =====
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

# ===== Step 1：家族成員 =====
st.header("Step 1. 家族成員")
all_names = [m["name"] for m in st.session_state.family]
with st.form("add_member"):
    c = st.columns(7)
    name     = c[0].text_input("姓名")
    gender   = c[1].selectbox("性別", ["男","女","其他/未知"], index=0)
    relation = c[2].selectbox("關係",["本人","配偶(現任)","前配偶","伴侶","子女","子女之配偶","孫子","孫女","孫輩之配偶","其他"], index=4)
    age      = c[3].number_input("年齡",0,120,30)
    alive    = c[4].checkbox("在世",True)
    father   = c[5].selectbox("父（選填）",[""]+all_names)
    mother   = c[6].selectbox("母（選填）",[""]+all_names)
    ok = st.form_submit_button("➕ 新增")
    if ok:
        name=N(name)
        if not name:
            st.error("請輸入姓名")
        elif any(m["name"]==name for m in st.session_state.family):
            st.error("姓名重複，請加註稱謂或別名")
        elif relation in {"子女","孫子","孫女"} and not (N(father) or N(mother)):
            st.error("子女/孫輩至少需指定父或母")
        else:
            st.session_state.family.append({
                "name":name,"gender":gender,"relation":relation,"age":age,"alive":alive,
                "father":N(father),"mother":N(mother),"dod":""
            })
            st.success(f"已新增：{name}")

if st.session_state.family:
    st.dataframe(pd.DataFrame(st.session_state.family), use_container_width=True)

st.divider()

# ===== Step 1b：伴侶關係 =====
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

# ===== Step 1c：在世 / 逝世 =====
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

# ===== 佈局核心 =====
CELL_W, CELL_H = 160, 84    # 人名框
H_GAP, V_GAP   = 36, 70     # 間距
BAR_W          = 46
RADIUS         = 12

def build_generations(fam):
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
    people={m["name"]:m for m in fam}; existing=set(people)
    gen = build_generations(fam)

    # 顯式配對 + 由子女推論生父母配對
    pair_type={}
    for u in unions:
        a,b=N(u["a"]),N(u["b"])
        if a in existing and b in existing and a!=b:
            pair_type[frozenset((a,b))]=u.get("type","伴侶")
    for m in fam:
        f,mo=N(m.get("father","")),N(m.get("mother",""))
        if f in existing and mo in existing and f and mo:
            pair_type.setdefault(frozenset((f,mo)),"生物父母")

    pairs={}
    singles=defaultdict(lambda:{"children":[],"gen":0})
    for key,typ in pair_type.items():
        a,b = tuple(key)
        g   = min(gen.get(a,0), gen.get(b,0))
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

    for p in pairs.values():
        p["children"].sort(key=lambda n:age_of(n), reverse=True)
    for s in singles.values():
        s["children"].sort(key=lambda n:age_of(n), reverse=True)

    return gen, pairs, singles

def layout_and_svg(fam, unions):
    if not fam: return "<p>尚無資料</p>"

    people={m["name"]:m for m in fam}
    gen, pairs, singles = compute_blocks(fam, unions)

    # 拆出「有孩子的雙親/單親」與「其它純配偶」
    parent_pairs = {k:v for k,v in pairs.items() if len(v["children"])>0}

    pos   = {}   # person -> (col,row)（col 允許小數）
    bars  = []   # (center_col, row+0.35, kind, width, parents, kids)
    max_col = 0

    min_g = min(gen.values() or [0]); max_g = max(gen.values() or [0])
    next_child_col = {g:0 for g in range(min_g, max_g+2)}
    next_free_col  = {g:0 for g in range(min_g, max_g+1)}

    # A. 會生孩子的父母區塊：先放孩子，再置中父母/單親
    for k, p in sorted(parent_pairs.items(), key=lambda kv:(kv[1]["gen"], ",".join(sorted(kv[0])))):
        a,b = tuple(k); g=p["gen"]; kids=p["children"]
        start = next_child_col[g+1]
        for i,c in enumerate(kids):
            if c not in pos: pos[c]=(start+i, g+1)
        next_child_col[g+1] += max(1,len(kids))

        center = start + (max(1,len(kids))-1)/2
        if a not in pos: pos[a]=(center-0.35, g)
        if b not in pos: pos[b]=(center+0.35, g)
        bars.append((center, g+0.35, "pair", BAR_W, (a,b), kids))
        max_col = max(max_col, next_child_col[g+1])

    for parent, s in sorted(singles.items(), key=lambda kv:(kv[1]["gen"], kv[0])):
        kids=s["children"]
        if not kids: continue
        g=s["gen"]
        start = next_child_col[g+1]
        for i,c in enumerate(kids):
            if c not in pos: pos[c]=(start+i, g+1)
        next_child_col[g+1] += max(1,len(kids))
        center = start + (max(1,len(kids))-1)/2
        if parent not in pos: pos[parent]=(center, g)
        bars.append((center, g+0.35, "single", BAR_W*0.7, (parent,), kids))
        max_col = max(max_col, next_child_col[g+1])

    # B. 其它純配偶：緊貼本人
    for u in sorted(unions, key=lambda x:min(gen.get(N(x["a"]),0), gen.get(N(x["b"]),0))):
        a,b=N(u["a"]),N(u["b"])
        if not a or not b or a==b: continue
        g=min(gen.get(a,0),gen.get(b,0))
        key=frozenset((a,b))
        if key in parent_pairs:
            if a in pos and b not in pos: pos[b]=(pos[a][0]+0.7, g)
            elif b in pos and a not in pos: pos[a]=(pos[b][0]-0.7, g)
            continue
        if a in pos and b not in pos:
            pos[b]=(pos[a][0]+0.7, g); center=(pos[a][0]+pos[b][0])/2
        elif b in pos and a not in pos:
            pos[a]=(pos[b][0]-0.7, g); center=(pos[a][0]+pos[b][0])/2
        elif a in pos and b in pos:
            center=(pos[a][0]+pos[b][0])/2
        else:
            c0=next_free_col[g]
            pos[a]=(c0-0.35, g); pos[b]=(c0+0.35, g)
            next_free_col[g]+=1; center=c0
        bars.append((center, g+0.35, "pair_only", BAR_W*0.8, (a,b), []))
        max_col = max(max_col, next_free_col[g])

    # C. 沒有配偶也沒有孩子的人名，補到該代右側
    placed=set(pos.keys())
    leftovers=defaultdict(list)
    for n in people:
        if n not in placed:
            leftovers[gen.get(n,0)].append(n)
    for g, arr in leftovers.items():
        arr.sort(key=lambda n:(n!="本人",-age_of(n),n))
        for n in arr:
            col=next_free_col[g]
            pos[n]=(col,g); next_free_col[g]+=1
            max_col=max(max_col,next_free_col[g])

    # --- SVG 輸出 ---
    max_col_from_pos = max([p[0] for p in pos.values()]) if pos else 0
    cols = int(math.ceil(max(max_col, max_col_from_pos) + 2))
    rows = (max_g - min_g + 1) + 1
    W = int(cols*CELL_W + (cols+1)*H_GAP)
    H = int(rows*CELL_H + (rows+1)*V_GAP)

    def to_xy(col,row):
        x = int(H_GAP + col*CELL_W + col*H_GAP)
        y = int(V_GAP + (row-min_g)*CELL_H + (row-min_g)*V_GAP)
        return x,y

    def fill_color(member):
        """底色規則：亡者淺灰；男性淺粉藍；女性淺粉紅；其他/未知極淺灰"""
        if not member.get("alive", True):
            return "#eeeeee"
        g = member.get("gender","其他/未知")
        if g == "男":
            return "#dbeafe"   # 淺粉藍
        if g == "女":
            return "#ffe4e8"   # 淺粉紅
        return "#f3f4f6"       # 中性極淺灰

    def person_rect(name):
        m = people[name]
        x,y = to_xy(*pos[name])
        w,h = CELL_W, CELL_H
        rx,ry = RADIUS, RADIUS
        alive = bool(m.get("alive",True))
        fill = fill_color(m)
        stroke = "#a0a0a0" if not alive else "#333"
        dash = ' stroke-dasharray="6,5"' if not alive else ""
        label = html.escape(label_of(m))
        return f'''
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>
  <text x="{x+w/2}" y="{y+h/2+6}" text-anchor="middle" font-family="Noto Sans CJK TC, Microsoft JhengHei" font-size="18" fill="#222">{label}</text>
'''

    def hline(x1,y1,x2): return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y1}" stroke="#222" stroke-width="2"/>'
    def vline(x1,y1,y2): return f'<line x1="{x1}" y1="{y1}" x2="{x1}" y2="{y2}" stroke="#222" stroke-width="2"/>'

    svg = [f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg">']

    # 先畫線
    for center, rY, kind, barw, parents, kids in bars:
        bx, by = to_xy(center, rY)
        if kind.startswith("pair"):
            a,b = parents if len(parents)==2 else (parents[0], parents[0])
            ax,ay = to_xy(*pos[a]); svg.append(vline(ax+CELL_W/2, ay+CELL_H, by))
            if len(parents)==2:
                bx2,by2 = to_xy(*pos[b]); svg.append(vline(bx2+CELL_W/2, by2+CELL_H, by))
            svg.append(hline(bx - barw/2, by, bx + barw/2))
        else:  # single
            p = parents[0]
            px,py = to_xy(*pos[p]); svg.append(vline(px+CELL_W/2, py+CELL_H, by))
            svg.append(hline(bx - barw/2, by, bx + barw/2))
        for c in kids:
            cx, cy = to_xy(*pos[c])
            svg.append(vline(bx, by, cy))
            svg.append(hline(min(bx, cx + CELL_W/2), cy, max(bx, cx + CELL_W/2)))

    # 再畫人名框
    for name in sorted(pos, key=lambda n:(pos[n][1], pos[n][0])):
        svg.append(person_rect(name))

    svg.append('</svg>')
    return "\n".join(svg)

# ===== 繪圖 =====
svg = layout_and_svg(st.session_state.family, st.session_state.unions)
st.markdown(svg, unsafe_allow_html=True)

st.divider()
st.markdown(
    f'🌐 <a href="{FOOTER_SITE}" target="_blank">{FOOTER_SITE.replace("https://","").replace("http://","")}</a>　｜　'
    f'✉️ <a href="mailto:{FOOTER_EMAIL}">{FOOTER_EMAIL}</a>　｜　《影響力》傳承策略平台｜永傳家族辦公室',
    unsafe_allow_html=True
)
