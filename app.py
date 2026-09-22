from collections import defaultdict
import datetime
import calendar

"""
app.py — Main Flask application
All web routes live here. Database logic lives in database.py.
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from database import init_db, seed_db, get_db
from collections import defaultdict
import datetime

app = Flask(__name__)
app.secret_key = 'wt-dev-2025'   # Required for flash messages

init_db()
seed_db()


# ═══════════════════════════════════════════════════════════════════════════
# HOME
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    conn = get_db()
    recent = conn.execute('''
        SELECT s.id, s.name, s.date, s.duration_minutes,
               COUNT(DISTINCT se.exercise_id) as ex_count,
               COUNT(se.id) as set_count
        FROM sessions s
        LEFT JOIN sets se ON se.session_id = s.id
        GROUP BY s.id
        ORDER BY s.date DESC, s.created_at DESC
        LIMIT 5
    ''').fetchall()

    today = datetime.date.today()
    cal = calendar.Calendar(firstweekday=6)  # Sunday-first
    month_weeks = cal.monthdayscalendar(today.year, today.month)

    month_sessions = conn.execute('''
        SELECT id, name, date FROM sessions
        WHERE strftime('%Y-%m', date) = ?
        ORDER BY date, created_at, id
    ''', (today.strftime('%Y-%m'),)).fetchall()
    conn.close()

    # Keyed by day-of-month; each value is a dict of categories.
    # 'sessions' today — 'meals' or anything else slots in the same way
    # once those features exist, with no change to this structure.
    calendar_days = defaultdict(dict)
    for s in month_sessions:
        day_num = int(s['date'][8:10])
        calendar_days[day_num].setdefault('sessions', []).append(
            {'id': s['id'], 'name': s['name']}
        )
    calendar_days = dict(calendar_days)  # plain dict — avoids defaultdict surprises in the template

    return render_template(
        'index.html', recent=recent,
        month_weeks=month_weeks, calendar_days=calendar_days,
        today_day=today.day, month_name=today.strftime('%B %Y')
    )


# ═══════════════════════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/templates')
def templates_list():
    conn = get_db()
    templates = conn.execute('''
        SELECT t.id, t.name, t.notes, COUNT(te.id) as ex_count
        FROM workout_templates t
        LEFT JOIN template_exercises te ON te.template_id = t.id
        GROUP BY t.id ORDER BY t.name
    ''').fetchall()
    conn.close()
    return render_template('templates_list.html', templates=templates)


@app.route('/templates/new', methods=['GET', 'POST'])
def template_new():
    if request.method == 'POST':
        name  = request.form['name'].strip()
        notes = request.form.get('notes', '').strip() or None
        if not name:
            flash('Name is required.')
            return redirect(url_for('template_new'))
        conn = get_db()
        cur  = conn.execute(
            'INSERT INTO workout_templates (name, notes) VALUES (?, ?)', (name, notes)
        )
        tid = cur.lastrowid
        conn.commit()
        conn.close()
        flash(f'"{name}" created. Now add exercises to it.')
        return redirect(url_for('template_view', template_id=tid))
    return render_template('template_new.html')


@app.route('/templates/<int:template_id>')
def template_view(template_id):
    conn = get_db()
    tmpl = conn.execute(
        'SELECT * FROM workout_templates WHERE id = ?', (template_id,)
    ).fetchone()
    if not tmpl:
        flash('Template not found.')
        return redirect(url_for('templates_list'))
    exercises = conn.execute('''
        SELECT te.id as te_id, te.order_position,
               te.target_sets, te.target_reps_min, te.target_reps_max, te.target_weight_kg,
               e.id as exercise_id, e.name, e.push_pull
        FROM template_exercises te
        JOIN exercises e ON e.id = te.exercise_id
        WHERE te.template_id = ?
        ORDER BY te.order_position
    ''', (template_id,)).fetchall()
    conn.close()
    return render_template('template_view.html', tmpl=tmpl, exercises=exercises)


@app.route('/templates/<int:template_id>/add-exercise', methods=['GET', 'POST'])
def template_add_exercise(template_id):
    conn = get_db()
    tmpl = conn.execute(
        'SELECT * FROM workout_templates WHERE id = ?', (template_id,)
    ).fetchone()
    if not tmpl:
        flash('Template not found.')
        return redirect(url_for('templates_list'))

    if request.method == 'POST':
        ex_id  = request.form.get('exercise_id', type=int)
        t_sets = request.form.get('target_sets',     type=int)
        t_min  = request.form.get('target_reps_min', type=int)
        t_max  = request.form.get('target_reps_max', type=int)
        t_wt   = request.form.get('target_weight_kg', type=float)

        max_pos = conn.execute(
            'SELECT COALESCE(MAX(order_position), 0) FROM template_exercises WHERE template_id = ?',
            (template_id,)
        ).fetchone()[0]

        conn.execute('''
            INSERT INTO template_exercises
            (template_id, exercise_id, order_position,
             target_sets, target_reps_min, target_reps_max, target_weight_kg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (template_id, ex_id, max_pos + 1, t_sets, t_min, t_max, t_wt))
        conn.commit()
        conn.close()
        flash('Exercise added.')
        return redirect(url_for('template_view', template_id=template_id))

    # Convert to dicts so Jinja2 selectattr works correctly
    all_exercises = [dict(r) for r in conn.execute(
        'SELECT id, name, push_pull FROM exercises ORDER BY push_pull, name'
    ).fetchall()]
    conn.close()
    return render_template('template_add_exercise.html',
                           tmpl=tmpl, all_exercises=all_exercises)


@app.route('/templates/<int:template_id>/remove-exercise/<int:te_id>', methods=['POST'])
def template_remove_exercise(template_id, te_id):
    conn = get_db()
    conn.execute(
        'DELETE FROM template_exercises WHERE id = ? AND template_id = ?',
        (te_id, template_id)
    )
    conn.commit()
    conn.close()
    flash('Exercise removed.')
    return redirect(url_for('template_view', template_id=template_id))

@app.route('/templates/<int:template_id>/move-exercise/<int:te_id>/<direction>',
           methods=['POST'])
def template_move_exercise(template_id, te_id, direction):
    """Move an exercise one position up or down within a template.
    Works by swapping order_position values between adjacent rows."""
    conn = get_db()

    # Get the exercise being moved
    current = conn.execute(
        'SELECT id, order_position FROM template_exercises WHERE id = ? AND template_id = ?',
        (te_id, template_id)
    ).fetchone()

    if not current:
        flash('Exercise not found.')
        conn.close()
        return redirect(url_for('template_view', template_id=template_id))

    pos = current['order_position']

    # Find the neighbour to swap with
    if direction == 'up':
        neighbour = conn.execute(
            '''SELECT id, order_position FROM template_exercises
               WHERE template_id = ? AND order_position < ?
               ORDER BY order_position DESC LIMIT 1''',
            (template_id, pos)
        ).fetchone()
    else:
        neighbour = conn.execute(
            '''SELECT id, order_position FROM template_exercises
               WHERE template_id = ? AND order_position > ?
               ORDER BY order_position ASC LIMIT 1''',
            (template_id, pos)
        ).fetchone()

    if neighbour:
        # Swap the two order_position values
        conn.execute(
            'UPDATE template_exercises SET order_position = ? WHERE id = ?',
            (neighbour['order_position'], te_id)
        )
        conn.execute(
            'UPDATE template_exercises SET order_position = ? WHERE id = ?',
            (pos, neighbour['id'])
        )
        conn.commit()

    conn.close()
    return redirect(url_for('template_view', template_id=template_id))

# ═══════════════════════════════════════════════════════════════════════════
# WORKOUTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/workout/start', methods=['GET', 'POST'])
def workout_start():
    conn  = get_db()
    templates = conn.execute(
        'SELECT id, name FROM workout_templates ORDER BY name'
    ).fetchall()

    if request.method == 'POST':
        tid   = request.form.get('template_id', type=int) or None
        today = datetime.date.today()

        if tid:
            row  = conn.execute('SELECT name FROM workout_templates WHERE id = ?', (tid,)).fetchone()
            name = row['name'] if row else f'Workout — {today.strftime("%d %b %Y")}'
        else:
            name = (request.form.get('name', '').strip()
                    or f'Workout — {today.strftime("%d %b %Y")}')

        cur = conn.execute(
            'INSERT INTO sessions (template_id, name, date) VALUES (?, ?, ?)',
            (tid, name, today.isoformat())
        )
        sid = cur.lastrowid
        conn.commit()
        conn.close()
        return redirect(url_for('workout_active', session_id=sid))

    conn.close()
    return render_template('workout_start.html', templates=templates)


@app.route('/workout/<int:session_id>')
def workout_active(session_id):
    conn = get_db()

    sess = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if not sess:
        flash('Session not found.')
        return redirect(url_for('history'))

    # Exercises from the template (shown even before any sets are logged)
    tmpl_exercises = []
    if sess['template_id']:
        tmpl_exercises = conn.execute('''
            SELECT e.id as exercise_id, e.name,
                   te.id as te_id, te.target_sets,
                   te.target_reps_min, te.target_reps_max, te.target_weight_kg
            FROM template_exercises te
            JOIN exercises e ON e.id = te.exercise_id
            WHERE te.template_id = ?
            ORDER BY te.order_position
        ''', (sess['template_id'],)).fetchall()

    # All sets logged so far, grouped by exercise_id
    all_sets = conn.execute('''
        SELECT s.*, e.name as exercise_name
        FROM sets s
        JOIN exercises e ON e.id = s.exercise_id
        WHERE s.session_id = ?
        ORDER BY s.exercise_id, s.set_number
    ''', (session_id,)).fetchall()

    sets_by_ex = defaultdict(list)
    for s in all_sets:
        sets_by_ex[s['exercise_id']].append(dict(s))

    # Last logged set per exercise — used to pre-fill the "Add Set" form
    last_set_by_ex = {eid: sl[-1] for eid, sl in sets_by_ex.items() if sl}

    # Exercises logged in this session that aren't in the template
    tmpl_ex_ids = {te['exercise_id'] for te in tmpl_exercises}
    extra_exercises = []
    for eid in sets_by_ex:
        if eid not in tmpl_ex_ids:
            ex = conn.execute('SELECT id, name FROM exercises WHERE id = ?', (eid,)).fetchone()
            if ex:
                extra_exercises.append(ex)

    # "Pending" exercise: just selected via Add Exercise, no sets yet
    pending_id = request.args.get('pending_ex', type=int)
    pending_exercise = None
    if pending_id:
        if pending_id in tmpl_ex_ids:
            flash('That exercise is already in your template. Use the form below it.')
        elif pending_id not in sets_by_ex:
            pending_exercise = conn.execute(
                'SELECT id, name FROM exercises WHERE id = ?', (pending_id,)
            ).fetchone()

    # Exercise dropdown: exclude exercises already in the template
    dropdown_exercises = [dict(r) for r in conn.execute(
        'SELECT id, name, push_pull FROM exercises ORDER BY push_pull, name'
    ).fetchall() if r['id'] not in tmpl_ex_ids]

    conn.close()
    return render_template('workout_active.html',
        sess=sess,
        tmpl_exercises=tmpl_exercises,
        extra_exercises=extra_exercises,
        pending_exercise=pending_exercise,
        sets_by_ex=dict(sets_by_ex),
        last_set_by_ex=last_set_by_ex,
        dropdown_exercises=dropdown_exercises
    )


@app.route('/workout/<int:session_id>/add-set', methods=['POST'])
def workout_add_set(session_id):
    ex_id  = request.form.get('exercise_id', type=int)
    reps   = request.form.get('reps',        type=int)
    weight = request.form.get('weight_kg',   type=float) or 0.0

    if not ex_id or reps is None:
        flash('Exercise and reps are required.')
        return redirect(url_for('workout_active', session_id=session_id))

    conn = get_db()
    last = conn.execute('''
        SELECT COALESCE(MAX(set_number), 0) as m
        FROM sets WHERE session_id = ? AND exercise_id = ?
    ''', (session_id, ex_id)).fetchone()

    conn.execute('''
        INSERT INTO sets (session_id, exercise_id, set_number, reps, weight_kg)
        VALUES (?, ?, ?, ?, ?)
    ''', (session_id, ex_id, last['m'] + 1, reps, weight))
    conn.commit()
    conn.close()
    return redirect(url_for('workout_active', session_id=session_id))


@app.route('/workout/<int:session_id>/delete-set/<int:set_id>', methods=['POST'])
def workout_delete_set(session_id, set_id):
    conn = get_db()
    conn.execute('DELETE FROM sets WHERE id = ? AND session_id = ?', (set_id, session_id))
    conn.commit()
    conn.close()
    return redirect(url_for('workout_active', session_id=session_id))


@app.route('/workout/<int:session_id>/add-exercise', methods=['POST'])
def workout_add_exercise(session_id):
    """Show an exercise's add-set form without logging anything yet."""
    ex_id = request.form.get('exercise_id', type=int)
    if not ex_id:
        flash('Please select an exercise.')
        return redirect(url_for('workout_active', session_id=session_id))
    return redirect(url_for('workout_active', session_id=session_id, pending_ex=ex_id))


@app.route('/workout/<int:session_id>/finish', methods=['POST'])
def workout_finish(session_id):
    duration = request.form.get('duration', type=int)
    notes    = request.form.get('notes', '').strip() or None
    conn = get_db()
    conn.execute(
        'UPDATE sessions SET duration_minutes = ?, notes = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?',
        (duration, notes, session_id)
    )
    conn.commit()
    conn.close()
    flash('Workout saved.')
    return redirect(url_for('session_view', session_id=session_id))


# ═══════════════════════════════════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/history')
def history():
    conn = get_db()
    sessions = conn.execute('''
        SELECT s.id, s.name, s.date, s.duration_minutes,
               COUNT(DISTINCT se.exercise_id) as ex_count,
               COUNT(se.id) as set_count
        FROM sessions s
        LEFT JOIN sets se ON se.session_id = s.id
        GROUP BY s.id
        ORDER BY s.date DESC, s.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('history.html', sessions=sessions)


@app.route('/history/<int:session_id>')
def session_view(session_id):
    conn = get_db()
    sess = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
    if not sess:
        flash('Session not found.')
        return redirect(url_for('history'))

    all_sets = conn.execute('''
        SELECT s.*, e.name as exercise_name
        FROM sets s
        JOIN exercises e ON e.id = s.exercise_id
        WHERE s.session_id = ?
        ORDER BY s.exercise_id, s.set_number
    ''', (session_id,)).fetchall()

    exercises_seen = []
    ex_ids_seen    = set()
    sets_by_ex     = defaultdict(list)
    for s in all_sets:
        eid = s['exercise_id']
        if eid not in ex_ids_seen:
            exercises_seen.append({'id': eid, 'name': s['exercise_name']})
            ex_ids_seen.add(eid)
        sets_by_ex[eid].append(dict(s))

    conn.close()
    return render_template('session_view.html',
        sess=sess,
        exercises=exercises_seen,
        sets_by_ex=dict(sets_by_ex)
    )

@app.route('/history/<int:session_id>/delete', methods=['POST'])
def session_delete(session_id):
    """Permanently delete a session and all its logged sets.
    The ON DELETE CASCADE on the sets table handles set deletion automatically."""
    conn = get_db()
    # Confirm session exists before deleting
    sess = conn.execute(
        'SELECT name FROM sessions WHERE id = ?', (session_id,)
    ).fetchone()
    if sess:
        conn.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        conn.commit()
        flash(f'"{sess["name"]}" deleted.')
    conn.close()
    return redirect(url_for('history'))


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/dashboard')
def dashboard():
    conn    = get_db()
    today   = datetime.date.today()
    week_ago = (today - datetime.timedelta(days=7)).isoformat()

    # ── Workouts this week ────────────────────────────────────────────────
    workout_count = conn.execute(
        'SELECT COUNT(*) FROM sessions WHERE date >= ?', (week_ago,)
    ).fetchone()[0]

    total_sets = conn.execute('''
        SELECT COUNT(se.id) FROM sets se
        JOIN sessions s ON s.id = se.session_id
        WHERE s.date >= ?
    ''', (week_ago,)).fetchone()[0]

    # ── Volume by push/pull category ──────────────────────────────────────
    cat_rows = conn.execute('''
        SELECT e.push_pull, COUNT(se.id) as set_count
        FROM sets se
        JOIN sessions s  ON s.id  = se.session_id
        JOIN exercises e ON e.id  = se.exercise_id
        WHERE s.date >= ? AND e.push_pull IS NOT NULL
        GROUP BY e.push_pull
    ''', (week_ago,)).fetchall()

    cat_volume  = {r['push_pull']: r['set_count'] for r in cat_rows}
    push_count  = cat_volume.get('push', 0)
    pull_count  = cat_volume.get('pull', 0)
    core_count  = cat_volume.get('core', 0)
    legs_count  = cat_volume.get('legs', 0)
    has_cat_data = any([push_count, pull_count, core_count, legs_count])

    # Push/pull imbalance message
    # Evidence base: since climbing already dominates pull volume, gym
    # training should target ~1:1. Flag if push < 70% of pull sets.
    if push_count > 0 and pull_count > 0:
        ratio = push_count / pull_count
        if ratio < 0.7:
            balance_status = 'warning'
            balance_msg = (
                f'Push volume ({push_count} sets) is low relative to pull '
                f'({pull_count} sets) — ratio {ratio:.2f}:1. '
                f'Climbing already loads pulling heavily; aim for closer to '
                f'1:1 push:pull in your gym sessions.'
            )
        elif ratio > 1.5:
            balance_status = 'warning'
            balance_msg = (
                f'Push volume ({push_count} sets) is notably higher than pull '
                f'({pull_count} sets) — ratio {ratio:.2f}:1. '
                f'Consider whether pull volume matches your climbing demands.'
            )
        else:
            balance_status = 'ok'
            balance_msg = (
                f'Push/pull balance looks good — {push_count} push sets, '
                f'{pull_count} pull sets (ratio {ratio:.2f}:1).'
            )
    elif push_count == 0 and pull_count > 0:
        balance_status = 'warning'
        balance_msg    = f'No push work logged in the last 7 days ({pull_count} pull sets recorded).'
    elif pull_count == 0 and push_count > 0:
        balance_status = 'warning'
        balance_msg    = f'No pull work logged in the last 7 days ({push_count} push sets recorded).'
    else:
        balance_status = None
        balance_msg    = None

    cat_chart = {
        'labels': ['Push', 'Pull', 'Core', 'Legs'],
        'datasets': [{
            'label': 'Sets',
            'data':  [push_count, pull_count, core_count, legs_count],
            'backgroundColor': ['#2563eb', '#dc2626', '#16a34a', '#d97706'],
        }]
    }

    # ── Volume by primary muscle group ────────────────────────────────────
    muscle_rows = conn.execute('''
        SELECT mg.name, COUNT(se.id) as set_count
        FROM sets se
        JOIN sessions s       ON s.id  = se.session_id
        JOIN exercise_muscles em ON em.exercise_id = se.exercise_id
                                AND em.role = 'primary'
        JOIN muscle_groups mg ON mg.id = em.muscle_group_id
        WHERE s.date >= ?
        GROUP BY mg.name
        ORDER BY set_count DESC
    ''', (week_ago,)).fetchall()

    muscle_chart = {
        'labels': [r['name']      for r in muscle_rows],
        'datasets': [{
            'label': 'Sets',
            'data':  [r['set_count'] for r in muscle_rows],
            'backgroundColor': '#6366f1',
        }]
    }

    # ── Double progression flags ──────────────────────────────────────────
    # Rule: if ALL sets in BOTH of the last 2 sessions for an exercise
    # reached target_reps_max, it's time to increase weight.
    te_rows = conn.execute('''
        SELECT te.template_id, te.exercise_id,
               te.target_reps_max, te.target_weight_kg,
               e.name  as exercise_name,
               t.name  as template_name
        FROM template_exercises te
        JOIN exercises          e ON e.id = te.exercise_id
        JOIN workout_templates  t ON t.id = te.template_id
        WHERE te.target_reps_max IS NOT NULL
    ''').fetchall()

    progression_flags = []
    for te in te_rows:
        # Last 2 sessions using this template that logged this exercise
        sessions = conn.execute('''
            SELECT DISTINCT s.id, s.date
            FROM sessions s
            JOIN sets se ON se.session_id = s.id
            WHERE s.template_id = ? AND se.exercise_id = ?
            ORDER BY s.date DESC, s.created_at DESC
            LIMIT 2
        ''', (te['template_id'], te['exercise_id'])).fetchall()

        if len(sessions) < 2:
            continue

        # Both sessions must have every set >= target_reps_max
        ready = True
        for sess in sessions:
            sets = conn.execute('''
                SELECT reps FROM sets
                WHERE session_id = ? AND exercise_id = ?
            ''', (sess['id'], te['exercise_id'])).fetchall()

            if not sets:
                ready = False
                break
            if not all(s['reps'] >= te['target_reps_max'] for s in sets):
                ready = False
                break

        if ready:
            progression_flags.append({
                'exercise_name': te['exercise_name'],
                'template_name': te['template_name'],
                'current_weight': te['target_weight_kg'],
                'target_reps_max': te['target_reps_max'],
            })

    conn.close()
    return render_template('dashboard.html',
        workout_count     = workout_count,
        total_sets        = total_sets,
        balance_status    = balance_status,
        balance_msg       = balance_msg,
        cat_chart         = cat_chart,
        muscle_chart      = muscle_chart,
        progression_flags = progression_flags,
        has_cat_data      = has_cat_data,
        has_muscle_data   = bool(muscle_rows),
        week_ago          = week_ago,
        today             = today.isoformat(),
    )


# ═══════════════════════════════════════════════════════════════════════════
# SKILLS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/skills')
def skills_list():
    conn = get_db()
    skills = conn.execute('''
        SELECT s.id, s.name, s.description,
               COUNT(DISTINCT sp.id) as stage_count,
               COUNT(sl.id)          as log_count
        FROM skills s
        LEFT JOIN skill_progressions sp ON sp.skill_id = s.id
        LEFT JOIN skill_logs sl         ON sl.skill_id = s.id
        GROUP BY s.id
        ORDER BY s.name
    ''').fetchall()

    # Current stage per skill = most recently logged stage
    current_stages = {}
    for skill in skills:
        row = conn.execute('''
            SELECT sp.stage_name
            FROM skill_logs sl
            JOIN skill_progressions sp ON sp.id = sl.progression_id
            WHERE sl.skill_id = ?
            ORDER BY sl.date DESC, sl.logged_at DESC
            LIMIT 1
        ''', (skill['id'],)).fetchone()
        current_stages[skill['id']] = row['stage_name'] if row else None

    conn.close()
    return render_template('skills_list.html', skills=skills, current_stages=current_stages)


@app.route('/skills/new', methods=['GET', 'POST'])
def skill_new():
    if request.method == 'POST':
        name        = request.form['name'].strip()
        description = request.form.get('description', '').strip() or None
        if not name:
            flash('Name is required.')
            return redirect(url_for('skill_new'))
        conn = get_db()
        if conn.execute('SELECT id FROM skills WHERE LOWER(name) = LOWER(?)', (name,)).fetchone():
            flash(f'A skill called "{name}" already exists.')
            conn.close()
            return redirect(url_for('skill_new'))
        cur      = conn.execute('INSERT INTO skills (name, description) VALUES (?, ?)', (name, description))
        skill_id = cur.lastrowid
        conn.commit()
        conn.close()
        flash(f'"{name}" created. Add progression stages below.')
        return redirect(url_for('skill_detail', skill_id=skill_id))
    return render_template('skill_new.html')


@app.route('/skills/<int:skill_id>')
def skill_detail(skill_id):
    conn  = get_db()
    skill = conn.execute('SELECT * FROM skills WHERE id = ?', (skill_id,)).fetchone()
    if not skill:
        flash('Skill not found.')
        return redirect(url_for('skills_list'))

    stages = conn.execute(
        'SELECT * FROM skill_progressions WHERE skill_id = ? ORDER BY stage_order',
        (skill_id,)
    ).fetchall()

    logs = conn.execute('''
        SELECT sl.id, sl.date, sl.hold_seconds, sl.quality, sl.notes,
               sp.id as progression_id, sp.stage_name, sp.stage_order
        FROM skill_logs sl
        JOIN skill_progressions sp ON sp.id = sl.progression_id
        WHERE sl.skill_id = ?
        ORDER BY sl.date DESC, sl.logged_at DESC
    ''', (skill_id,)).fetchall()

    current_stage = logs[0]['stage_name'] if logs else None

    # ── Chart data ───────────────────────────────────────────────────────
    # One dataset (line) per stage that has been logged, X = date, Y = hold secs
    colors     = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed']
    all_dates  = sorted(set(r['date'] for r in logs)) if logs else []
    datasets   = []

    for i, stage in enumerate(stages):
        stage_logs = [r for r in logs if r['progression_id'] == stage['id']]
        if not stage_logs:
            continue

        date_to_val = {}
        for r in stage_logs:
            val = r['hold_seconds'] if r['hold_seconds'] is not None else r['quality']
            if val is not None:
                date_to_val[r['date']] = val

        if date_to_val:
            datasets.append({
                'label':           stage['stage_name'],
                'data':            [date_to_val.get(d) for d in all_dates],
                'borderColor':     colors[i % len(colors)],
                'backgroundColor': colors[i % len(colors)],
                'spanGaps':        False,
                'tension':         0.2,
                'pointRadius':     5,
                'fill':            False,
            })

    chart_data = {'labels': all_dates, 'datasets': datasets}

    conn.close()
    return render_template('skill_detail.html',
        skill         = skill,
        stages        = stages,
        logs          = logs,
        current_stage = current_stage,
        chart_data    = chart_data,
        has_chart_data= bool(datasets)
    )


@app.route('/skills/<int:skill_id>/log', methods=['GET', 'POST'])
def skill_log(skill_id):
    conn  = get_db()
    skill = conn.execute('SELECT * FROM skills WHERE id = ?', (skill_id,)).fetchone()
    if not skill:
        flash('Skill not found.')
        return redirect(url_for('skills_list'))

    stages = conn.execute(
        'SELECT * FROM skill_progressions WHERE skill_id = ? ORDER BY stage_order',
        (skill_id,)
    ).fetchall()

    if request.method == 'POST':
        progression_id = request.form.get('progression_id', type=int)
        hold_seconds   = request.form.get('hold_seconds',   type=float) or None
        quality        = request.form.get('quality',        type=int)   or None
        notes          = request.form.get('notes', '').strip() or None
        date           = request.form.get('date') or datetime.date.today().isoformat()

        if not progression_id:
            flash('Please select a stage.')
            conn.close()
            return redirect(url_for('skill_log', skill_id=skill_id))

        conn.execute('''
            INSERT INTO skill_logs
            (skill_id, progression_id, date, hold_seconds, quality, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (skill_id, progression_id, date, hold_seconds, quality, notes))
        conn.commit()
        conn.close()
        flash('Session logged.')
        return redirect(url_for('skill_detail', skill_id=skill_id))

    # Pre-select the most recently logged stage
    last = conn.execute('''
        SELECT progression_id FROM skill_logs
        WHERE skill_id = ?
        ORDER BY date DESC, logged_at DESC LIMIT 1
    ''', (skill_id,)).fetchone()
    default_stage_id = last['progression_id'] if last else (stages[0]['id'] if stages else None)

    conn.close()
    return render_template('skill_log.html',
        skill            = skill,
        stages           = stages,
        default_stage_id = default_stage_id,
        today            = datetime.date.today().isoformat()
    )


@app.route('/skills/<int:skill_id>/delete-log/<int:log_id>', methods=['POST'])
def skill_delete_log(skill_id, log_id):
    conn = get_db()
    conn.execute('DELETE FROM skill_logs WHERE id = ? AND skill_id = ?', (log_id, skill_id))
    conn.commit()
    conn.close()
    return redirect(url_for('skill_detail', skill_id=skill_id))


@app.route('/skills/<int:skill_id>/add-stage', methods=['GET', 'POST'])
def skill_add_stage(skill_id):
    conn  = get_db()
    skill = conn.execute('SELECT * FROM skills WHERE id = ?', (skill_id,)).fetchone()
    if not skill:
        flash('Skill not found.')
        return redirect(url_for('skills_list'))

    if request.method == 'POST':
        stage_name  = request.form['stage_name'].strip()
        description = request.form.get('description', '').strip() or None
        if not stage_name:
            flash('Stage name is required.')
            conn.close()
            return redirect(url_for('skill_add_stage', skill_id=skill_id))

        max_order = conn.execute(
            'SELECT COALESCE(MAX(stage_order), 0) FROM skill_progressions WHERE skill_id = ?',
            (skill_id,)
        ).fetchone()[0]

        conn.execute(
            'INSERT INTO skill_progressions (skill_id, stage_name, stage_order, description) '
            'VALUES (?, ?, ?, ?)',
            (skill_id, stage_name, max_order + 1, description)
        )
        conn.commit()
        conn.close()
        flash(f'Stage "{stage_name}" added.')
        return redirect(url_for('skill_detail', skill_id=skill_id))

    conn.close()
    return render_template('skill_add_stage.html', skill=skill)


# ═══════════════════════════════════════════════════════════════════════════
# EXERCISE LIBRARY
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/exercises')
def exercises_list():
    conn = get_db()
    exercises = conn.execute(
        'SELECT id, name, push_pull FROM exercises ORDER BY push_pull, name'
    ).fetchall()
    conn.close()
    return render_template('exercises_list.html', exercises=exercises)


@app.route('/exercises/new', methods=['GET', 'POST'])
def exercise_new():
    conn = get_db()
    muscle_groups = conn.execute(
        'SELECT id, name FROM muscle_groups ORDER BY name'
    ).fetchall()

    if request.method == 'POST':
        name      = request.form['name'].strip()
        push_pull = request.form['push_pull']
        primary   = request.form.getlist('primary_muscles')    # list of muscle_group ids
        secondary = request.form.getlist('secondary_muscles')  # list of muscle_group ids

        if not name:
            flash('Exercise name is required.')
            conn.close()
            return redirect(url_for('exercise_new'))

        # Prevent duplicates
        existing = conn.execute(
            'SELECT id FROM exercises WHERE LOWER(name) = LOWER(?)', (name,)
        ).fetchone()
        if existing:
            flash(f'An exercise called "{name}" already exists.')
            conn.close()
            return redirect(url_for('exercise_new'))

        cur = conn.execute(
            'INSERT INTO exercises (name, category, push_pull) VALUES (?, ?, ?)',
            (name, 'strength', push_pull)
        )
        ex_id = cur.lastrowid

        for mg_id in primary:
            conn.execute(
                'INSERT INTO exercise_muscles (exercise_id, muscle_group_id, role) '
                'VALUES (?, ?, ?)', (ex_id, int(mg_id), 'primary')
            )
        for mg_id in secondary:
            if mg_id not in primary:   # avoid tagging same muscle twice
                conn.execute(
                    'INSERT INTO exercise_muscles (exercise_id, muscle_group_id, role) '
                    'VALUES (?, ?, ?)', (ex_id, int(mg_id), 'secondary')
                )

        conn.commit()
        conn.close()
        flash(f'"{name}" added to your exercise library.')
        return redirect(url_for('exercises_list'))

    conn.close()
    return render_template('exercise_new.html', muscle_groups=muscle_groups)


# ═══════════════════════════════════════════════════════════════════════════
# DEBUG
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/db-check')
def db_check():
    conn = get_db()
    exercises = conn.execute(
        'SELECT name, push_pull FROM exercises ORDER BY push_pull, name'
    ).fetchall()
    skills = conn.execute('''
        SELECT s.name AS skill, sp.stage_order, sp.stage_name
        FROM skill_progressions sp JOIN skills s ON s.id = sp.skill_id
        ORDER BY s.name, sp.stage_order
    ''').fetchall()
    conn.close()
    ex_rows = ''.join(
        f'<tr><td>{e["name"]}</td><td>{e["push_pull"]}</td></tr>' for e in exercises
    )
    sk_rows = ''.join(
        f'<tr><td>{s["skill"]}</td><td>{s["stage_order"]}</td><td>{s["stage_name"]}</td></tr>'
        for s in skills
    )
    return f'''<h1>DB Check</h1>
    <h2>Exercises ({len(exercises)})</h2>
    <table border="1" cellpadding="4">
        <tr><th>Name</th><th>Category</th></tr>{ex_rows}
    </table>
    <h2>Skills</h2>
    <table border="1" cellpadding="4">
        <tr><th>Skill</th><th>Stage</th><th>Name</th></tr>{sk_rows}
    </table>
    <a href="/">Back</a>'''


# ═══════════════════════════════════════════════════════════════════════════
# NUTRITION
# ═══════════════════════════════════════════════════════════════════════════

ACTIVITY_MULTIPLIERS = {
    'sedentary':          1.2,
    'lightly_active':     1.375,
    'moderately_active':  1.55,
    'very_active':        1.725,
    'extra_active':       1.9,
}


def calculate_calorie_target(weight_kg, activity_multiplier, goal, weekly_rate_lb=None,
                              sex=None, age=None, height_cm=None, body_fat_pct=None):
    """
    Returns (bmr, tdee, target_calories), all rounded to the nearest kcal.
    Uses Katch-McArdle if body_fat_pct is given — which needs neither sex
    nor age — otherwise falls back to Mifflin-St Jeor.
    """
    if body_fat_pct is not None:
        lean_mass_kg = weight_kg * (1 - body_fat_pct / 100)
        bmr = 370 + (21.6 * lean_mass_kg)
    elif sex == 'male':
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    tdee = bmr * activity_multiplier

    if goal == 'maintain' or not weekly_rate_lb:
        target_calories = tdee
    else:
        daily_adjustment = (weekly_rate_lb * 3500) / 7
        target_calories = tdee - daily_adjustment if goal == 'lose' else tdee + daily_adjustment

    return round(bmr), round(tdee), round(target_calories)

@app.route('/foods')
def foods_list():
    conn = get_db()
    foods = conn.execute(
        'SELECT id, name, brand, calories, protein_g, carbs_g, fat_g '
        'FROM foods ORDER BY name'
    ).fetchall()
    conn.close()
    return render_template('foods_list.html', foods=foods)


@app.route('/foods/new', methods=['GET', 'POST'])
def food_new():
    if request.method == 'POST':
        name  = request.form['name'].strip()
        brand = request.form.get('brand', '').strip() or None

        if not name:
            flash('Food name is required.')
            return redirect(url_for('food_new'))

        conn = get_db()

        existing = conn.execute(
            'SELECT id FROM foods WHERE LOWER(name) = LOWER(?) '
            'AND LOWER(COALESCE(brand, "")) = LOWER(COALESCE(?, ""))',
            (name, brand)
        ).fetchone()
        if existing:
            flash(f'"{name}"' + (f' ({brand})' if brand else '') + ' is already in the database.')
            conn.close()
            return redirect(url_for('food_new'))

        conn.execute('''
            INSERT INTO foods (name, brand, calories, protein_g, carbs_g, fat_g,
                                saturated_fat_g, trans_fat_g, fiber_g, sugar_g,
                                sodium_mg, cholesterol_mg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name, brand,
            request.form.get('calories', type=float) or 0,
            request.form.get('protein_g', type=float) or 0,
            request.form.get('carbs_g', type=float) or 0,
            request.form.get('fat_g', type=float) or 0,
            request.form.get('saturated_fat_g', type=float),
            request.form.get('trans_fat_g', type=float),
            request.form.get('fiber_g', type=float),
            request.form.get('sugar_g', type=float),
            request.form.get('sodium_mg', type=float),
            request.form.get('cholesterol_mg', type=float),
        ))
        conn.commit()
        conn.close()
        flash(f'"{name}" added to your food database.')
        return redirect(url_for('foods_list'))

    return render_template('food_new.html')

@app.route('/nutrition/goal/calculate', methods=['POST'])
def calorie_goal_calculate():
    sex          = request.form.get('sex')
    age          = request.form.get('age', type=int)
    height_cm    = request.form.get('height_cm', type=float)
    weight_kg    = request.form.get('weight_kg', type=float)
    body_fat_pct = request.form.get('body_fat_pct', type=float)
    activity_key = request.form.get('activity_level')
    goal         = request.form.get('goal')
    weekly_rate  = request.form.get('weekly_rate_lb', type=float)

    activity_multiplier = ACTIVITY_MULTIPLIERS.get(activity_key, 1.2)

    bmr, tdee, target = calculate_calorie_target(
        weight_kg=weight_kg, activity_multiplier=activity_multiplier,
        goal=goal, weekly_rate_lb=weekly_rate,
        sex=sex, age=age, height_cm=height_cm, body_fat_pct=body_fat_pct
    )

    conn = get_db()
    current = conn.execute(
        'SELECT * FROM calorie_goals ORDER BY start_date DESC, created_at DESC LIMIT 1'
    ).fetchone()
    history = conn.execute(
        'SELECT * FROM calorie_goals ORDER BY start_date DESC, created_at DESC'
    ).fetchall()
    conn.close()

    calculated = {
        'bmr': bmr, 'tdee': tdee, 'target_calories': target,
        'sex': sex, 'age': age, 'height_cm': height_cm, 'weight_kg': weight_kg,
        'body_fat_pct': body_fat_pct, 'activity_multiplier': activity_multiplier,
        'goal': goal, 'weekly_rate_lb': weekly_rate,
    }
    return render_template('calorie_goal.html', current=current, history=history, calculated=calculated)

@app.route('/nutrition/goal', methods=['GET', 'POST'])
def calorie_goal():
    conn = get_db()

    if request.method == 'POST':
        daily_calories = request.form.get('daily_calories', type=int)
        if not daily_calories:
            flash('Daily calorie target is required.')
            conn.close()
            return redirect(url_for('calorie_goal'))

        conn.execute('''
            INSERT INTO calorie_goals (
                daily_calories, protein_g, carbs_g, fat_g,
                sex, age, height_cm, weight_kg, body_fat_pct,
                activity_multiplier, goal, weekly_rate_lb
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            daily_calories,
            request.form.get('protein_g', type=int),
            request.form.get('carbs_g', type=int),
            request.form.get('fat_g', type=int),
            request.form.get('sex') or None,
            request.form.get('age', type=int),
            request.form.get('height_cm', type=float),
            request.form.get('weight_kg', type=float),
            request.form.get('body_fat_pct', type=float),
            request.form.get('activity_multiplier', type=float),
            request.form.get('goal') or None,
            request.form.get('weekly_rate_lb', type=float),
        ))
        conn.commit()
        conn.close()
        flash('Calorie goal updated.')
        return redirect(url_for('calorie_goal'))

    current = conn.execute(
        'SELECT * FROM calorie_goals ORDER BY start_date DESC, created_at DESC LIMIT 1'
    ).fetchone()
    history = conn.execute(
        'SELECT * FROM calorie_goals ORDER BY start_date DESC, created_at DESC'
    ).fetchall()
    conn.close()
    return render_template('calorie_goal.html', current=current, history=history)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
