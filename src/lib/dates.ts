export const MONTH_NAMES = [
  "Styczeń",
  "Luty",
  "Marzec",
  "Kwiecień",
  "Maj",
  "Czerwiec",
  "Lipiec",
  "Sierpień",
  "Wrzesień",
  "Październik",
  "Listopad",
  "Grudzień",
];

export const MONTH_SHORT = [
  "sty",
  "lut",
  "mar",
  "kwi",
  "maj",
  "cze",
  "lip",
  "sie",
  "wrz",
  "paź",
  "lis",
  "gru",
];
export const WEEKDAY_SHORT = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Nie"];

const pad = (n: number) => String(n).padStart(2, "0");

export function isoDate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function parseISODate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function parseYear(value: string | null | undefined): number {
  const parsed = Number.parseInt(value || "", 10);
  const current = new Date().getFullYear();
  if (parsed >= 2020 && parsed <= current + 2) return parsed;
  return current;
}

export function parseMonth(value: string | null | undefined): number {
  const parsed = Number.parseInt(value || "", 10);
  if (parsed >= 1 && parsed <= 12) return parsed;
  return new Date().getMonth() + 1;
}

export function yearContext(year: number) {
  const today = new Date();
  const cy = today.getFullYear();
  return {
    year,
    yearOptions: Array.from({ length: cy + 2 - 2023 }, (_, i) => 2023 + i),
    today,
    todayIso: isoDate(today),
  };
}

export function fmtDays(days: number): string {
  const full = Math.trunc(days);
  const hours = Math.round((days - full) * 8 * 2) / 2;
  if (hours === 0) return `${full} dni`;
  if (full === 0) return `${hours}h`;
  return `${full} dni ${hours}h`;
}

export function fmtDatePl(date: string | Date | null | undefined): string {
  if (!date) return "";
  const d = typeof date === "string" ? parseISODate(date.substring(0, 10)) : date;
  return `${WEEKDAY_SHORT[(d.getDay() + 6) % 7]}, ${d.getDate()} ${MONTH_SHORT[d.getMonth()]} ${d.getFullYear()}`;
}

export function getCalendarDays(year: number, month: number): Date[] {
  const first = new Date(year, month - 1, 1);
  const last = new Date(year, month, 0);
  const start = new Date(first);
  start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
  const end = new Date(last);
  end.setDate(last.getDate() + ((7 - last.getDay()) % 7));

  const days: Date[] = [];
  const cur = new Date(start);
  while (cur <= end) {
    days.push(new Date(cur));
    cur.setDate(cur.getDate() + 1);
  }
  return days;
}

export function easterDate(year: number): Date {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(year, month - 1, day);
}

export function addDays(d: Date, days: number): Date {
  const copy = new Date(d);
  copy.setDate(copy.getDate() + days);
  return copy;
}

export function getPolishHolidays(year: number): Record<string, string> {
  const easter = easterDate(year);
  const holidays: Record<string, string> = {};
  const add = (date: Date, name: string) => {
    holidays[isoDate(date)] = name;
  };
  add(new Date(year, 0, 1), "Nowy Rok");
  add(new Date(year, 0, 6), "Trzech Króli");
  add(easter, "Wielkanoc");
  add(addDays(easter, 1), "Lany Poniedziałek");
  add(new Date(year, 4, 1), "Święto Pracy");
  add(new Date(year, 4, 3), "Święto Konstytucji");
  add(addDays(easter, 49), "Zielone Świątki");
  add(addDays(easter, 60), "Boże Ciało");
  add(new Date(year, 7, 15), "Wniebowzięcie NMP");
  add(new Date(year, 10, 1), "Wszyscy Święci");
  add(new Date(year, 10, 11), "Niepodległość");
  add(new Date(year, 11, 25), "Boże Narodzenie");
  add(new Date(year, 11, 26), "2. dzień Bożego Narodzenia");
  return holidays;
}
