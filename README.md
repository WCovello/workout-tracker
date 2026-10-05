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

## Recipes and repeat meals

1. Add ingredients under **Foods**, with nutrition values per 100g.
2. Open **Recipes → New Recipe**. Enter a name, the number of servings in the
   batch, ingredient weights in grams, and optional preparation instructions.
3. Save the recipe to see nutrition for the whole batch and per serving.
4. Choose the date and servings eaten, then **Add to Food Log**. Fractional
   servings are supported. Use recipe search or **Log Again** to repeat a meal.

Recipes can be edited or deleted. Existing food log entries retain the name and
nutrition saved when they were logged. The food log currently tracks saved
recipes; it does not yet include individual food entries.

The new tables are created automatically on app startup, including for existing
databases. No manual migration is required.

Run the recipe integration tests against an isolated temporary database:

```
python -m unittest discover -s tests -v
```

## Meal ideas

Open **Recipes → Meal Ideas** for eight breakfast, lunch and dinner ideas using
everyday ingredients suitable for a Sainsbury's shop. Preview batch quantities
and preparation, then choose **Save to Recipes** to edit and log servings with
the existing food log. Repeated saves reopen your saved copy, including after
you rename it; deleting a saved recipe allows you to import it again.

Nutrition uses clearly labelled generic estimates, not verified retailer product
labels. For more precise tracking, add foods using your package labels and swap
them into the saved recipe. Meat weights are raw, grain weights dry, and tinned
beans and tuna drained. Storage guidance is included. No recipes or foods are
added to your database until you save an idea.

The catalogue and its estimates are maintained in `meal_ideas.py`.

## Project files

```
workout-tracker/
├── app.py              # Main Flask application - routes live here
├── database.py         # Database setup and helper functions
├── requirements.txt    # Python dependencies
├── workouts.db         # SQLite database (created automatically on first run)
├── templates/          # HTML pages
└── static/             # CSS, JavaScript, images
```
