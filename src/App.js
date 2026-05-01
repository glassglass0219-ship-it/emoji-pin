import { useMemo, useState } from "react";
import charactersData from "./data/characters.json";
import skillsData from "./data/skills.json";
import asinsData from "./data/asins.json";

const CHARACTERS = [...charactersData].sort((a, b) => (Number(a?.id) || 0) - (Number(b?.id) || 0));
const SKILLS = skillsData;
const SKILLS_BY_ID = new Map(SKILLS.map((s) => [s.id, s]));

/**
 * ─── Kindle連携用ユーティリティ ───
 */

// 各巻の開始話数（1〜114巻）
const VOLUME_STARTS = [
  1, 9, 18, 27, 36, 45, 54, 63, 72, 82, 91, 100, 109, 118, 127, 137, 146, 156, 167, 177,
  187, 196, 206, 217, 227, 237, 247, 257, 265, 276, 286, 296, 306, 317, 328, 337, 347, 358, 368, 378,
  389, 400, 410, 420, 431, 441, 451, 460, 471, 482, 492, 503, 513, 523, 533, 542, 552, 563, 574, 585,
  595, 604, 615, 626, 637, 647, 657, 668, 679, 689, 701, 711, 722, 732, 743, 753, 764, 776, 786, 796,
  807, 817, 828, 839, 849, 859, 870, 880, 890, 901, 911, 922, 932, 943, 954, 965, 975, 985, 995, 1005,
  1016, 1026, 1036, 1047, 1058, 1069, 1081, 1091, 1101, 1111, 1122, 1134, 1145, 1156,
];

// 話数から巻数を計算する（VOLUME_STARTS による正確マッピング）
const getVolumeFromEpisode = (episode) => {
  if (!episode) return 1;
  const ep = parseInt(episode, 10);
  if (!Number.isFinite(ep) || ep <= 0) return 1;

  // 114巻より後の話数は最新巻(114)扱い
  if (ep >= VOLUME_STARTS[VOLUME_STARTS.length - 1]) return VOLUME_STARTS.length;

  // 末尾から探索すると速く・実装も簡単（114巻固定なので十分）
  for (let i = VOLUME_STARTS.length - 1; i >= 0; i--) {
    if (ep >= VOLUME_STARTS[i]) return i + 1; // index0 => 1巻
  }

  return 1;
};

// Kindleストアの検索URLを生成（「Kindle版」に絞り込み）
const getKindleStoreSearchUrl = (vol) => {
  const query = encodeURIComponent(`ONE PIECE ${vol} Kindle版`);
  return `https://www.amazon.co.jp/s?k=${query}&i=digital-text`;
};

// ASINがある巻は Kindle Cloud Reader に直行、なければ検索へフォールバック
const getKindleUrl = (episode) => {
  const vol = getVolumeFromEpisode(episode);
  const asin = asinsData?.[String(vol)] || asinsData?.[vol];
  if (asin) return `https://read.amazon.co.jp/?asin=${asin}`;
  return getKindleStoreSearchUrl(vol);
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
  return nums.map((n) => ({ episode: n, label: `第${n}話` }));
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
  text-align: center;
  padding: 32px 0 24px;
  position: relative;
}

.header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 200px;
  height: 3px;
  background: linear-gradient(90deg, transparent, var(--red-main), transparent);
}

.logo-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 48px;
  letter-spacing: 6px;
  background: linear-gradient(135deg, var(--red-main), var(--red-deep), #8B1A2B);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1.1;
}

.logo-sub {
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 4px;
  margin-top: 6px;
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
  padding: 16px;
  text-align: center;
}

.char-name {
  font-size: 18px;
  font-weight: 900;
  color: #2d1f14;
  margin: 0;
  letter-spacing: 0.2px;
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

/* mobile overflow guard */
.table-scroll {
  max-width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.table-scroll table {
  min-width: 520px;
}

/* ─── Appearance Table ─── */
.appearance-table {
  width: 100%;
  border-collapse: collapse;
}

.appearance-table th {
  text-align: left;
  padding: 8px 12px;
  font-size: 11px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 1px;
  border-bottom: 1px solid var(--border);
}

.appearance-table td {
  padding: 10px 12px;
  font-size: 13px;
  border-bottom: 1px solid rgba(232, 223, 208, 0.7);
}

.appearance-table tr:hover td {
  background: var(--bg-card);
}

.kindle-link {
  color: var(--red-main);
  text-decoration: none;
  font-size: 12px;
  padding: 3px 10px;
  border: 1px solid var(--red-main);
  border-radius: 4px;
  transition: all 0.2s;
  white-space: nowrap;
}

.kindle-link:hover {
  background: var(--red-main);
  color: white;
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

.episode-links {
  margin-top: 6px;
  font-size: 10px;
  color: var(--text-dim);
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.episode-links a {
  color: var(--red-main);
  text-decoration: none;
}

.episode-links a:hover {
  text-decoration: underline;
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
`;

// ─── Components ───

function CharacterCard({ char, onClick }) {
  return (
    <div className="char-card" onClick={() => onClick(char)}>
      <div className="char-image-container">
        <img
          src={`/images/thumbnails/${char.id}.webp`}
          alt={char.name}
          loading="lazy"
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

function DetailPanel({ char, onClose, onNavigate }) {
  const [tab, setTab] = useState("appearances");

  const appearances = char.appearances || [];
  const coverAppearances = appearances.filter((a) => String(a?.title ?? "").includes("の扉絵"));
  const mainAppearances = appearances.filter((a) => !String(a?.title ?? "").includes("の扉絵"));

  const renderAppearanceTable = (rows) => (
    <div className="table-scroll">
      <table className="appearance-table">
        <thead>
          <tr>
            <th>話</th>
            <th>タイトル</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((a, i) => (
            <tr key={i}>
              <td style={{ color: "var(--red-main)", fontWeight: 700 }}>第{a.episode}話</td>
              <td>{a.title}</td>
              <td>
                <a href={getKindleUrl(a.episode)} target="_blank" rel="noopener noreferrer" className="kindle-link">
                  Kindleで読む →
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="detail-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="detail-panel">
        <div className="detail-header">
          <button className="detail-close" onClick={onClose}>✕</button>
          <div className="detail-name">{char.name}</div>
          <div className="detail-name-en">{char.reading}</div>
          <div className="detail-info-grid">
            <div className="info-item">
              <div className="info-label">所属</div>
              <div className="info-value">{char.affiliation || "—"}</div>
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
          <button className={`detail-tab ${tab === "relations" ? "active" : ""}`} onClick={() => setTab("relations")}>
            関係性
          </button>
        </div>

        <div className="detail-content">
          {tab === "appearances" && (
            renderAppearanceTable(mainAppearances)
          )}

          {tab === "covers" && (
            coverAppearances.length > 0 ? (
              renderAppearanceTable(coverAppearances)
            ) : (
              <div className="empty-state" style={{ padding: "24px 0" }}>
                <div className="empty-state-text">扉絵への登場はありません</div>
              </div>
            )
          )}

          {tab === "abilities" && (
            <div className="ability-list">
              {(char.abilities || []).map((ab, i) => (
                <div className="ability-card" key={i}>
                  <div className="ability-info">
                    <div className="ability-name">{ab.name}</div>
                    <div className="ability-desc">{SKILLS_BY_ID.get(ab.id)?.description || ab.reading || "—"}</div>
                    <div className="episode-links">
                      登場話:{" "}
                      {(() => {
                        const skill = SKILLS_BY_ID.get(ab.id);
                        const items = getEpisodeLinkItems(skill?.episodes);
                        return items.length ? (
                          items.map((it, idx) => (
                            <span key={it.episode}>
                              {idx > 0 ? "、" : ""}
                              <a href={getKindleUrl(it.episode)} target="_blank" rel="noopener noreferrer">
                                {it.label}
                              </a>
                            </span>
                          ))
                        ) : (
                          "—"
                        );
                      })()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === "relations" && (
            <div className="relation-list">
              {(char.coAppearances || []).map((rel, i) => {
                const relChar = CHARACTERS.find((c) => c.id === rel.id);
                return (
                  <div className="relation-card" key={i} onClick={() => relChar && onNavigate(relChar)}>
                    <span className="relation-type" style={{ background: "#6662", color: "#666" }}>
                      共演
                    </span>
                    <div className="relation-name">{relChar?.name || rel.name || String(rel.id)}</div>
                    <div className="relation-label">共演回数: {rel.count}</div>
                  </div>
                );
              })}
            </div>
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
  const [crewFilter, setCrewFilter] = useState("all");
  const [selectedChar, setSelectedChar] = useState(null);

  const crews = useMemo(() => {
    const set = new Set(CHARACTERS.map((c) => c.affiliation).filter(Boolean));
    return ["all", ...set];
  }, []);

  const filteredChars = useMemo(() => {
    return CHARACTERS.filter((c) => {
      const matchSearch =
        !search ||
        c.name.includes(search) ||
        (c.reading || "").includes(search) ||
        (c.affiliation || "").includes(search) ||
        (c.devilFruit || "").includes(search);
      const matchCrew = crewFilter === "all" || (c.affiliation || "") === crewFilter;
      return matchSearch && matchCrew;
    });
  }, [search, crewFilter]);

  const abilityResults = useMemo(() => {
    if (activeTab !== "abilities" || !search) return [];
    const q = search.toLowerCase();
    return SKILLS.filter((s) => {
      return (
        s.name.toLowerCase().includes(q) ||
        (s.reading || "").toLowerCase().includes(q) ||
        (s.description || "").toLowerCase().includes(q)
      );
    });
  }, [activeTab, search]);

  return (
    <>
      <style>{styles}</style>
      <div className="app">
        <header className="header">
          <div className="logo-title">GRAND LINE DATABASE</div>
          <div className="logo-sub">ONE PIECE CHARACTER ENCYCLOPEDIA</div>
        </header>

        <nav className="nav-tabs">
          {[
            { key: "characters", label: "キャラクター" },
            { key: "abilities", label: "技・能力検索" },
          ].map((t) => (
            <button
              key={t.key}
              className={`nav-tab ${activeTab === t.key ? "active" : ""}`}
              onClick={() => {
                setActiveTab(t.key);
                setSearch("");
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
              <div className="search-box">
                <input
                  className="search-input"
                  placeholder="キャラクター名、よみ、所属、悪魔の実で検索..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <div className="affiliation-filter">
                {crewFilter === "all" && <span className="affiliation-placeholder">所属を選択</span>}
                <span className="affiliation-caret">▼</span>
                <select
                  className={`affiliation-select ${crewFilter === "all" ? "is-placeholder" : ""}`}
                  value={crewFilter}
                  onChange={(e) => setCrewFilter(e.target.value)}
                  aria-label="所属を選択"
                >
                  {crews.map((c) => (
                    <option key={c} value={c}>
                      {c === "all" ? "すべて" : c}
                    </option>
                  ))}
                </select>
              </div>
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
                            <div className="episode-links">
                              登場話:{" "}
                              {(() => {
                                const items = getEpisodeLinkItems(s.episodes);
                                return items.length ? (
                                  items.map((it, idx) => (
                                    <span key={it.episode}>
                                      {idx > 0 ? "、" : ""}
                                      <a href={getKindleUrl(it.episode)} target="_blank" rel="noopener noreferrer">
                                        {it.label}
                                      </a>
                                    </span>
                                  ))
                                ) : (
                                  "—"
                                );
                              })()}
                            </div>
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

        {/* ─── Detail Panel ─── */}
        {selectedChar && (
          <DetailPanel
            char={selectedChar}
            onClose={() => setSelectedChar(null)}
            onNavigate={(c) => setSelectedChar(c)}
          />
        )}

        <footer className="app-footer">
          当サイトはファンが制作した非公式のデータベースです。使用している画像や情報の著作権は、著者・出版社および各権利所有者に帰属します。権利を侵害する目的はありません。
        </footer>
      </div>
    </>
  );
}
