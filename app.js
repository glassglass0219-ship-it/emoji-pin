require('dotenv').config();
const { App, ExpressReceiver } = require('@slack/bolt');
const cron = require('node-cron');

const APP_NAME = 'Emoji Pin';
const SLACK_APP_ID = process.env.SLACK_APP_ID;
const REQUIRED_BOT_SCOPES = [
  'channels:read',
  'channels:history',
  'chat:write',
  'reactions:read',
  'users:read',
];
const AUTO_JOIN_PUBLIC_CHANNELS = process.env.AUTO_JOIN_PUBLIC_CHANNELS !== 'false';
const HOME_ITEM_LIMIT = 14;

// --- デバッグ用：起動時に環境変数が読み込めているか確認 ---
console.log('--- Environment Check ---');
console.log('CLIENT_ID:', process.env.SLACK_CLIENT_ID ? 'OK' : 'MISSING');
console.log('CLIENT_SECRET:', process.env.SLACK_CLIENT_SECRET ? 'OK' : 'MISSING');
console.log('SIGNING_SECRET:', process.env.SLACK_SIGNING_SECRET ? 'OK' : 'MISSING');
console.log('DATABASE_URL:', process.env.DATABASE_URL ? 'OK' : 'MISSING');
console.log('--- --- --- --- --- ---');

const missingEnv = [
  ['SLACK_SIGNING_SECRET', process.env.SLACK_SIGNING_SECRET],
  ['SLACK_CLIENT_ID', process.env.SLACK_CLIENT_ID],
  ['SLACK_CLIENT_SECRET', process.env.SLACK_CLIENT_SECRET],
  ['SLACK_STATE_SECRET', process.env.SLACK_STATE_SECRET],
  ['DATABASE_URL', process.env.DATABASE_URL],
].filter(([, value]) => !value);

if (missingEnv.length > 0) {
  console.error('\n[Emoji Pin] .env に未設定の項目があります:');
  missingEnv.forEach(([name]) => console.error(`  - ${name}`));
  console.error('\nSlack API → Basic Information から CLIENT_ID / CLIENT_SECRET をコピーし、');
  console.error('Render → PostgreSQL → External Database URL を DATABASE_URL に設定してください。');
  console.error('.env を保存したあと、node app.js を再起動してください。\n');
  process.exit(1);
}

const db = require('./db');
const {
  getSettings,
  saveTask,
  completeTask,
  getPendingTasks,
  getHomeTasks,
  reopenTask,
  deleteTask,
  deleteCompletedTasks,
  getFolders,
  replaceFolders,
  updateTaskFolder,
  getReminderTimes,
  replaceReminderTimes,
  getUserIdsForReminderTime,
  countPendingCheckingTasks,
  getAllUserIdsWithPendingOldTasks,
  getInstallationBotToken,
} = db;

// 1. Receiverの作成
const receiver = new ExpressReceiver({
  signingSecret: process.env.SLACK_SIGNING_SECRET,
  clientId: process.env.SLACK_CLIENT_ID,
  clientSecret: process.env.SLACK_CLIENT_SECRET,
  stateSecret: process.env.SLACK_STATE_SECRET || 'emoji-pin-default-state-secret',
  scopes: ['channels:read', 'channels:history', 'chat:write', 'reactions:read', 'users:read'],
  installationStore: {
    storeInstallation: async (installation) => {
      const teamId = installation.team?.id || installation.enterprise?.id;
      console.log(`💾 Saving installation for team: ${teamId}`);

      const dataToStore = typeof installation === 'string' ? installation : JSON.stringify(installation);

      await db.knex('installations').insert({
        team_id: teamId,
        installation: dataToStore,
      }).onConflict('team_id').merge();
    },
    fetchInstallation: async (installQuery) => {
      const teamId = installQuery.teamId || installQuery.enterpriseId;
      const row = await db.knex('installations').where({ team_id: teamId }).first();

      if (row) {
        console.log(`🔍 Found installation in DB for team: ${teamId}`);
        const data = (typeof row.installation === 'string')
          ? JSON.parse(row.installation)
          : row.installation;

        return data;
      }
      console.error(`❌ No installation found for team: ${teamId}`);
      throw new Error('No installation found');
    },
  },
  installerOptions: {
    directInstall: true,
  },
});

// 2. Appの作成（receiverを必ず渡す）
const app = new App({
  receiver: receiver, // これを渡すとOAuthモードとして起動しようとします
});

// 以降、app.event や app.action のロジックを続ける...

function getAppHomeButton() {
  return {
    type: 'button',
    text: { type: 'plain_text', text: `${APP_NAME} を開く`, emoji: true },
    action_id: 'open_app_home_from_reminder',
    ...(SLACK_APP_ID ? { url: `https://slack.com/app_redirect?app=${SLACK_APP_ID}` } : {}),
  };
}

function buildCheckingReminderBlocks(count) {
  return [
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: '🚨🚨🚨 *Emoji Pin リマインド* 🚨🚨🚨',
      },
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `確認中のタスクが *${count}件* あります！ 忘れないうちにチェックしましょう 🚀`,
      },
    },
    {
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: '⏰ *今すぐチェック* ｜ 👀 確認中タブを開いて整理しましょう ✨',
        },
      ],
    },
    { type: 'divider' },
    {
      type: 'actions',
      elements: [getAppHomeButton()],
    },
  ];
}

function getTeamId(payload = {}) {
  return payload.team?.id || payload.team_id || payload.event?.team || payload.authorizations?.[0]?.team_id || 'default';
}

// ─── ユーティリティ ──────────────────────────────────────────────────────────

function buildHomeView(homeTasks, selectedTab = 'checking', folders = ['未分類'], selectedFolder = 'すべて') {
  const checkingItems = homeTasks.filter((t) => t.category === 'TASK' && t.status === 'pending');
  const infoItems = homeTasks.filter((t) => t.category === 'INFO' && t.status === 'pending');
  const doneItems = homeTasks
    .filter((t) => t.status === 'completed')
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  const isCheckingTab = selectedTab === 'checking';
  const isInfoTab = selectedTab === 'info';
  const isDoneTab = selectedTab === 'done';
  const folderOptions = ['すべて', ...folders.filter((folder) => folder !== 'すべて')];
  const safeSelectedFolder = folderOptions.includes(selectedFolder) ? selectedFolder : 'すべて';
  const filteredInfoItems =
    safeSelectedFolder === 'すべて'
      ? infoItems
      : infoItems.filter((t) => (t.folder || '未分類') === safeSelectedFolder);
  const visibleItems = isDoneTab ? doneItems : isInfoTab ? filteredInfoItems : checkingItems;
  const limitedItems = visibleItems.slice(0, HOME_ITEM_LIMIT);
  const blocks = [
    {
      type: 'actions',
      elements: [
        {
          type: 'button',
          text: { type: 'plain_text', text: `👀 確認中 (${checkingItems.length})`, emoji: true },
          action_id: 'switch_tab_checking',
          value: 'checking',
          ...(isCheckingTab ? { style: 'primary' } : {}),
        },
        {
          type: 'button',
          text: { type: 'plain_text', text: `📖 資料 (${infoItems.length})`, emoji: true },
          action_id: 'switch_tab_info',
          value: 'info',
          ...(isInfoTab ? { style: 'primary' } : {}),
        },
        {
          type: 'button',
          text: { type: 'plain_text', text: '✅ DONE', emoji: true },
          action_id: 'switch_tab_done',
          value: 'done',
          ...(isDoneTab ? { style: 'primary' } : {}),
        },
        {
          type: 'button',
          text: { type: 'plain_text', text: '⚙️ 設定', emoji: true },
          value: JSON.stringify({ tab: selectedTab, folder: safeSelectedFolder }),
          action_id: 'open_settings_modal',
        },
      ],
    },
    { type: 'divider' },
  ];

  if (isInfoTab) {
    const folderButtons = [
      {
        type: 'button',
        text: { type: 'plain_text', text: '➕', emoji: true },
        action_id: 'manage_folders',
        value: 'manage',
      },
      ...folderOptions.map((folder, index) => ({
        type: 'button',
        text: { type: 'plain_text', text: folder, emoji: true },
        action_id: `switch_folder_${index}`,
        value: folder,
        ...(folder === safeSelectedFolder ? { style: 'primary' } : {}),
      })),
    ];

    for (let i = 0; i < folderButtons.length; i += 5) {
      blocks.push({
        type: 'actions',
        elements: folderButtons.slice(i, i + 5),
      });
    }

    blocks.push({ type: 'divider' });
  }

  if (isDoneTab && doneItems.length > 0) {
    blocks.push({
      type: 'actions',
      elements: [
        {
          type: 'button',
          text: { type: 'plain_text', text: '💥 DONEを一括削除', emoji: true },
          style: 'danger',
          action_id: 'clear_all_done',
          value: 'done',
          confirm: {
            title: { type: 'plain_text', text: '本当によろしいですか？' },
            text: { type: 'plain_text', text: 'DONEに入っているすべてのアイテムを完全に削除します。' },
            confirm: { type: 'plain_text', text: '削除する' },
            deny: { type: 'plain_text', text: 'キャンセル' },
          },
        },
      ],
    });
    blocks.push({ type: 'divider' });
  }

  const defaultUserIcon = 'https://api.slack.com/img/blocks/breadcrumbs/avatar.png';

  const buildItemCardBlocks = (t) => {
    const link = `https://slack.com/archives/${t.channelId}/p${t.messageTs.replace('.', '')}`;
    const createdAt = new Date(t.createdAt).toLocaleString('ja-JP', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).replace(/\//g, '.');
    const displayUser = t.itemUser || t.userId;
    const iconUrl = t.user_icon || t.userIcon || defaultUserIcon;
    const cardBlocks = [{ type: 'divider' }];

    let bodyText = `*<@${displayUser}>*\n`;
    if (isInfoTab) {
      bodyText += `📁 ${t.folder || '未分類'}\n`;
    }
    bodyText += t.text || '(テキストなし)';

    const cardSection = {
      type: 'section',
      text: { type: 'mrkdwn', text: bodyText },
    };

    if (isDoneTab) {
      cardSection.accessory = {
        type: 'button',
        text: { type: 'plain_text', text: '🔄 確認中に戻す', emoji: true },
        style: 'primary',
        action_id: 'reopen_to_checking',
        value: JSON.stringify({ taskId: t.id }),
      };
    }

    cardBlocks.push(cardSection);

    cardBlocks.push({
      type: 'context',
      elements: [
        {
          type: 'image',
          image_url: iconUrl,
          alt_text: 'user',
        },
        {
          type: 'mrkdwn',
          text: `🕒 ${createdAt}  |  <${link}|メッセージを表示>`,
        },
      ],
    });

    if (isCheckingTab || isInfoTab) {
      const actionElements = [];
      if (isInfoTab) {
        actionElements.push({
          type: 'button',
          text: { type: 'plain_text', text: '📁 移動', emoji: true },
          action_id: 'open_move_folder_modal',
          value: JSON.stringify({ taskId: t.id, folder: t.folder || '未分類' }),
        });
      }
      actionElements.push({
        type: 'button',
        text: { type: 'plain_text', text: '✅ Done', emoji: true },
        style: 'primary',
        action_id: 'complete_task',
        value: JSON.stringify({ taskId: t.id, tab: selectedTab, folder: safeSelectedFolder }),
      });
      cardBlocks.push({
        type: 'actions',
        elements: actionElements,
      });
    }

    if (isDoneTab) {
      cardBlocks.push({
        type: 'actions',
        elements: [
          {
            type: 'button',
            text: { type: 'plain_text', text: '🔄 資料に戻す', emoji: true },
            action_id: 'reopen_to_info',
            value: JSON.stringify({ taskId: t.id }),
          },
          {
            type: 'button',
            text: { type: 'plain_text', text: '🗑️ 削除', emoji: true },
            style: 'danger',
            action_id: 'delete_item',
            value: JSON.stringify({ taskId: t.id }),
          },
        ],
      });
    }

    return cardBlocks;
  };

  const renderItems = (items, totalCount) => {
    if (items.length === 0) return [];
    const section = [];

    items.forEach((t) => {
      section.push(...buildItemCardBlocks(t));
    });

    if (items.length > 0) {
      section.push({ type: 'divider' });
    }

    if (totalCount > items.length) {
      section.push({
        type: 'context',
        elements: [
          {
            type: 'mrkdwn',
            text: `表示上限のため先頭 ${items.length} 件のみ表示しています。残り ${totalCount - items.length} 件あります。`,
          },
        ],
      });
    }
    return section;
  };

  blocks.push(...renderItems(limitedItems, visibleItems.length));

  if (visibleItems.length === 0) {
    const emptyLabel = isDoneTab ? 'DONEアイテム' : isInfoTab ? '資料' : '確認中アイテム';
    blocks.push({
      type: 'section',
      text: { type: 'mrkdwn', text: `${emptyLabel}はありません 🎉` },
    });
  }

  const safeBlocks = blocks.filter(Boolean);
  if (safeBlocks.length === 0) {
    safeBlocks.push({
      type: 'section',
      text: { type: 'mrkdwn', text: `${APP_NAME} を読み込みました。` },
    });
  }

  return {
    type: 'home',
    callback_id: 'emoji_pin_home',
    external_id: 'emoji_pin_home',
    private_metadata: APP_NAME,
    blocks: safeBlocks,
  };
}

async function publishHomeView(client, userId, tasks, selectedTab = 'checking', selectedFolder = 'すべて', teamId = 'default') {
  if (!userId) {
    console.error(`[${APP_NAME}] views.publish をスキップしました: user_id がありません。`);
    return;
  }

  const safeTab = ['checking', 'info', 'done'].includes(selectedTab) ? selectedTab : 'checking';
  const folders = await getFolders(userId, teamId);
  const view = buildHomeView(Array.isArray(tasks) ? tasks : [], safeTab, folders, selectedFolder);
  console.log(JSON.stringify(view, null, 2));

  await client.views.publish({
    user_id: userId,
    view,
  });
}

function toSortRadioOption(sort) {
  if (sort === 'asc') {
    return { text: { type: 'plain_text', text: '古い順（昇順）' }, value: 'asc' };
  }
  return { text: { type: 'plain_text', text: '新しい順（降順）' }, value: 'desc' };
}

function getInitialSortOption(sort) {
  return toSortRadioOption(sort === 'asc' ? 'asc' : 'desc');
}

function normalizeSort(sort) {
  return sort === 'asc' ? 'asc' : 'desc';
}

async function fetchHomeTasks(userId, teamId) {
  const settings = await getSettings(userId, teamId);
  return getHomeTasks(
    userId,
    teamId,
    normalizeSort(settings.checkingSort),
    normalizeSort(settings.docsSort)
  );
}

function withBotToken(args, botToken) {
  return botToken ? { ...args, token: botToken } : args;
}

async function getDmChannel(client, userId, botToken) {
  const res = await client.conversations.open(withBotToken({ users: userId }, botToken));
  return res.channel.id;
}

async function getUserIcon(client, userId) {
  if (!userId) return null;
  try {
    const res = await client.users.info({ user: userId });
    return res.user?.profile?.image_48 || res.user?.profile?.image_72 || null;
  } catch (error) {
    console.warn(`[${APP_NAME}] ユーザーアイコンを取得できませんでした (${userId}): ${getSlackErrorCode(error)}`);
    return null;
  }
}

function getSlackErrorCode(error) {
  return error?.data?.error || error?.code || error?.message || 'unknown_error';
}

function logPermissionHint(action, error, scopes) {
  const code = getSlackErrorCode(error);
  const needed = error?.data?.needed;
  const provided = error?.data?.provided;
  console.error(`[${APP_NAME}] ${action} に失敗しました: ${code}`);
  if (needed || code === 'missing_scope') {
    console.error(
      `[${APP_NAME}] SlackアプリのOAuthスコープを確認してください。必要な権限: ${scopes.join(', ')}`
    );
    if (needed) console.error(`[${APP_NAME}] Slack API reported needed scope: ${needed}`);
    if (provided) console.error(`[${APP_NAME}] Current provided scopes: ${provided}`);
  }
}

async function ensureJoinedChannel(client, channelId, botToken) {
  try {
    await client.conversations.join(withBotToken({ channel: channelId }, botToken));
    return true;
  } catch (error) {
    const code = getSlackErrorCode(error);
    if (code === 'already_in_channel') return true;

    // private channel, shared channel, or missing channel:join cannot be auto-joined.
    if (['missing_scope', 'not_allowed_token_type', 'method_not_supported_for_channel_type'].includes(code)) {
      logPermissionHint('チャンネル自動参加', error, ['channels:join', 'channels:read']);
      return false;
    }

    console.warn(`[${APP_NAME}] チャンネル ${channelId} への自動参加をスキップしました: ${code}`);
    return false;
  }
}

async function getMessageText(client, channelId, messageTs) {
  try {
    const result = await client.conversations.history({
      channel: channelId,
      latest: messageTs,
      limit: 1,
      inclusive: true,
    });
    return result.messages?.[0]?.text || '';
  } catch (error) {
    const code = getSlackErrorCode(error);
    if (code === 'not_in_channel') {
      const joined = await ensureJoinedChannel(client, channelId);
      if (joined) {
        const result = await client.conversations.history({
          channel: channelId,
          latest: messageTs,
          limit: 1,
          inclusive: true,
        });
        return result.messages?.[0]?.text || '';
      }
    }

    if (code === 'missing_scope') {
      logPermissionHint('メッセージ本文取得', error, ['channels:history', 'groups:history']);
    } else {
      console.warn(`[${APP_NAME}] メッセージ本文を取得できませんでした: ${code}`);
    }
    return '';
  }
}

async function verifyInstallReadiness(client, botToken) {
  console.log(`[${APP_NAME}] 推奨Bot OAuthスコープ: ${REQUIRED_BOT_SCOPES.join(', ')}`);

  try {
    await client.conversations.list(withBotToken({
      types: 'public_channel',
      exclude_archived: true,
      limit: 1,
    }, botToken));
  } catch (error) {
    logPermissionHint('パブリックチャンネル一覧取得', error, ['channels:read']);
  }
}

async function joinAllPublicChannels(client, botToken) {
  if (!AUTO_JOIN_PUBLIC_CHANNELS) {
    console.log(`[${APP_NAME}] AUTO_JOIN_PUBLIC_CHANNELS=false のため、起動時の自動参加をスキップします。`);
    return;
  }

  let cursor;
  let joinedCount = 0;
  let skippedCount = 0;

  try {
    do {
      const response = await client.conversations.list(withBotToken({
        types: 'public_channel',
        exclude_archived: true,
        limit: 200,
        cursor,
      }, botToken));

      for (const channel of response.channels || []) {
        if (channel.is_member) {
          skippedCount += 1;
          continue;
        }

        const joined = await ensureJoinedChannel(client, channel.id, botToken);
        if (joined) joinedCount += 1;
        else skippedCount += 1;
      }

      cursor = response.response_metadata?.next_cursor;
    } while (cursor);

    console.log(`[${APP_NAME}] パブリックチャンネル自動参加完了: joined=${joinedCount}, skipped=${skippedCount}`);
  } catch (error) {
    logPermissionHint('パブリックチャンネル自動参加', error, ['channels:read', 'channels:join']);
  }
}

const DEFAULT_CHECKING_EMOJI = 'eyes';
const DEFAULT_INFO_EMOJI = 'bookmark';

const businessEmojiOptions = [
  { icon: '✅', name: 'white_check_mark' },
  { icon: '🚩', name: 'triangular_flag_on_post' },
  { icon: '📝', name: 'memo' },
  { icon: '👀', name: 'eyes' },
  { icon: '🔖', name: 'bookmark' },
  { icon: '📂', name: 'open_file_folder' },
  { icon: '📎', name: 'paperclip' },
  { icon: '🆗', name: 'ok' },
  { icon: '🏁', name: 'checkered_flag' },
  { icon: '🎯', name: 'dart' },
  { icon: '💡', name: 'bulb' },
];

function toSlackSelectOption(option) {
  return {
    text: { type: 'plain_text', text: `${option.icon} ${option.name}`, emoji: true },
    value: option.name,
  };
}

function getInitialEmojiOption(savedValue, fallbackValue) {
  const selected =
    businessEmojiOptions.find((option) => option.name === savedValue) ||
    businessEmojiOptions.find((option) => option.name === fallbackValue);
  return toSlackSelectOption(selected);
}

function formatReminderTime({ hour, minute }) {
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}

function parseTimepickerValue(timeString) {
  if (!timeString) return null;
  const [hourStr, minuteStr] = timeString.split(':');
  const hour = Number(hourStr);
  const minute = Number(minuteStr);
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) return null;
  if (!Number.isInteger(minute) || minute < 0 || minute > 59) return null;
  return { hour, minute };
}

function normalizeReminderTimesList(times) {
  const map = new Map();
  for (const time of times || []) {
    const hour = Number(time.hour);
    const minute = Number(time.minute ?? 0);
    if (Number.isInteger(hour) && hour >= 0 && hour <= 23 && Number.isInteger(minute) && minute >= 0 && minute <= 59) {
      map.set(`${hour}:${minute}`, { hour, minute });
    }
  }
  return [...map.values()].sort((a, b) => a.hour - b.hour || a.minute - b.minute);
}

function parseSettingsModalMetadata(privateMetadata) {
  try {
    const parsed = JSON.parse(privateMetadata || '{}');
    return {
      tab: parsed.tab || 'checking',
      folder: parsed.folder || 'すべて',
      reminderTimes: normalizeReminderTimesList(parsed.reminderTimes || []),
    };
  } catch {
    return { tab: 'checking', folder: 'すべて', reminderTimes: [] };
  }
}

function buildSettingsModalMetadata(homeContext, reminderTimes) {
  return JSON.stringify({
    tab: homeContext.tab || 'checking',
    folder: homeContext.folder || 'すべて',
    reminderTimes: normalizeReminderTimesList(reminderTimes),
  });
}

function getSettingsFromViewOrDefaults(view, dbSettings) {
  const vals = view?.state?.values || {};
  return {
    taskEmoji: vals.checking_emoji_block?.checking_emoji_input?.selected_option?.value || dbSettings.taskEmoji,
    infoEmoji: vals.info_emoji_block?.info_emoji_input?.selected_option?.value || dbSettings.infoEmoji,
    checkingSort: vals.checking_sort_block?.checking_sort_input?.selected_option?.value || dbSettings.checkingSort,
    docsSort: vals.docs_sort_block?.docs_sort_input?.selected_option?.value || dbSettings.docsSort,
  };
}

function buildSettingsModalBlocks(settings, reminderTimes) {
  const emojiOptions = businessEmojiOptions.map(toSlackSelectOption);
  const blocks = [
    {
      type: 'input',
      block_id: 'checking_emoji_block',
      label: { type: 'plain_text', text: '確認中用スタンプ' },
      element: {
        type: 'static_select',
        action_id: 'checking_emoji_input',
        placeholder: { type: 'plain_text', text: '絵文字を選択' },
        options: emojiOptions,
        initial_option: getInitialEmojiOption(settings.taskEmoji, DEFAULT_CHECKING_EMOJI),
      },
    },
    {
      type: 'input',
      block_id: 'info_emoji_block',
      label: { type: 'plain_text', text: '資料用スタンプ' },
      element: {
        type: 'static_select',
        action_id: 'info_emoji_input',
        placeholder: { type: 'plain_text', text: '絵文字を選択' },
        options: emojiOptions,
        initial_option: getInitialEmojiOption(settings.infoEmoji, DEFAULT_INFO_EMOJI),
      },
    },
    {
      type: 'input',
      block_id: 'checking_sort_block',
      label: { type: 'plain_text', text: '確認中の並び替え' },
      element: {
        type: 'radio_buttons',
        action_id: 'checking_sort_input',
        options: [toSortRadioOption('desc'), toSortRadioOption('asc')],
        initial_option: getInitialSortOption(settings.checkingSort),
      },
    },
    {
      type: 'input',
      block_id: 'docs_sort_block',
      label: { type: 'plain_text', text: '資料の並び替え' },
      element: {
        type: 'radio_buttons',
        action_id: 'docs_sort_input',
        options: [toSortRadioOption('desc'), toSortRadioOption('asc')],
        initial_option: getInitialSortOption(settings.docsSort),
      },
    },
    { type: 'divider' },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: '*⏰ リマインド時刻*\n登録した時刻に、確認中タスクのリマインドを送信します。',
      },
    },
  ];

  if (reminderTimes.length === 0) {
    blocks.push({
      type: 'context',
      elements: [{ type: 'mrkdwn', text: 'リマインド時刻はまだ設定されていません。' }],
    });
  } else {
    reminderTimes.forEach((time, index) => {
      blocks.push({
        type: 'section',
        text: { type: 'mrkdwn', text: `• *${formatReminderTime(time)}*` },
        accessory: {
          type: 'button',
          text: { type: 'plain_text', text: '🗑️ 削除', emoji: true },
          action_id: 'remove_reminder_time',
          value: String(index),
        },
      });
    });
  }

  blocks.push(
    {
      type: 'input',
      block_id: 'new_reminder_time_block',
      optional: true,
      label: { type: 'plain_text', text: '追加する時刻' },
      element: {
        type: 'timepicker',
        action_id: 'new_reminder_time_input',
        placeholder: { type: 'plain_text', text: '時:分 を選択' },
      },
    },
    {
      type: 'actions',
      block_id: 'reminder_time_actions',
      elements: [
        {
          type: 'button',
          text: { type: 'plain_text', text: '➕ 追加', emoji: true },
          action_id: 'add_reminder_time',
          style: 'primary',
        },
      ],
    }
  );

  return blocks;
}

function buildSettingsModalView(settings, reminderTimes, homeContext) {
  return {
    type: 'modal',
    callback_id: 'save_settings',
    private_metadata: buildSettingsModalMetadata(homeContext, reminderTimes),
    title: { type: 'plain_text', text: '環境設定' },
    submit: { type: 'plain_text', text: '保存' },
    close: { type: 'plain_text', text: 'キャンセル' },
    blocks: buildSettingsModalBlocks(settings, reminderTimes),
  };
}

async function updateSettingsModal(client, body, reminderTimes) {
  const teamId = getTeamId(body);
  const dbSettings = await getSettings(body.user.id, teamId);
  const metadata = parseSettingsModalMetadata(body.view.private_metadata);
  const settings = getSettingsFromViewOrDefaults(body.view, dbSettings);

  await client.views.update({
    view_id: body.view.id,
    hash: body.view.hash,
    view: buildSettingsModalView(settings, reminderTimes, {
      tab: metadata.tab,
      folder: metadata.folder,
    }),
  });
}

function toFolderSelectOption(folder) {
  return {
    text: { type: 'plain_text', text: folder, emoji: true },
    value: folder,
  };
}

function getInitialFolderOption(folders, selectedFolder) {
  const folder = folders.includes(selectedFolder) ? selectedFolder : '未分類';
  return toFolderSelectOption(folder);
}

function parseCompleteTaskActionValue(value) {
  if (!value) return null;

  try {
    const payload = JSON.parse(value);
    const taskId = Number(payload.taskId);
    if (!Number.isInteger(taskId) || taskId <= 0) return null;
    return {
      taskId,
      selectedTab: ['checking', 'info', 'done'].includes(payload.tab) ? payload.tab : 'checking',
      selectedFolder: payload.folder || 'すべて',
    };
  } catch (_) {
    const taskId = Number(value);
    if (!Number.isInteger(taskId) || taskId <= 0) return null;
    return { taskId, selectedTab: 'checking', selectedFolder: 'すべて' };
  }
}

// ─── App Home ────────────────────────────────────────────────────────────────

app.event('app_home_opened', async ({ event, body, client }) => {
  const teamId = getTeamId(body);
  const tasks = await fetchHomeTasks(event.user, teamId);
  await publishHomeView(client, event.user, tasks, 'checking', 'すべて', teamId);
});

app.action(/^switch_tab_/, async ({ body, action, client, ack }) => {
  await ack();
  const selectedTab =
    action.value === 'done' || action.action_id === 'switch_tab_done'
      ? 'done'
      : action.value === 'info' || action.action_id === 'switch_tab_info'
        ? 'info'
        : 'checking';
  const teamId = getTeamId(body);
  const tasks = await fetchHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, selectedTab, 'すべて', teamId);
});

app.action(/^switch_folder_/, async ({ body, action, client, ack }) => {
  await ack();
  const selectedFolder = action.value || 'すべて';
  const teamId = getTeamId(body);
  const tasks = await fetchHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, 'info', selectedFolder, teamId);
});

app.action('open_app_home_from_reminder', async ({ body, client, ack }) => {
  await ack();
  const teamId = getTeamId(body);
  const tasks = await fetchHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, 'checking', 'すべて', teamId);
});

// ─── 完了ボタン ───────────────────────────────────────────────────────────────

app.action('complete_task', async ({ body, action, client, ack }) => {
  await ack();
  const { knex } = require('./db');
  const teamId = getTeamId(body);
  const parsedAction = parseCompleteTaskActionValue(action.value || body.actions?.[0]?.value);
  if (!parsedAction) {
    console.warn(`[${APP_NAME}] 完了ボタンのvalueからtaskIdを取得できませんでした: ${action.value}`);
    const tasks = await fetchHomeTasks(body.user.id, teamId);
    await publishHomeView(client, body.user.id, tasks, 'checking', 'すべて', teamId);
    return;
  }

  await knex('tasks').where({ id: parsedAction.taskId, teamId, userId: body.user.id }).update({ status: 'completed' });

  const tasks = await fetchHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, parsedAction.selectedTab, parsedAction.selectedFolder, teamId);
});

app.action(/^(reopen_to_checking|reopen_to_info)$/, async ({ body, action, client, ack }) => {
  await ack();
  const teamId = getTeamId(body);
  const parsedAction = parseCompleteTaskActionValue(action.value || body.actions?.[0]?.value);
  if (!parsedAction) {
    console.warn(`[${APP_NAME}] 再オープンボタンのvalueからtaskIdを取得できませんでした: ${action.value}`);
    const tasks = await fetchHomeTasks(body.user.id, teamId);
    await publishHomeView(client, body.user.id, tasks, 'done', 'すべて', teamId);
    return;
  }

  const nextCategory = action.action_id === 'reopen_to_info' ? 'INFO' : 'TASK';
  await reopenTask(body.user.id, parsedAction.taskId, nextCategory, teamId);

  const tasks = await fetchHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, 'done', 'すべて', teamId);
});

app.action('delete_item', async ({ body, action, client, ack }) => {
  await ack();
  const teamId = getTeamId(body);
  const parsedAction = parseCompleteTaskActionValue(action.value || body.actions?.[0]?.value);
  if (!parsedAction) {
    console.warn(`[${APP_NAME}] 削除ボタンのvalueからtaskIdを取得できませんでした: ${action.value}`);
    return;
  }

  await deleteTask(body.user.id, parsedAction.taskId, teamId);
  const tasks = await fetchHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, 'done', 'すべて', teamId);
});

app.action('clear_all_done', async ({ body, client, ack }) => {
  await ack();
  const teamId = getTeamId(body);
  await deleteCompletedTasks(body.user.id, teamId);
  const tasks = await fetchHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, 'done', 'すべて', teamId);
});

// ─── 環境設定モーダル ────────────────────────────────────────────────────────

app.action('open_settings_modal', async ({ body, client, ack }) => {
  await ack();
  const teamId = getTeamId(body);
  const settings = await getSettings(body.user.id, teamId);
  const reminderTimes = await getReminderTimes(body.user.id, teamId);
  let homeContext = { tab: 'checking', folder: 'すべて' };
  try {
    const parsed = JSON.parse(body.actions?.[0]?.value || '{}');
    if (parsed.tab) homeContext = parsed;
  } catch {
    // legacy button value
  }
  await client.views.open({
    trigger_id: body.trigger_id,
    view: buildSettingsModalView(settings, reminderTimes, homeContext),
  });
});

app.action('add_reminder_time', async ({ body, client, ack }) => {
  await ack();
  const metadata = parseSettingsModalMetadata(body.view.private_metadata);
  const selectedTime = body.view.state.values.new_reminder_time_block?.new_reminder_time_input?.selected_time;
  const parsed = parseTimepickerValue(selectedTime);
  if (!parsed) return;

  const reminderTimes = normalizeReminderTimesList([...metadata.reminderTimes, parsed]);
  await updateSettingsModal(client, body, reminderTimes);
});

app.action('remove_reminder_time', async ({ body, client, ack, action }) => {
  await ack();
  const metadata = parseSettingsModalMetadata(body.view.private_metadata);
  const index = Number(action.value);
  const reminderTimes = metadata.reminderTimes.filter((_, i) => i !== index);
  await updateSettingsModal(client, body, reminderTimes);
});

app.view('save_settings', async ({ view, body, client, ack }) => {
  await ack();
  const vals = view.state.values;
  const userId = body.user.id;
  const teamId = getTeamId(body);
  const checkingEmoji = vals.checking_emoji_block.checking_emoji_input.selected_option.value;
  const infoEmoji = vals.info_emoji_block.info_emoji_input.selected_option.value;
  const checkingSort = normalizeSort(vals.checking_sort_block.checking_sort_input.selected_option?.value);
  const docsSort = normalizeSort(vals.docs_sort_block.docs_sort_input.selected_option?.value);
  const modalMetadata = parseSettingsModalMetadata(view.private_metadata);
  const homeContext = { tab: modalMetadata.tab, folder: modalMetadata.folder };
  let reminderTimes = modalMetadata.reminderTimes;
  const pendingTime = parseTimepickerValue(
    vals.new_reminder_time_block?.new_reminder_time_input?.selected_time
  );
  if (pendingTime) {
    reminderTimes = normalizeReminderTimesList([...reminderTimes, pendingTime]);
  }

  const { knex } = require('./db');
  const existingSettings = await knex('settings').where({ teamId, userId }).first();
  if (existingSettings) {
    await knex('settings').where({ teamId, userId }).update({
      taskEmoji: checkingEmoji,
      infoEmoji,
      checkingSort,
      docsSort,
    });
  } else {
    const legacySettings = await knex('settings').where({ teamId: 'default', userId }).first();
    if (legacySettings) {
      await knex('settings')
        .where({ teamId: 'default', userId })
        .update({ teamId, taskEmoji: checkingEmoji, infoEmoji, checkingSort, docsSort });
    } else {
      await knex('settings').insert({
        teamId,
        userId,
        taskEmoji: checkingEmoji,
        infoEmoji,
        checkingSort,
        docsSort,
      });
    }
  }
  await replaceReminderTimes(userId, reminderTimes, teamId);

  const tasks = await fetchHomeTasks(userId, teamId);
  await publishHomeView(
    client,
    userId,
    tasks,
    homeContext.tab || 'checking',
    homeContext.folder || 'すべて',
    teamId
  );

  const dmChannel = await getDmChannel(client, userId);
  const reminderText =
    reminderTimes.length > 0
      ? reminderTimes.map((time) => formatReminderTime(time)).join(', ')
      : '未設定';
  const checkingSortLabel = checkingSort === 'asc' ? '古い順（昇順）' : '新しい順（降順）';
  const docsSortLabel = docsSort === 'asc' ? '古い順（昇順）' : '新しい順（降順）';
  await client.chat.postMessage({
    channel: dmChannel,
    text: `✅ ${APP_NAME} の環境設定を保存しました！\n• 確認中用: :${checkingEmoji}:\n• 資料用: :${infoEmoji}:\n• 確認中の並び替え: ${checkingSortLabel}\n• 資料の並び替え: ${docsSortLabel}\n• リマインド時間: ${reminderText}`,
  });
});

app.action(/^(manage_folders|open_folder_settings_modal)$/, async ({ body, client, ack }) => {
  await ack();
  const teamId = getTeamId(body);
  const folders = await getFolders(body.user.id, teamId);
  const editableFolders = folders.filter((folder) => !['すべて', '未分類'].includes(folder));
  await client.views.open({
    trigger_id: body.trigger_id,
    view: {
      type: 'modal',
      callback_id: 'save_folder_settings',
      title: { type: 'plain_text', text: 'フォルダ管理' },
      submit: { type: 'plain_text', text: '保存' },
      close: { type: 'plain_text', text: 'キャンセル' },
      blocks: [
        {
          type: 'input',
          block_id: 'folders_block',
          optional: true,
          label: { type: 'plain_text', text: 'フォルダ名（1行に1つ）' },
          element: {
            type: 'plain_text_input',
            action_id: 'folders_input',
            multiline: true,
            ...(editableFolders.length > 0 ? { initial_value: editableFolders.join('\n') } : {}),
            placeholder: { type: 'plain_text', text: 'プロジェクトA、マニュアル など' },
          },
        },
        {
          type: 'context',
          elements: [
            {
              type: 'mrkdwn',
              text: '「未分類」は自動で用意されます。',
            },
          ],
        },
      ],
    },
  });
});

app.view('save_folder_settings', async ({ view, body, client, ack }) => {
  await ack();
  const userId = body.user.id;
  const teamId = getTeamId(body);
  const rawFolders = view.state.values.folders_block.folders_input.value || '';
  const folders = rawFolders
    .split(/\r?\n|,/)
    .map((folder) => folder.trim())
    .filter(Boolean);

  await replaceFolders(userId, folders, teamId);

  const tasks = await fetchHomeTasks(userId, teamId);
  await publishHomeView(client, userId, tasks, 'info', 'すべて', teamId);
});

app.action('open_move_folder_modal', async ({ body, action, client, ack }) => {
  await ack();
  let payload;
  try {
    payload = JSON.parse(action.value);
  } catch (_) {
    console.warn(`[${APP_NAME}] 移動ボタンのvalueを解析できませんでした: ${action.value}`);
    return;
  }

  const teamId = getTeamId(body);
  const folders = await getFolders(body.user.id, teamId);
  const folderOptions = folders.map(toFolderSelectOption);
  await client.views.open({
    trigger_id: body.trigger_id,
    view: {
      type: 'modal',
      callback_id: 'save_move_folder',
      private_metadata: JSON.stringify({ taskId: payload.taskId }),
      title: { type: 'plain_text', text: '資料を移動' },
      submit: { type: 'plain_text', text: '移動' },
      close: { type: 'plain_text', text: 'キャンセル' },
      blocks: [
        {
          type: 'input',
          block_id: 'folder_block',
          label: { type: 'plain_text', text: '移動先フォルダ' },
          element: {
            type: 'static_select',
            action_id: 'folder_input',
            placeholder: { type: 'plain_text', text: 'フォルダを選択' },
            options: folderOptions,
            initial_option: getInitialFolderOption(folders, payload.folder || '未分類'),
          },
        },
        {
          type: 'context',
          elements: [
            {
              type: 'mrkdwn',
              text: `既存フォルダ: ${folders.join(' · ')}`,
            },
          ],
        },
      ],
    },
  });
});

app.view('save_move_folder', async ({ view, body, client, ack }) => {
  await ack();
  let metadata;
  try {
    metadata = JSON.parse(view.private_metadata || '{}');
  } catch (_) {
    metadata = {};
  }

  const taskId = Number(metadata.taskId);
  if (!Number.isInteger(taskId) || taskId <= 0) {
    console.warn(`[${APP_NAME}] 移動対象のtaskIdが不正です: ${view.private_metadata}`);
    return;
  }

  const userId = body.user.id;
  const teamId = getTeamId(body);
  const folder = view.state.values.folder_block.folder_input.selected_option?.value || '未分類';
  const task = await updateTaskFolder(userId, taskId, folder, teamId);
  console.log(`[${APP_NAME}] 資料フォルダ移動完了:`, task);

  const tasks = await fetchHomeTasks(userId, teamId);
  await publishHomeView(client, userId, tasks, 'info', task?.folder || '未分類', teamId);
});

// ─── リアクション検知 ─────────────────────────────────────────────────────────

app.event('reaction_added', async ({ event, body, client }) => {
  try {
    const { reaction, user, item } = event;
    if (item.type !== 'message') return;
    const teamId = getTeamId(body);

    await ensureJoinedChannel(client, item.channel);

    const settings = await getSettings(user, teamId);

    let category = null;
    // 確認中スタンプ
    if (reaction === settings.taskEmoji) category = 'TASK';
    else if (reaction === settings.infoEmoji) category = 'INFO';
    if (!category) return;

    const text = await getMessageText(client, item.channel, item.ts);
    const itemUser = event.item_user || user;
    const userIcon = await getUserIcon(client, itemUser);
    const task = await saveTask({
      teamId,
      userId: user,
      itemUser,
      user_icon: userIcon,
      messageTs: item.ts,
      channelId: item.channel,
      text,
      emoji: reaction,
      category,
    });
    console.log('DB保存完了:', task);
  } catch (error) {
    console.error(`[${APP_NAME}] reaction_added処理エラー:`, error);
  }
});

// ─── リマインド（毎分・カスタム時刻） ───────────────────────────────────────────

cron.schedule('* * * * *', async () => {
  const now = new Date();
  const currentHour = now.getHours();
  const currentMinute = now.getMinutes();
  console.log(`⏰ リマインドチェック中: ${currentHour}:${String(currentMinute).padStart(2, '0')}`);
  const reminderTargets = await getUserIdsForReminderTime(currentHour, currentMinute);

  for (const { teamId, userId } of reminderTargets) {
    try {
      const count = await countPendingCheckingTasks(userId, teamId);
      if (count === 0) continue;

      const botToken = await getInstallationBotToken(teamId);
      if (!botToken) {
        console.warn(`[${APP_NAME}] インストール情報がないためリマインドをスキップしました: team=${teamId}`);
        continue;
      }

      const dmChannel = await getDmChannel(app.client, userId, botToken);
      await app.client.chat.postMessage({
        token: botToken,
        channel: dmChannel,
        text: `🚨🚨🚨 Emoji Pin リマインド 🚨🚨🚨 確認中のタスクが ${count}件 あります！ 忘れないうちにチェックしましょう 🚀`,
        blocks: buildCheckingReminderBlocks(count),
      });
    } catch (error) {
      console.error(`[${APP_NAME}] カスタムリマインド送信エラー (${userId}):`, error);
    }
  }
});

cron.schedule('0 9 * * *', async () => {
  const reminderTargets = await getAllUserIdsWithPendingOldTasks(24);
  for (const { teamId, userId } of reminderTargets) {
    try {
      const tasks = await getPendingTasks(userId, teamId);
      const old = tasks.filter(
        (t) => new Date(t.createdAt) < new Date(Date.now() - 24 * 60 * 60 * 1000)
      );
      if (old.length === 0) continue;

      const botToken = await getInstallationBotToken(teamId);
      if (!botToken) {
        console.warn(`[${APP_NAME}] インストール情報がないため24時間リマインドをスキップしました: team=${teamId}`);
        continue;
      }

      const dmChannel = await getDmChannel(app.client, userId, botToken);
      const lines = old
        .map((t) => {
          const link = `https://slack.com/archives/${t.channelId}/p${t.messageTs.replace('.', '')}`;
          const label = t.category === 'TASK' ? '👀 確認中' : '📖 資料';
          return `${label} <${link}|${t.text?.slice(0, 40) || 'メッセージ'}>`;
        })
        .join('\n');

      await app.client.chat.postMessage({
        token: botToken,
        channel: dmChannel,
        text: `📣 *${APP_NAME} リマインド*: 24時間以上経過した未完了アイテムが ${old.length} 件あります！\n${lines}`,
      });
    } catch (e) {
      console.error(`Remind error for ${userId}:`, e.message);
    }
  }
});

// ─── 起動 ─────────────────────────────────────────────────────────────────────

(async () => {
  try {
    // 【重要】データベースのテーブルを作成・確認する
    await db.initDb();

    const port = process.env.PORT || 3000;
    await app.start(port);
    console.log(`⚡️ Emoji Pin is Live on port ${port}!`);
  } catch (error) {
    console.error('Failed to start app:', error);
  }
})();
