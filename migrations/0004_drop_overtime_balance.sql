-- Saldo nadgodzin liczone jest z overtime_log — kolumna nigdy nie była czytana.
ALTER TABLE year_config DROP COLUMN overtime_balance;
