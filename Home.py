# Home.py — 家族樹（穩定佈局｜每人獨立，父/母各自連線｜性別底色）
import math
import html
import streamlit as st
import pandas as pd
from collections import defaultdict

# ===== 網站 & Email =====
FOOTER_SITE  = "https://gracefo.com"
FOOTER_EMAIL = "service@gracefo.com"

# ===== 基本設定 =====
st.set_page_config(page_title="家族盤點｜傳承樹", page_icon="🌳", layout="wide")
st.title("Step 3. 家族樹（只顯示姓名｜穩定佈局）")

# ===== Demo（含 gender）=====
DEMO_FAMILY = [
    {"name":"陳志明","gender":"男","relation":"本人","age":65,"alive":True,"father":"","mother":"","dod":""},
    {"name":"王春嬌","gender":"女","relation":"配偶(現任)","age":62,"alive":True,"father":"","mother":"","dod":""},
    {"name":"陳小明","gender":"男","relation":"子女","age":35,"alive":True,"father":"陳志明","mother":"王春嬌","dod":""},
    {"name":"陳小芳","gender":"女","relation":"子女","age":32,"alive":True,"father":"陳志明","mother":"王春嬌","dod":""},
]
DEMO_ASSETS = []

# ===== util =====
def N(s): return s.strip() if isinstance(s,str) else ""

def age_of(name):
    m = next((x for x in st.session_state.family if x["name"]==name), None)
    return int(m.get("age",0)) if m else 0

def label_of(mem):
    if mem.get("alive",True):
        return mem["name"]
    return f'{mem["name"]} ✝{N(mem.get("dod","")) or "不在世"}'

# ===== state =====
if "family" not in st.session_state: st.session_state.family = DEMO_FAMILY.copy()
if "assets" not in st.session_state: st.session_state.assets = DEMO_ASSETS.copy()
if "unions" not in st.session_state: st.session_state.unions = []     # {"a","b","type"}

# 兼容舊資料
for m in st.session_state.family:
    if "gender" not in m: m["gender"] = "其他/未知"

# ===== 快捷 =====
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

# ===== Step 1：成員 =====
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

# ===== Step 1c：在世/逝世 =====
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

# ===== 佈局核心（獨立節點；父/母各自連線；婚姻不參與排版）=====
CELL_W, CELL_H = 160, 84
H_GAP, V_GAP   = 36, 70
RADIUS         = 12

def build_generations(fam):
    """由親子關係推到代別；不足則用關係 fallback。"""
    people={m["name"] for m in fam}
    parent_of=defaultdict(set); child_of=defaultdict(set)
    for m in fam:
        n=m["name"]; f,mo=N(m.get("father","")),N(m.get("mother",""))
        if f in people: parent_of[f].add(n); child_of[n].add(f)
        if mo in people: parent_of[mo].add(n); child_of[n].add(mo)
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

def layout_independent(fam):
    """每個人獨立排版：同代依「父母平均 X（若可）」排序；不把夫妻綁成一塊。"""
    people={m["name"]:m for m in fam}
    gen = build_generations(fam)

    # 按代收集
    by_g=defaultdict(list)
    for n,g in gen.items(): by_g[g].append(n)
    min_g = min(by_g.keys()); max_g = max(by_g.keys())

    # 先隨機（按關係/年齡）給每代一個初始順序
    col = {}
    for g in range(min_g, max_g+1):
        arr = by_g[g]
        arr.sort(key=lambda n:(
            0 if people[n].get("relation")=="本人" else
            1 if "配偶" in people[n].get("relation","") or people[n].get("relation")=="伴侶" else
            2, -people[n].get("alive",True), -age_of(n), n))
        for i,n in enumerate(arr):
            col[n]=float(i)

    # 迭代 2~3 次：用「父母平均 X」微調每一代的順序（單親就用該親）
    for _ in range(3):
        for g in range(min_g+1, max_g+1):
            arr = by_g[g]
            def target_x(n):
                f=N(people[n].get("father","")); m=N(people[n].get("mother",""))
                xs=[]
                if f in col: xs.append(col[f])
                if m in col: xs.append(col[m])
                if xs: return sum(xs)/len(xs)
                return col[n]  # 沒父母位置就保持
            arr.sort(key=lambda n:(target_x(n), -age_of(n), n))
            for i,n in enumerate(arr):
                col[n]=float(i)

    # 座標
    pos={}
    for n,g in gen.items(): pos[n]=(col[n], g)
    return pos, gen

def draw_svg(fam, unions, pos, gen):
    people={m["name"]:m for m in fam}

    # 畫布大小
    min_g = min(gen.values()); max_g = max(gen.values())
    max_c = max(p[0] for p in pos.values()) if pos else 0
    cols  = int(math.ceil(max_c+2))
    rows  = (max_g - min_g + 1) + 1
    W = int(cols*CELL_W + (cols+1)*H_GAP)
    H = int(rows*CELL_H + (rows+1)*V_GAP)

    def to_xy(col,row):
        x = int(H_GAP + col*CELL_W + col*H_GAP)
        y = int(V_GAP + (row-min_g)*CELL_H + (row-min_g)*V_GAP)
        return x,y

    def fill_color(member):
        if not member.get("alive", True): return "#eeeeee"
        g = member.get("gender","其他/未知")
        if g=="男": return "#dbeafe"
        if g=="女": return "#ffe4e8"
        return "#f3f4f6"

    def person_rect(name):
        m = people[name]
        x,y = to_xy(*pos[name]); w,h= CELL_W,CELL_H
        rx,ry= RADIUS,RADIUS
        alive = bool(m.get("alive",True))
        fill = fill_color(m)
        stroke = "#a0a0a0" if not alive else "#333"
        dash = ' stroke-dasharray="6,5"' if not alive else ""
        label = html.escape(label_of(m))
        return f'''
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>
  <text x="{x+w/2}" y="{y+h/2+6}" text-anchor="middle" font-family="Noto Sans CJK TC, Microsoft JhengHei" font-size="18" fill="#222">{label}</text>
'''

    def hline(x1,y1,x2,w=2): return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y1}" stroke="#222" stroke-width="{w}"/>'
    def vline(x1,y1,y2,w=2): return f'<line x1="{x1}" y1="{y1}" x2="{x1}" y2="{y2}" stroke="#222" stroke-width="{w}"/>'

    svg=[f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg">']

    # 1) 親子連線：父/母各自用「L 型」連到孩子（不經由夫妻桿）
    for child,m in people.items():
        cx, cy = to_xy(*pos[child])
        xC = cx + CELL_W/2
        for parent_key in ("father","mother"):
            p = N(m.get(parent_key,""))
            if p and p in pos:
                px, py = to_xy(*pos[p]); xP = px + CELL_W/2
                y1 = py + CELL_H
                y2 = cy
                ymid = int((y1 + y2) / 2)
                svg.append(vline(xP, y1, ymid))
                svg.append(hline(min(xP, xC), ymid, max(xP, xC)))
                svg.append(vline(xC, ymid, y2))

    # 2) 婚姻連線（只示意兩人關係，不參與佈局；前配偶用虛線）
    for u in st.session_state.unions:
        a,b=N(u["a"]),N(u["b"])
        if a in pos and b in pos and gen.get(a)==gen.get(b):
            ax, ay = to_xy(*pos[a]); bx, by = to_xy(*pos[b])
            y = int((ay + by)/2) + CELL_H + 8
            x1 = ax + CELL_W/2; x2 = bx + CELL_W/2
            dashed = ' stroke-dasharray="6,6"' if "前配偶" in u.get("type","") else ""
            svg.append(f'<line x1="{min(x1,x2)}" y1="{y}" x2="{max(x1,x2)}" y2="{y}" stroke="#444" stroke-width="2"{dashed}/>')

    # 3) 人名框
    for name in sorted(pos, key=lambda n:(pos[n][1], pos[n][0])):
        svg.append(person_rect(name))

    svg.append("</svg>")
    return "\n".join(svg)

# === 產生與繪製 ===
pos, gen = layout_independent(st.session_state.family)
svg = draw_svg(st.session_state.family, st.session_state.unions, pos, gen)
st.markdown(svg, unsafe_allow_html=True)

st.divider()
st.markdown(
    f'🌐 <a href="{FOOTER_SITE}" target="_blank">{FOOTER_SITE.replace("https://","").replace("http://","")}</a>　｜　'
    f'✉️ <a href="mailto:{FOOTER_EMAIL}">{FOOTER_EMAIL}</a>　｜　《影響力》傳承策略平台｜永傳家族辦公室',
    unsafe_allow_html=True
)
