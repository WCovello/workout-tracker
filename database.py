"""
database.py
Handles everything database-related:
  - get_db()   : open a connection
  - init_db()  : create tables from schema.sql
  - seed_db()  : populate default exercises and skills (runs once only)
"""

import sqlite3

DATABASE = 'workouts.db'


# ── Connection ────────────────────────────────────────────────────────────

def get_db():
    """Open a database connection.
    Rows come back as sqlite3.Row objects, so you can access columns by name:
        row['name']  instead of  row[0]
    Foreign key enforcement is turned on — this prevents orphaned records.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Schema ────────────────────────────────────────────────────────────────

def init_db():
    """Create all tables if they don't already exist.
    Safe to call every time the app starts."""
    conn = get_db()
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("[DB] Tables ready.")


# ── Seed data ─────────────────────────────────────────────────────────────
# Default exercises and skills loaded on first run.
# Edit these lists freely — just delete workouts.db and restart to re-seed.

MUSCLE_GROUPS = [
    'Chest', 'Back', 'Shoulders', 'Biceps', 'Triceps',
    'Core', 'Hip Flexors', 'Quads', 'Hamstrings', 'Glutes', 'Calves', 'Forearms',
]

# Format: (name, category, push_pull, [(muscle_name, role), ...])
# push_pull drives the imbalance calculator — tag everything carefully.
EXERCISES = [
    # ── Push ────────────────────────────────────────────────────────────────
    ('Push-up',
        'strength', 'push',
        [('Chest', 'primary'), ('Triceps', 'primary'), ('Shoulders', 'secondary')]),
    ('Pike Push-up',
        'strength', 'push',
        [('Shoulders', 'primary'), ('Triceps', 'secondary')]),
    ('Dip',
        'strength', 'push',
        [('Chest', 'primary'), ('Triceps', 'primary'), ('Shoulders', 'secondary')]),
    ('Diamond Push-up',
        'strength', 'push',
        [('Triceps', 'primary'), ('Chest', 'secondary')]),
    ('Handstand Push-up',
        'strength', 'push',
        [('Shoulders', 'primary'), ('Triceps', 'secondary')]),

    # ── Pull ────────────────────────────────────────────────────────────────
    ('Pull-up',
        'strength', 'pull',
        [('Back', 'primary'), ('Biceps', 'secondary'), ('Forearms', 'secondary')]),
    ('Chin-up',
        'strength', 'pull',
        [('Biceps', 'primary'), ('Back', 'primary'), ('Forearms', 'secondary')]),
    ('Australian Row',
        'strength', 'pull',
        [('Back', 'primary'), ('Biceps', 'secondary')]),
    ('Archer Pull-up',
        'strength', 'pull',
        [('Back', 'primary'), ('Biceps', 'primary')]),

    # ── Core ────────────────────────────────────────────────────────────────
    ('Hollow Body Hold',
        'strength', 'core',
        [('Core', 'primary')]),
    ('Plank',
        'strength', 'core',
        [('Core', 'primary'), ('Shoulders', 'secondary')]),
    ('Leg Raises',
        'strength', 'core',
        [('Core', 'primary'), ('Hip Flexors', 'primary')]),
    ('Dragon Flag',
        'strength', 'core',
        [('Core', 'primary'), ('Hip Flexors', 'secondary')]),
    ('L-sit',
        'strength', 'core',
        [('Core', 'primary'), ('Hip Flexors', 'primary'), ('Triceps', 'secondary')]),

    # ── Legs ────────────────────────────────────────────────────────────────
    ('Squat',
        'strength', 'legs',
        [('Quads', 'primary'), ('Glutes', 'primary'), ('Hamstrings', 'secondary')]),
    ('Bulgarian Split Squat',
        'strength', 'legs',
        [('Quads', 'primary'), ('Glutes', 'primary')]),
    ('Pistol Squat',
        'strength', 'legs',
        [('Quads', 'primary'), ('Glutes', 'secondary')]),
    ('Glute Bridge',
        'strength', 'legs',
        [('Glutes', 'primary'), ('Hamstrings', 'primary')]),
    ('Calf Raise',
        'strength', 'legs',
        [('Calves', 'primary')]),
    ('Nordic Curl',
        'strength', 'legs',
        [('Hamstrings', 'primary')]),
]

# Format: (name, description, [(stage_name, stage_order, description), ...])
# Stages run from easiest (1) to hardest.
SKILLS = [
    ('Front Lever',
     'A horizontal pulling hold with the body parallel to the ground.',
     [
         ('Tuck',          1, 'Knees pulled to chest, hips at 90°'),
         ('Advanced Tuck', 2, 'Hips extended, knees still tucked'),
         ('Single Leg',    3, 'One leg extended, one tucked'),
         ('Straddle',      4, 'Both legs extended and spread wide'),
         ('Full',          5, 'Both legs together, fully extended'),
     ]),

    ('Planche',
     'A horizontal pushing hold with the body parallel to the ground.',
     [
         ('Planche Lean',  1, 'Straight-arm push-up position, leaning forward over hands'),
         ('Tuck Planche',  2, 'Knees pulled to chest, feet off the ground'),
         ('Advanced Tuck', 3, 'Hips extended, knees still tucked'),
         ('Straddle',      4, 'Both legs extended and spread wide'),
         ('Full Planche',  5, 'Both legs together, fully extended'),
     ]),

    ('Handstand',
     'A freestanding balance on two hands.',
     [
         ('Wall Handstand',        1, 'Chest-to-wall or back-to-wall hold'),
         ('Kick-up Practice',      2, 'Consistently getting into a freestanding handstand'),
         ('5s Freestanding Hold',  3, 'Hold a freestanding handstand for 5 seconds'),
         ('15s Freestanding Hold', 4, 'Hold a freestanding handstand for 15 seconds'),
         ('30s Freestanding Hold', 5, 'Hold a freestanding handstand for 30 seconds'),
     ]),

    ('Muscle-up',
     'A pull-up that transitions above the bar into a dip.',
     [
         ('High Pull-up',       1, 'Pull-up with chest to bar'),
         ('Negative Muscle-up', 2, 'Controlled descent from above the bar'),
         ('Kipping Muscle-up',  3, 'Using momentum to get above the bar'),
         ('Strict Muscle-up',   4, 'No kipping, controlled transition'),
         ('Weighted Muscle-up', 5, 'Strict muscle-up with added weight'),
     ]),

    ('L-sit to Handstand',
     'A pressing skill transitioning from a static L-sit hold to a handstand.',
     [
         ('L-sit Hold',              1, 'Static L-sit hold for 10+ seconds'),
         ('Tuck Press Practice',     2, 'Pressing from L-sit through tuck toward handstand'),
         ('Straddle Press',          3, 'Pressing through straddle position to handstand'),
         ('Half Press',              4, 'Controlled press halfway to handstand'),
         ('Full L-sit to Handstand', 5, 'Complete unbroken press from L-sit to handstand'),
     ]),
]


def seed_db():
    """Populate the database with default exercises and skills.
    Checks if data already exists before inserting — safe to call every startup."""
    conn = get_db()

    if conn.execute('SELECT COUNT(*) FROM exercises').fetchone()[0] > 0:
        print("[DB] Already seeded — skipping.")
        conn.close()
        return

    # Insert muscle groups
    for name in MUSCLE_GROUPS:
        conn.execute('INSERT INTO muscle_groups (name) VALUES (?)', (name,))
    conn.commit()

    # Build a name → id lookup so we don't need to hardcode IDs
    mg_lookup = {
        row['name']: row['id']
        for row in conn.execute('SELECT id, name FROM muscle_groups').fetchall()
    }

    # Insert exercises and their muscle group links
    for name, category, push_pull, muscles in EXERCISES:
        cursor = conn.execute(
            'INSERT INTO exercises (name, category, push_pull) VALUES (?, ?, ?)',
            (name, category, push_pull)
        )
        ex_id = cursor.lastrowid
        for muscle_name, role in muscles:
            conn.execute(
                'INSERT INTO exercise_muscles (exercise_id, muscle_group_id, role) '
                'VALUES (?, ?, ?)',
                (ex_id, mg_lookup[muscle_name], role)
            )
    conn.commit()

    # Insert skills and their progression stages
    for skill_name, skill_desc, stages in SKILLS:
        cursor = conn.execute(
            'INSERT INTO skills (name, description) VALUES (?, ?)',
            (skill_name, skill_desc)
        )
        skill_id = cursor.lastrowid
        for stage_name, stage_order, stage_desc in stages:
            conn.execute(
                'INSERT INTO skill_progressions '
                '(skill_id, stage_name, stage_order, description) VALUES (?, ?, ?, ?)',
                (skill_id, stage_name, stage_order, stage_desc)
            )
    conn.commit()
    conn.close()
    print("[DB] Seeded with default exercises and skills.")
