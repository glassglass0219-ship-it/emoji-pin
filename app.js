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
  getReminderHours,
  replaceReminderHours,
  getUserIdsForReminderHour,
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
      await db.knex('installations').insert({
        team_id: teamId,
        installation: JSON.stringify(installation),
      }).onConflict('team_id').merge();
    },
    fetchInstallation: async (installQuery) => {
      const teamId = installQuery.teamId || installQuery.enterpriseId;
      const row = await db.knex('installations').where({ team_id: teamId }).first();
      if (row) return JSON.parse(row.installation);
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
          value: 'settings',
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

  const renderItems = (items, totalCount) => {
    if (items.length === 0) return [];
    const section = [];
    const spacerBlock = {
      type: 'section',
      text: { type: 'mrkdwn', text: '\u200B' },
    };

    items.forEach((t, index) => {
      const link = `https://slack.com/archives/${t.channelId}/p${t.messageTs.replace('.', '')}`;
      const createdAt = new Date(t.createdAt).toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      }).replace(/\//g, '.');
      if (index > 0) section.push(spacerBlock);
      section.push({ type: 'divider' });
      section.push(spacerBlock);
      section.push({
        type: 'context',
        elements: [
          {
            type: 'image',
            image_url: t.user_icon || t.userIcon || 'https://api.slack.com/img/blocks/base/plants/plant1.png',
            alt_text: 'user_icon',
          },
          {
            type: 'mrkdwn',
            text: `*<@${t.itemUser || t.userId}>*`,
          },
        ],
      });
      section.push({
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: t.text || '(テキストなし)',
        },
      });
      section.push({
        type: 'context',
        elements: [
          {
            type: 'mrkdwn',
            text: `🕒 ${createdAt}  ·  <${link}|🔗 メッセージを表示>`,
          },
        ],
      });
      const actionElements = [];
      if (isDoneTab) {
        actionElements.push(
          {
            type: 'button',
            text: { type: 'plain_text', text: '🔄 確認中に戻す', emoji: true },
            action_id: 'reopen_to_checking',
            value: JSON.stringify({ taskId: t.id }),
          },
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
          }
        );
      } else {
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
          action_id: 'complete_task',
          value: JSON.stringify({ taskId: t.id, tab: selectedTab, folder: safeSelectedFolder }),
        });
      }
      section.push({
        type: 'actions',
        elements: actionElements,
      });
    });
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

function toReminderHourOption(hour) {
  return {
    text: { type: 'plain_text', text: `${hour}:00`, emoji: true },
    value: String(hour),
  };
}

function getReminderHourOptions() {
  return Array.from({ length: 24 }, (_, hour) => toReminderHourOption(hour));
}

function getInitialReminderHourOptions(hours) {
  return hours.map((hour) => toReminderHourOption(hour));
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
  const tasks = await getHomeTasks(event.user, teamId);
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
  const tasks = await getHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, selectedTab, 'すべて', teamId);
});

app.action(/^switch_folder_/, async ({ body, action, client, ack }) => {
  await ack();
  const selectedFolder = action.value || 'すべて';
  const teamId = getTeamId(body);
  const tasks = await getHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, 'info', selectedFolder, teamId);
});

app.action('open_app_home_from_reminder', async ({ body, client, ack }) => {
  await ack();
  const teamId = getTeamId(body);
  const tasks = await getHomeTasks(body.user.id, teamId);
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
    const tasks = await getHomeTasks(body.user.id, teamId);
    await publishHomeView(client, body.user.id, tasks, 'checking', 'すべて', teamId);
    return;
  }

  await knex('tasks').where({ id: parsedAction.taskId, teamId, userId: body.user.id }).update({ status: 'completed' });

  const tasks = await getHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, parsedAction.selectedTab, parsedAction.selectedFolder, teamId);
});

app.action(/^(reopen_to_checking|reopen_to_info)$/, async ({ body, action, client, ack }) => {
  await ack();
  const teamId = getTeamId(body);
  const parsedAction = parseCompleteTaskActionValue(action.value || body.actions?.[0]?.value);
  if (!parsedAction) {
    console.warn(`[${APP_NAME}] 再オープンボタンのvalueからtaskIdを取得できませんでした: ${action.value}`);
    const tasks = await getHomeTasks(body.user.id, teamId);
    await publishHomeView(client, body.user.id, tasks, 'done', 'すべて', teamId);
    return;
  }

  const nextCategory = action.action_id === 'reopen_to_info' ? 'INFO' : 'TASK';
  await reopenTask(body.user.id, parsedAction.taskId, nextCategory, teamId);

  const tasks = await getHomeTasks(body.user.id, teamId);
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
  const tasks = await getHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, 'done', 'すべて', teamId);
});

app.action('clear_all_done', async ({ body, client, ack }) => {
  await ack();
  const teamId = getTeamId(body);
  await deleteCompletedTasks(body.user.id, teamId);
  const tasks = await getHomeTasks(body.user.id, teamId);
  await publishHomeView(client, body.user.id, tasks, 'done', 'すべて', teamId);
});

// ─── 環境設定モーダル ────────────────────────────────────────────────────────

app.action('open_settings_modal', async ({ body, client, ack }) => {
  await ack();
  const teamId = getTeamId(body);
  const settings = await getSettings(body.user.id, teamId);
  const emojiOptions = businessEmojiOptions.map(toSlackSelectOption);
  const reminderHours = await getReminderHours(body.user.id, teamId);
  await client.views.open({
    trigger_id: body.trigger_id,
    view: {
      type: 'modal',
      callback_id: 'save_settings',
      title: { type: 'plain_text', text: '環境設定' },
      submit: { type: 'plain_text', text: '保存' },
      close: { type: 'plain_text', text: 'キャンセル' },
      blocks: [
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
          block_id: 'reminder_hours_block',
          optional: true,
          label: { type: 'plain_text', text: 'リマインド時間を選択（複数選択可）' },
          element: {
            type: 'multi_static_select',
            action_id: 'reminder_hours_input',
            placeholder: { type: 'plain_text', text: 'リマインドする時間を選択' },
            options: getReminderHourOptions(),
            ...(reminderHours.length > 0
              ? { initial_options: getInitialReminderHourOptions(reminderHours) }
              : {}),
          },
        },
      ],
    },
  });
});

app.view('save_settings', async ({ view, body, client, ack }) => {
  await ack();
  const vals = view.state.values;
  const userId = body.user.id;
  const teamId = getTeamId(body);
  const checkingEmoji = vals.checking_emoji_block.checking_emoji_input.selected_option.value;
  const infoEmoji = vals.info_emoji_block.info_emoji_input.selected_option.value;
  const reminderHours =
    vals.reminder_hours_block.reminder_hours_input.selected_options?.map((option) =>
      Number(option.value)
    ) || [];

  const { knex } = require('./db');
  const existingSettings = await knex('settings').where({ teamId, userId }).first();
  if (existingSettings) {
    await knex('settings').where({ teamId, userId }).update({ taskEmoji: checkingEmoji, infoEmoji });
  } else {
    const legacySettings = await knex('settings').where({ teamId: 'default', userId }).first();
    if (legacySettings) {
      await knex('settings')
        .where({ teamId: 'default', userId })
        .update({ teamId, taskEmoji: checkingEmoji, infoEmoji });
    } else {
      await knex('settings').insert({ teamId, userId, taskEmoji: checkingEmoji, infoEmoji });
    }
  }
  await replaceReminderHours(userId, reminderHours, teamId);

  const dmChannel = await getDmChannel(client, userId);
  const reminderText =
    reminderHours.length > 0
      ? reminderHours
          .slice()
          .sort((a, b) => a - b)
          .map((hour) => `${hour}:00`)
          .join(', ')
      : '未設定';
  await client.chat.postMessage({
    channel: dmChannel,
    text: `✅ ${APP_NAME} の環境設定を保存しました！\n• 確認中用: :${checkingEmoji}:\n• 資料用: :${infoEmoji}:\n• リマインド時間: ${reminderText}`,
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

  const tasks = await getHomeTasks(userId, teamId);
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

  const tasks = await getHomeTasks(userId, teamId);
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

// ─── リマインド (毎日 09:00) ──────────────────────────────────────────────────

cron.schedule('0 * * * *', async () => {
  const currentHour = new Date().getHours();
  const reminderTargets = await getUserIdsForReminderHour(currentHour);

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
        text: `${APP_NAME}: 確認中のタスクが ${count} 件あります。`,
        blocks: [
          {
            type: 'section',
            text: {
              type: 'mrkdwn',
              text: `*${APP_NAME} リマインド*\n確認中のタスクが *${count}件* あります。`,
            },
          },
          {
            type: 'actions',
            elements: [getAppHomeButton()],
          },
        ],
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
  await db.initDb(); // データベースの初期化
  await app.start(process.env.PORT || 3000);
  console.log('⚡️ Emoji Pin Slack app (OAuth mode) is running!');
})();
