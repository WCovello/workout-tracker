-- schema.sql
-- Defines every table in the database.
-- Uses CREATE TABLE IF NOT EXISTS throughout, so this file is safe to re-run
-- without destroying existing data.

-- ── Reference tables ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS muscle_groups (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- ── Exercise library ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS exercises (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    -- 'strength' = sets/reps exercise. 'skill' = reserved for future use.
    category   TEXT    NOT NULL CHECK(category IN ('strength', 'skill')),
    -- Used for push/pull balance calculations
    push_pull  TEXT    CHECK(push_pull IN ('push', 'pull', 'legs', 'core', 'other')),
    notes      TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Links each exercise to the muscle groups it works
CREATE TABLE IF NOT EXISTS exercise_muscles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id     INTEGER NOT NULL REFERENCES exercises(id)      ON DELETE CASCADE,
    muscle_group_id INTEGER NOT NULL REFERENCES muscle_groups(id),
    role            TEXT    NOT NULL CHECK(role IN ('primary', 'secondary'))
);

-- ── Workout templates ─────────────────────────────────────────────────────

-- A template is a saved workout you can load at the start of a session.
-- Think of it as the plan; a session is the execution.
CREATE TABLE IF NOT EXISTS workout_templates (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    notes      TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- The exercises within a template, with target rep ranges for double progression
CREATE TABLE IF NOT EXISTS template_exercises (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id      INTEGER NOT NULL REFERENCES workout_templates(id) ON DELETE CASCADE,
    exercise_id      INTEGER NOT NULL REFERENCES exercises(id),
    order_position   INTEGER NOT NULL,   -- controls display order in the template
    target_sets      INTEGER,
    target_reps_min  INTEGER,            -- lower bound of the rep range, e.g. 6
    target_reps_max  INTEGER,            -- upper bound of the rep range, e.g. 10
    target_weight_kg REAL                -- current working weight; updated as you progress
);

-- ── Logged sessions ───────────────────────────────────────────────────────

-- One completed workout. template_id is nullable — you can log freely
-- without needing a template.
CREATE TABLE IF NOT EXISTS sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id      INTEGER REFERENCES workout_templates(id),
    name             TEXT NOT NULL,
    date             DATE NOT NULL DEFAULT CURRENT_DATE,
    duration_minutes INTEGER,
    notes            TEXT,
    completed_at     DATETIME,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Individual sets within a session
CREATE TABLE IF NOT EXISTS sets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    set_number  INTEGER NOT NULL,
    reps        INTEGER,
    weight_kg   REAL,
    -- RPE (Rate of Perceived Exertion): 1–10 scale, optional.
    -- Useful later for auto-regulating when to add load.
    rpe         INTEGER CHECK(rpe BETWEEN 1 AND 10),
    notes       TEXT,
    logged_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Skill tracking ────────────────────────────────────────────────────────

-- A calisthenics skill with a defined progression ladder (e.g. Front Lever)
CREATE TABLE IF NOT EXISTS skills (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- The individual stages on a skill's progression ladder
-- (e.g. Tuck → Advanced Tuck → Straddle → Full)
CREATE TABLE IF NOT EXISTS skill_progressions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id    INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    stage_name  TEXT    NOT NULL,
    stage_order INTEGER NOT NULL,  -- 1 = easiest, ascending to hardest
    description TEXT
);

-- One logged attempt at a skill stage
CREATE TABLE IF NOT EXISTS skill_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id       INTEGER NOT NULL REFERENCES skills(id),
    progression_id INTEGER NOT NULL REFERENCES skill_progressions(id),
    date           DATE NOT NULL DEFAULT CURRENT_DATE,
    hold_seconds   REAL,       -- for static holds (front lever, planche, etc.)
    quality        INTEGER CHECK(quality BETWEEN 1 AND 5),  -- for dynamic skills (muscle-up)
    notes          TEXT,
    logged_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Nutrition: food database ──────────────────────────────────────────────

-- A single food or branded product. All nutrient values are per 100g,
-- matching how nutrition labels are standardized — actual intake gets
-- calculated later by scaling these against the weight actually logged.
CREATE TABLE IF NOT EXISTS foods (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    brand           TEXT,                       -- nullable: generic foods have no brand
    calories        REAL    NOT NULL,            -- kcal per 100g
    protein_g       REAL    NOT NULL DEFAULT 0,
    carbs_g         REAL    NOT NULL DEFAULT 0,
    fat_g           REAL    NOT NULL DEFAULT 0,
    saturated_fat_g REAL,
    trans_fat_g     REAL,
    fiber_g         REAL,
    sugar_g         REAL,
    sodium_mg       REAL,
    cholesterol_mg  REAL,
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, brand)
);

-- ── Nutrition: calorie goals ──────────────────────────────────────────────

-- Your daily calorie (and optionally macro) target. Goals are logged with
-- a start date instead of overwritten, so past goals stay visible in
-- history even after you change them — useful once you're cutting one
-- month and bulking the next.
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    servings REAL NOT NULL CHECK(servings > 0),
    instructions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    food_id INTEGER NOT NULL REFERENCES foods(id),
    grams REAL NOT NULL CHECK(grams > 0)
);

-- Snapshot nutrition at logging time so later recipe edits cannot alter history.
CREATE TABLE IF NOT EXISTS recipe_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    date DATE NOT NULL,
    servings REAL NOT NULL CHECK(servings > 0),
    calories REAL NOT NULL,
    protein_g REAL NOT NULL,
    carbs_g REAL NOT NULL,
    fat_g REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS recipe_logs_date ON recipe_logs(date);

CREATE TABLE IF NOT EXISTS starter_meal_imports (
    slug TEXT PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS calorie_goals (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    daily_calories       INTEGER NOT NULL,
    protein_g            INTEGER,
    carbs_g              INTEGER,
    fat_g                INTEGER,
    -- Calculator inputs, nullable — a manually-typed goal won't have these
    sex                  TEXT    CHECK(sex IN ('male', 'female')),
    age                  INTEGER,
    height_cm            REAL,
    weight_kg            REAL,
    body_fat_pct         REAL,     -- optional; switches the calc to Katch-McArdle
    activity_multiplier  REAL,
    goal                 TEXT    CHECK(goal IN ('lose', 'maintain', 'gain')),
    weekly_rate_lb       REAL,     -- null when goal = 'maintain'
    start_date           DATE    NOT NULL DEFAULT CURRENT_DATE,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);
