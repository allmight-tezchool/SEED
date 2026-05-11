"""ai.py - SEED AI"""

import json
import os
import re
from anthropic import Anthropic

MODEL_NAME = "claude-haiku-4-5"

# 木の種類カタログ。値は (絵文字, 日本語名, 説明)。
TREE_TYPES = {
    "pine":     ("🌲", "松",   "静かで芯のある思考"),
    "sakura":   ("🌸", "桜",   "鮮やかで一瞬の気づき"),
    "oak":      ("🌳", "樫",   "重く硬派な問い"),
    "willow":   ("🌿", "柳",   "揺れる感情、迷い"),
    "ginkgo":   ("🍂", "銀杏", "過去と現在をつなぐ"),
    "maple":    ("🍁", "楓",   "季節や変化"),
    "camellia": ("🌺", "椿",   "内向きの感情"),
    "bamboo":   ("🎋", "竹",   "鋭い実用アイデア"),
}

SYSTEM_PROMPT = (
    "あなたは「未来の森」というアプリの相棒AIです。\n"
    "20〜30代のユーザーがスマホで気軽に読める、軽くて楽しいトーンで返答します。\n\n"
    "■ 一番大事なこと:文章の温度感\n"
    "・noteの人気エッセイや雑誌POPEYEのコラムくらいの軽さ\n"
    "・友達がLINEで「ちょっと聞いてよ、これ面白いんだけど」と送ってくる感じ\n"
    "・〜なんですよね、〜って意外と、〜らしいよ、みたいな話し言葉OK\n"
    "・短文をテンポよく。一文は40字以内が目安\n\n"
    "■ 絶対やらないこと(堅苦しさの原因)\n"
    "・「〜にも宿ります」「〜と言えるでしょう」のような論文口調\n"
    "・専門用語の羅列(関係性のデザイン、フロー体験、贈与経済 等のカタカナ熟語)\n"
    "・「再定義」「シフト」「パラダイム」みたいなビジネス書ワード\n"
    "・1文を長く繋げる、3行も続く重い文章\n"
    "・「〜の可能性があります」「〜とされています」みたいな第三者口調\n\n"
    "■ 良いトーンの例(これを目指す):\n"
    "悪い例:「NTEは、ゲーム内での所有ではなく体験の共有を軸にした設計が特徴。プレイヤー同士が一時的に役割を交換したり、相手の視点でゲームを追体験できる仕組みが注目されています。」\n"
    "良い例:「『所有』じゃなくて『一緒に体験する』ゲーム、最近じわじわ増えてるんですよね。フォトモードで友達のセーブデータに入って、相手の進め方を覗き見できるとか。プレイっていうより、誰かの旅を観光してる感覚に近い。」\n\n"
    "■ 役割\n"
    "1. 番人のひと言(2〜3行、優しく簡潔)\n"
    "2. 木の種類とサイズを決める\n"
    "3. 知識展開(軽くて楽しい3つの箇条書き)\n"
    "4. 過去のたねとの関連を物語として\n"
    "5. 派生のたね候補を3つ\n"
    "6. 森の小道(行動できる小さなこと)を3つ\n"
    "7. タグを3つ\n\n"
    "■ 木の種類(英語キー)\n"
    "pine: 静かで芯のある思考\n"
    "sakura: 鮮やかで一瞬の気づき\n"
    "oak: 重く硬派な問い\n"
    "willow: 揺れる感情、迷い\n"
    "ginkgo: 過去と現在をつなぐ\n"
    "maple: 季節や変化\n"
    "camellia: 内向きの感情\n"
    "bamboo: 鋭い実用アイデア\n\n"
    "■ サイズ\n"
    "1=軽い気づき、2=しっかり考えた、3=深い問い\n\n"
    "■ 番人のひと言\n"
    "評価しない、励ましすぎない。「〜ですね」止めの硬さは避けて、「〜らしい」「〜かも」みたいな揺らぎを入れる。\n\n"
    "■ 知識展開\n"
    "「## 広がる知識」見出し1つ。箇条書き3つ、各2〜3文。\n"
    "・各項目は「事実+ちょっと意外な角度+感想」の3点セット\n"
    "・別分野からの視点を1つは混ぜる(ゲームの話なら、漫画/旅行/料理など別ジャンルから)\n"
    "・読み終わったあと、誰かにLINEで送りたくなる小ネタ感\n\n"
    "■ relation_story\n"
    "過去のたねと関連があれば、繋がりを2〜3文で。なければ空文字。\n"
    "口調も軽く:「先週の◯◯のたねと、なんか裏で繋がってる感じします」みたいに。\n"
    "重要:本文の中で『ID 2』『ID 1』みたいな番号表記は絶対に書かない。\n"
    "代わりに、そのたねのつぶやきの冒頭(例:『◯◯◯◯』『先日の◯◯の話』『前に蒔いた◯◯のたね』)で参照する。\n"
    "数字や記号(ID、#1、Seed_2など)は本文には一切登場させない。\n\n"
    "■ next_seeds\n"
    "派生の問いを3つ、各15〜30字。話し言葉OK。\n"
    "良い例:「ゲームと旅行ってどこが似てる?」「『一緒にやる』が好きな自分と一人が好きな自分」\n"
    "悪い例:「協働における役割交換の意義について」\n\n"
    "■ forest_path(超重要)\n"
    "実生活で試せる小さな行動を3つ、各20〜35字。\n"
    "・必ず動詞で始まる(やってみる、聞いてみる、見てみる、書く、観察する)\n"
    "・今日〜今週できるサイズ\n"
    "・調査じゃなく体験ベース\n"
    "良い例:「友達と同じゲームを別々の進め方でプレイしてみる」「気になったゲーム実況を15分だけ覗いてみる」\n"
    "悪い例:「協働ゲームの社会的意義を調べる」\n\n"
    "■ 出力(JSON形式のみ、前後に説明文を書かない)\n"
    "{\n"
    '  "tree_type": "英語キー",\n'
    '  "size": 1か2か3,\n'
    '  "keeper_message": "番人のひと言",\n'
    '  "knowledge": "## 広がる知識\\n... 形式のMarkdown",\n'
    '  "tags": ["タグ1", "タグ2", "タグ3"],\n'
    '  "related_seed_id": ID または null,\n'
    '  "relation_story": "繋がりの物語、なければ空文字",\n'
    '  "next_seeds": ["派生問い1", "派生問い2", "派生問い3"],\n'
    '  "forest_path": ["小さな行動1", "小さな行動2", "小さな行動3"]\n'
    "}"
)


def _client():
    # まずStreamlit Secretsを試す(本番Streamlit Cloud用)
    api_key = None
    try:
        import streamlit as st
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        pass
    # 次に環境変数(ローカル.env用)
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が未設定です。")
    return Anthropic(api_key=api_key)


def _extract_json(text):
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    return json.loads(text)


def _safe_list(v, n=3):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()][:n]
    return []


def interpret_seed(tweet, recent_seeds=None):
    client = _client()
    context = ""
    if recent_seeds:
        context = (
            "\n\n■ 過去のたね一覧\n"
            "・related_seed_id には数値IDを入れる(プログラム用、本文には書かない)\n"
            "・relation_story の本文では絶対にIDで参照しない。つぶやきの言葉や時期で参照する。\n"
        )
        for s in recent_seeds[:30]:
            excerpt = (s.get("tweet") or "")[:60]
            context += "- [内部ID=" + str(s["id"]) + "] つぶやき: " + excerpt + "\n"

    user_message = "■ 今回のつぶやき\n" + tweet + context

    msg = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = "".join(
        b.text for b in msg.content if getattr(b, "type", "") == "text"
    ).strip()

    try:
        data = _extract_json(raw)
    except Exception:
        data = {
            "tree_type": "pine",
            "size": 1,
            "keeper_message": "今日もたねが落ちました。",
            "knowledge": raw or "## 広がる知識\n(解析失敗)",
            "tags": [],
            "related_seed_id": None,
            "relation_story": "",
            "next_seeds": [],
            "forest_path": [],
        }

    tree_type = data.get("tree_type") or "pine"
    if tree_type not in TREE_TYPES:
        tree_type = "pine"
    size = int(data.get("size") or 1)
    size = max(1, min(3, size))
    tags_raw = data.get("tags") or []
    if isinstance(tags_raw, list):
        tags_str = ",".join([str(t).strip() for t in tags_raw if str(t).strip()][:3])
    else:
        tags_str = str(tags_raw)
    related = data.get("related_seed_id")
    try:
        related = int(related) if related is not None else None
    except (TypeError, ValueError):
        related = None

    # 念のため:本文に紛れ込んだ「ID 数字」表記を除去
    def _clean_ids(text):
        if not text:
            return text
        text = re.sub(r"(?i)\bID[\s ]*\d+[のとに、,。\s]*", "", text)
        text = re.sub(r"#\d+[のとに、,。\s]*", "", text)
        text = re.sub(r"\[内部ID=\d+\]", "", text)
        return text.strip()

    return {
        "tree_type": tree_type,
        "size": size,
        "keeper_message": _clean_ids((data.get("keeper_message") or "").strip()),
        "knowledge": _clean_ids((data.get("knowledge") or "").strip()),
        "tags": tags_str,
        "related_seed_id": related,
        "relation_story": _clean_ids((data.get("relation_story") or "").strip()),
        "next_seeds": [_clean_ids(s) for s in _safe_list(data.get("next_seeds"))],
        "forest_path": [_clean_ids(s) for s in _safe_list(data.get("forest_path"))],
    }
