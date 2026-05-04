#!/usr/bin/env python3
"""公式名に合わせた name の一括置換（ID・appearances・covers は変更しない）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"


def normalize(name: str) -> str:
    return re.sub(r"[・\s\-]", "", (name or "").strip())


RENAME_BY_NORM: dict[str, str] = {
    normalize("アイダ"): "イーダ",
    normalize("モザ"): "モサ公",
    normalize("すねこすり"): "すくね",
    normalize("ウルフ"): "ウォルフ",
    normalize("ブレード"): "ブレイド",
    normalize("リモシフ・キリンガム"): "リモシフ・キリンガム聖",
    normalize("シェパード・サマーズ"): "シェパード・ソマーズ聖",
    normalize("シャルロス"): "ロズワード・チャルロス聖",
    normalize("ジャルール"): "ヤルル",
    normalize("マガッタ"): "ベント",
    normalize("ロンヤ"): "ローニャ",
}


def patch_names(obj: object, rename_by_norm: dict[str, str], changes: list[tuple[str, str]]) -> None:
    if isinstance(obj, dict):
        if "name" in obj and isinstance(obj["name"], str):
            nk = normalize(obj["name"])
            if nk in rename_by_norm:
                new_name = rename_by_norm[nk]
                if obj["name"] != new_name:
                    changes.append((obj["name"], new_name))
                    obj["name"] = new_name
        for v in obj.values():
            patch_names(v, rename_by_norm, changes)
    elif isinstance(obj, list):
        for item in obj:
            patch_names(item, rename_by_norm, changes)


def run_fix() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    top_before = {
        normalize(c.get("name", ""))
        for c in chars
        if isinstance(c, dict) and normalize(c.get("name", "")) in RENAME_BY_NORM
    }

    changes: list[tuple[str, str]] = []
    patch_names(chars, RENAME_BY_NORM, changes)

    top_count = len(top_before)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    for old, new in sorted(set(changes), key=lambda x: x[0]):
        print(f"✅ '{old}' -> '{new}' に更新")

    print(f"\n完了！ トップレベルキャラで {top_count} 名の名前を修正しました（JSON 全体の name も同期）。")


if __name__ == "__main__":
    run_fix()
