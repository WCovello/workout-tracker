# migrate_add_calorie_calculator.py — run once, then safe to delete
import sqlite3

conn = sqlite3.connect('workouts.db')

new_columns = [
    ('sex', 'TEXT'),
    ('age', 'INTEGER'),
    ('height_cm', 'REAL'),
    ('weight_kg', 'REAL'),
    ('body_fat_pct', 'REAL'),
    ('activity_multiplier', 'REAL'),
    ('goal', 'TEXT'),
    ('weekly_rate_lb', 'REAL'),
]
for name, col_type in new_columns:
    conn.execute(f'ALTER TABLE calorie_goals ADD COLUMN {name} {col_type}')

conn.commit()
conn.close()
print('Done — calculator columns added to calorie_goals.')