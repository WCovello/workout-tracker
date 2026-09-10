# Workout Tracker

A personal workout tracking app built with Python + Flask + SQLite.

## Setup (first time only)

1. Open PowerShell and navigate to this folder:
   ```
   cd path\to\workout-tracker
   ```

2. Create and activate the virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the app

Every time you want to use the app:

1. Open PowerShell
2. Navigate to the project folder
3. Activate the virtual environment:
   ```
   venv\Scripts\activate
   ```
4. Start the app:
   ```
   python app.py
   ```
5. Open your browser and go to: http://localhost:5000

## Accessing from your phone (same WiFi)

Find your computer's local IP address:
```
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter, e.g. 192.168.1.42
Then on your phone open: http://192.168.1.42:5000

## Project Structure

```
workout-tracker/
├── app.py              # Main Flask application - routes live here
├── database.py         # Database setup and helper functions
├── requirements.txt    # Python dependencies
├── workouts.db         # SQLite database (created automatically on first run)
├── templates/          # HTML pages
└── static/             # CSS, JavaScript, images
```
