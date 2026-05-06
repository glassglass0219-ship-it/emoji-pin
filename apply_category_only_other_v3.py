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
    for ch in ["・", "･", "“", "”", "〝", "〟", "「", "」", "『", "』", "｢", "｣"]:
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
    category_to_add = "その他"
    targets = [
        "MIKIO ITOO",
        "近海の主（ゴア王国）",
        "ソーロ",
        "怪鳥ピンキー",
        "どーも君",
        "ココックス",
        "バッチー",
        "パンダマン",
        "パンサメ",
        "電伝虫",
        "ニュース・クー",
        "雪だるさん",
        "スノウクイーン",
        "へのへのうんち",
        "ブロントザウルス",
        "島食い",
        "ハイキングベア",
        "ハイパー雪だるさん",
        "シロラー",
        "ラパーン",
        "ロブソン",
        "スノウバード（雪鳥）",
        "海ネコ",
        "クンフージュゴン",
        "ワルサギ",
        "サンドラ大トカゲ",
        "ハサミ",
        "サンドラマレナマズ",
        "海イノシシ",
        "マッシュ",
        "トマトギャング",
        "サウスバード",
        "空魚",
        "特急エビ",
        "ハコワン",
        "クラバウターマン",
        "ノラ",
        "カシ神",
        "カシ神の子",
        "タコバルーン",
        "シーモンキー",
        "七色ウツボブラザーズ",
        "ダッ～～～～クスフント",
        "カ～～～～モノハシ",
        "ユキヒョ～～～～ウ",
        "近海の主（ロングリングロングランド）",
        "ヤガラ",
        "土番長",
        "森番長",
        "ヨコヅナ",
        "スズメ",
        "ユルスマジマスク",
        "海兎",
        "サルウ",
        "マスケレドモ・ゴアユー鳥",
        "海カバ",
        "ヒューマンドリル",
        "スルメ",
        "海獅子",
        "海リス",
        "海熊",
        "ダイダロス",
        "ノースバード",
        "ウエスタンバード",
        "イースタンバード",
        "ドラゴン十三號",
        "スマイリー",
        "ドラゴン二十一號",
        "キャメル",
        "闘魚",
        "イエローカブ（山吹オオカブトムシ）",
        "ピンクビー（桃色スズメバチ）",
        "リニアフォックス",
        "子海ネコ",
        "海イヌのおまわりさん/海獣保安官",
        "抜け雀",
        "ウッホーくん",
        "象主",
        "昇り龍（りゅーのすけ）",
        "ワーニー",
        "ねこざえもん",
        "虎三郎",
        "ヨロイオコゼ",
        "ナワバリウミウシ",
        "ニトロ",
        "ラビヤン",
        "海アリ",
        "ユニコーン",
        "キノコビト",
        "ドスコイパンダ",
        "豚車",
        "パンドラ",
        "レディツリー",
        "タルトタンク",
        "タマ",
        "ガマ・ピョンの助",
        "春ダコ",
        "夢鯉",
        "ひひ丸",
        "マッドサウルス",
        "狛ちよ",
        "ぶんぶく君",
        "ワニザメ",
        "狛鹿",
        "さいころ",
        "タニシ",
        "ホメ",
        "和道一文字（刀擬人化）",
        "三代鬼徹（刀擬人化）",
        "秋水（刀擬人化）",
        "三助",
        "狛デーン",
        "狛鶏",
        "狛虎",
        "グリフォン（刀擬人化）",
        "黒刀よる子（刀擬人化）",
        "おまけ子（刀擬人化）",
        "小山",
        "山さん",
        "魂の喪剣（刀擬人化）",
        "麦わら帽子（帽子擬人化）",
        "魔法の天候棒（擬人化）",
        "ヤマトの横乳（擬人化）",
        "八斎戒（金棒擬人化）",
        "建（金棒擬人化）",
        "火前坊",
        "BLACK（巨大パチンコ黒カブト擬人化）",
        "GUMMER（がま口カバン擬人化）",
        "忠治",
        "ハラマキ子（ゾロの腹巻擬人化）",
        "ピアス三姉妹（ゾロのピアス擬人化）",
        "メカシャーク",
        "ベガフォース01",
        "リサイクルワン",
        "エメト",
        "鬼哭（刀擬人化）",
        "土竜（槍擬人化）",
        "イム",
        "エース（刀擬人化）",
        "蜜蜂兵",
        "針神様",
        "イスカット",
        "ヒルムンガルド",
        "ムギン",
        "グルトバニー（耳神様）",
        "パイパー",
        "ビブロ",
        "ケルベロス（剣）",
        "にーずほっぐ（MMA）",
        "ふぇんりる（MMA）",
        "かみなり（MMA）",
        "どらうぐる（MMA）",
        "おばけ（MMA）",
        "電語虫",
        "ナッシュ",
        "グロッキーザウルス",
        "アスラ",
        "ウタ",
    ]

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

    changed = 0
    skipped = 0
    missing: list[str] = []
    multi: list[tuple[str, list[int]]] = []

    for name in targets:
        bucket = idx.get(norm_name(name)) or []
        if not bucket:
            missing.append(name)
            continue
        if len(bucket) > 1:
            ids = sorted(int(x.get("id", 10**9)) for x in bucket)
            multi.append((name, ids))
        ch = min(bucket, key=lambda x: int(x.get("id", 10**9)))

        cats = ensure_list(ch.get("category"))
        if category_to_add in cats:
            skipped += 1
            continue
        cats.append(category_to_add)
        ch["category"] = cats
        changed += 1

    chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
    path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"category_added={category_to_add}")
    print(f"changed={changed}")
    print(f"skipped_already_had_category={skipped}")
    print(f"missing_count={len(missing)}")
    for m in missing:
        print(f"MISSING {m}")
    print(f"multi_hit_count={len(multi)}")
    for n, ids in multi[:50]:
        print(f"MULTI {n} ids={ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

