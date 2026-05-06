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
    category_to_add = "海賊"
    targets = [
        "アイルワン",
        "ハンガン",
        "リフォルト",
        "サンファン・ウルフ",
        "バスコ・ショット",
        "カタリーナ・デボン",
        "アバロ・ピサロ",
        "アーサー",
        "ホワイティベイ",
        "チャドロス・ヒゲリゲス（茶ひげ）",
        "ポルシェーミ",
        "ブルージャム",
        "ハリーツ・ケンディヨ",
        "アイアンボーイ・スコッチ",
        "ナインス",
        "ブロンディ",
        "デマロ・ブラック",
        "ショコラ",
        "トルコ",
        "マウンブルテン",
        "マンジャロウ",
        "ドリップ",
        "ココア",
        "のらギツネ",
        "アマドブ",
        "ウォレム",
        "バガリー",
        "カリブー",
        "コリブー",
        "ブリュー",
        "ブロッカ",
        "ラッシュ",
        "グレートミカエル",
        "キャンズ",
        "アンドレ",
        "チョイ",
        "キンガ",
        "コルスコン",
        "アグシリー",
        "ユリウス",
        "ズッカ",
        "アルビオン",
        "リップ・〝サービス〟・ドウティ",
        "アンコロ",
        "ハモンド",
        "カサゴバ",
        "ヒョウゾウ",
        "ホーディ・ジョーンズ",
        "ドスン",
        "ゼオ",
        "ダルマ",
        "イカロス・ムッヒ",
        "ワダツミ",
        "バンダー・デッケン九世",
        "フィッシャー・タイガー",
        "アラディン",
        "スプラッシュ",
        "スプラッタ",
        "ジャイロ",
        "ペコムズ",
        "タマゴ男爵",
        "モネ",
        "ヴェルゴ",
        "ベビー5",
        "バッファロー",
        "チンジャオ",
        "サイ",
        "ブー",
        "スレイマン",
        "アブドーラ",
        "ジェット",
        "オオロンブス",
        "キャベンディッシュ（ハクバ）",
        "ガンビア",
        "バルトロメオ",
        "イデオ",
        "ハイルディン",
        "ブルーギリー",
        "レオ",
        "ボンバ",
        "フラッパー",
        "ウィッカ",
        "ジョーラ",
        "カブ",
        "ビアン",
        "インヘル",
        "バクスコン",
        "ファルル",
        "グラディウス",
        "デリンジャー",
        "シュガー",
        "セニョール・ピンク",
        "マッハバイス",
        "ラオG",
        "ディアマンテ",
        "トレーボル",
        "チャオ",
        "三下",
        "イブス",
        "ピーカ",
        "四下",
        "キュイーン",
        "ドンキホーテ・ロシナンテ（コラソン）",
        "ディエス・バレルズ",
        "カイドウ",
        "エドワード・ウィーブル",
        "バッキンガム・ステューシー",
        "ジャック",
        "シープスヘッド",
        "ジンラミー",
        "クリオネ",
        "ウニ",
        "イッカク",
        "ヴィト",
        "シャーロット・プリン",
        "ゴッティ",
        "シャーロット・モスカート",
        "シャーロット・リンリン（ビッグ・マム）",
        "シャーロット・プラリネ",
        "貴族ワニ",
        "ランドルフ",
        "シャーロット・ブリュレ",
        "シャーロット・シフォン",
        "カポネ・ペッツ",
        "シャーロット・ペロスペロー",
        "シャーロット・クラッカー",
        "キングバーム",
        "シャーロット・モンドール",
        "シャーロット・オペラ",
        "シャーロット・ガレット",
        "シャーロット・ミュークル",
        "シャーロット・カウンター",
        "シャーロット・カデンツァ",
        "シャーロット・カバレッタ",
        "シャーロット・ガラ",
        "シャーロット・アナナ",
        "シャーロット・ドルチェ",
        "シャーロット・ドラジェ",
        "シャーロット・ウエハース",
        "シャーロット・ドシャ",
        "シャーロット・ノルマンド",
        "シャーロット・ウィロ",
        "シャーロット・アングレ",
        "シャーロット・アマンド",
        "シャーロット・スムージー",
        "チェス戎兵",
        "ディーゼル",
        "ナスの兵士",
        "ナポレオン",
        "プロメテウス",
        "ゼウス",
        "シャーロット・モンデ",
        "シャーロット・ダクワーズ",
        "シャーロット・カトウ",
        "シャーロット・メリゼ",
        "ボビン",
        "シュトロイゼン",
        "シャーロット・カタクリ",
        "シャーロット・コンポート",
        "シャーロット・ポワール",
        "シャーロット・カスタード",
        "シャーロット・モーツァルト",
        "シャーロット・バサンズ",
        "シャーロット・ドスマルシェ",
        "シャーロット・コンポ",
        "シャーロット・ダイフク",
        "シャーロット・オーブン",
        "シャーロット・ラウリン",
        "シャーロット・モービル",
        "シャーロット・ハイファット",
        "シャーロット・タブレット",
        "シャーロット・ノアゼット",
        "シャーロット・サンマルク",
        "シャーロット・エフィレ",
        "シャーロット・バスカルテ",
        "ゲルズ",
        "ライディーン",
        "ヨルル",
        "ヤルル",
        "シャーロット・カンテン",
        "シャーロット・ズコット",
        "シャーロット・エンゼル",
        "シャーロット・ブロワイエ",
        "シャーロット・マルニエ",
        "シャーロット・マッシュ",
        "シャーロット・アッシュ",
        "ウホリシア",
        "チチリシア",
        "WCI31",
        "ブッシュ",
        "シャーロット・マスカルポーネ",
        "シャーロット・ジョスカルポーネ",
        "シャーロット・ババロア",
        "シャーロット・フランペ",
        "シャーロット・シトロン",
        "シャーロット・シナモン",
        "シャーロット・ニューイチ",
        "シャーロット・ニュージ",
        "シャーロット・ニューサン",
        "シャーロット・ニューシ",
        "シャーロット・ニューゴ",
        "シャーロット・ナツメグ",
        "シャーロット・アキメグ",
        "シャーロット・オールメグ",
        "シャーロット・ハルメグ",
        "シャーロット・フユメグ",
        "シャーロット・マーブル",
        "シャーロット・レザン",
        "シャーロット・ユーエン",
        "シャーロット・ヌガー",
        "シャーロット・ブラウニー",
        "シャーロット・ジョコンド",
        "シャーロット・スナック",
        "シャーロット・シブースト",
        "シャーロット・プリム",
        "シャーロット・パンナ",
        "シャーロット・メープル",
        "ロード",
        "シャーロット・モンブ",
        "シャーロット・ヌストルテ",
        "ゴールドバーグ",
        "シャーロット・コンスターチ",
        "三日月のギャリー",
        "桃ひげ",
        "コロンブス",
        "マッスイ",
        "ダッキー・ブリー",
        "ミハール",
        "ディスクJ",
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

