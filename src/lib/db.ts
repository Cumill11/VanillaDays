import bcrypt from 'bcryptjs';
import type { LeaveEntry, LeaveType, OvertimeEntry, YearConfig } from './types';
import { fmtDays, isoDate, MONTH_SHORT, todayLocal } from './dates';

const OKOL_LIMIT = 2;

export async function checkPassword(password: string, hash: string): Promise<boolean> {
  try {
    return await bcrypt.compare(password, hash);
  } catch {
    return false;
  }
}

export async function checkRateLimit(db: D1Database, key: string): Promise<{ allowed: boolean; wait: number }> {
  const now = Math.floor(Date.now() / 1000);
  const row = await db.prepare('SELECT count, locked_until FROM login_attempts WHERE key = ?').bind(key).first<{ count: number; locked_until: number | null }>();
  if (row?.locked_until && now < row.locked_until) {
    return { allowed: false, wait: row.locked_until - now };
  }
  return { allowed: true, wait: 0 };
}

export async function recordFailure(db: D1Database, key: string): Promise<number> {
  const now = Math.floor(Date.now() / 1000);
  const row = await db.prepare('SELECT count FROM login_attempts WHERE key = ?').bind(key).first<{ count: number }>();
  const count = Number(row?.count ?? 0) + 1;
  const lockedUntil = count >= 5 ? now + 15 * 60 : null;
  await db.prepare(`
    INSERT INTO login_attempts (key, count, locked_until, updated_at)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(key) DO UPDATE SET count = excluded.count, locked_until = excluded.locked_until, updated_at = excluded.updated_at
  `).bind(key, count >= 5 ? 0 : count, lockedUntil, now).run();
  return lockedUntil ? lockedUntil - now : 0;
}

export async function clearFailures(db: D1Database, key: string): Promise<void> {
  await db.prepare('DELETE FROM login_attempts WHERE key = ?').bind(key).run();
}

export async function getOrCreateConfig(db: D1Database, year: number): Promise<YearConfig> {
  const existing = await db.prepare('SELECT * FROM year_config WHERE year = ?').bind(year).first<YearConfig>();
  if (existing) return existing;
  await db.prepare(`
    INSERT INTO year_config (year, vacation_limit, ho_limit, vacation_carried_over)
    VALUES (?, 26, 24, 0)
    ON CONFLICT(year) DO NOTHING
  `).bind(year).run();
  const created = await db.prepare('SELECT * FROM year_config WHERE year = ?').bind(year).first<YearConfig>();
  if (!created) throw new Error('Could not create year config');
  return created;
}

function yearRange(year: number): [string, string] {
  return [`${year}-01-01`, `${year}-12-31`];
}

async function countLeave(db: D1Database, year: number, type: LeaveType): Promise<number> {
  const [start, end] = yearRange(year);
  const row = await db.prepare('SELECT COUNT(*) AS cnt FROM leave_entries WHERE date >= ? AND date <= ? AND type = ?')
    .bind(start, end, type)
    .first<{ cnt: number }>();
  return Number(row?.cnt ?? 0);
}

export async function getBalance(db: D1Database, year: number) {
  const cfg = await getOrCreateConfig(db, year);
  const [vacUsed, hoUsed, okolUsed, bezpUsed, l4Used, zaUsed] = await Promise.all([
    countLeave(db, year, 'vacation'),
    countLeave(db, year, 'home_office'),
    countLeave(db, year, 'okolicznosciowy'),
    countLeave(db, year, 'bezplatny'),
    countLeave(db, year, 'l4'),
    countLeave(db, year, 'za_swieto'),
  ]);
  const [start, end] = yearRange(year);
  const ot = await db.prepare(`
    SELECT
      COALESCE(SUM(CASE WHEN type = 'earned' THEN hours ELSE 0 END), 0) AS earned,
      COALESCE(SUM(CASE WHEN type = 'taken' THEN hours ELSE 0 END), 0) AS taken
    FROM overtime_log WHERE date >= ? AND date <= ?
  `).bind(start, end).first<{ earned: number; taken: number }>();

  const vacTotal = Math.round((Number(cfg.vacation_limit) + Number(cfg.vacation_carried_over)) * 100) / 100;
  const hoLimit = Number(cfg.ho_limit);

  return {
    vacation: {
      limit: Number(cfg.vacation_limit),
      carried_over: Number(cfg.vacation_carried_over),
      total: vacTotal,
      used: vacUsed,
      remaining: Math.round((vacTotal - vacUsed) * 100) / 100,
      pct: vacTotal ? Math.min(100, Math.round((vacUsed / vacTotal) * 100)) : 0,
    },
    home_office: {
      limit: hoLimit,
      used: hoUsed,
      remaining: hoLimit - hoUsed,
      pct: hoLimit ? Math.min(100, Math.round((hoUsed / hoLimit) * 100)) : 0,
    },
    okolicznosciowy: {
      limit: OKOL_LIMIT,
      used: okolUsed,
      remaining: Math.max(0, OKOL_LIMIT - okolUsed),
      pct: Math.min(100, Math.round((okolUsed / OKOL_LIMIT) * 100)),
    },
    bezplatny: { used: bezpUsed },
    l4: { used: l4Used },
    za_swieto: { used: zaUsed },
    overtime_balance: Number(ot?.earned ?? 0) - Number(ot?.taken ?? 0),
  };
}

export async function getStats(db: D1Database, year: number) {
  const [start, end] = yearRange(year);
  const rows = await db.prepare(`
    SELECT CAST(strftime('%m', date) AS INTEGER) AS month, type, COUNT(*) AS days
    FROM leave_entries
    WHERE date >= ? AND date <= ?
    GROUP BY month, type
    ORDER BY month
  `).bind(start, end).all<{ month: number; type: LeaveType; days: number }>();
  const monthly = MONTH_SHORT.map((label, i) => ({ month: i + 1, label, vacation: 0, home_office: 0 }));
  for (const row of rows.results || []) {
    if (row.type === 'vacation' || row.type === 'home_office') {
      monthly[Number(row.month) - 1][row.type] = Number(row.days);
    }
  }
  return monthly;
}

export async function getRecentEntries(db: D1Database, year: number): Promise<LeaveEntry[]> {
  const [start, end] = yearRange(year);
  const rows = await db.prepare('SELECT * FROM leave_entries WHERE date >= ? AND date <= ? ORDER BY date DESC LIMIT 10')
    .bind(start, end)
    .all<LeaveEntry>();
  return rows.results || [];
}

export async function getEntriesBetween(db: D1Database, start: string, end: string): Promise<LeaveEntry[]> {
  const rows = await db.prepare('SELECT * FROM leave_entries WHERE date >= ? AND date <= ? ORDER BY date').bind(start, end).all<LeaveEntry>();
  return rows.results || [];
}

export async function getOvertimeBetween(db: D1Database, start: string, end: string): Promise<OvertimeEntry[]> {
  const rows = await db.prepare('SELECT * FROM overtime_log WHERE date >= ? AND date <= ? ORDER BY date').bind(start, end).all<OvertimeEntry>();
  return rows.results || [];
}

export async function getHistoryEntries(db: D1Database, year: number, typeFilter: string, month: number | null): Promise<LeaveEntry[]> {
  const start = month ? `${year}-${String(month).padStart(2, '0')}-01` : `${year}-01-01`;
  const end = month ? isoDate(new Date(year, month, 0)) : `${year}-12-31`;
  const params: (string | number)[] = [start, end];
  let sql = 'SELECT * FROM leave_entries WHERE date >= ? AND date <= ?';
  if (typeFilter) {
    sql += ' AND type = ?';
    params.push(typeFilter);
  }
  sql += ' ORDER BY date DESC';
  const rows = await db.prepare(sql).bind(...params).all<LeaveEntry>();
  return rows.results || [];
}

export async function getHistoryOvertime(db: D1Database, year: number, month: number | null): Promise<OvertimeEntry[]> {
  const start = month ? `${year}-${String(month).padStart(2, '0')}-01` : `${year}-01-01`;
  const end = month ? isoDate(new Date(year, month, 0)) : `${year}-12-31`;
  const rows = await db.prepare('SELECT * FROM overtime_log WHERE date >= ? AND date <= ? ORDER BY date DESC').bind(start, end).all<OvertimeEntry>();
  return rows.results || [];
}

export async function getWarnings(db: D1Database, year: number, balance: Awaited<ReturnType<typeof getBalance>>) {
  const today = todayLocal();
  const warns: Array<[string, string, string]> = [];
  const vacRem = balance.vacation.remaining;
  const hoRem = balance.home_office.remaining;
  const okolRem = balance.okolicznosciowy.remaining;

  if (vacRem === 0) {
    warns.push(['error', 'Urlop wyczerpany', 'Nie masz już dni urlopu na ten rok.']);
  } else if (vacRem <= 3) {
    warns.push(['warning', `Zostało ${fmtDays(vacRem)} urlopu`, 'Zaplanuj ostatnie dni urlopowe.']);
  }

  if (today.getFullYear() === year) {
    const end = new Date(year, 11, 31);
    const daysLeft = Math.floor((end.getTime() - today.getTime()) / 86400000);
    if (daysLeft > 0 && daysLeft <= 60 && vacRem >= 3) {
      warns.push(['info', `Koniec roku za ${daysLeft} dni`, `Masz jeszcze ${fmtDays(vacRem)} urlopu do wykorzystania lub przeniesienia.`]);
    }
  }

  if (hoRem === 0) {
    warns.push(['warning', 'Limit HO wyczerpany', 'Nie masz już dni Home Office — HO nie przechodzi na kolejny rok.']);
  } else if (hoRem <= 2) {
    warns.push(['warning', `Zostały ${hoRem} ${hoRem === 1 ? 'dzień' : 'dni'} HO`, 'Pamiętaj, że HO nie przechodzi na kolejny rok.']);
  }

  if (okolRem === 0) {
    warns.push(['warning', 'Limit urlopu okolicznościowego wyczerpany', 'Wykorzystałeś już 2 dni urlopu okolicznościowego w tym roku.']);
  }

  return warns;
}
