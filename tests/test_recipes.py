import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
from werkzeug.datastructures import MultiDict

# Import routes without touching the user's database or seeding it.
with patch.object(database, 'init_db'), patch.object(database, 'seed_db'):
    app = importlib.import_module('app').app


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, 'DATABASE', str(Path(self.directory.name) / 'test.db'))
        self.db_patch.start()
        database.init_db()
        with database.get_db() as conn:
            conn.executemany('INSERT INTO foods (name, calories, protein_g, carbs_g, fat_g) VALUES (?, ?, ?, ?, ?)',
                             [('Rice', 100, 2, 20, 1), ('Chicken', 200, 30, 0, 5)])
        conn.close()
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        self.db_patch.stop()
        self.directory.cleanup()

    def recipe_form(self, **overrides):
        data = {'name': 'Chicken bowl', 'servings': '4', 'instructions': 'Mix and cook.',
                'food_id': ['1', '2'], 'grams': ['200', '300']}
        data.update(overrides)
        return MultiDict((key, item) for key, value in data.items()
                         for item in (value if isinstance(value, list) else [value]))

    def create_recipe(self):
        response = self.client.post('/recipes/new', data=self.recipe_form())
        self.assertEqual(response.status_code, 302)
        return response.headers['Location']

    def fetch(self, sql):
        conn = database.get_db()
        try:
            return [dict(row) for row in conn.execute(sql).fetchall()]
        finally:
            conn.close()

    def test_create_recall_scale_and_repeat_log(self):
        location = self.create_recipe()
        page = self.client.get(location)
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'200.0 kcal', page.data)
        self.assertIn(b'Mix and cook.', page.data)
        for _ in range(2):
            response = self.client.post(location, data={'date': '2026-09-22', 'servings': '1.5'}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
        rows = self.fetch('SELECT * FROM recipe_logs')
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0]['calories'], 300)
        self.assertAlmostEqual(rows[0]['protein_g'], 35.25)
        self.assertAlmostEqual(rows[0]['carbs_g'], 15)
        self.assertAlmostEqual(rows[0]['fat_g'], 6.375)
        self.assertIn(b'600.0 kcal', response.data)
        self.assertIn(b'Chicken bowl', self.client.get('/recipes?q=CHICKEN').data)
        self.assertIn(b'No recipes match', self.client.get('/recipes?q=missing').data)
        self.assertIn(b'No recipes logged', self.client.get('/nutrition/log?date=2026-09-21').data)

    def test_edit_and_delete_preserve_history(self):
        location = self.create_recipe()
        self.client.post(location, data={'date': '2026-09-22', 'servings': '1'})
        saved = self.fetch('SELECT * FROM recipe_logs')[0]
        response = self.client.post(location + '/edit', data=self.recipe_form(name='Updated', servings='2'), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'400.0 kcal', response.data)
        self.assertEqual(self.fetch('SELECT * FROM recipe_logs')[0], saved)
        self.client.post(location + '/delete')
        self.assertEqual(self.fetch('SELECT * FROM recipe_ingredients'), [])
        row = self.fetch('SELECT * FROM recipe_logs')[0]
        self.assertIsNone(row['recipe_id'])
        self.assertEqual(row['name'], 'Chicken bowl')
        self.assertEqual(row['calories'], 200)
        response = self.client.post('/nutrition/log/1/delete', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.fetch('SELECT * FROM recipe_logs'), [])

    def test_invalid_recipes_do_not_write_and_keep_input(self):
        for overrides in ({'name': ''}, {'servings': '0'}, {'servings': 'nan'},
                          {'grams': ['-2', '300']}, {'grams': ['inf', '300']},
                          {'food_id': ['999', '2']}, {'food_id': []}, {'grams': ['1']}):
            with self.subTest(overrides=overrides):
                response = self.client.post('/recipes/new', data=self.recipe_form(**overrides))
                self.assertEqual(response.status_code, 400)
                self.assertIn(b'Mix and cook.', response.data)
                self.assertEqual(self.fetch('SELECT * FROM recipes'), [])
        location = self.create_recipe()
        self.client.post(location + '/edit', data=self.recipe_form(grams=['0', '300']))
        self.assertEqual(len(self.fetch('SELECT * FROM recipe_ingredients')), 2)

    def test_invalid_logs_and_missing_resources(self):
        location = self.create_recipe()
        for data in ({'servings': '0'}, {'servings': 'nan'}, {'servings': 'inf'},
                     {'servings': '-1'}, {'date': '2026-02-30'}, {'date': ''}):
            self.assertEqual(self.client.post(location, data=data).status_code, 400)
        self.assertEqual(self.fetch('SELECT * FROM recipe_logs'), [])
        for path in ('/recipes/999', '/recipes/999/edit'):
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get('/nutrition/log?date=bad').status_code, 400)

    def test_schema_upgrade_is_repeatable_and_pages_render(self):
        self.create_recipe()
        database.init_db()
        self.assertEqual(len(self.fetch('SELECT * FROM recipes')), 1)
        self.assertEqual(len(self.fetch('SELECT * FROM foods')), 2)
        for path in ('/', '/foods', '/recipes', '/recipes/new', '/recipes/1/edit', '/nutrition/log'):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_meal_ideas_preview_import_and_log(self):
        from meal_ideas import MEALS, nutrition
        page = self.client.get('/recipes/ideas')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'generic ingredients', page.data)
        self.assertEqual(self.fetch('SELECT * FROM recipes'), [])
        for meal in MEALS:
            with self.subTest(meal=meal['slug']):
                response = self.client.post('/recipes/ideas/' + meal['slug'] + '/save')
                self.assertEqual(response.status_code, 302)
                location = response.headers['Location']
                self.assertEqual(self.client.get(location).status_code, 200)
                self.assertEqual(self.client.post(location, data={
                    'date': '2026-09-27', 'servings': '0.5'}).status_code, 302)
                logged = self.fetch('SELECT * FROM recipe_logs ORDER BY id DESC')[0]
                for key, value in nutrition(meal).items():
                    self.assertAlmostEqual(logged[key], value / 2)
        self.assertEqual(len(self.fetch('SELECT * FROM recipes')), 8)
        self.assertIn(b'Open saved recipe', self.client.get('/recipes/ideas').data)
        self.assertEqual(self.fetch('SELECT * FROM foods WHERE id = 1')[0]['name'], 'Rice')

    def test_meal_import_is_repeatable_after_rename_and_reimportable_after_delete(self):
        path = '/recipes/ideas/berry-oats/save'
        location = self.client.post(path).headers['Location']
        self.client.post(location + '/edit', data=self.recipe_form(name='My oats'))
        before = self.fetch('SELECT * FROM foods')
        self.assertEqual(self.client.post(path).headers['Location'], location)
        self.assertEqual(len(self.fetch('SELECT * FROM recipes')), 1)
        self.assertEqual(self.fetch('SELECT * FROM recipes')[0]['name'], 'My oats')
        self.assertEqual(self.fetch('SELECT * FROM foods'), before)
        self.client.post(location + '/delete')
        self.assertEqual(self.fetch('SELECT * FROM starter_meal_imports'), [])
        self.assertEqual(self.client.post(path).status_code, 302)
        self.assertEqual(len(self.fetch('SELECT * FROM recipes')), 1)
        self.assertEqual(self.fetch('SELECT * FROM foods'), before)
        self.assertEqual(self.client.post('/recipes/ideas/missing/save').status_code, 404)
        self.assertEqual(self.client.get(path).status_code, 405)


if __name__ == '__main__':
    unittest.main()
