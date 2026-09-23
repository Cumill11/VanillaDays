/**
 * Rodzaje wpisów — jedyne źródło dla formularza, walidacji, list, kalendarza i CSV.
 * `cls` to końcówka klas CSS: `chip--{cls}`, `cal-chip--{cls}`, `cal-day--{cls}`.
 * Dopisując typ, rozszerz też CHECK w migracji `leave_entries.type`.
 */
export const LEAVE_TYPES = [
  {
    type: "vacation",
    cls: "vacation",
    icon: "beach_access",
    label: "Urlop",
    fullLabel: "Urlop",
    shortLabel: "Urlop",
    calendarLabel: "URL",
    placeholder: "np. urlop wypoczynkowy, wyjazd…",
  },
  {
    type: "home_office",
    cls: "ho",
    icon: "home",
    label: "Home Office",
    fullLabel: "Home Office",
    shortLabel: "HO",
    calendarLabel: "HO",
    placeholder: "np. praca zdalna, projekt X…",
  },
  {
    type: "okolicznosciowy",
    cls: "okol",
    icon: "celebration",
    label: "Okolicznościowy",
    fullLabel: "Urlop okolicznościowy",
    shortLabel: "Okol.",
    calendarLabel: "Okol.",
    placeholder: "dodatkowe informacje…",
  },
  {
    type: "bezplatny",
    cls: "bezp",
    icon: "money_off",
    label: "Bezpłatny",
    fullLabel: "Urlop bezpłatny",
    shortLabel: "Bezpł.",
    calendarLabel: "Bezpł.",
    placeholder: "np. opieka nad dzieckiem, powód…",
  },
  {
    type: "l4",
    cls: "l4",
    icon: "medical_services",
    label: "L4",
    fullLabel: "L4",
    shortLabel: "L4",
    calendarLabel: "L4",
    placeholder: "dodatkowe informacje…",
  },
  {
    type: "za_swieto",
    cls: "za_swieto",
    icon: "event_repeat",
    label: "Za święto",
    fullLabel: "Urlop za święto",
    shortLabel: "Za św.",
    calendarLabel: "Za św.",
    placeholder: "dodatkowe informacje…",
  },
] as const;

export type LeaveType = (typeof LEAVE_TYPES)[number]["type"];
type LeaveTypeMeta = (typeof LEAVE_TYPES)[number];

export const LEAVE_TYPE_KEYS = LEAVE_TYPES.map((meta) => meta.type) as [LeaveType, ...LeaveType[]];

const BY_TYPE = new Map<string, LeaveTypeMeta>(LEAVE_TYPES.map((meta) => [meta.type, meta]));

export function getLeaveTypeMeta(type: string) {
  return (
    BY_TYPE.get(type) ?? {
      type,
      cls: "",
      icon: "event",
      label: type,
      fullLabel: type,
      shortLabel: type,
      calendarLabel: type,
      placeholder: "",
    }
  );
}
