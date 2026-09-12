# migrate_add_completed_at.py — run once, Comepletely harmless once ran
import sqlite3

conn = sqlite3.connect('workouts.db')
conn.execute('ALTER TABLE sessions ADD COLUMN completed_at DATETIME')
conn.commit()
conn.close()
print('Done — completed_at column added.')