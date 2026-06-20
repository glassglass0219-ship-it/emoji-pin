require('dotenv').config();

const knex = require('knex')({
  client: 'pg',
  connection: {
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
  },
  pool: {
    min: 0,
    max: 10,
    idleTimeoutMillis: 30000,
  },
  searchPath: ['knex', 'public'],
});

const DEFAULT_CHECKING_EMOJI = 'eyes';
const DEFAULT_INFO_EMOJI = 'bookmark';
const TASK_EMOJI_DEFAULT_MIGRATION = 'default_task_emoji_eyes';
const DEFAULT_TEAM_ID = 'default';

async function ensureColumn(tableName, columnName, addColumn) {
  const hasColumn = await knex.schema.hasColumn(tableName, columnName);
  if (!hasColumn) {
    await knex.schema.alterTable(tableName, addColumn);
  }
}

async function initDb() {
  const hasTasks = await knex.schema.hasTable('tasks');
  if (!hasTasks) {
    await knex.schema.createTable('tasks', (t) => {
      t.increments('id').primary();
      t.string('teamId').notNullable().defaultTo(DEFAULT_TEAM_ID);
      t.string('userId').notNullable();
      t.string('itemUser');
      t.string('userIcon');
      t.string('user_icon');
      t.string('messageTs').notNullable();
      t.string('channelId').notNullable();
      t.text('text');
      t.string('emoji');
      t.string('category').notNullable(); // TASK | INFO
      t.string('folder').notNullable().defaultTo('未分類');
      t.string('status').notNullable().defaultTo('pending'); // pending | completed
      t.timestamp('createdAt').defaultTo(knex.fn.now());
    });
  }

  await ensureColumn('tasks', 'teamId', (t) => {
    t.string('teamId').notNullable().defaultTo(DEFAULT_TEAM_ID);
  });

  await ensureColumn('tasks', 'itemUser', (t) => {
    t.string('itemUser');
  });

  await ensureColumn('tasks', 'userIcon', (t) => {
    t.string('userIcon');
  });

  await ensureColumn('tasks', 'user_icon', (t) => {
    t.string('user_icon');
  });

  const hasFolderColumn = await knex.schema.hasColumn('tasks', 'folder');
  if (!hasFolderColumn) {
    await knex.schema.alterTable('tasks', (t) => {
      t.string('folder').notNullable().defaultTo('未分類');
    });
  }

  const hasSettings = await knex.schema.hasTable('settings');
  if (!hasSettings) {
    await knex.schema.createTable('settings', (t) => {
      t.string('teamId').notNullable().defaultTo(DEFAULT_TEAM_ID);
      t.string('userId').notNullable();
      t.string('taskEmoji').defaultTo(DEFAULT_CHECKING_EMOJI);
      t.string('infoEmoji').defaultTo(DEFAULT_INFO_EMOJI);
      t.primary(['teamId', 'userId']);
    });
  }

  await ensureColumn('settings', 'teamId', (t) => {
    t.string('teamId').notNullable().defaultTo(DEFAULT_TEAM_ID);
  });

  const hasReminderSettings = await knex.schema.hasTable('reminder_settings');
  if (!hasReminderSettings) {
    await knex.schema.createTable('reminder_settings', (t) => {
      t.string('team_id').notNullable().defaultTo(DEFAULT_TEAM_ID);
      t.string('user_id').notNullable();
      t.integer('hour').notNullable();
      t.primary(['team_id', 'user_id', 'hour']);
    });
  }

  await ensureColumn('reminder_settings', 'team_id', (t) => {
    t.string('team_id').notNullable().defaultTo(DEFAULT_TEAM_ID);
  });

  const hasFolderSettings = await knex.schema.hasTable('folder_settings');
  if (!hasFolderSettings) {
    await knex.schema.createTable('folder_settings', (t) => {
      t.string('team_id').notNullable().defaultTo(DEFAULT_TEAM_ID);
      t.string('user_id').notNullable();
      t.string('name').notNullable();
      t.primary(['team_id', 'user_id', 'name']);
    });
  }

  await ensureColumn('folder_settings', 'team_id', (t) => {
    t.string('team_id').notNullable().defaultTo(DEFAULT_TEAM_ID);
  });

  const hasMigrations = await knex.schema.hasTable('migrations');
  if (!hasMigrations) {
    await knex.schema.createTable('migrations', (t) => {
      t.string('name').primary();
      t.timestamp('createdAt').defaultTo(knex.fn.now());
    });
  }

  const defaultMigration = await knex('migrations').where({ name: TASK_EMOJI_DEFAULT_MIGRATION }).first();
  if (!defaultMigration) {
    await knex('settings').where({ taskEmoji: 'white_check_mark' }).update({ taskEmoji: DEFAULT_CHECKING_EMOJI });
    await knex('migrations').insert({ name: TASK_EMOJI_DEFAULT_MIGRATION });
  }

  const hasInstallations = await knex.schema.hasTable('installations');
  if (!hasInstallations) {
    await knex.schema.createTable('installations', (t) => {
      t.string('team_id').primary();
      t.jsonb('installation');
      t.timestamp('created_at').defaultTo(knex.fn.now());
    });
  }

  await ensureColumn('installations', 'team_id', (t) => {
    t.string('team_id');
  });

  await ensureColumn('installations', 'installation', (t) => {
    t.jsonb('installation');
  });

  await ensureColumn('installations', 'created_at', (t) => {
    t.timestamp('created_at').defaultTo(knex.fn.now());
  });

}

function getInstallationTeamId(query = {}) {
  const teamId = query.teamId || query.team?.id || query.team_id || null;
  const enterpriseId = query.enterpriseId || query.enterprise?.id || query.enterprise_id || null;

  if (teamId) return teamId;
  if (enterpriseId) return enterpriseId;

  throw new Error('Slack installation is missing teamId or enterpriseId.');
}

function parseInstallationData(data) {
  return typeof data === 'string' ? JSON.parse(data) : data;
}

async function storeInstallation(installation) {
  const teamId = getInstallationTeamId(installation);
  const row = {
    team_id: teamId,
    installation,
  };

  await knex('installations')
    .insert(row)
    .onConflict('team_id')
    .merge({
      installation: row.installation,
    });
}

async function fetchInstallation(installQuery) {
  const teamId = getInstallationTeamId(installQuery);
  const row = await knex('installations').where({ team_id: teamId }).first();
  if (!row) {
    throw new Error(`Slack installation not found: ${teamId}`);
  }

  return parseInstallationData(row.installation);
}

async function deleteInstallation(installQuery) {
  const teamId = getInstallationTeamId(installQuery);
  await knex('installations').where({ team_id: teamId }).delete();
}

async function getInstallationBotToken(teamId) {
  if (!teamId) return null;
  const row = await knex('installations').where({ team_id: teamId }).first();
  const installation = row ? parseInstallationData(row.installation) : null;
  return installation?.bot?.token || null;
}

async function getInstallationBotTokens() {
  const rows = await knex('installations').select('team_id as teamId', 'installation');
  return rows
    .map((row) => {
      const installation = parseInstallationData(row.installation);
      return { teamId: row.teamId, botToken: installation?.bot?.token || null };
    })
    .filter((row) => row.botToken);
}

async function getSettings(userId, teamId = DEFAULT_TEAM_ID) {
  let row = await knex('settings').where({ userId, teamId }).first();
  if (!row && teamId !== DEFAULT_TEAM_ID) {
    const legacyRow = await knex('settings').where({ userId, teamId: DEFAULT_TEAM_ID }).first();
    if (legacyRow) {
      await knex('settings').where({ userId, teamId: DEFAULT_TEAM_ID }).update({ teamId });
      row = await knex('settings').where({ userId, teamId }).first();
    }
  }
  if (!row) {
    await knex('settings').insert({
      teamId,
      userId,
      taskEmoji: DEFAULT_CHECKING_EMOJI,
      infoEmoji: DEFAULT_INFO_EMOJI,
    });
    row = await knex('settings').where({ userId, teamId }).first();
  }
  return row;
}

async function saveTask({ teamId = DEFAULT_TEAM_ID, userId, itemUser, userIcon, user_icon, messageTs, channelId, text, emoji, category }) {
  const iconUrl = user_icon || userIcon || null;
  const existing = await knex('tasks').where({ teamId, userId, messageTs, channelId, category }).first();
  if (existing) {
    await knex('tasks').where({ id: existing.id }).update({ text, emoji, itemUser, user_icon: iconUrl, status: 'pending' });
    return knex('tasks').where({ id: existing.id }).first();
  }

  const [inserted] = await knex('tasks')
    .insert({ teamId, userId, itemUser, user_icon: iconUrl, messageTs, channelId, text, emoji, category })
    .returning('id');
  const id = typeof inserted === 'object' ? inserted.id : inserted;
  return knex('tasks').where({ id }).first();
}

function normalizeFolderName(name) {
  const folder = String(name || '').trim();
  return folder || '未分類';
}

async function completeTask({ teamId = DEFAULT_TEAM_ID, messageTs, channelId }) {
  return knex('tasks').where({ teamId, messageTs, channelId, status: 'pending' }).update({ status: 'completed' });
}

async function getPendingTasks(userId, teamId = DEFAULT_TEAM_ID) {
  return knex('tasks').where({ teamId, userId, status: 'pending' }).orderBy('createdAt', 'asc');
}

async function getHomeTasks(userId, teamId = DEFAULT_TEAM_ID) {
  return knex('tasks')
    .where({ teamId, userId })
    .orderByRaw("CASE WHEN status = 'completed' THEN createdAt END DESC")
    .orderBy('createdAt', 'asc');
}

async function reopenTask(userId, taskId, category, teamId = DEFAULT_TEAM_ID) {
  const nextCategory = category === 'INFO' ? 'INFO' : 'TASK';
  await knex('tasks')
    .where({ id: taskId, userId, teamId })
    .update({
      category: nextCategory,
      status: 'pending',
      folder: nextCategory === 'INFO' ? '未分類' : '未分類',
    });
  return knex('tasks').where({ id: taskId, userId, teamId }).first();
}

async function deleteTask(userId, taskId, teamId = DEFAULT_TEAM_ID) {
  return knex('tasks').where({ id: taskId, userId, teamId }).delete();
}

async function deleteCompletedTasks(userId, teamId = DEFAULT_TEAM_ID) {
  return knex('tasks').where({ userId, teamId, status: 'completed' }).delete();
}

async function getFolders(userId, teamId = DEFAULT_TEAM_ID) {
  const savedFolders = await knex('folder_settings').where({ team_id: teamId, user_id: userId }).orderBy('name', 'asc');
  const usedFolders = await knex('tasks')
    .where({ teamId, userId, category: 'INFO' })
    .whereNotNull('folder')
    .distinct('folder')
    .select('folder');

  const customFolders = [
    ...new Set([
      ...savedFolders.map((row) => normalizeFolderName(row.name)),
      ...usedFolders.map((row) => normalizeFolderName(row.folder)),
    ]),
  ].filter((folder) => folder && !['すべて', '未分類'].includes(folder));

  return ['未分類', ...customFolders];
}

async function replaceFolders(userId, folders, teamId = DEFAULT_TEAM_ID) {
  const validFolders = [
    ...new Set(
      folders
        .map(normalizeFolderName)
        .filter((folder) => folder && !['すべて', '未分類'].includes(folder))
    ),
  ];

  await knex.transaction(async (trx) => {
    await trx('folder_settings').where({ team_id: teamId, user_id: userId }).delete();
    if (validFolders.length > 0) {
      await trx('folder_settings').insert(validFolders.map((name) => ({ team_id: teamId, user_id: userId, name })));
    }
  });
}

async function updateTaskFolder(userId, taskId, folder, teamId = DEFAULT_TEAM_ID) {
  const normalizedFolder = normalizeFolderName(folder);
  await knex('tasks').where({ id: taskId, userId, teamId }).update({ category: 'INFO', folder: normalizedFolder });
  return knex('tasks').where({ id: taskId, userId, teamId }).first();
}

async function getReminderHours(userId, teamId = DEFAULT_TEAM_ID) {
  const rows = await knex('reminder_settings').where({ team_id: teamId, user_id: userId }).orderBy('hour', 'asc');
  return rows.map((row) => row.hour);
}

async function replaceReminderHours(userId, hours, teamId = DEFAULT_TEAM_ID) {
  const validHours = [...new Set(hours.map((hour) => Number(hour)).filter((hour) => Number.isInteger(hour) && hour >= 0 && hour <= 23))];

  await knex.transaction(async (trx) => {
    await trx('reminder_settings').where({ team_id: teamId, user_id: userId }).delete();
    if (validHours.length > 0) {
      await trx('reminder_settings').insert(validHours.map((hour) => ({ team_id: teamId, user_id: userId, hour })));
    }
  });
}

async function getUserIdsForReminderHour(hour) {
  const rows = await knex('reminder_settings')
    .where({ hour })
    .distinct('team_id', 'user_id')
    .select('team_id', 'user_id');
  return rows.map((row) => ({ teamId: row.team_id, userId: row.user_id }));
}

async function countPendingCheckingTasks(userId, teamId = DEFAULT_TEAM_ID) {
  const row = await knex('tasks')
    .where({ teamId, userId, category: 'TASK', status: 'pending' })
    .count({ count: '*' })
    .first();
  return Number(row?.count || 0);
}

async function getPendingTasksOlderThan(hours, teamId = DEFAULT_TEAM_ID) {
  const threshold = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
  return knex('tasks').where({ teamId, status: 'pending' }).where('createdAt', '<', threshold);
}

async function getAllUserIdsWithPendingOldTasks(hours) {
  const threshold = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
  const rows = await knex('tasks')
    .where({ status: 'pending' })
    .where('createdAt', '<', threshold)
    .distinct('teamId', 'userId')
    .select('teamId', 'userId');
  return rows.map((r) => ({ teamId: r.teamId, userId: r.userId }));
}

module.exports = {
  knex,
  initDb,
  storeInstallation,
  fetchInstallation,
  deleteInstallation,
  getInstallationBotToken,
  getInstallationBotTokens,
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
  getPendingTasksOlderThan,
  getAllUserIdsWithPendingOldTasks,
};
