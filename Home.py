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

def name_exists(n: str) -> bool:
    return any(m["name"] == n for m in st.session_state["family"])

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

            # 自動建立伴侶配對（夫妻橫桿＋幹線）
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
# Step 3: 家族樹（重構版：結構清晰，連線穩定）
# =============================
st.header("Step 3. 家族樹（世代清楚、上下分層）")

if st.session_state["family"]:
    dot = Digraph(comment='Family Tree')
    dot.attr(
        rankdir="TB",      # 由上到下繪製
        splines="ortho",     # 使用直角連接線
        nodesep="0.6",     # 節點間最小間距
        ranksep="1.0",     # 層級間最小間距
        newrank="true"
    )
    dot.attr('node', shape='box', style='rounded,filled', fontname="Microsoft JhengHei") # 預設節點樣式
    dot.attr('edge', arrowhead='none') # 預設邊線樣式

    # --- 1. 建立所有成員節點 ---
    # 同時按世代分組，方便後續處理
    generations = defaultdict(list)
    member_map = {m["name"]: m for m in st.session_state["family"]}

    for name, member in member_map.items():
        # 節點標籤：包含姓名、關係、是否在世
        label = f"{name}\n({member['relation']}"
        if not member.get('alive', True):
            label += "・歿"
        label += ")"
        
        # 本人標示特殊顏色
        fillcolor = "#FFDDC1" if member["relation"] == "本人" else "#E8E8E8"
        
        dot.node(name, label, fillcolor=fillcolor)
        
        # 按世代分組
        gen = get_generation(member.get("relation", ""))
        generations[gen].append(name)

    # --- 2. 建立夫妻關係與同代排序 ---
    # 找出所有夫妻組合
    couples = set()
    for m in st.session_state["family"]:
        f = m.get("father", "").strip()
        m = m.get("mother", "").strip()
        if f and m and f in member_map and m in member_map:
            couples.add(tuple(sorted((f, m))))
    
    for u in st.session_state.get("unions", []):
        a = u.get("a", "").strip()
        b = u.get("b", "").strip()
        if a and b and a in member_map and b in member_map:
            couples.add(tuple(sorted((a, b))))

    # 為每一代建立一個子圖 (subgraph) 來確保他們在同一水平線上
    for gen_level in sorted(generations.keys()):
        with dot.subgraph() as s:
            s.attr(rank='same')
            # 將該世代的所有人加入子圖
            for name in generations[gen_level]:
                s.node(name)

    # --- 3. 建立親子之間的連線 ---
    children_by_parents = defaultdict(list)
    for name, member in member_map.items():
        f = member.get("father", "").strip()
        m = member.get("mother", "").strip()

        # 有雙親的情況
        if f and m and f in member_map and m in member_map:
            parent_key = tuple(sorted((f, m)))
            children_by_parents[parent_key].append(name)
        # 僅有單親的情況
        elif (f and f in member_map and not m):
            dot.edge(f, name)
        elif (m and m in member_map and not f):
            dot.edge(m, name)

    # 處理有雙親的家庭單位
    for parent_tuple, children in children_by_parents.items():
        p1, p2 = parent_tuple
        
        # 建立一個隱形的 "家庭中心點"
        union_node_id = f"union_{p1}_{p2}"
        dot.node(union_node_id, shape='point', style='invis')

        # 父母連接到中心點
        dot.edge(p1, union_node_id)
        dot.edge(p2, union_node_id)

        # 中心點連接到所有子女
        for child in children:
            dot.edge(union_node_id, child)
        
        # 確保夫妻和他們的中心點在同一層級
        with dot.subgraph() as s:
            s.attr(rank='same')
            s.node(p1)
            s.node(union_node_id)
            s.node(p2)
            # 用隱形邊確保 p1 -> 中心點 -> p2 的順序
            s.edge(p1, union_node_id, style='invis')
            s.edge(union_node_id, p2, style='invis')


    # --- 繪製圖形 ---
    try:
        st.graphviz_chart(dot)
    except Exception as e:
        st.error(f"繪製圖形時發生錯誤：{e}")
        st.code(dot.source) # 如果出錯，顯示原始碼方便除錯

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
