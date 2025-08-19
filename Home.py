def layout_and_svg(fam, unions):
    if not fam: return "<p>尚無資料</p>"

    people={m["name"]:m for m in fam}
    gen, pairs, singles = compute_blocks(fam, unions)

    # 將「有孩子的雙親/單親」與「純配偶（沒孩子或尚未登錄孩子）」拆開
    parent_pairs = {k:v for k,v in pairs.items() if len(v["children"])>0}
    other_pairs  = [u for u in unions if frozenset((N(u["a"]),N(u["b"]))) not in parent_pairs]

    # 準備佈局容器
    pos   = {}               # person -> (col,row)（col 允許小數，方便左右相鄰）
    bars  = []               # (center_col, row+0.35, kind, width, parents, kids)
    max_col = 0

    min_g = min(gen.values() or [0]); max_g = max(gen.values() or [0])
    # 每一代下一個「孩子欄位」指標；以及純人名的空欄位指標（不影響孩子）
    next_child_col = {g:0 for g in range(min_g, max_g+2)}
    next_free_col  = {g:0 for g in range(min_g, max_g+1)}

    # ---------- Phase A：先排「會生孩子的」父母區塊 ----------
    # 1) 雙親
    for k, p in sorted(parent_pairs.items(), key=lambda kv:(kv[1]["gen"], ",".join(sorted(kv[0])))):
        a,b = tuple(k)
        g   = p["gen"]
        kids = p["children"]

        # 把孩子放在 g+1 代的連續欄位
        start = next_child_col[g+1]
        for i, c in enumerate(kids):
            if c not in pos:
                pos[c] = (start+i, g+1)
        next_child_col[g+1] += max(1, len(kids))

        # 父母置中在孩子群上方
        center = start + (max(1,len(kids)) - 1) / 2
        if a not in pos: pos[a] = (center-0.35, g)
        if b not in pos: pos[b] = (center+0.35, g)
        bars.append((center, g+0.35, "pair", BAR_W, (a,b), kids))
        max_col = max(max_col, next_child_col[g+1])

    # 2) 單親
    for parent, s in sorted(singles.items(), key=lambda kv:(kv[1]["gen"], kv[0])):
        kids = s["children"]
        if not kids:  # 沒孩子的單親不需要橫桿，等會當作普通人名處理
            continue
        g = s["gen"]
        start = next_child_col[g+1]
        for i, c in enumerate(kids):
            if c not in pos:
                pos[c] = (start+i, g+1)
        next_child_col[g+1] += max(1, len(kids))

        center = start + (max(1,len(kids)) - 1)/2
        if parent not in pos: pos[parent] = (center, g)
        bars.append((center, g+0.35, "single", BAR_W*0.7, (parent,), kids))
        max_col = max(max_col, next_child_col[g+1])

    # ---------- Phase B：再排「純配偶／其它配對」讓配偶緊貼本人 ----------
    for u in sorted(unions, key=lambda x:min(gen.get(N(x["a"]),0), gen.get(N(x["b"]),0))):
        a, b = N(u["a"]), N(u["b"])
        if not a or not b or a==b: 
            continue
        g = min(gen.get(a,0), gen.get(b,0))
        key = frozenset((a,b))
        # 已在 parent_pairs 畫過婚姻桿的仍補一條配偶實線，但不再重新分配孩子
        if key in parent_pairs:
            # 確保父母相鄰（萬一一方還沒定位）
            if a in pos and b not in pos:
                pos[b] = (pos[a][0]+0.7, g)
            elif b in pos and a not in pos:
                pos[a] = (pos[b][0]-0.7, g)
            else:
                # 兩者都在，略
                pass
            # 婚姻橫桿已在 Phase A 生成；這裡不再加 bars
            continue

        # 純配偶／無孩子的配對：緊貼本人
        if a in pos and b not in pos:
            pos[b] = (pos[a][0]+0.7, g)
            center = (pos[a][0]+pos[b][0])/2
        elif b in pos and a not in pos:
            pos[a] = (pos[b][0]-0.7, g)
            center = (pos[a][0]+pos[b][0])/2
        elif a in pos and b in pos:
            center = (pos[a][0]+pos[b][0])/2
        else:
            # 兩人都還沒位置，開新欄位
            c0 = next_free_col[g]
            pos[a] = (c0-0.35, g)
            pos[b] = (c0+0.35, g)
            next_free_col[g] += 1
            center = c0

        bars.append((center, g+0.35, "pair_only", BAR_W*0.8, (a,b), []))
        max_col = max(max_col, next_free_col[g])

    # ---------- Phase C：把尚未出現的人名補上（例如沒配偶沒孩子的成員） ----------
    placed = set(pos.keys())
    leftovers_by_gen = defaultdict(list)
    for n,m in people.items():
        if n not in placed:
            leftovers_by_gen[gen.get(n,0)].append(n)
    for g, arr in leftovers_by_gen.items():
        arr.sort(key=lambda n:(n!="本人",-age_of(n),n))
        for n in arr:
            col = next_free_col[g]
            pos[n]=(col, g)
            next_free_col[g]+=1
            max_col = max(max_col, next_free_col[g])

    # ---------- 繪製 SVG ----------
    cols = int(max(max_col, *(c for c,_ in pos.values())) + 2)
    rows = (max_g - min_g + 1) + 1
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
        fill = "#f7e08c" if (is_me and alive) else ("#eeeeee" if not alive else "#e7e7e7")
        stroke = "#a0a0a0" if not alive else "#333"
        dash = ' stroke-dasharray="6,5"' if not alive else ""
        label = html.escape(label_of(m))
        return f'''
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>
  <text x="{x+w/2}" y="{y+h/2+6}" text-anchor="middle" font-family="Noto Sans CJK TC, Microsoft JhengHei" font-size="18" fill="#222">{label}</text>
'''

    def hline(x1,y1,x2):
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y1}" stroke="#222" stroke-width="2"/>'
    def vline(x1,y1,y2):
        return f'<line x1="{x1}" y1="{y1}" x2="{x1}" y2="{y2}" stroke="#222" stroke-width="2"/>'

    svg = [f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg">']

    # 線條（先）
    for center, rY, kind, barw, parents, kids in bars:
        bx, by = to_xy(center, rY)
        if kind.startswith("pair"):
            a,b = parents if len(parents)==2 else (parents[0], parents[0])
            # 兩人自下而上到婚姻桿
            ax,ay = to_xy(*pos[a]); svg.append(vline(ax+CELL_W/2, ay+CELL_H, by))
            if len(parents)==2:
                bx2,by2 = to_xy(*pos[b]); svg.append(vline(bx2+CELL_W/2, by2+CELL_H, by))
            # 婚姻橫桿
            svg.append(hline(bx - barw/2, by, bx + barw/2))
        else:  # single
            p = parents[0]
            px,py = to_xy(*pos[p]); svg.append(vline(px+CELL_W/2, py+CELL_H, by))
            svg.append(hline(bx - barw/2, by, bx + barw/2))

        # 從桿垂直到孩子列，再短水平接到孩子中線
        for c in kids:
            cx, cy = to_xy(*pos[c])
            svg.append(vline(bx, by, cy))
            svg.append(hline(min(bx, cx + CELL_W/2), cy, max(bx, cx + CELL_W/2)))

    # 人名框（後）
    for name in sorted(pos, key=lambda n:(pos[n][1], pos[n][0])):
        svg.append(person_rect(name))

    svg.append('</svg>')
    return "\n".join(svg)
