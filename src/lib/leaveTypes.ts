export const leaveTypeMeta: Record<string, { icon: string; className: string; label: string; shortLabel: string; calendarClass: string; calendarLabel: string }> = {
  vacation: {
    icon: 'beach_access',
    className: 'chip--vacation',
    label: 'Urlop',
    shortLabel: 'Urlop',
    calendarClass: 'cal-chip--vacation',
    calendarLabel: 'URL',
  },
  home_office: {
    icon: 'home',
    className: 'chip--ho',
    label: 'Home Office',
    shortLabel: 'HO',
    calendarClass: 'cal-chip--ho',
    calendarLabel: 'HO',
  },
  okolicznosciowy: {
    icon: 'celebration',
    className: 'chip--okol',
    label: 'Okolicznościowy',
    shortLabel: 'Okol.',
    calendarClass: 'cal-chip--okol',
    calendarLabel: 'Okol.',
  },
  bezplatny: {
    icon: 'money_off',
    className: 'chip--bezp',
    label: 'Bezpłatny',
    shortLabel: 'Bezpł.',
    calendarClass: 'cal-chip--bezp',
    calendarLabel: 'Bezpł.',
  },
  l4: {
    icon: 'medical_services',
    className: 'chip--l4',
    label: 'L4',
    shortLabel: 'L4',
    calendarClass: 'cal-chip--l4',
    calendarLabel: 'L4',
  },
  za_swieto: {
    icon: 'event_repeat',
    className: 'chip--za',
    label: 'Za święto',
    shortLabel: 'Za św.',
    calendarClass: 'cal-chip--za_swieto',
    calendarLabel: 'Za św.',
  },
};

export function getLeaveTypeMeta(type: string) {
  return leaveTypeMeta[type] || {
    icon: 'event',
    className: '',
    label: type,
    shortLabel: type,
    calendarClass: '',
    calendarLabel: type,
  };
}
