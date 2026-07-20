CREATE TABLE IF NOT EXISTS year_config (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  year INTEGER NOT NULL UNIQUE,
  vacation_limit REAL NOT NULL DEFAULT 26,
  ho_limit INTEGER NOT NULL DEFAULT 24,
  vacation_carried_over REAL NOT NULL DEFAULT 0,
  overtime_balance REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leave_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('vacation','home_office','okolicznosciowy','bezplatny','l4','za_swieto')),
  notes TEXT DEFAULT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (date, type)
);

CREATE TRIGGER IF NOT EXISTS leave_entries_updated_at
AFTER UPDATE ON leave_entries
FOR EACH ROW
BEGIN
  UPDATE leave_entries SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

CREATE TABLE IF NOT EXISTS overtime_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  hours REAL NOT NULL,
  type TEXT NOT NULL DEFAULT 'earned' CHECK (type IN ('earned','taken')),
  notes TEXT DEFAULT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_attempts (
  key TEXT PRIMARY KEY,
  count INTEGER NOT NULL DEFAULT 0,
  locked_until INTEGER,
  updated_at INTEGER NOT NULL
);
