#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re

SOURCE_MAP_PATH = "src/data/character_all.json"
TARGET_JSON_PATH = "src/data/characters.json"


def run_reassign() -> None:
    if not os.path.exists(SOURCE_MAP_PATH) or not os.path.exists(TARGET_JSON_PATH):
        print("エラー: 必要なファイルが見つかりません。")
        return

    # 1. ソースマップを解析（ID: 名前）
    name_to_new_id: dict[str, int] = {}
    max_id = 0
    with open(SOURCE_MAP_PATH, "r", encoding="utf-8") as f:
        for line in f:
            match = re.match(r"(\d+):\s*(.*)", line.strip())
            if not match:
                continue
            new_id = int(match.group(1))
            name = match.group(2).strip()
            if not name:
                continue
            name_to_new_id[name] = new_id
            if new_id > max_id:
                max_id = new_id

    # 2. ターゲットJSONを読み込み
    with open(TARGET_JSON_PATH, "r", encoding="utf-8") as f:
        chars = json.load(f)

    # 3. キャラクターを「一致組」と「新規採番組」に分ける
    matched = []
    to_assign = []

    for c in chars:
        if c.get("name") in name_to_new_id:
            c["id"] = name_to_new_id[c["name"]]
            matched.append(c)
        else:
            to_assign.append(c)

    # 4. 未一致キャラに新しいIDを振る（現在のID順）
    to_assign.sort(key=lambda x: int(x.get("id", 0)))
    current_id = max_id + 1
    for c in to_assign:
        old_id = c.get("id")
        print(f"📦 未一致のため新規採番: {c.get('name')} ({old_id} -> {current_id})")
        c["id"] = current_id
        current_id += 1

    # 5. 全体をID順に並べ替えて保存
    all_chars = matched + to_assign
    all_chars.sort(key=lambda x: int(x.get("id", 0)))

    with open(TARGET_JSON_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(all_chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"\n✅ 完了！ {len(matched)} 名をマッピングし、{len(to_assign)} 名に新規IDを割り振りました。")


if __name__ == "__main__":
    run_reassign()

