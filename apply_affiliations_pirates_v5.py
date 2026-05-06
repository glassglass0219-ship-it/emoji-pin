#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


_SPACE_RE = re.compile(r"[ \t\u3000]+")


def norm_name(s: str) -> str:
    t = nfkc(s)
    t = _SPACE_RE.sub("", t)
    t = t.lower()
    for ch in ["・", "･", "“", "”", "〝", "〟", "「", "」", "『", "』"]:
        t = t.replace(ch, "")
    return t


def ensure_list(v: object) -> list[str]:
    if isinstance(v, list):
        out: list[str] = []
        seen: set[str] = set()
        for x in v:
            if not isinstance(x, str):
                continue
            t = x.strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out
    if isinstance(v, str):
        t = v.strip()
        return [t] if t else []
    return []


def main() -> int:
    path = Path("src/data/characters.json")
    chars = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    idx: dict[str, list[dict]] = {}
    for c in chars:
        if not isinstance(c, dict):
            continue
        nm = str(c.get("name") or "")
        if nm:
            idx.setdefault(norm_name(nm), []).append(c)

    assignments: dict[str, list[str]] = {
        "ファイアタンク海賊団": ["カポネ・ベッジ", "ヴィト", "ゴッティ", "シャーロット・シフォン", "カポネ・ペッツ"],
        "フォクシー海賊団": [
            "ポルチェ",
            "フォクシー",
            "ハンバーグ",
            "キバガエル",
            "イトミミズ",
            "チュチューン",
            "カポーティ",
            "モンダ",
            "ピクルス",
            "ビッグパン",
            "マウンテンリッキー",
            "ジョージ・マッハ",
            "ソニエ",
            "ドノバン",
            "ジーナ",
        ],
        "フライング海賊団": ["アンコロ", "バンダー・デッケン九世"],
        "ブリキング海賊団": ["チェス", "クロマーリモ"],
        "ブルージャム海賊団": ["ポルシェーミ", "ブルージャム"],
        "ふんばりカレー海賊団": ["シミター太", "ヒッピー・ザ・ドクロカレー", "ヒロ★ゴーモン"],
        "ホーキンス海賊団": ["バジル・ホーキンス", "ファウスト"],
        "ホカホカ海賊団": ["オコメ"],
        "ボニー海賊団": ["ジュエリー・ボニー", "パート", "ポテト", "ギョギョ", "トッツ"],
        "マクロー一味": ["マクロ", "ギャロ", "タンスイ"],
        "マシラ海賊団": ["マシラ"],
        "元新魚人海賊団": ["ワダツミ"],
        "元麦わらの一味": ["ネフェルタリ・ビビ", "カルー"],
        "元ロジャー海賊団": [
            "ゴール・Ｄ・ロジャー",
            "シャンクス",
            "バギー",
            "クロッカス",
            "シルバーズ・レイリー",
            "シーガル・ガンズ・ノズドン",
            "サンベル",
            "スコッパー・ギャバン",
            "ミレ・パイン",
            "眼竜",
            "ドリンゴ",
            "タロウ",
            "ピータームー",
            "ドンキーノ",
            "CBギャラン",
            "ユーイ",
            "ムーン・アイザックJr.",
            "スペンサー",
            "Mr.モモラ",
            "ローウィング",
            "エリオ",
            "バンクロ",
            "ジャクソンバナー",
            "ミュグレン大佐",
            "ラングラム",
            "ブルマリン",
            "ヤモン",
        ],
        "元ロックス海賊団": [
            "エドワード・ニューゲート（白ひげ）",
            "キャプテン・ジョン",
            "グロリオーサ（ニョン婆）",
            "カイドウ",
            "バッキンガム・ステューシー",
            "シャーロット・リンリン（ビッグ・マム）",
            "ガンズイ",
            "ギル・バスター",
            "シキ（金獅子）",
            "ロックス・D・ジーベック（デービー・D・ジーベック）",
            "首領・マーロン",
            "王直",
            "凶（銀斧）",
            "バーベル",
        ],
        "ヨンタマリア大船団": ["オオロンブス", "コロンブス"],
    }

    changed = 0
    missing: list[str] = []
    multi: list[tuple[str, list[int]]] = []

    for group, names in assignments.items():
        for name in names:
            bucket = idx.get(norm_name(name)) or []
            if not bucket:
                missing.append(name)
                continue
            if len(bucket) > 1:
                ids = sorted(int(x.get("id", 10**9)) for x in bucket)
                multi.append((name, ids))
            ch = min(bucket, key=lambda x: int(x.get("id", 10**9)))

            cats = ensure_list(ch.get("category"))
            if "海賊" not in cats:
                cats.append("海賊")
                ch["category"] = cats
                changed += 1

            groups = ensure_list(ch.get("group"))
            if group not in groups:
                groups.append(group)
                ch["group"] = groups
                changed += 1

    chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
    path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"changed={changed}")
    print(f"missing_count={len(missing)}")
    for m in missing:
        print(f"MISSING {m}")
    print(f"multi_hit_count={len(multi)}")
    for n, ids in multi[:50]:
        print(f"MULTI {n} ids={ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

