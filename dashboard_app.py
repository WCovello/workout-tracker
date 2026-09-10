"""
dashboard_app.py
A standalone desktop dashboard for exploring your workout data.
Reads directly from workouts.db — no server or internet needed.

Run with: python dashboard_app.py

Four sections:
  Overview  — session count, weekly activity chart, recent sessions
  Exercises — per-exercise progression chart (weight or reps over time)
  Skills    — skill hold-time progression by stage
  Volume    — push/pull balance and muscle group volume by date range
"""

import os
import sys
import sqlite3
import datetime

# Set matplotlib backend before any other matplotlib imports
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import customtkinter as ctk

# ── Appearance ────────────────────────────────────────────────────────────
ctk.set_appearance_mode("System")      # follows Windows light/dark setting
ctk.set_default_color_theme("blue")

COLORS = ['#2563eb', '#dc2626', '#16a34a', '#d97706',
          '#7c3aed', '#0891b2', '#db2777', '#65a30d']


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION WINDOW
# ═══════════════════════════════════════════════════════════════════════════

class WorkoutDashboard(ctk.CTk):

    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.title("Workout Tracker — Dashboard")
        self.geometry("1200x760")
        self.minsize(900, 600)
        self._build_layout()
        self.show_overview()

    # ── Database ──────────────────────────────────────────────────────────

    def get_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Layout helpers ────────────────────────────────────────────────────

    def _build_layout(self):
        # Left sidebar
        self.sidebar = ctk.CTkFrame(self, width=195, corner_radius=0)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar, text="Workout\nTracker",
            font=ctk.CTkFont(size=18, weight='bold')
        ).pack(pady=(26, 2), padx=16)

        ctk.CTkLabel(
            self.sidebar,
            text=os.path.basename(self.db_path),
            font=ctk.CTkFont(size=10), text_color='gray'
        ).pack(pady=(0, 22))

        self._nav_btns = {}
        for label, cmd in [
            ('Overview',  self.show_overview),
            ('Exercises', self.show_exercises),
            ('Skills',    self.show_skills),
            ('Volume',    self.show_volume),
        ]:
            btn = ctk.CTkButton(
                self.sidebar, text=label, command=cmd,
                fg_color='transparent',
                text_color=('gray10', 'gray90'),
                hover_color=('gray75', 'gray30'),
                anchor='w', height=38, width=172,
                font=ctk.CTkFont(size=14)
            )
            btn.pack(pady=2, padx=10)
            self._nav_btns[label] = btn

        # Main scrollable content area
        self.main = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.main.pack(side='right', fill='both', expand=True)

    def _clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def _highlight(self, active: str):
        for label, btn in self._nav_btns.items():
            btn.configure(
                fg_color=('gray75', 'gray30') if label == active
                else 'transparent'
            )

    def _title(self, text: str):
        ctk.CTkLabel(
            self.main, text=text,
            font=ctk.CTkFont(size=20, weight='bold')
        ).pack(anchor='w', padx=24, pady=(22, 8))

    def _subtitle(self, text: str):
        ctk.CTkLabel(
            self.main, text=text,
            font=ctk.CTkFont(size=15, weight='bold')
        ).pack(anchor='w', padx=24, pady=(16, 6))

    # ── Chart helpers ─────────────────────────────────────────────────────

    def _make_fig(self, figsize=(9, 3.2)):
        """Create a matplotlib Figure styled to match the current UI theme."""
        dark  = ctk.get_appearance_mode() == 'Dark'
        bg    = '#2b2b2b' if dark else '#efefef'
        fg    = '#e0e0e0' if dark else '#1a1a1a'
        grid  = '#444' if dark else '#ccc'

        fig = Figure(figsize=figsize, facecolor=bg)
        ax  = fig.add_subplot(111)
        ax.set_facecolor(bg)
        ax.tick_params(colors=fg, labelsize=9)
        ax.xaxis.label.set_color(fg)
        ax.yaxis.label.set_color(fg)
        ax.title.set_color(fg)
        for spine in ax.spines.values():
            spine.set_color(grid)
        return fig, ax

    def _embed(self, fig: Figure, parent, height: int = 260):
        """Embed a matplotlib figure into a tkinter parent widget."""
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        w = canvas.get_tk_widget()
        w.configure(height=height)
        w.pack(fill='x')
        return canvas


    # ═══════════════════════════════════════════════════════════════════════
    # OVERVIEW
    # ═══════════════════════════════════════════════════════════════════════

    def show_overview(self):
        self._clear()
        self._highlight('Overview')
        self._title('Overview')

        conn = self.get_db()

        total_sessions = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
        total_sets     = conn.execute('SELECT COUNT(*) FROM sets').fetchone()[0]
        total_ex       = conn.execute(
            'SELECT COUNT(DISTINCT exercise_id) FROM sets'
        ).fetchone()[0]
        skill_sessions = conn.execute('SELECT COUNT(*) FROM skill_logs').fetchone()[0]

        # ── Stat cards ───────────────────────────────────────────────────
        row = ctk.CTkFrame(self.main, fg_color='transparent')
        row.pack(fill='x', padx=24, pady=(0, 6))

        for label, value in [
            ('Workouts',      total_sessions),
            ('Total Sets',    total_sets),
            ('Exercises Used',total_ex),
            ('Skill Sessions',skill_sessions),
        ]:
            card = ctk.CTkFrame(row)
            card.pack(side='left', expand=True, fill='both', padx=6, pady=4)
            ctk.CTkLabel(
                card, text=str(value),
                font=ctk.CTkFont(size=32, weight='bold')
            ).pack(pady=(14, 2))
            ctk.CTkLabel(
                card, text=label,
                text_color='gray', font=ctk.CTkFont(size=12)
            ).pack(pady=(0, 14))

        # ── Sessions per week (last 10 weeks) ─────────────────────────────
        today = datetime.date.today()
        week_labels, week_counts = [], []

        for i in range(9, -1, -1):
            monday  = today - datetime.timedelta(days=today.weekday() + 7 * i)
            sunday  = monday + datetime.timedelta(days=6)
            count   = conn.execute(
                'SELECT COUNT(*) FROM sessions WHERE date >= ? AND date <= ?',
                (monday.isoformat(), sunday.isoformat())
            ).fetchone()[0]
            week_labels.append(monday.strftime('%d %b'))
            week_counts.append(count)

        if any(week_counts):
            self._subtitle('Sessions per Week')
            card = ctk.CTkFrame(self.main)
            card.pack(fill='x', padx=24, pady=4)

            fig, ax = self._make_fig(figsize=(9, 2.6))
            xs   = list(range(len(week_labels)))
            bars = ax.bar(xs, week_counts, color=COLORS[0], alpha=0.85, zorder=3)
            ax.bar_label(bars, fmt='%d', padding=2, fontsize=9,
                         color=ax.title.get_color())
            ax.set_xticks(xs)
            ax.set_xticklabels(week_labels, rotation=30, ha='right', fontsize=8)
            ax.set_ylabel('Sessions')
            ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            ax.grid(axis='y', alpha=0.3, zorder=0)
            ax.set_ylim(0, max(week_counts) * 1.25 + 0.5)
            fig.tight_layout(pad=1.5)
            self._embed(fig, card, height=210)

        # ── Recent sessions table ─────────────────────────────────────────
        self._subtitle('Recent Sessions')

        sessions = conn.execute('''
            SELECT s.name, s.date, s.duration_minutes,
                   COUNT(DISTINCT se.exercise_id) as ex_count,
                   COUNT(se.id)                   as set_count
            FROM sessions s
            LEFT JOIN sets se ON se.session_id = s.id
            GROUP BY s.id
            ORDER BY s.date DESC, s.created_at DESC
            LIMIT 15
        ''').fetchall()

        cols   = [('Date', 100), ('Name', 260), ('Exercises', 90),
                  ('Sets', 70), ('Duration', 90)]
        header = ctk.CTkFrame(self.main, fg_color=('gray80', 'gray25'))
        header.pack(fill='x', padx=24)

        for text, width in cols:
            ctk.CTkLabel(
                header, text=text, width=width, anchor='w',
                font=ctk.CTkFont(weight='bold')
            ).pack(side='left', padx=8, pady=7)

        for i, s in enumerate(sessions):
            bg  = ('gray92', 'gray20') if i % 2 == 0 else ('gray86', 'gray17')
            row = ctk.CTkFrame(self.main, fg_color=bg)
            row.pack(fill='x', padx=24)
            dur = f"{s['duration_minutes']} min" if s['duration_minutes'] else '—'
            for text, width in [
                (s['date'], 100), (s['name'], 260),
                (str(s['ex_count']), 90), (str(s['set_count']), 70), (dur, 90)
            ]:
                ctk.CTkLabel(
                    row, text=text, width=width, anchor='w'
                ).pack(side='left', padx=8, pady=5)

        conn.close()


    # ═══════════════════════════════════════════════════════════════════════
    # EXERCISES
    # ═══════════════════════════════════════════════════════════════════════

    def show_exercises(self):
        self._clear()
        self._highlight('Exercises')
        self._title('Exercise Progression')

        conn      = self.get_db()
        exercises = conn.execute('''
            SELECT DISTINCT e.id, e.name, e.push_pull
            FROM exercises e
            JOIN sets s ON s.exercise_id = e.id
            ORDER BY e.push_pull, e.name
        ''').fetchall()
        conn.close()

        if not exercises:
            ctk.CTkLabel(self.main, text='No exercises logged yet.',
                         text_color='gray').pack(padx=24, pady=20)
            return

        ex_names = [e['name'] for e in exercises]
        ex_ids   = {e['name']: e['id'] for e in exercises}

        # ── Controls ──────────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self.main, fg_color='transparent')
        ctrl.pack(fill='x', padx=24, pady=8)

        ex_var   = ctk.StringVar(value=ex_names[0])
        mode_var = ctk.StringVar(value='Max Weight (kg)')

        ctk.CTkLabel(ctrl, text='Exercise:').pack(side='left', padx=(0, 6))
        ex_menu = ctk.CTkOptionMenu(
            ctrl, variable=ex_var, values=ex_names, width=230
        )
        ex_menu.pack(side='left', padx=(0, 20))

        ctk.CTkLabel(ctrl, text='Show:').pack(side='left', padx=(0, 6))
        mode_menu = ctk.CTkOptionMenu(
            ctrl, variable=mode_var,
            values=['Max Weight (kg)', 'Total Reps per Session', 'Max Reps in a Set'],
            width=200
        )
        mode_menu.pack(side='left')

        # Chart card and stats row below it
        chart_card  = ctk.CTkFrame(self.main)
        chart_card.pack(fill='x', padx=24, pady=8)
        stats_row   = ctk.CTkFrame(self.main, fg_color='transparent')
        stats_row.pack(fill='x', padx=24, pady=(0, 8))

        def draw(*_):
            for w in chart_card.winfo_children():
                w.destroy()
            for w in stats_row.winfo_children():
                w.destroy()

            conn  = self.get_db()
            ex_id = ex_ids[ex_var.get()]
            mode  = mode_var.get()

            rows = conn.execute('''
                SELECT s.date,
                       MAX(se.weight_kg) as max_weight,
                       SUM(se.reps)      as total_reps,
                       MAX(se.reps)      as max_reps
                FROM sets se
                JOIN sessions s ON s.id = se.session_id
                WHERE se.exercise_id = ?
                GROUP BY s.date
                ORDER BY s.date
            ''', (ex_id,)).fetchall()
            conn.close()

            if not rows:
                ctk.CTkLabel(chart_card, text='No data for this exercise.',
                             text_color='gray').pack(pady=20)
                return

            dates = [r['date'] for r in rows]
            xs    = list(range(len(dates)))

            if mode == 'Max Weight (kg)':
                values = [float(r['max_weight'] or 0) for r in rows]
                ylabel = 'Weight (kg)'
            elif mode == 'Total Reps per Session':
                values = [int(r['total_reps'] or 0) for r in rows]
                ylabel = 'Total Reps'
            else:
                values = [int(r['max_reps'] or 0) for r in rows]
                ylabel = 'Max Reps in a Set'

            fig, ax = self._make_fig(figsize=(9, 3.4))
            ax.plot(xs, values, marker='o', color=COLORS[0],
                    linewidth=2, markersize=5, zorder=3)
            ax.fill_between(xs, values, alpha=0.10, color=COLORS[0])
            ax.set_xticks(xs)
            ax.set_xticklabels(dates, rotation=35, ha='right', fontsize=8)
            ax.set_ylabel(ylabel)
            ax.set_title(f'{ex_var.get()} — {mode}')
            ax.grid(axis='y', alpha=0.3, zorder=0)
            ax.set_xlim(-0.4, len(dates) - 0.6)
            ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            fig.tight_layout(pad=1.5)
            self._embed(fig, chart_card, height=270)

            # Mini stats below the chart
            best  = max(values)
            first = values[0]
            last  = values[-1]
            diff  = last - first
            sign  = '+' if diff >= 0 else ''
            for label, val in [
                ('Sessions', str(len(rows))),
                (f'Best {ylabel}', str(best)),
                (f'First → Last', f'{first} → {last}  ({sign}{diff:.3g})'),
            ]:
                card = ctk.CTkFrame(stats_row)
                card.pack(side='left', expand=True, fill='both', padx=6)
                ctk.CTkLabel(
                    card, text=val,
                    font=ctk.CTkFont(size=15, weight='bold')
                ).pack(pady=(10, 2))
                ctk.CTkLabel(
                    card, text=label,
                    text_color='gray', font=ctk.CTkFont(size=11)
                ).pack(pady=(0, 10))

        ex_menu.configure(command=draw)
        mode_menu.configure(command=draw)
        draw()


    # ═══════════════════════════════════════════════════════════════════════
    # SKILLS
    # ═══════════════════════════════════════════════════════════════════════

    def show_skills(self):
        self._clear()
        self._highlight('Skills')
        self._title('Skill Progression')

        conn   = self.get_db()
        skills = conn.execute('''
            SELECT s.id, s.name FROM skills s
            WHERE EXISTS (SELECT 1 FROM skill_logs sl WHERE sl.skill_id = s.id)
            ORDER BY s.name
        ''').fetchall()
        conn.close()

        if not skills:
            ctk.CTkLabel(self.main, text='No skill sessions logged yet.',
                         text_color='gray').pack(padx=24, pady=20)
            return

        skill_names = [s['name'] for s in skills]
        skill_ids   = {s['name']: s['id'] for s in skills}

        # ── Controls ──────────────────────────────────────────────────────
        ctrl = ctk.CTkFrame(self.main, fg_color='transparent')
        ctrl.pack(fill='x', padx=24, pady=8)

        skill_var = ctk.StringVar(value=skill_names[0])
        ctk.CTkLabel(ctrl, text='Skill:').pack(side='left', padx=(0, 6))
        skill_menu = ctk.CTkOptionMenu(
            ctrl, variable=skill_var, values=skill_names, width=250
        )
        skill_menu.pack(side='left')

        chart_card   = ctk.CTkFrame(self.main)
        chart_card.pack(fill='x', padx=24, pady=8)
        stage_row    = ctk.CTkFrame(self.main, fg_color='transparent')
        stage_row.pack(fill='x', padx=24, pady=(0, 8))

        def draw(*_):
            for w in chart_card.winfo_children():
                w.destroy()
            for w in stage_row.winfo_children():
                w.destroy()

            conn     = self.get_db()
            skill_id = skill_ids[skill_var.get()]

            stages = conn.execute(
                'SELECT * FROM skill_progressions WHERE skill_id = ? ORDER BY stage_order',
                (skill_id,)
            ).fetchall()

            logs = conn.execute('''
                SELECT sl.date, sl.hold_seconds, sl.quality,
                       sp.id as prog_id, sp.stage_name, sp.stage_order
                FROM skill_logs sl
                JOIN skill_progressions sp ON sp.id = sl.progression_id
                WHERE sl.skill_id = ?
                ORDER BY sl.date, sl.logged_at
            ''', (skill_id,)).fetchall()
            conn.close()

            if not logs:
                ctk.CTkLabel(chart_card, text='No sessions logged yet.',
                             text_color='gray').pack(pady=20)
                return

            all_dates = sorted(set(r['date'] for r in logs))
            date_idx  = {d: i for i, d in enumerate(all_dates)}

            fig, ax = self._make_fig(figsize=(9, 3.6))

            for i, stage in enumerate(stages):
                stage_logs = [r for r in logs if r['prog_id'] == stage['id']]
                if not stage_logs:
                    continue
                d2v = {}
                for r in stage_logs:
                    val = r['hold_seconds'] if r['hold_seconds'] is not None else r['quality']
                    if val is not None:
                        d2v[r['date']] = val
                if d2v:
                    xs = [date_idx[d] for d in d2v]
                    ys = list(d2v.values())
                    col = COLORS[i % len(COLORS)]
                    ax.plot(xs, ys, marker='o', label=stage['stage_name'],
                            color=col, linewidth=2, markersize=5, zorder=3)
                    ax.scatter(xs, ys, color=col, zorder=4, s=30)

            ax.set_xticks(list(range(len(all_dates))))
            ax.set_xticklabels(all_dates, rotation=35, ha='right', fontsize=8)
            ax.set_ylabel('Hold (s) / Quality')
            ax.set_title(skill_var.get())
            ax.legend(fontsize=9, loc='upper left')
            ax.grid(axis='y', alpha=0.3, zorder=0)
            ax.set_xlim(-0.4, len(all_dates) - 0.6)
            fig.tight_layout(pad=1.5)
            self._embed(fig, chart_card, height=280)

            # Progression ladder below chart
            current = logs[-1]['stage_name']
            for stage in stages:
                is_current = stage['stage_name'] == current
                tag = ctk.CTkFrame(
                    stage_row,
                    fg_color=('#2563eb' if is_current else ('gray80', 'gray30'))
                )
                tag.pack(side='left', padx=4, pady=4)
                ctk.CTkLabel(
                    tag,
                    text=f"{stage['stage_order']}. {stage['stage_name']}",
                    text_color=('white' if is_current else ('gray10', 'gray90')),
                    font=ctk.CTkFont(weight='bold' if is_current else 'normal',
                                     size=12)
                ).pack(padx=10, pady=6)

        skill_menu.configure(command=draw)
        draw()


    # ═══════════════════════════════════════════════════════════════════════
    # VOLUME
    # ═══════════════════════════════════════════════════════════════════════

    def show_volume(self):
        self._clear()
        self._highlight('Volume')
        self._title('Volume Analysis')

        ctrl = ctk.CTkFrame(self.main, fg_color='transparent')
        ctrl.pack(fill='x', padx=24, pady=8)

        period_var = ctk.StringVar(value='Last 7 days')
        ctk.CTkLabel(ctrl, text='Period:').pack(side='left', padx=(0, 6))
        period_menu = ctk.CTkOptionMenu(
            ctrl, variable=period_var,
            values=['Last 7 days', 'Last 30 days', 'Last 90 days', 'All time'],
            width=160
        )
        period_menu.pack(side='left')

        content = ctk.CTkFrame(self.main, fg_color='transparent')
        content.pack(fill='x', padx=24, pady=8)

        def draw(*_):
            for w in content.winfo_children():
                w.destroy()

            today  = datetime.date.today()
            period = period_var.get()
            since  = {
                'Last 7 days':  (today - datetime.timedelta(days=7)).isoformat(),
                'Last 30 days': (today - datetime.timedelta(days=30)).isoformat(),
                'Last 90 days': (today - datetime.timedelta(days=90)).isoformat(),
                'All time':     '2000-01-01',
            }[period]

            conn = self.get_db()

            # Push / pull / core / legs
            cat_rows = conn.execute('''
                SELECT e.push_pull, COUNT(se.id) as cnt
                FROM sets se
                JOIN sessions s  ON s.id  = se.session_id
                JOIN exercises e ON e.id  = se.exercise_id
                WHERE s.date >= ? AND e.push_pull IS NOT NULL
                GROUP BY e.push_pull
            ''', (since,)).fetchall()

            # Muscle group volume
            mg_rows = conn.execute('''
                SELECT mg.name, COUNT(se.id) as cnt
                FROM sets se
                JOIN sessions s          ON s.id  = se.session_id
                JOIN exercise_muscles em ON em.exercise_id = se.exercise_id
                                        AND em.role = 'primary'
                JOIN muscle_groups mg    ON mg.id = em.muscle_group_id
                WHERE s.date >= ?
                GROUP BY mg.name
                ORDER BY cnt DESC
            ''', (since,)).fetchall()
            conn.close()

            if not cat_rows and not mg_rows:
                ctk.CTkLabel(content, text='No data for this period.',
                             text_color='gray').pack(pady=20)
                return

            # ── Push / pull bar chart ──────────────────────────────────────
            if cat_rows:
                cat_map  = {r['push_pull']: r['cnt'] for r in cat_rows}
                cats     = ['Push', 'Pull', 'Core', 'Legs']
                cat_keys = ['push', 'pull', 'core', 'legs']
                vals     = [cat_map.get(k, 0) for k in cat_keys]
                colors   = COLORS[:4]

                ctk.CTkLabel(
                    content, text='Push / Pull / Core / Legs',
                    font=ctk.CTkFont(size=14, weight='bold')
                ).pack(anchor='w', pady=(4, 4))

                card = ctk.CTkFrame(content)
                card.pack(fill='x', pady=(0, 8))

                fig, ax = self._make_fig(figsize=(9, 2.5))
                bars = ax.barh(cats, vals, color=colors, alpha=0.85)
                ax.bar_label(bars, padding=4, fontsize=10,
                             color=ax.title.get_color())
                ax.set_xlabel('Sets')
                ax.set_xlim(0, max(vals) * 1.18 + 0.5 if max(vals) > 0 else 1)
                ax.grid(axis='x', alpha=0.3)
                fig.tight_layout(pad=1.5)
                self._embed(fig, card, height=200)

                # Imbalance message
                push_c = cat_map.get('push', 0)
                pull_c = cat_map.get('pull', 0)
                if push_c > 0 and pull_c > 0:
                    ratio = push_c / pull_c
                    if ratio < 0.7:
                        msg = (f'⚠  Push:pull ratio is {ratio:.2f}:1 — push is low. '
                               f'Climbing loads pulling heavily; aim for ~1:1 in gym sessions.')
                        col = '#d97706'
                    elif ratio > 1.5:
                        msg = f'⚠  Push:pull ratio is {ratio:.2f}:1 — unusually high push volume.'
                        col = '#d97706'
                    else:
                        msg = f'✓  Push:pull ratio is {ratio:.2f}:1 — balanced.'
                        col = '#16a34a'
                    ctk.CTkLabel(
                        content, text=msg, text_color=col,
                        font=ctk.CTkFont(size=12), wraplength=800, justify='left'
                    ).pack(anchor='w', pady=(0, 12))

            # ── Muscle group bar chart ─────────────────────────────────────
            if mg_rows:
                ctk.CTkLabel(
                    content, text='Volume by Primary Muscle Group',
                    font=ctk.CTkFont(size=14, weight='bold')
                ).pack(anchor='w', pady=(4, 4))

                card = ctk.CTkFrame(content)
                card.pack(fill='x', pady=(0, 8))

                names  = [r['name'] for r in mg_rows]
                vals   = [r['cnt']  for r in mg_rows]
                height = max(2.8, len(names) * 0.42)

                fig, ax = self._make_fig(figsize=(9, height))
                bars = ax.barh(names, vals, color='#6366f1', alpha=0.85)
                ax.bar_label(bars, padding=4, fontsize=10,
                             color=ax.title.get_color())
                ax.set_xlabel('Sets')
                ax.set_xlim(0, max(vals) * 1.18 + 0.5 if max(vals) > 0 else 1)
                ax.invert_yaxis()
                ax.grid(axis='x', alpha=0.3)
                fig.tight_layout(pad=1.5)
                self._embed(fig, card, height=int(height * 78))

        period_menu.configure(command=draw)
        draw()


# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def find_database() -> str | None:
    """Look for workouts.db next to this script, or let the user browse."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default    = os.path.join(script_dir, 'workouts.db')
    if os.path.exists(default):
        return default

    # Not found — ask the user to locate it
    import tkinter as tk
    from tkinter import filedialog, messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(
        'Workout Tracker',
        'workouts.db was not found next to this script.\n'
        'Please locate it manually.'
    )
    path = filedialog.askopenfilename(
        title='Select workouts.db',
        filetypes=[('SQLite Database', '*.db'), ('All files', '*.*')]
    )
    root.destroy()
    return path or None


if __name__ == '__main__':
    try:
        import customtkinter  # noqa: F401
    except ImportError:
        print("Run:  pip install customtkinter matplotlib")
        sys.exit(1)

    db = find_database()
    if not db:
        print("No database selected — exiting.")
        sys.exit(1)

    WorkoutDashboard(db).mainloop()
