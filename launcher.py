"""
launcher.py
Run this instead of app.py for the desktop experience.

What it does:
  - Starts the Flask server silently in a background thread
  - Opens your browser automatically to the app
  - Shows a small icon in the Windows system tray
  - Right-click the tray icon to stop the server

For development (live code reloading):
  Use 'python app.py' as normal — that keeps the terminal visible
  and reloads when you save files.

For daily use (no terminal):
  Use 'python launcher.py' — clean, background, tray icon.
"""

import threading
import webbrowser
import sys
import os
import time

# ── Make sure we run from the project folder ─────────────────────────────
# This is important so Flask can find templates/, static/, and workouts.db
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ── Imports ───────────────────────────────────────────────────────────────
try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Missing dependencies. Run: pip install pystray pillow")
    sys.exit(1)

from app import app   # imports the Flask app (also runs init_db/seed_db)


# ── Flask thread ──────────────────────────────────────────────────────────

def run_flask():
    """Run Flask in a background thread.
    debug=False and use_reloader=False are required here —
    the reloader doesn't work inside threads."""
    app.run(
        host        = '0.0.0.0',
        port        = 5000,
        debug       = False,
        use_reloader= False,
    )


# ── Tray icon ─────────────────────────────────────────────────────────────

def make_icon_image():
    """Draw a simple coloured square icon with 'WT' text.
    No external image files needed."""
    size  = 64
    img   = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw  = ImageDraw.Draw(img)

    # Blue rounded-ish square background
    draw.rounded_rectangle([2, 2, size - 2, size - 2],
                           radius=12, fill='#2563eb')

    # White 'WT' text, centred
    # PIL's default font is small but reliable — no font files needed
    draw.text((14, 18), 'WT', fill='white')

    return img


def open_browser(icon=None, item=None):
    webbrowser.open('http://localhost:5000')


def stop_app(icon, item):
    icon.stop()
    os._exit(0)   # Force exit — cleanly kills the Flask thread too


def build_tray_icon():
    menu = pystray.Menu(
        item('Open Workout Tracker', open_browser, default=True),
        item('Stop',                 stop_app),
    )
    return pystray.Icon(
        name   = 'workout-tracker',
        icon   = make_icon_image(),
        title  = 'Workout Tracker',   # tooltip on hover
        menu   = menu,
    )


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    # 1. Start Flask in a daemon thread
    #    daemon=True means it dies automatically when the main process exits
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 2. Give Flask a moment to start before opening the browser
    time.sleep(1.2)
    webbrowser.open('http://localhost:5000')

    # 3. Start the system tray icon — this blocks until stop_app() is called
    print("Workout Tracker running. Look for the icon in your system tray.")
    print("Right-click the tray icon to stop.")
    icon = build_tray_icon()
    icon.run()
