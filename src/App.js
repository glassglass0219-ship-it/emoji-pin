import { useEffect, useMemo, useState } from "react";
import charactersData from "./data/characters.json";
import skillsData from "./data/skills.json";
import locationsData from "./data/locations.json";
import mangaAnimeMap from "./data/manga_anime_map.json";
import netflixIds from "./data/netflix_ids.json";
import organizationMaster from "./data/organization_master.json";
import updatesData from "./data/updates.json";
const CHARACTERS = [...charactersData].sort((a, b) => (Number(a?.id) || 0) - (Number(b?.id) || 0));
const LOCATIONS = [...locationsData];
const SKILLS = skillsData;
const SKILLS_BY_ID = new Map(SKILLS.map((s) => [s.id, s]));

/** キャラ検索「登場編」フィルター（データの arcs と一致させる） */
const ARC_FILTER_OPTIONS = [
  "東の海（イーストブルー）編",
  "アラバスタ編",
  "空島編",
  "デービーバックファイト編",
  "ウォーターセブン編",
  "エニエス・ロビー編",
  "スリラーバーク編",
  "シャボンディ諸島編",
  "女ヶ島アマゾン・リリー編",
  "大監獄インペルダウン編",
  "マリンフォード頂上戦争編",
  "魚人島編",
  "パンクハザード編",
  "ドレスローザ編",
  "ゾウ編",
  "ホールケーキアイランド編",
  "世界会議（レヴェリー）編",
  "ワノ国編",
  "エッグヘッド編",
  "エルバフ編",
  "ゴッドバレー編",
  "表紙連載",
  "その他",
];

/**
 * 技検索用：全角・半角・互換字形を Unicode NFKC で揃え、英字は小文字化
 */
const unifyAbilitySearchWidthAndCase = (raw) =>
  String(raw ?? "")
    .normalize("NFKC")
    .toLowerCase();

/**
 * ひらがな（ぁ〜ゖ、小ゃゅょ・っ等を含む）を対応するカタカナへ。漢字・カタカナ・英数はそのまま。
 */
const hiraganaToKatakana = (raw) => {
  let out = "";
  for (const ch of String(raw ?? "")) {
    const cp = ch.codePointAt(0);
    if (cp >= 0x3041 && cp <= 0x3096) {
      out += String.fromCodePoint(cp + 0x60);
    } else {
      out += ch;
    }
  }
  return out;
};

/** 検索クエリ・比較対象文字列をカタカナ基準の同一キーに正規化（name / reading / description 用） */
const normalizeAbilitySearchKey = (raw) =>
  hiraganaToKatakana(unifyAbilitySearchWidthAndCase(raw));

/**
 * ─── Kindle連携用ユーティリティ ───
 */

// 各巻の開始話数（1〜115巻）— 110巻1111話〜、115巻（未収録）1167話〜
const VOLUME_STARTS = [
  1, 9, 18, 27, 36, 45, 54, 63, 72, 82, 91, 100, 109, 118, 127, 137, 146, 156, 167, 177,
  187, 196, 206, 217, 227, 237, 247, 257, 265, 276, 286, 296, 306, 317, 328, 337, 347, 358, 368, 378,
  389, 400, 410, 420, 431, 441, 451, 460, 471, 482, 492, 503, 513, 523, 533, 542, 552, 563, 574, 585,
  595, 604, 615, 626, 637, 647, 657, 668, 679, 689, 701, 711, 722, 732, 743, 753, 764, 776, 786, 796,
  807, 817, 828, 839, 849, 859, 870, 880, 890, 901, 911, 922, 932, 943, 954, 965, 975, 985, 995, 1005,
  1016, 1026, 1036, 1047, 1056, 1066, 1077, 1089, 1101, 1111, 1122, 1134, 1145, 1156, 1167,
];

/** 配信済みしきい値（必要に応じて更新） */
const PUBLISHED_LIMITS = {
  MONO_VOL: 114, // モノクロ版 既刊
  COLOR_VOL: 106, // カラー版 既刊
  ANIME_EP: 1160, // アニメ 放送済み
};

// 話数から巻数を計算する（VOLUME_STARTS による正確マッピング）
const getVolumeFromEpisode = (episode) => {
  if (!episode) return 1;
  const ep = parseInt(episode, 10);
  if (!Number.isFinite(ep) || ep <= 0) return 1;

  // 1巻は話数1〜8まで固定で確実に1巻判定（開始話数マップより優先）
  if (ep >= 1 && ep <= 8) return 1;

  // 115巻開始話（1167）以降の話数は最新巻(115)扱い
  if (ep >= VOLUME_STARTS[VOLUME_STARTS.length - 1]) return VOLUME_STARTS.length;

  // 末尾から探索すると速く・実装も簡単（115巻まで固定マップ）
  for (let i = VOLUME_STARTS.length - 1; i >= 0; i--) {
    if (ep >= VOLUME_STARTS[i]) return i + 1; // index0 => 1巻
  }

  return 1;
};

// 115巻の開始話（VOLUME_STARTS の末尾）より十分先は、未単行本収録の可能性として「—」表示
const LATEST_VOLUME_START_EPISODE = VOLUME_STARTS[VOLUME_STARTS.length - 1];
const VOLUME_LABEL_UNKNOWN_BEYOND = LATEST_VOLUME_START_EPISODE + 12;

const getVolumeLabelForAppearance = (episode) => {
  const ep = parseInt(episode, 10);
  if (!Number.isFinite(ep) || ep <= 0) return "—";
  if (ep >= VOLUME_LABEL_UNKNOWN_BEYOND) return "—";
  return String(getVolumeFromEpisode(episode));
};

/** 登場話リンク用：未収録扱いは「-」、それ以外は「△巻」（角括弧内に入れる文字列） */
const getEpisodeVolBracketContents = (episode) => {
  if (getVolumeLabelForAppearance(episode) === "—") return "-";
  return `${getVolumeFromEpisode(episode)}巻`;
};

const getEpisodeLinkLabel = (episodeNum) => {
  return `第${episodeNum}話[${getEpisodeVolBracketContents(episodeNum)}]`;
};

/**
 * type: 'mono' | 'color' — ASIN は使わず、Kindle ストア検索 URL のみ生成
 */
const getKindleUrl = (episode, type) => {
  const vol = getVolumeFromEpisode(episode);
  const query =
    type === "color"
      ? `ONE PIECE カラー版 ${vol}`
      : `ONE PIECE モノクロ版 ${vol}`;
  return `https://www.amazon.co.jp/s?k=${encodeURIComponent(query)}&i=digital-text`;
};

const getNetflixUrl = (mangaEpisode) => {
  const animeData = mangaAnimeMap[String(mangaEpisode)];
  const ONE_PIECE_TOP_ID = "80106403";

  if (animeData != null) {
    const animeEpNum =
      typeof animeData === "object" && animeData.ep != null
        ? String(animeData.ep).trim()
        : typeof animeData !== "object"
          ? String(animeData).trim()
          : "";
    if (animeEpNum) {
      const nId = netflixIds[animeEpNum];
      if (nId) {
        return `https://www.netflix.com/watch/${nId}`;
      }
    }
  }
  return `https://www.netflix.com/title/${ONE_PIECE_TOP_ID}`;
};

const handleKindleNavClick = (episode, url, kind) => {
  const vol = getVolumeFromEpisode(episode);
  console.log("[Kindle]", { episode, volume: vol, kind, url });
};

const getSortedEpisodeNumbers = (episodes) => {
  const nums = (episodes || [])
    .map((e) => parseInt(e?.episode, 10))
    .filter((n) => Number.isFinite(n) && n > 0)
    .sort((a, b) => a - b);
  // unique
  return nums.filter((n, i) => i === 0 || n !== nums[i - 1]);
};

const getEpisodeLinkItems = (episodes) => {
  const nums = getSortedEpisodeNumbers(episodes);
  return nums.map((n) => ({ episode: n, label: getEpisodeLinkLabel(n) }));
};

// ─── Styles ───
const styles = `
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&family=Bebas+Neue&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --red-deep: #A0001C;
  --red-main: #C41E3A;
  --red-bright: #E63946;
  --yellow-main: #C8960A;
  --yellow-light: #FFF8E1;
  --yellow-warm: #D4A017;
  --bg-dark: #FDFAF3;
  --bg-card: #FFFFFF;
  --bg-card-hover: #FFF8ED;
  --text-main: #2D1F14;
  --text-muted: #6B5744;
  --text-dim: #A89880;
  --border: #E8DFD0;
  --shadow: 0 4px 24px rgba(120,90,50,0.10);
}

body {
  font-family: 'Noto Sans JP', sans-serif;
  background: var(--bg-dark);
  color: var(--text-main);
  min-height: 100vh;
}

.app {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
}

/* ─── Header ─── */
.header {
  position: relative;
  overflow: hidden;
  text-align: center;
  padding: 92px 20px;
  background-image: url("/images/header-bg.webp");
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  cursor: pointer;
  transition: opacity 0.2s;
}

.header:active {
  opacity: 0.9;
}

.header::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(to bottom, var(--bg-dark) 0%, transparent 20%, transparent 80%, var(--bg-dark) 100%),
    linear-gradient(rgba(255,255,255,0.5), rgba(255,255,255,0.65));
  z-index: 1;
}

.logo-title {
  position: relative;
  z-index: 2;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 48px;
  letter-spacing: 6px;
  font-weight: 900;
  color: #A0001C;
  line-height: 1.1;
  text-shadow:
    0 0 15px rgba(255, 255, 255, 1),
    0 0 30px rgba(255, 255, 255, 0.8),
    2px 2px 4px rgba(255, 255, 255, 1);
  -webkit-background-clip: initial;
  -webkit-text-fill-color: initial;
}

.logo-sub {
  position: relative;
  z-index: 2;
  font-size: 13px;
  font-weight: 900;
  color: #444;
  letter-spacing: 6px;
  margin-top: 10px;
  text-shadow: 0 0 8px #fff;
}

/* ─── Navigation Tabs ─── */
.nav-tabs {
  display: flex;
  gap: 4px;
  margin: 28px 0 24px;
  border-bottom: 2px solid var(--border);
  padding-bottom: 0;
}

.nav-tab {
  padding: 10px 20px;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 14px;
  font-family: 'Noto Sans JP', sans-serif;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
  white-space: nowrap;
}

.nav-tab:hover { color: var(--text-main); }

.nav-tab.active {
  color: var(--red-main);
  border-bottom-color: var(--red-main);
}

/* ─── Search ─── */
.search-area {
  margin-bottom: 24px;
}

/* ─── Results Meta (Count) ─── */
.results-info-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 0 4px 12px;
  border-bottom: 1px solid rgba(232, 223, 208, 0.6);
}

.results-count-box {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.results-count-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 32px;
  color: var(--red-main);
  line-height: 1;
  text-shadow: 1px 1px 0px rgba(255,255,255,0.8);
}

.results-count-label {
  font-size: 12px;
  font-weight: 900;
  color: var(--text-dim);
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.results-divider {
  flex-grow: 1;
  height: 1px;
  background: linear-gradient(to right, var(--border), transparent);
  margin-left: 20px;
}

/* 数字が変わった時のアニメーション */
@keyframes countPop {
  0% { transform: scale(1); }
  50% { transform: scale(1.1); color: var(--red-bright); }
  100% { transform: scale(1); }
}

.count-animate {
  display: inline-block;
  animation: countPop 0.3s ease-out;
}

.search-box {
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-input {
  flex: 1;
  padding: 12px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-main);
  font-size: 15px;
  font-family: 'Noto Sans JP', sans-serif;
  outline: none;
  transition: border-color 0.2s;
}

.search-input::placeholder { color: var(--text-dim); }
.search-input:focus { border-color: var(--red-main); }

.filter-row {
  display: flex;
  gap: 6px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.filter-chip {
  padding: 5px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 20px;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: 'Noto Sans JP', sans-serif;
}

.filter-chip:hover { border-color: var(--text-muted); }

.filter-chip.active {
  background: var(--red-main);
  border-color: var(--red-main);
  color: white;
}

/* ─── Character tab: search + arc + affiliation row ─── */
.character-search-row {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 10px;
}

.character-search-row .search-box {
  flex: 1 1 220px;
  min-width: 180px;
}

.character-search-row .affiliation-filter {
  margin-top: 0;
}

/* ─── Arc / Affiliation Filter (Select) ─── */
.arc-filter-wrap {
  position: relative;
  display: inline-block;
}

.arc-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text-main);
  font-size: 14px;
  font-family: 'Noto Sans JP', sans-serif;
  padding: 10px 38px 10px 12px;
  outline: none;
  transition: border-color 0.2s;
  cursor: pointer;
  min-width: 200px;
  max-width: min(280px, 100%);
}

.arc-select:focus {
  border-color: var(--red-main);
}

.arc-select.is-placeholder {
  color: transparent;
  -webkit-text-fill-color: transparent;
}

.arc-select.is-placeholder option {
  color: var(--text-main);
  -webkit-text-fill-color: var(--text-main);
}

.arc-placeholder {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 14px;
  font-family: 'Noto Sans JP', sans-serif;
  pointer-events: none;
}

.arc-caret {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 10px;
  pointer-events: none;
}

/* ─── Affiliation Filter (Select) ─── */
.affiliation-filter {
  margin-top: 10px;
  position: relative;
  display: inline-block;
}

.affiliation-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text-main);
  font-size: 14px;
  font-family: 'Noto Sans JP', sans-serif;
  padding: 10px 38px 10px 12px;
  outline: none;
  transition: border-color 0.2s;
  cursor: pointer;
  min-width: 180px;
}

.affiliation-select:focus {
  border-color: var(--red-main);
}

/* When crewFilter is 'all', show placeholder overlay */
.affiliation-select.is-placeholder {
  color: transparent;
  -webkit-text-fill-color: transparent;
}

.affiliation-select.is-placeholder option {
  color: var(--text-main);
  -webkit-text-fill-color: var(--text-main);
}

.affiliation-placeholder {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 14px;
  font-family: 'Noto Sans JP', sans-serif;
  pointer-events: none;
}

.affiliation-caret {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  font-size: 14px;
  pointer-events: none;
}

/* ─── Character Grid ─── */
.char-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.char-card {
  background: #fff;
  border: none;
  border-radius: 16px;
  padding: 0;
  cursor: pointer;
  transition: box-shadow 0.25s ease, transform 0.25s ease;
  position: relative;
  overflow: hidden;
  box-shadow: 0 8px 26px rgba(20, 20, 20, 0.08);
  display: flex;
  flex-direction: column;
}

.char-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 40px rgba(20, 20, 20, 0.14);
}

.char-image-container {
  width: 100%;
  aspect-ratio: 1 / 1;
  position: relative;
  background: #f0f0f0;
  overflow: hidden;
}

.char-image-container img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  transform: scale(1);
  transition: transform 0.35s ease;
}

.char-card:hover .char-image-container img {
  transform: scale(1.05);
}

.no-image-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  color: #999;
  font-size: 14px;
  letter-spacing: 2px;
  font-family: 'Bebas Neue', sans-serif;
}

.char-name-container {
  padding: 10px 10px 11px;
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  min-width: 0;
  width: 100%;
}

.char-name {
  font-size: 15px;
  font-weight: 900;
  color: var(--text-main);
  letter-spacing: 0.02em;
  line-height: 1.1;
  margin: 0;
  text-align: center;
}

.meta-label {
  color: var(--text-dim);
  min-width: 50px;
}

.meta-value {
  color: var(--text-muted);
}

.bounty-value {
  color: var(--red-main);
  font-weight: 700;
}

/* ─── SBS (detail panel) ─── */
.sbs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.sbs-item {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
}

.sbs-item.brain {
  grid-column: 1 / -1;
  background: linear-gradient(180deg, rgba(255, 248, 237, 0.95), rgba(255, 241, 220, 0.98));
  border-color: rgba(200, 150, 10, 0.35);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
}

.sbs-label {
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.sbs-value {
  margin-top: 6px;
  font-size: 14px;
  font-weight: 800;
  color: var(--text-main);
  line-height: 1.55;
  word-break: break-word;
}

.sbs-tab {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.sbs-basic .sbs-grid {
  margin: 0;
}

.sbs-materials-heading {
  margin: 0 0 14px;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: var(--text-main);
}

.sbs-materials-gallery {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 20px 24px;
  align-items: flex-start;
  justify-content: flex-start;
}

.sbs-img-field {
  flex: 0 1 240px;
  max-width: 240px;
  min-width: 0;
}

.sbs-img-field--preload {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}

.sbs-img-field--loaded {
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 12px 12px 10px;
  background: var(--bg-card);
  box-shadow: 0 2px 12px rgba(45, 31, 20, 0.08);
}

.sbs-img-field-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 10px;
  line-height: 1.35;
}

.sbs-img-field-photo {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: rgba(0, 0, 0, 0.03);
}

.sbs-img-field-caption {
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-dim);
  line-height: 1.45;
  text-align: center;
}

@media (max-width: 640px) {
  .sbs-grid {
    grid-template-columns: 1fr;
  }
  .sbs-item.brain {
    grid-column: auto;
  }
  .sbs-materials-gallery {
    flex-direction: column;
    align-items: center;
  }
  .sbs-img-field {
    flex: 0 0 auto;
    width: 100%;
    max-width: 240px;
    margin-left: auto;
    margin-right: auto;
  }
}

/* ─── Detail Panel ─── */
.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(45,31,20,0.35);
  backdrop-filter: blur(4px);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  animation: fadeIn 0.2s;
}

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

.detail-panel {
  background: var(--bg-dark);
  border: 1px solid var(--border);
  border-radius: 16px;
  max-width: 800px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  animation: slideUp 0.3s ease-out;
}

.detail-header {
  padding: 28px 28px 20px;
  border-bottom: 1px solid var(--border);
  position: relative;
}

.detail-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 24px;
  cursor: pointer;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.detail-close:hover {
  background: var(--bg-card);
  color: var(--text-main);
}

.detail-alias {
  font-size: 14px;
  font-weight: 700;
  color: var(--red-main);
  margin-bottom: 4px;
  letter-spacing: 0.1em;
}

.detail-name {
  font-size: 28px;
  font-weight: 900;
}

.detail-name-en {
  font-size: 13px;
  color: var(--text-dim);
  letter-spacing: 2px;
  margin-top: 2px;
}

.detail-info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.info-item {
  background: var(--bg-card);
  padding: 10px 14px;
  border-radius: 8px;
}

.info-label {
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.info-value {
  font-size: 14px;
  margin-top: 2px;
  font-weight: 500;
}

.info-value.highlight {
  color: var(--red-main);
}

/* ─── Detail Tabs ─── */
.detail-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  padding: 0 28px;
}

.detail-tab {
  padding: 12px 18px;
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.2s;
  font-family: 'Noto Sans JP', sans-serif;
}

.detail-tab:hover { color: var(--text-muted); }

.detail-tab.active {
  color: var(--red-main);
  border-bottom-color: var(--red-main);
}

.detail-content {
  padding: 24px 28px;
  max-width: 100%;
}

/* mobile overflow guard：狭い画面でも横スクロールで列が潰れない */
.table-scroll {
  max-width: 100%;
  min-width: 500px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.table-scroll .appearance-table {
  min-width: 500px;
}

/* ─── Appearance Table ─── */
.appearance-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
}

.appearance-table th {
  padding: 8px 10px;
  font-size: 11px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.appearance-table td {
  padding: 8px 10px;
  font-size: 13px;
  border-bottom: 1px solid rgba(232, 223, 208, 0.7);
  vertical-align: middle;
}

.appearance-table th.appearance-col-vol,
.appearance-table td.appearance-col-vol {
  width: 50px;
  max-width: 50px;
  text-align: center;
  white-space: nowrap;
}

.appearance-table th.appearance-col-ep,
.appearance-table td.appearance-col-ep {
  width: 70px;
  max-width: 70px;
  text-align: left;
  white-space: nowrap;
}

.appearance-table th.appearance-col-title,
.appearance-table td.appearance-col-title {
  width: auto;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.appearance-table th.appearance-col-kindle,
.appearance-table td.appearance-col-kindle {
  width: 170px;
  max-width: 170px;
  text-align: right;
  white-space: nowrap;
}

.appearance-table td.appearance-col-vol {
  color: var(--text-dim);
}

.appearance-table td.appearance-col-ep {
  color: var(--red-main);
  font-weight: 700;
}

.appearance-table tr:hover td {
  background: var(--bg-card);
}

/* ─── Episode list tab (main) ─── */
.episode-list-container {
  margin-bottom: 24px;
}

.volume-card {
  display: flex;
  background: var(--bg-card);
  border-radius: 20px;
  margin-bottom: 48px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(45, 31, 20, 0.08);
  border: 1px solid var(--border);
}

.volume-sidebar {
  width: 240px;
  background: #fdfaf3;
  padding: 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-right: 1px solid var(--border);
  flex-shrink: 0;
  min-height: 100%;
}

.volume-cover-large {
  width: 100%;
  height: auto;
  border-radius: 4px;
  box-shadow: 0 15px 30px rgba(0, 0, 0, 0.2);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.volume-card:hover .volume-cover-large {
  transform: scale(1.03) translateY(-5px);
}

.volume-badge {
  margin-top: 24px;
  text-align: center;
  display: flex;
  flex-direction: column-reverse;
  align-items: center;
}

.volume-badge .vol-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 42px;
  color: var(--red-main);
  line-height: 1;
}

.volume-badge .vol-label {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 14px;
  letter-spacing: 4px;
  color: var(--text-dim);
  margin-bottom: 4px;
}

.volume-episodes {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* 地名タブ用（旧 volume-group / volume-header 相当） */
.location-volume-block {
  margin-bottom: 40px;
  background: var(--bg-card);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
  border: 1px solid var(--border);
}

.location-volume-header {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 16px 28px;
  background: linear-gradient(135deg, #fdfbf7 0%, #f5f0e6 100%);
  border-left: 6px solid var(--red-main);
  border-bottom: 2px solid var(--border);
}

.location-volume-info {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.location-volume-header .vol-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 24px;
  color: var(--red-main);
}

.location-volume-header .vol-label {
  font-size: 14px;
  font-weight: 900;
  color: var(--text-main);
}

.location-volume-rows {
  display: flex;
  flex-direction: column;
}

.episode-list-row {
  padding: 18px 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(232, 223, 208, 0.4);
  transition: background 0.2s;
}

.episode-list-row:last-child {
  border-bottom: none;
}

.episode-list-row:hover {
  background: #fffcf5;
}

.ep-main-info {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.ep-number {
  font-size: 13px;
  font-weight: 700;
  color: var(--red-main);
  min-width: 70px;
  flex-shrink: 0;
}

.ep-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.ep-meta-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.anime-info-badge {
  display: flex;
  align-items: center;
  background: #f0f0f0;
  border-radius: 6px;
  padding: 2px 2px 2px 8px;
  gap: 8px;
  border: 1px solid var(--border);
  min-width: 100px;
}

.anime-info-badge .anime-label {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 10px;
  color: #888;
  letter-spacing: 1px;
}

.anime-info-badge .anime-value {
  background: #ffffff;
  color: var(--text-main);
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05);
}

@media (max-width: 900px) {
  .volume-card {
    flex-direction: column;
  }

  .volume-sidebar {
    width: 100%;
    flex-direction: row;
    padding: 20px;
    gap: 20px;
    border-right: none;
    border-bottom: 1px solid var(--border);
  }

  .volume-cover-large {
    width: 80px;
    flex-shrink: 0;
  }

  .volume-badge {
    margin-top: 0;
    align-items: flex-start;
  }
}

@media (max-width: 768px) {
  .episode-list-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .ep-meta-info {
    width: 100%;
    justify-content: space-between;
  }
}

/* ─── Major locations tab ─── */
.location-main-info {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 14px;
  flex: 1;
  min-width: 0;
}

.location-name-primary {
  font-size: 15px;
  font-weight: 800;
  color: var(--text-main);
}

.location-chapter-tag {
  font-size: 13px;
  font-weight: 700;
  color: var(--red-main);
  flex-shrink: 0;
}

.location-note-label {
  font-size: 11px;
  color: var(--text-dim);
  margin-left: 10px;
  font-weight: 400;
}

@media (max-width: 768px) {
  .location-note-label {
    margin-left: 0;
    width: 100%;
  }
}

.kindle-btn-group {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
  align-items: center;
  flex-wrap: nowrap;
}

.kindle-btn-group--compact {
  margin-left: 4px;
  vertical-align: middle;
  justify-content: flex-end;
}

.kindle-btn-mono,
.kindle-btn-color {
  display: inline-block;
  padding: 2px 6px;
  font-size: 10px;
  line-height: 1;
  border-radius: 4px;
  color: #fff;
  text-decoration: none;
  white-space: nowrap;
  font-weight: 600;
  border: 1px solid transparent;
  box-sizing: border-box;
  transition: filter 0.15s, background 0.15s, color 0.15s;
}

.kindle-btn-mono {
  background: #50a0d5;
  color: #fff;
  border-color: #50a0d5;
}

.kindle-btn-mono:hover {
  filter: brightness(1.08);
  color: #fff;
}

.kindle-btn-color {
  background: #d42d25;
  color: #fff;
  border-color: #d42d25;
}

.kindle-btn-color:hover {
  filter: brightness(1.08);
  color: #fff;
}

.kindle-btn-netflix {
  display: inline-block;
  padding: 2px 8px;
  font-size: 10px;
  line-height: 1;
  border-radius: 4px;
  color: #ffffff;
  text-decoration: none;
  white-space: nowrap;
  font-weight: 600;
  background: #222222;
  border: 1px solid #222222;
  transition: all 0.15s;
  margin-left: 4px;
  min-width: 60px;
  text-align: center;
}

.kindle-btn-netflix:hover {
  background: #444444;
  border-color: #444444;
  filter: brightness(1.2);
}

.kindle-btn-group a.disabled {
  background: #e0e0e0 !important;
  border-color: #d0d0d0 !important;
  color: #a0a0a0 !important;
  cursor: not-allowed;
  pointer-events: none;
  box-shadow: none !important;
  filter: grayscale(1);
}

/* ─── Ability Cards ─── */
.ability-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ability-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 18px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  transition: border-color 0.2s;
}

.ability-card:hover {
  border-color: var(--red-main);
}

.ability-type-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
  min-width: 56px;
  text-align: center;
  margin-top: 2px;
}

.ability-info { flex: 1; }

.ability-name {
  font-size: 15px;
  font-weight: 700;
}

.ability-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 3px;
  line-height: 1.5;
}

.ability-first-use {
  font-size: 11px;
  color: var(--text-dim);
  margin-top: 6px;
}

.episode-preview {
  font-size: 10px;
  color: var(--text-dim);
  margin-top: 6px;
  line-height: 1.4;
}

.episode-links-section {
  margin-top: 6px;
  font-size: 10px;
  color: var(--text-dim);
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.episode-links-heading {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-dim);
  margin-bottom: 4px;
}

.episode-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.episode-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.episode-row:last-child {
  border-bottom: none;
}

.episode-row .episode-link-label {
  color: var(--red-main);
  font-weight: 700;
  font-size: 10px;
  flex: 1;
  min-width: 0;
}

.episode-row .kindle-btn-group {
  flex-shrink: 0;
  justify-content: flex-end;
}

.episode-links-empty {
  font-size: 10px;
  color: var(--text-dim);
  padding: 2px 0;
}

/* ─── DetailPanel: 技アコーディオン ─── */
.ability-list.ability-accordion-list {
  gap: 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border);
}

.ability-item {
  border-bottom: 1px solid rgba(232, 223, 208, 0.6);
  background: var(--bg-card);
}

.ability-item:last-child {
  border-bottom: none;
}

.ability-header {
  padding: 14px 20px;
  display: flex;
  align-items: center;
  cursor: pointer;
  transition: background 0.2s;
  gap: 12px;
}

.ability-header:hover {
  background: #fdfaf3;
}

.ability-toggle-icon {
  font-size: 10px;
  color: var(--red-main);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  line-height: 1;
}

.ability-item.open .ability-toggle-icon {
  transform: rotate(90deg);
}

.ability-name-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.ability-item .ability-name {
  font-size: 15px;
  font-weight: 800;
  color: var(--text-main);
}

.ability-reading-small {
  font-size: 11px;
  color: var(--text-dim);
  font-weight: 500;
}

.ability-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  background: #faf9f5;
}

.ability-item.open .ability-content {
  max-height: 3000px;
  border-top: 1px solid rgba(0, 0, 0, 0.03);
}

.ability-inner-padding {
  padding: 16px 20px 20px 42px;
}

/* ─── Relations ─── */
.relation-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.relation-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.relation-card:hover {
  border-color: var(--red-main);
  transform: translateY(-1px);
}

.relation-type {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
  display: inline-block;
  margin-bottom: 6px;
}

.relation-name {
  font-size: 15px;
  font-weight: 700;
}

.relation-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* ─── Ability Search Tab ─── */
.ability-search-results {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.ability-result-group {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 20px;
}

.ability-result-char {
  font-size: 11px;
  color: var(--red-main);
  letter-spacing: 1px;
  margin-bottom: 8px;
  font-weight: 700;
}

/* ─── Arc Timeline ─── */
.arc-timeline {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.arc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border);
  font-size: 13px;
  transition: all 0.2s;
}

.arc-item:hover {
  border-color: var(--red-main);
}

.arc-num {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 18px;
  color: var(--red-main);
  min-width: 28px;
}

.arc-name {
  flex: 1;
}

.arc-chars {
  display: flex;
  gap: 4px;
}

.arc-char-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--red-main), var(--yellow-warm));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 900;
  color: white;
}

/* ─── Empty / No Results ─── */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
}

.empty-state-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-state-text {
  font-size: 14px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg-dark); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #C4B8A6; }

/* ─── Footer ─── */
.app-footer {
  text-align: center;
  padding: 40px 0;
  font-size: 11px;
  color: var(--text-dim);
  border-top: 1px solid var(--border);
  margin-top: 40px;
}

.scroll-to-top {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 50px;
  height: 50px;
  background-color: var(--red-main);
  color: white;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  box-shadow: 0 4px 15px rgba(160, 0, 28, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: scrollTopPopIn 0.3s ease-out;
}

.scroll-to-top:hover {
  background-color: var(--red-deep);
  transform: translateY(-5px);
  box-shadow: 0 6px 20px rgba(160, 0, 28, 0.4);
}

@keyframes scrollTopPopIn {
  from {
    transform: scale(0) translateY(20px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

@media (max-width: 768px) {
  .scroll-to-top {
    bottom: 20px;
    right: 20px;
    width: 45px;
    height: 45px;
  }
}

.updates-container {
  max-width: 800px;
  margin: 40px auto;
  padding: 0 20px;
}

.timeline {
  position: relative;
  padding-left: 32px;
  border-left: 2px solid var(--border);
}

.timeline-item {
  position: relative;
  margin-bottom: 40px;
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: -41px;
  top: 4px;
  width: 16px;
  height: 16px;
  background: var(--bg-dark);
  border: 3px solid var(--red-main);
  border-radius: 50%;
  z-index: 2;
}

.timeline-date {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 18px;
  color: var(--red-main);
  letter-spacing: 2px;
  margin-bottom: 8px;
  display: block;
}

.timeline-content {
  background: var(--bg-card);
  padding: 20px 24px;
  border-radius: 12px;
  border: 1px solid var(--border);
  box-shadow: 0 4px 15px rgba(0,0,0,0.03);
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-main);
  font-weight: 500;
}

.timeline-content b {
  color: var(--red-main);
  font-weight: 900;
}

.timeline-content {
  background: var(--bg-card);
  padding: 24px 28px;
  border-radius: 16px;
  border: 1px solid var(--border);
  box-shadow: 0 8px 30px rgba(45, 31, 20, 0.04);
}

.update-header {
  font-size: 11px;
  font-weight: 900;
  color: #fff;
  background: var(--red-main);
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  margin-bottom: 16px;
  letter-spacing: 0.1em;
}

.update-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.update-char {
  font-size: 13px;
  font-weight: 800;
  color: var(--text-main);
  border-bottom: 1px solid rgba(160, 0, 28, 0.1);
  padding-bottom: 4px;
  display: inline-block;
  width: fit-content;
}

.update-list {
  list-style: none;
  padding-left: 14px;
  margin: 0 0 4px 0;
}

.update-list li {
  font-size: 13px;
  color: var(--text-muted);
  position: relative;
  line-height: 1.8;
}

.update-list li::before {
  content: '-';
  position: absolute;
  left: -14px;
  color: var(--red-main);
  font-weight: bold;
}
`;

// ─── Components ───

function KindleDualLinks({ episode, compact = false, showNetflix = true }) {
  const vol = getVolumeFromEpisode(episode);
  const animeData = mangaAnimeMap[String(episode)];
  const animeEp =
    animeData != null && typeof animeData === "object" && animeData.ep != null
      ? parseInt(String(animeData.ep).trim(), 10) || 0
      : animeData != null && typeof animeData !== "object"
        ? parseInt(String(animeData).trim(), 10) || 0
        : 0;

  const isMonoAvailable = vol <= PUBLISHED_LIMITS.MONO_VOL;
  const isColorAvailable = vol <= PUBLISHED_LIMITS.COLOR_VOL;
  const isNetflixAvailable = animeEp > 0 && animeEp <= PUBLISHED_LIMITS.ANIME_EP;

  const monoUrl = getKindleUrl(episode, "mono");
  const colorUrl = getKindleUrl(episode, "color");
  const netflixUrl = getNetflixUrl(episode);
  const netflixLinkTitle =
    animeEp > 0 ? `アニメ第${animeEp}話を Netflix で開く` : "ONE PIECE（Netflix）";

  return (
    <div className={`kindle-btn-group${compact ? " kindle-btn-group--compact" : ""}`}>
      <a
        className={`kindle-btn-mono ${!isMonoAvailable ? "disabled" : ""}`}
        href={isMonoAvailable ? monoUrl : undefined}
        target={isMonoAvailable ? "_blank" : undefined}
        rel="noopener noreferrer"
        onClick={isMonoAvailable ? () => handleKindleNavClick(episode, monoUrl, "mono") : undefined}
      >
        モノクロ
      </a>
      <a
        className={`kindle-btn-color ${!isColorAvailable ? "disabled" : ""}`}
        href={isColorAvailable ? colorUrl : undefined}
        target={isColorAvailable ? "_blank" : undefined}
        rel="noopener noreferrer"
        onClick={isColorAvailable ? () => handleKindleNavClick(episode, colorUrl, "color") : undefined}
      >
        カラー
      </a>
      {showNetflix && (
        <a
          className={`kindle-btn-netflix ${!isNetflixAvailable ? "disabled" : ""}`}
          href={isNetflixAvailable ? netflixUrl : undefined}
          target={isNetflixAvailable ? "_blank" : undefined}
          rel="noopener noreferrer"
          title={isNetflixAvailable ? netflixLinkTitle : undefined}
          onClick={isNetflixAvailable ? () => handleKindleNavClick(episode, netflixUrl, "netflix") : undefined}
        >
          Netflix
        </a>
      )}
    </div>
  );
}

function CharacterCard({ char, onClick }) {
  return (
    <div className="char-card" onClick={() => onClick(char)}>
      <div className="char-image-container">
        <img
          src={`/images/thumbnails/${char.id}.webp`}
          alt={char.name}
          loading="lazy"
          decoding="async"
          onError={(e) => {
            e.target.style.display = "none";
            if (e.target.nextSibling) e.target.nextSibling.style.display = "flex";
          }}
        />
        <div className="no-image-overlay" style={{ display: "none" }}>
          No Image
        </div>
      </div>
      <div className="char-name-container">
        <div className="char-name">{char.name}</div>
      </div>
    </div>
  );
}

function SbsImageField({ src, heading }) {
  const path = String(src ?? "").trim();
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    setStatus("loading");
  }, [path]);

  if (!path) return null;
  if (status === "error") return null;

  const preload = status !== "ok";

  return (
    <div
      className={`sbs-img-field ${preload ? "sbs-img-field--preload" : "sbs-img-field--loaded"}`}
    >
      {status === "ok" && <div className="sbs-img-field-title">{heading}</div>}
      <img
        className="sbs-img-field-photo"
        src={path}
        alt="SBS資料画像"
        loading="lazy"
        decoding="async"
        onLoad={() => setStatus("ok")}
        onError={() => setStatus("error")}
      />
      {status === "ok" && <div className="sbs-img-field-caption">{heading}</div>}
    </div>
  );
}

function AbilityAccordionItem({ ability }) {
  const [open, setOpen] = useState(false);
  const skill = SKILLS_BY_ID.get(ability.id);
  const reading = String(skill?.reading ?? ability?.reading ?? "").trim();
  const items = getEpisodeLinkItems(skill?.episodes);

  const toggle = () => setOpen((v) => !v);
  const onHeaderKeyDown = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      toggle();
    }
  };

  return (
    <div className={`ability-item${open ? " open" : ""}`}>
      <div
        className="ability-header"
        onClick={toggle}
        onKeyDown={onHeaderKeyDown}
        role="button"
        tabIndex={0}
        aria-expanded={open}
      >
        <span className="ability-toggle-icon" aria-hidden="true">
          ▶
        </span>
        <div className="ability-name-row">
          <span className="ability-name">{ability.name}</span>
          {reading ? <span className="ability-reading-small">{reading}</span> : null}
        </div>
      </div>
      <div className="ability-content">
        <div className="ability-inner-padding">
          <div className="episode-links-section">
            <div className="episode-links-heading">登場話</div>
            {items.length ? (
              <div className="episode-links">
                {items.map((it) => (
                  <div key={it.episode} className="episode-row">
                    <span className="episode-link-label">{it.label}</span>
                    <KindleDualLinks episode={it.episode} compact />
                  </div>
                ))}
              </div>
            ) : (
              <span className="episode-links-empty">—</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailPanel({ char, onClose }) {
  const [tab, setTab] = useState("appearances");

  useEffect(() => {
    setTab("appearances");
  }, [char?.id]);

  const appearances = char.appearances || [];
  const coverAppearances = appearances.filter((a) => String(a?.title ?? "").includes("の扉絵"));
  const mainAppearances = appearances.filter((a) => !String(a?.title ?? "").includes("の扉絵"));

  const sbs = char.sbs;
  const animalPart = String(sbs?.animal ?? "").trim();
  const numberPart = String(sbs?.number ?? "").trim();
  const animalNumber =
    animalPart && numberPart
      ? `${animalPart} / ${numberPart}`
      : animalPart || numberPart || "";

  const sbsImages = sbs?.images && typeof sbs.images === "object" ? sbs.images : null;
  const sbsImageSlots =
    sbsImages == null
      ? []
      : [
          { key: "child", heading: "幼少期の姿", src: sbsImages.child },
          { key: "future_good", heading: "未来（通常）", src: sbsImages.future_good },
          { key: "future_bad", heading: "未来（何かあった場合）", src: sbsImages.future_bad },
        ].filter((row) => String(row.src ?? "").trim());
  const hasSbsImageUrls =
    sbsImages != null &&
    ["child", "future_good", "future_bad"].some((k) => String(sbsImages[k] ?? "").trim());

  const formatCoverTitleForDisplay = (title) => String(title ?? "").replace(/の扉絵/g, "扉絵");

  const renderAppearanceTable = (rows, { normalizeCoverTitle = false, showNetflix = true } = {}) => (
    <div className="table-scroll">
      <table className="appearance-table">
        <thead>
          <tr>
            <th className="appearance-col-vol">巻</th>
            <th className="appearance-col-ep">話</th>
            <th className="appearance-col-title">タイトル</th>
            <th className="appearance-col-kindle" aria-label="Kindle"></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a, i) => {
            const volNum = getVolumeLabelForAppearance(a.episode);
            const volCell = volNum === "—" ? "—" : `${volNum}巻`;
            return (
            <tr key={i}>
              <td className="appearance-col-vol">{volCell}</td>
              <td className="appearance-col-ep">第{a.episode}話</td>
              <td
                className="appearance-col-title"
                title={normalizeCoverTitle ? formatCoverTitleForDisplay(a.title) : String(a.title ?? "")}
              >
                {normalizeCoverTitle ? formatCoverTitleForDisplay(a.title) : a.title}
              </td>
              <td className="appearance-col-kindle">
                <KindleDualLinks episode={a.episode} showNetflix={showNetflix} />
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="detail-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="detail-panel">
        <div className="detail-header">
          <button className="detail-close" onClick={onClose}>✕</button>
          {String(char.alias ?? "").trim() ? (
            <div className="detail-alias">
              {"\u201c"}
              {String(char.alias).trim()}
              {"\u201d"}
            </div>
          ) : null}
          <div className="detail-name">{char.name}</div>
          <div className="detail-name-en">{char.reading}</div>
          <div className="detail-info-grid">
            <div className="info-item">
              <div className="info-label">組織</div>
              <div className="info-value">{`[${
                Array.isArray(char.category) ? (char.category.length ? char.category.join(" / ") : "—") : (char.category || "—")
              }] / ${
                Array.isArray(char.group) ? (char.group.length ? char.group.join(" / ") : "—") : (char.group || "—")
              }`}</div>
            </div>
            <div className="info-item">
              <div className="info-label">懸賞金</div>
              <div className="info-value highlight">{char.bounty || "—"}</div>
            </div>
            <div className="info-item">
              <div className="info-label">悪魔の実</div>
              <div className="info-value">{char.devilFruit || "—"}</div>
            </div>
            <div className="info-item">
              <div className="info-label">初登場</div>
              <div className="info-value">第{char.firstAppearance}話</div>
            </div>
            <div className="info-item">
              <div className="info-label">誕生日</div>
              <div className="info-value">{char.birthday || "—"}</div>
            </div>
            <div className="info-item">
              <div className="info-label">性別</div>
              <div className="info-value">{char.gender || "—"}</div>
            </div>
          </div>
        </div>

        <div className="detail-tabs">
          <button className={`detail-tab ${tab === "appearances" ? "active" : ""}`} onClick={() => setTab("appearances")}>
            登場話一覧
          </button>
          <button className={`detail-tab ${tab === "covers" ? "active" : ""}`} onClick={() => setTab("covers")}>
            扉絵一覧
          </button>
          <button className={`detail-tab ${tab === "abilities" ? "active" : ""}`} onClick={() => setTab("abilities")}>
            技・能力
          </button>
          <button className={`detail-tab ${tab === "sbs" ? "active" : ""}`} onClick={() => setTab("sbs")}>
            SBS
          </button>
        </div>

        <div className="detail-content">
          {tab === "appearances" && (
            renderAppearanceTable(mainAppearances)
          )}

          {tab === "covers" && (
            coverAppearances.length > 0 ? (
              renderAppearanceTable(coverAppearances, { normalizeCoverTitle: true, showNetflix: false })
            ) : (
              <div className="empty-state" style={{ padding: "24px 0" }}>
                <div className="empty-state-text">扉絵への登場はありません</div>
              </div>
            )
          )}

          {tab === "abilities" && (
            <div className="ability-list ability-accordion-list">
              {(char.abilities || []).map((ab, i) => (
                <AbilityAccordionItem key={ab.id != null ? String(ab.id) : `ab-${char.id}-${i}`} ability={ab} />
              ))}
            </div>
          )}

          {tab === "sbs" && (
            sbs ? (
              <div className="sbs-tab">
                <div className="sbs-basic">
                  <div className="sbs-grid">
                    <div className="sbs-item">
                      <div className="sbs-label">イメージ国</div>
                      <div className="sbs-value">{String(sbs.nationality ?? "").trim() || "—"}</div>
                    </div>
                    <div className="sbs-item">
                      <div className="sbs-label">イメージカラー</div>
                      <div className="sbs-value">{String(sbs.color ?? "").trim() || "—"}</div>
                    </div>
                    <div className="sbs-item">
                      <div className="sbs-label">家族に例えると</div>
                      <div className="sbs-value">{String(sbs.family ?? "").trim() || "—"}</div>
                    </div>
                    <div className="sbs-item brain">
                      <div className="sbs-label">脳内構造</div>
                      <div className="sbs-value">{String(sbs.brain ?? "").trim() || "—"}</div>
                    </div>
                    <div className="sbs-item">
                      <div className="sbs-label">入浴頻度</div>
                      <div className="sbs-value">{String(sbs.bath ?? "").trim() || "—"}</div>
                    </div>
                    <div className="sbs-item">
                      <div className="sbs-label">睡眠時間</div>
                      <div className="sbs-value">{String(sbs.sleep ?? "").trim() || "—"}</div>
                    </div>
                    <div className="sbs-item">
                      <div className="sbs-label">イメージの香り</div>
                      <div className="sbs-value">{String(sbs.scent ?? "").trim() || "—"}</div>
                    </div>
                    <div className="sbs-item">
                      <div className="sbs-label">イメージ動物・番号</div>
                      <div className="sbs-value">{animalNumber || "—"}</div>
                    </div>
                  </div>
                </div>

                {hasSbsImageUrls && (
                  <section className="sbs-materials" aria-label="設定資料（SBS画像）">
                    <h3 className="sbs-materials-heading">設定資料（SBS画像）</h3>
                    <div className="sbs-materials-gallery">
                      {sbsImageSlots.map((row) => (
                        <SbsImageField key={row.key} src={row.src} heading={row.heading} />
                      ))}
                    </div>
                  </section>
                )}
              </div>
            ) : (
              <div className="empty-state" style={{ padding: "24px 0" }}>
                <div className="empty-state-text">このキャラクターのSBS情報はありません</div>
              </div>
            )
          )}

        </div>
      </div>
    </div>
  );
}

// ─── Main App ───
export default function App() {
  const [activeTab, setActiveTab] = useState("characters");
  const [search, setSearch] = useState("");
  const [episodeSearch, setEpisodeSearch] = useState("");
  const [locationSearch, setLocationSearch] = useState("");
  const [orgCategoryFilter, setOrgCategoryFilter] = useState("all");
  const [orgGroupFilter, setOrgGroupFilter] = useState("all");
  const [arcFilter, setArcFilter] = useState("all");
  const [selectedChar, setSelectedChar] = useState(null);
  const [showScrollTop, setShowScrollTop] = useState(false);

  const handleHeaderClick = () => {
    setActiveTab("characters");
    setSearch("");
    setEpisodeSearch("");
    setLocationSearch("");
    setOrgCategoryFilter("all");
    setOrgGroupFilter("all");
    setArcFilter("all");
    setSelectedChar(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    console.log("Anime Map Data:", mangaAnimeMap);
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 400) {
        setShowScrollTop(true);
      } else {
        setShowScrollTop(false);
      }
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const orgCategories = useMemo(() => {
    const desiredOrder = [
      "海賊",
      "天竜人",
      "世界政府",
      "海軍",
      "革命軍",
      "科学者",
      "王家",
      "戦う者達",
      "市民",
      "その他",
    ];

    const cats = Object.keys(organizationMaster || {});
    const remaining = cats.filter((c) => !desiredOrder.includes(c));
    remaining.sort((a, b) => a.localeCompare(b, "ja"));

    const ordered = desiredOrder.filter((c) => cats.includes(c));
    return ["all", ...ordered, ...remaining];
  }, []);

  const orgGroupsForSelectedCategory = useMemo(() => {
    if (orgCategoryFilter === "all") return ["all"];
    const groups = Array.isArray(organizationMaster?.[orgCategoryFilter]) ? organizationMaster[orgCategoryFilter] : [];
    const uniq = Array.from(new Set(groups.filter(Boolean)));
    uniq.sort((a, b) => String(a).localeCompare(String(b), "ja"));
    return ["all", ...uniq];
  }, [orgCategoryFilter]);

  /** mangaAnimeMap をマスタにした漫画話一覧（登場データがなくても map に title があれば表示） */
  const mangaEpisodes = useMemo(() => {
    return Object.keys(mangaAnimeMap)
      .map((epNum) => {
        const episode = parseInt(epNum, 10);
        const raw = mangaAnimeMap[epNum];
        const meta = raw != null && typeof raw === "object" ? raw : {};
        return {
          episode,
          title: meta.title || "タイトル未設定",
          volume: getVolumeFromEpisode(episode),
        };
      })
      .filter((row) => Number.isFinite(row.episode) && row.episode > 0)
      .sort((a, b) => a.episode - b.episode);
  }, [mangaAnimeMap]);

  const episodesByVolume = useMemo(() => {
    const q = episodeSearch.trim();
    const qLower = q.toLowerCase();
    const filtered = mangaEpisodes.filter((ep) => {
      if (!q) return true;
      return (
        (ep.title || "").toLowerCase().includes(qLower) ||
        String(ep.episode).includes(q)
      );
    });
    const groups = {};
    filtered.forEach((ep) => {
      const volLabel = getVolumeLabelForAppearance(ep.episode);
      const volKey = volLabel === "—" ? "—" : String(getVolumeFromEpisode(ep.episode));
      if (!groups[volKey]) groups[volKey] = [];
      groups[volKey].push(ep);
    });
    Object.keys(groups).forEach((k) => {
      groups[k].sort((a, b) => a.episode - b.episode);
    });
    return groups;
  }, [mangaEpisodes, episodeSearch]);

  const episodeVolumeKeysSorted = useMemo(() => {
    return Object.keys(episodesByVolume).sort((a, b) => {
      if (a === "—") return 1;
      if (b === "—") return -1;
      return Number(a) - Number(b);
    });
  }, [episodesByVolume]);

  const locationsByVolume = useMemo(() => {
    const q = locationSearch.trim();
    const qNorm = q.normalize("NFKC").toLowerCase();
    const filtered = LOCATIONS.filter((loc) => {
      if (!q) return true;
      const name = String(loc.name ?? "")
        .normalize("NFKC")
        .toLowerCase();
      const note = String(loc.note ?? "")
        .normalize("NFKC")
        .toLowerCase();
      return name.includes(qNorm) || note.includes(qNorm) || String(loc.chapter).includes(q);
    });
    const groups = {};
    filtered.forEach((loc) => {
      const volLabel = getVolumeLabelForAppearance(loc.chapter);
      const volKey = volLabel === "—" ? "—" : String(getVolumeFromEpisode(loc.chapter));
      if (!groups[volKey]) groups[volKey] = [];
      groups[volKey].push(loc);
    });
    Object.keys(groups).forEach((k) => {
      groups[k].sort((a, b) => a.chapter - b.chapter || String(a.name).localeCompare(String(b.name), "ja"));
    });
    return groups;
  }, [locationSearch]);

  const filteredChars = useMemo(() => {
    return CHARACTERS.filter((c) => {
      const matchSearch =
        !search ||
        c.name.includes(search) ||
        (c.reading || "").includes(search) ||
        (c.alias || "").includes(search) ||
        (c.devilFruit || "").includes(search);
      const charCategories = Array.isArray(c.category) ? c.category : (c.category ? [c.category] : []);
      const matchOrgCategory = orgCategoryFilter === "all" || charCategories.includes(orgCategoryFilter);
      const charGroups = Array.isArray(c.group) ? c.group : (c.group ? [c.group] : []);
      const matchOrgGroup = orgGroupFilter === "all" || charGroups.includes(orgGroupFilter);
      const arcs = Array.isArray(c.arcs) ? c.arcs : [];
      const matchArc = arcFilter === "all" || arcs.includes(arcFilter);
      return matchSearch && matchOrgCategory && matchOrgGroup && matchArc;
    });
  }, [search, orgCategoryFilter, orgGroupFilter, arcFilter]);

  const abilityResults = useMemo(() => {
    if (activeTab !== "abilities") return [];
    const trimmed = search.trim();
    if (!trimmed) return [];
    const q = normalizeAbilitySearchKey(trimmed);
    if (!q) return [];
    return SKILLS.filter((s) => {
      const name = normalizeAbilitySearchKey(s.name ?? "");
      const reading = normalizeAbilitySearchKey(s.reading ?? "");
      const desc = normalizeAbilitySearchKey(s.description ?? "");
      return name.includes(q) || reading.includes(q) || desc.includes(q);
    });
  }, [activeTab, search]);

  return (
    <>
      <style>{styles}</style>
      <div className="app">
        <header className="header" onClick={handleHeaderClick} style={{ cursor: "pointer" }}>
          <div className="logo-title">GRAND LINE DATABASE</div>
          <div className="logo-sub">ONE PIECE CHARACTER ENCYCLOPEDIA</div>
        </header>

        <nav className="nav-tabs">
          {[
            { key: "characters", label: "キャラクター" },
            { key: "abilities", label: "技・能力検索" },
            { key: "locations", label: "主要な地名" },
            { key: "episodes", label: "エピソード一覧" },
            { key: "updates", label: "更新履歴" },
          ].map((t) => (
            <button
              key={t.key}
              className={`nav-tab ${activeTab === t.key ? "active" : ""}`}
              onClick={() => {
                setActiveTab(t.key);
                setSearch("");
                setEpisodeSearch("");
                setLocationSearch("");
              }}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {/* ─── Characters Tab ─── */}
        {activeTab === "characters" && (
          <>
            <div className="search-area">
              <div className="character-search-row">
                <div className="search-box">
                  <input
                    className="search-input"
                    placeholder="キャラクター名、読み、悪魔の実で検索…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </div>
                <div className="arc-filter-wrap">
                  {arcFilter === "all" && <span className="arc-placeholder">編を選択</span>}
                  <span className="arc-caret">▼</span>
                  <select
                    className={`arc-select ${arcFilter === "all" ? "is-placeholder" : ""}`}
                    value={arcFilter}
                    onChange={(e) => setArcFilter(e.target.value)}
                    aria-label="登場編で絞り込み"
                  >
                    <option value="all">すべての編</option>
                    {ARC_FILTER_OPTIONS.map((arc) => (
                      <option key={arc} value={arc}>
                        {arc}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="affiliation-filter">
                  {orgCategoryFilter === "all" && <span className="affiliation-placeholder">分類を選択</span>}
                  <span className="affiliation-caret">▼</span>
                  <select
                    className={`affiliation-select ${orgCategoryFilter === "all" ? "is-placeholder" : ""}`}
                    value={orgCategoryFilter}
                    onChange={(e) => {
                      const next = e.target.value;
                      setOrgCategoryFilter(next);
                      setOrgGroupFilter("all");
                    }}
                    aria-label="分類を選択"
                  >
                    {orgCategories.map((c) => (
                      <option key={c} value={c}>
                        {c === "all" ? "すべて" : c}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="affiliation-filter">
                  {orgGroupFilter === "all" && (
                    <span className="affiliation-placeholder">
                      {orgCategoryFilter === "all" ? "組織（分類を先に選択）" : "組織を選択"}
                    </span>
                  )}
                  <span className="affiliation-caret">▼</span>
                  <select
                    className={`affiliation-select ${orgGroupFilter === "all" ? "is-placeholder" : ""}`}
                    value={orgGroupFilter}
                    onChange={(e) => setOrgGroupFilter(e.target.value)}
                    aria-label="組織を選択"
                    disabled={orgCategoryFilter === "all"}
                  >
                    {orgGroupsForSelectedCategory.map((g) => (
                      <option key={g} value={g}>
                        {g === "all" ? "すべて" : g}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* ─── Results Info Bar ─── */}
            <div className="results-info-bar">
              <div className="results-count-box">
                <span className="results-count-label">FOUND</span>
                <span key={filteredChars.length} className="results-count-num count-animate">
                  {filteredChars.length}
                </span>
                <span className="results-count-label">CHARACTERS</span>
              </div>
              <div className="results-divider"></div>
            </div>

            {filteredChars.length > 0 ? (
              <div className="char-grid">
                {filteredChars.map((c) => (
                  <CharacterCard key={c.id} char={c} onClick={setSelectedChar} />
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">🏴‍☠️</div>
                <div className="empty-state-text">該当するキャラクターが見つかりませんでした</div>
              </div>
            )}
          </>
        )}

        {/* ─── Abilities Tab ─── */}
        {activeTab === "abilities" && (
          <>
            <div className="search-area">
              <div className="search-box">
                <input
                  className="search-input"
                  placeholder="技名、読み、説明で検索（例：ゴムゴム、覇気...）"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
            </div>

            {!search ? (
              <div className="empty-state">
                <div className="empty-state-icon">⚔️</div>
                <div className="empty-state-text">技名やタイプを入力して検索してください</div>
              </div>
            ) : abilityResults.length > 0 ? (
              <div className="ability-search-results">
                {abilityResults.map((s) => {
                  return (
                    <div className="ability-result-group" key={s.id}>
                      <div className="ability-result-char">
                        {s.name}
                        <span style={{ marginLeft: 10, color: "var(--text-dim)", fontSize: 12 }}>{s.reading}</span>
                      </div>
                      <div className="ability-list">
                        <div className="ability-card" style={{ border: "none", padding: "8px 0" }}>
                          <div className="ability-info">
                            <div className="ability-desc">{s.description || "—"}</div>
                            <div className="ability-first-use">
                              使用者: {(s.users || []).slice(0, 6).map((u) => u.name).join("、") || "—"}
                            </div>
                            {(() => {
                              const items = getEpisodeLinkItems(s.episodes);
                              return (
                                <div className="episode-links-section">
                                  <div className="episode-links-heading">登場話:</div>
                                  {items.length ? (
                                    <div className="episode-links">
                                      {items.map((it) => (
                                        <div key={it.episode} className="episode-row">
                                          <span className="episode-link-label">{it.label}</span>
                                          <KindleDualLinks episode={it.episode} compact />
                                        </div>
                                      ))}
                                    </div>
                                  ) : (
                                    <span className="episode-links-empty">—</span>
                                  )}
                                </div>
                              );
                            })()}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">🔍</div>
                <div className="empty-state-text">「{search}」に一致する技は見つかりませんでした</div>
              </div>
            )}
          </>
        )}

        {/* ─── Major locations tab ─── */}
        {activeTab === "locations" && (
          <div className="episode-list-container">
            <div className="search-area">
              <div className="search-box">
                <input
                  className="search-input"
                  placeholder="地名・補足・話数で検索..."
                  value={locationSearch}
                  onChange={(e) => setLocationSearch(e.target.value)}
                />
              </div>
            </div>
            {Object.keys(locationsByVolume).length > 0 ? (
              Object.keys(locationsByVolume)
                .sort((a, b) => {
                  if (a === "—") return 1;
                  if (b === "—") return -1;
                  return Number(a) - Number(b);
                })
                .map((vol) => (
                  <div key={vol} className="location-volume-block">
                    <div className="location-volume-header">
                      <div className="location-volume-info">
                        <span className="vol-num">{vol}</span>
                        <span className="vol-label">巻</span>
                      </div>
                    </div>
                    <div className="location-volume-rows">
                      {locationsByVolume[vol].map((loc) => (
                        <div key={`${loc.chapter}-${loc.name}`} className="episode-list-row">
                          <div className="location-main-info">
                            <span className="location-name-primary">{loc.name}</span>
                            <span className="location-chapter-tag">第{loc.chapter}話</span>
                            {loc.note ? <span className="location-note-label">{loc.note}</span> : null}
                          </div>
                          <div className="ep-meta-info">
                            <KindleDualLinks episode={loc.chapter} compact />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">🗺️</div>
                <div className="empty-state-text">
                  {locationSearch.trim()
                    ? "該当する地名が見つかりませんでした"
                    : "表示できる地名がありません"}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── Episodes list tab ─── */}
        {activeTab === "episodes" && (
          <div className="episode-list-container">
            <div className="search-area">
              <div className="search-box">
                <input
                  className="search-input"
                  placeholder="話数やタイトルで検索..."
                  value={episodeSearch}
                  onChange={(e) => setEpisodeSearch(e.target.value)}
                />
              </div>
            </div>
            {Object.keys(episodesByVolume).length > 0 ? (
              episodeVolumeKeysSorted.map((vol) => (
                  <div key={vol} className="volume-card">
                    <div className="volume-sidebar">
                      <img
                        src={`/images/covers/${vol}.png`}
                        alt={`Volume ${vol}`}
                        className="volume-cover-large"
                        loading="lazy"
                        decoding="async"
                        onError={(e) => {
                          e.target.style.display = "none";
                        }}
                      />
                      <div className="volume-badge">
                        <span className="vol-num">{vol}</span>
                        <span className="vol-label">VOL.</span>
                      </div>
                    </div>
                    <div className="volume-episodes">
                      {episodesByVolume[vol].map((ep) => {
                        const epKey = String(ep.episode);
                        const rawAnime = mangaAnimeMap[epKey];
                        const animeEpNum =
                          rawAnime != null && typeof rawAnime === "object" && rawAnime.ep != null
                            ? String(rawAnime.ep).trim()
                            : rawAnime != null && typeof rawAnime !== "object"
                              ? String(rawAnime).trim()
                              : "";
                        const hasAnime = animeEpNum !== "";
                        const animeDisplay = hasAnime ? `第${animeEpNum}話` : "—";
                        return (
                          <div key={ep.episode} className="episode-list-row">
                            <div className="ep-main-info">
                              <span className="ep-number">第{ep.episode}話</span>
                              <span className="ep-title" title={ep.title}>
                                {ep.title}
                              </span>
                            </div>
                            <div className="ep-meta-info">
                              <div
                                className="anime-info-badge"
                                aria-label={hasAnime ? `アニメ${animeDisplay}` : "アニメ話数未登録"}
                              >
                                <span className="anime-label">ANIME</span>
                                <span className="anime-value">{animeDisplay}</span>
                              </div>
                              <KindleDualLinks episode={ep.episode} compact />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">📖</div>
                <div className="empty-state-text">
                  {episodeSearch.trim()
                    ? "該当する話が見つかりませんでした"
                    : "表示できるエピソードがありません"}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── Updates Tab ─── */}
        {activeTab === "updates" && (
          <div className="updates-container">
            <div className="timeline">
              {[...updatesData]
                .sort((a, b) => String(b.date).localeCompare(String(a.date)))
                .map((u, i) => (
                  <div key={`${u.date}-${i}`} className="timeline-item">
                    <span className="timeline-date">{u.date}</span>
                    <div
                      className="timeline-content"
                      dangerouslySetInnerHTML={{ __html: u.content }}
                    />
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* ─── Detail Panel ─── */}
        {selectedChar && (
          <DetailPanel
            char={selectedChar}
            onClose={() => setSelectedChar(null)}
          />
        )}

        <footer className="app-footer">
          当サイトはファンが制作した非公式のデータベースです。使用している画像や情報の著作権は、著者・出版社および各権利所有者に帰属します。権利を侵害する目的はありません。
        </footer>

        {showScrollTop && (
          <button
            type="button"
            className="scroll-to-top"
            onClick={scrollToTop}
            aria-label="トップに戻る"
          >
            ▲
          </button>
        )}
      </div>
    </>
  );
}
