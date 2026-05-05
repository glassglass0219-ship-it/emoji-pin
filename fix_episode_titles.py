#!/usr/bin/env python3
"""manga_anime_map / characters / skills の話タイトルを title_fix_map で一括修正。"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

title_fix_map = {
    7: "友達",
    11: "敗走",
    12: "犬",
    13: "宝物",
    17: "格",
    21: "町",
    27: "謎の男",
    29: "死闘",
    31: "真実",
    32: "大海賊",
    41: "海へ",
    45: "嵐前",
    49: "嵐",
    52: "誓い",
    59: "責任",
    60: "解決",
    61: "鬼",
    74: "理由",
    76: "約束",
    81: "涙",
    89: "四皇",
    92: "幸福",
    98: "暗雲",
    114: "進路",
    119: "決着",
    126: "本望",
    132: "冒険",
    137: "海賊",
    138: "頂上",
    144: "雪",
    152: "満月",
    167: "戦線",
    172: "反乱（うねり）",
    175: "解放",
    182: "怒号",
    186: "４（フォー）",
    187: "互角",
    189: "２（ツー）",
    196: "１（ワン）",
    206: "点火",
    207: "悪夢",
    210: "０（ゼロ）",
    211: "王",
    221: "怪物",
    243: "存在",
    251: "冒険",
    268: "海賊船",
    272: "戯れ",
    274: "神",
    275: "海賊",
    277: "願い",
    280: "勝敗",
    282: "望み",
    287: "神の国",
    288: "呪い",
    289: "望郷",
    293: "恋",
    294: "雷",
    318: "開幕",
    333: "船長",
    347: "六式",
    358: "復活",
    361: "追撃",
    364: "再会",
    379: "決断",
    381: "応戦",
    387: "決戦",
    389: "応答",
    390: "海列車",
    405: "宣戦布告",
    413: "狩り",
    417: "騎士",
    424: "出航",
    429: "帰還",
    466: "決着",
    480: "再会",
    484: "出発",
    487: "戦争",
    505: "麦わらの一味",
    523: "地獄",
    535: "地獄の釜",
    558: "弟",
    559: "兄",
    566: "死",
    580: "終戦",
    590: "兄弟",
    592: "再出発",
    595: "宣言",
}


def _ep_int(ep_val: object) -> int | None:
    try:
        return int(ep_val)
    except (TypeError, ValueError):
        return None


def update_json_file(path: Path, ep_key_name: str, list_keys: list[str]) -> None:
    if not path.exists():
        print(f"スキップ（なし）: {path}")
        return
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    updated = 0
    if isinstance(data, dict):
        for ep_num_str, info in data.items():
            try:
                ch = int(ep_num_str)
            except (TypeError, ValueError):
                continue
            if ch not in title_fix_map or not isinstance(info, dict):
                continue
            info["title"] = title_fix_map[ch]
            updated += 1
    elif isinstance(data, list):
        for entry in data:
            if not isinstance(entry, dict):
                continue
            for key in list_keys:
                lst = entry.get(key)
                if not isinstance(lst, list):
                    continue
                for item in lst:
                    if not isinstance(item, dict):
                        continue
                    ep_i = _ep_int(item.get(ep_key_name))
                    if ep_i is not None and ep_i in title_fix_map:
                        item["title"] = title_fix_map[ep_i]
                        updated += 1

    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✅ {path}: {updated} 箇所のタイトルを修正しました。")


if __name__ == "__main__":
    os.chdir(ROOT)
    data_dir = ROOT / "src" / "data"
    update_json_file(data_dir / "manga_anime_map.json", "episode", [])
    update_json_file(data_dir / "characters.json", "episode", ["appearances", "covers"])
    update_json_file(data_dir / "skills.json", "episode", ["episodes"])
