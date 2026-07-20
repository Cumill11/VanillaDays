export type LeaveType = 'vacation' | 'home_office' | 'okolicznosciowy' | 'bezplatny' | 'l4' | 'za_swieto';
export type OvertimeType = 'earned' | 'taken';

export interface YearConfig {
  id: number;
  year: number;
  vacation_limit: number;
  ho_limit: number;
  vacation_carried_over: number;
  overtime_balance: number;
  created_at: string;
}

export interface LeaveEntry {
  id: number;
  date: string;
  type: LeaveType;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface OvertimeEntry {
  id: number;
  date: string;
  hours: number;
  type: OvertimeType;
  notes: string | null;
  created_at: string;
}

export interface SessionData {
  csrf: string;
  exp: number;
}
