"""
forest.py
----------
SEED「未来の森」のSVG描画モジュール。
データベースから木のリストを受け取り、1枚のSVGコードを返す。
"""

from __future__ import annotations
import hashlib

# キャンバスサイズ
W, H = 1100, 520
GROUND_Y = 420  # 地面の高さ

# ----- 木のSVGパーツ(サイズ別に3段階) -----
# サイズ1: 芽、 サイズ2: 若木、 サイズ3: 大木

def _tree_svg(tree_type: str, size: int, cx: float, cy: float, seed_id: int) -> str:
    """1本の木のSVG文字列を返す。cx,cyは根元の位置。"""
    scale = {1: 0.45, 2: 0.75, 3: 1.0}.get(size, 0.5)
    # 高さの基準
    h = int(140 * scale)
    w = int(70 * scale)
    trunk_w = max(3, int(8 * scale))
    leaf = LEAF_RENDERERS.get(tree_type, _leaf_pine)
    return leaf(cx, cy, w, h, trunk_w, scale, seed_id)


# ---------- 各木の葉(冠)描画関数 ----------

def _trunk(cx: float, cy: float, h: int, trunk_w: int, color: str = "#5b4530") -> str:
    return (
        f'<rect x="{cx - trunk_w/2:.1f}" y="{cy - h*0.35:.1f}" '
        f'width="{trunk_w}" height="{h*0.35:.1f}" fill="{color}" rx="1"/>'
    )


def _leaf_pine(cx, cy, w, h, trunk_w, scale, seed_id):
    """松 — 三角形の重なり"""
    trunk = _trunk(cx, cy, h, trunk_w, "#4a3622")
    top_y = cy - h
    layers = []
    for i in range(3):
        y0 = top_y + i * (h * 0.22)
        ww = w * (0.5 + i * 0.18)
        layers.append(
            f'<polygon points="{cx:.1f},{y0:.1f} {cx-ww:.1f},{y0+h*0.32:.1f} {cx+ww:.1f},{y0+h*0.32:.1f}" '
            f'fill="#3a6a3f" stroke="#2c5132" stroke-width="0.7"/>'
        )
    return trunk + "".join(layers)


def _leaf_sakura(cx, cy, w, h, trunk_w, scale, seed_id):
    """桜 — ピンクの円+花"""
    trunk = _trunk(cx, cy, h, trunk_w, "#5a3a2a")
    cy2 = cy - h * 0.78
    ball = (
        f'<circle cx="{cx:.1f}" cy="{cy2:.1f}" r="{w*0.85:.1f}" fill="#f7c6d4" stroke="#e09bb3" stroke-width="0.6"/>'
        f'<circle cx="{cx-w*0.4:.1f}" cy="{cy2-h*0.05:.1f}" r="{w*0.55:.1f}" fill="#fadce5"/>'
        f'<circle cx="{cx+w*0.4:.1f}" cy="{cy2+h*0.05:.1f}" r="{w*0.5:.1f}" fill="#f7c6d4"/>'
    )
    return trunk + ball


def _leaf_oak(cx, cy, w, h, trunk_w, scale, seed_id):
    """樫 — 厚みのある楕円の冠"""
    trunk = _trunk(cx, cy, h, trunk_w, "#3e2c1a")
    cy2 = cy - h * 0.7
    crown = (
        f'<ellipse cx="{cx:.1f}" cy="{cy2:.1f}" rx="{w*1.0:.1f}" ry="{h*0.42:.1f}" '
        f'fill="#2f5d2c" stroke="#1f3f1d" stroke-width="0.7"/>'
        f'<ellipse cx="{cx-w*0.35:.1f}" cy="{cy2-h*0.12:.1f}" rx="{w*0.5:.1f}" ry="{h*0.22:.1f}" fill="#3a6e36"/>'
        f'<ellipse cx="{cx+w*0.4:.1f}" cy="{cy2-h*0.05:.1f}" rx="{w*0.45:.1f}" ry="{h*0.20:.1f}" fill="#386b34"/>'
    )
    return trunk + crown


def _leaf_willow(cx, cy, w, h, trunk_w, scale, seed_id):
    """柳 — 垂れ下がる葉"""
    trunk = _trunk(cx, cy, h, trunk_w, "#5d4630")
    top = cy - h
    strands = []
    for i in range(7):
        x0 = cx - w*0.5 + i * (w / 6)
        ctrl_x = x0 + (-1 if i < 3 else 1) * 5
        end_y = top + h * (0.6 + (i % 3) * 0.07)
        strands.append(
            f'<path d="M{x0:.1f},{top+h*0.15:.1f} Q{ctrl_x:.1f},{(top+end_y)/2:.1f} {x0:.1f},{end_y:.1f}" '
            f'stroke="#7ba968" stroke-width="1.2" fill="none" opacity="0.85"/>'
        )
    cap = (
        f'<ellipse cx="{cx:.1f}" cy="{top+h*0.18:.1f}" rx="{w*0.55:.1f}" ry="{h*0.12:.1f}" fill="#7ba968"/>'
    )
    return trunk + cap + "".join(strands)


def _leaf_ginkgo(cx, cy, w, h, trunk_w, scale, seed_id):
    """銀杏 — 黄色い扇形の葉が重なる"""
    trunk = _trunk(cx, cy, h, trunk_w, "#4a3a22")
    cy2 = cy - h * 0.72
    crown = (
        f'<circle cx="{cx:.1f}" cy="{cy2:.1f}" r="{w*0.9:.1f}" fill="#e8c63e" stroke="#b89a25" stroke-width="0.6"/>'
        f'<circle cx="{cx-w*0.3:.1f}" cy="{cy2+h*0.05:.1f}" r="{w*0.45:.1f}" fill="#f0d56a"/>'
        f'<circle cx="{cx+w*0.35:.1f}" cy="{cy2-h*0.08:.1f}" r="{w*0.4:.1f}" fill="#d9b425"/>'
    )
    return trunk + crown


def _leaf_maple(cx, cy, w, h, trunk_w, scale, seed_id):
    """楓 — 赤い葉の冠"""
    trunk = _trunk(cx, cy, h, trunk_w, "#3d2818")
    cy2 = cy - h * 0.7
    crown = (
        f'<circle cx="{cx:.1f}" cy="{cy2:.1f}" r="{w*0.85:.1f}" fill="#c5402b" stroke="#8c2818" stroke-width="0.6"/>'
        f'<circle cx="{cx-w*0.3:.1f}" cy="{cy2+h*0.04:.1f}" r="{w*0.45:.1f}" fill="#e06547"/>'
        f'<circle cx="{cx+w*0.35:.1f}" cy="{cy2-h*0.05:.1f}" r="{w*0.4:.1f}" fill="#a83520"/>'
    )
    return trunk + crown


def _leaf_camellia(cx, cy, w, h, trunk_w, scale, seed_id):
    """椿 — 濃い緑+赤い花点"""
    trunk = _trunk(cx, cy, h, trunk_w, "#3a2a1a")
    cy2 = cy - h * 0.7
    crown = (
        f'<circle cx="{cx:.1f}" cy="{cy2:.1f}" r="{w*0.85:.1f}" fill="#1f4a25" stroke="#143018" stroke-width="0.6"/>'
        f'<circle cx="{cx-w*0.25:.1f}" cy="{cy2+h*0.05:.1f}" r="{w*0.4:.1f}" fill="#2c5d30"/>'
        f'<circle cx="{cx+w*0.18:.1f}" cy="{cy2-h*0.1:.1f}" r="{w*0.18:.1f}" fill="#cf2c2c"/>'
        f'<circle cx="{cx-w*0.35:.1f}" cy="{cy2+h*0.12:.1f}" r="{w*0.13:.1f}" fill="#cf2c2c"/>'
    )
    return trunk + crown


def _leaf_bamboo(cx, cy, w, h, trunk_w, scale, seed_id):
    """竹 — 細い縦線+葉"""
    stalks = []
    for i, ox in enumerate([-w*0.3, 0, w*0.25]):
        col = "#4a8c3d" if i != 1 else "#5fa54f"
        stalks.append(
            f'<rect x="{cx+ox-trunk_w*0.3:.1f}" y="{cy-h*1.0:.1f}" '
            f'width="{trunk_w*0.6:.1f}" height="{h*1.0:.1f}" fill="{col}" rx="0.5"/>'
        )
    leaves = []
    for i in range(6):
        lx = cx - w*0.4 + (i * w*0.18)
        ly = cy - h*0.7 - (i % 2) * h*0.1
        leaves.append(
            f'<ellipse cx="{lx:.1f}" cy="{ly:.1f}" rx="{w*0.18:.1f}" ry="{h*0.05:.1f}" '
            f'fill="#5fa54f" transform="rotate({-30 + i*12} {lx} {ly})"/>'
        )
    return "".join(stalks) + "".join(leaves)


LEAF_RENDERERS = {
    "pine": _leaf_pine,
    "sakura": _leaf_sakura,
    "oak": _leaf_oak,
    "willow": _leaf_willow,
    "ginkgo": _leaf_ginkgo,
    "maple": _leaf_maple,
    "camellia": _leaf_camellia,
    "bamboo": _leaf_bamboo,
}


# ---------- 全体の森を組み立てる ----------

def _bg() -> str:
    """空+雲+地面の背景。"""
    sky = (
        f'<defs>'
        f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#cfe6f0"/>'
        f'<stop offset="100%" stop-color="#fcf2dc"/>'
        f'</linearGradient>'
        f'<linearGradient id="ground" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#83a25a"/>'
        f'<stop offset="100%" stop-color="#5b7039"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="url(#sky)"/>'
    )
    clouds = (
        f'<ellipse cx="180" cy="80" rx="55" ry="14" fill="#ffffff" opacity="0.85"/>'
        f'<ellipse cx="220" cy="90" rx="40" ry="11" fill="#ffffff" opacity="0.8"/>'
        f'<ellipse cx="780" cy="60" rx="65" ry="15" fill="#ffffff" opacity="0.75"/>'
        f'<ellipse cx="820" cy="72" rx="42" ry="11" fill="#ffffff" opacity="0.7"/>'
        f'<ellipse cx="500" cy="110" rx="48" ry="11" fill="#ffffff" opacity="0.7"/>'
    )
    distant_hills = (
        f'<path d="M0,{GROUND_Y-30} Q200,{GROUND_Y-90} 400,{GROUND_Y-40} '
        f'T800,{GROUND_Y-50} T{W},{GROUND_Y-30} L{W},{GROUND_Y} L0,{GROUND_Y} Z" '
        f'fill="#a4b07c" opacity="0.55"/>'
    )
    ground = (
        f'<rect x="0" y="{GROUND_Y}" width="{W}" height="{H-GROUND_Y}" fill="url(#ground)"/>'
    )
    return sky + clouds + distant_hills + ground


def _hash_to_int(s: str, mod: int) -> int:
    """文字列から安定した整数を作る(配置のランダム性に使う)。"""
    h = hashlib.md5(s.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % mod


def render_forest(seeds: list[dict]) -> str:
    """
    seeds: 各レコードは dict like {'id', 'tree_type', 'size', 'x_position', 'linked_seed_id', ...}
    返り値: 完全なSVG文字列
    """
    parts = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
        f'preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;border-radius:14px;">'
    ]
    parts.append(_bg())

    if not seeds:
        # まだ何も植わっていない時のメッセージ
        parts.append(
            f'<text x="{W/2}" y="{GROUND_Y-40}" text-anchor="middle" '
            f'fill="#3d3a2c" font-family="serif" font-size="22" opacity="0.7">'
            f'まだたねがありません。最初の一言をつぶやいてみましょう。'
            f'</text>'
        )
    else:
        # 木をサイズ順(大→小)にソートして奥行きを出す
        # 大きい木は手前に来るので最後に描く
        sorted_seeds = sorted(seeds, key=lambda s: s.get("size") or 1)

        # 枝(links)を先に描いて、木の後ろに置く
        link_lines = []
        positions: dict[int, tuple[float, float]] = {}
        for s in sorted_seeds:
            x_norm = float(s.get("x_position") or 0.5)
            x_norm = max(0.03, min(0.97, x_norm))
            cx = x_norm * W
            size = int(s.get("size") or 1)
            # サイズに応じてY軸を少しだけ手前に
            cy = GROUND_Y + (size - 1) * 6
            positions[s["id"]] = (cx, cy)

        # 枝(過去の木とのつながり)
        for s in sorted_seeds:
            link_id = s.get("linked_seed_id")
            if link_id and link_id in positions and s["id"] in positions:
                x1, y1 = positions[s["id"]]
                x2, y2 = positions[link_id]
                # 上に弧を描く
                mx = (x1 + x2) / 2
                my = min(y1, y2) - 80
                link_lines.append(
                    f'<path d="M{x1:.1f},{y1-30:.1f} Q{mx:.1f},{my:.1f} {x2:.1f},{y2-30:.1f}" '
                    f'stroke="#a48b5b" stroke-width="1.4" stroke-dasharray="3 4" fill="none" opacity="0.5"/>'
                )
        parts.extend(link_lines)

        # 木本体(クリック可能なリンクで囲む)
        for s in sorted_seeds:
            cx, cy = positions[s["id"]]
            size = int(s.get("size") or 1)
            tree_type = s.get("tree_type") or "pine"
            tree_html = _tree_svg(tree_type, size, cx, cy, s["id"])
            parts.append(
                f'<a href="?seed={s["id"]}" target="_self" style="cursor:pointer;">'
                f'<title>{(s.get("tweet_excerpt") or "")[:40]}</title>'
                f'{tree_html}</a>'
            )

    parts.append("</svg>")
    return "".join(parts)


def assign_position_for_new_seed(existing_seeds: list[dict], new_seed_text: str) -> float:
    """
    新しいたねの x_position を決める。
    既存の木と被らない位置を、テキストハッシュから安定的に選ぶ。
    """
    # テキストから候補位置を作成
    base = _hash_to_int(new_seed_text, 1000) / 1000.0  # 0.0〜1.0
    base = 0.05 + base * 0.9  # 0.05〜0.95

    # 既存と近すぎないかチェック、被ったら少しずらす
    used = [float(s.get("x_position") or 0.5) for s in existing_seeds]
    for offset in [0, 0.06, -0.06, 0.12, -0.12, 0.18, -0.18, 0.24, -0.24]:
        candidate = base + offset
        if candidate < 0.03 or candidate > 0.97:
            continue
        if all(abs(candidate - u) > 0.04 for u in used):
            return candidate
    return base
