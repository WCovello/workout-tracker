"""Import the user's eleven selected cheese-free meals as seven-serving recipes.

Run explicitly; importing this module does not change the database.
"""
from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3

import database
from meal_ideas import FOODS, meal, save_meal


# Generic estimates per 100g, matching the ingredient states in the meal table.
EXTRA_FOODS = {
    'Pork mince 5% fat (raw)': (137, 21, 0, 5),
    'Turkey mince 7% fat (raw)': (150, 20, 0, 7),
    'Potatoes (raw, edible portion)': (77, 2, 17, 0.1),
    'Sweet potato (raw, edible portion)': (86, 1.6, 20, 0.1),
    'Peas': (80, 5.2, 10, 1),
    'Green beans': (31, 1.8, 4, 0.2),
    'Carrots (trimmed)': (41, 0.9, 10, 0.2),
    'Cauliflower': (25, 1.9, 3, 0.3),
    'Wholemeal pitta': (250, 9, 47, 2),
    'High-protein plain yoghurt': (60, 10, 4, 0),
    'Vegetable oil': (900, 0, 0, 100),
    'Paprika (generic estimate)': (300, 10, 40, 10),
    'Shawarma spice mix (generic estimate)': (300, 10, 40, 10),
    'Cumin and paprika mix (generic estimate)': (300, 10, 40, 10),
    'Curry spices (generic estimate)': (300, 10, 40, 10),
    'Kebab spice mix (generic estimate)': (300, 10, 40, 10),
    'Mixed dried herbs (generic estimate)': (250, 10, 30, 5),
}

CHICKEN = 'Chicken breast (raw, skinless)'
PORK = 'Pork mince 5% fat (raw)'
POTATO = 'Potatoes (raw, edible portion)'
EGG = 'Eggs (without shells)'
ONION = 'Onion (peeled)'
OIL = 'Vegetable oil'
MILK = 'Semi-skimmed milk'
HERBS = 'Mixed dried herbs (generic estimate)'
PAPRIKA = 'Paprika (generic estimate)'

NOTES = (
    'Cheese-free. Makes 7 lunch or dinner portions. All quantities below are for '
    'the entire batch; divide every component equally among seven containers. '
    'Meat and potatoes are weighed raw, tuna drained and eggs without shells. '
    'Milk is approximated as 1g per ml for tracking. Salt and pepper may be added '
    'to taste. Optional sauces are not included in the nutrition.\n\n'
    'Cook poultry and minced-meat patties, koftas or meatballs thoroughly; the '
    'centre should reach 75°C for 30 seconds. Cook egg mixtures until set. '
    'Times are guides; thickness and oven loading change cooking time.'
)
FREEZER = (
    'Cool promptly in shallow portions and refrigerate or freeze within 1–2 hours. '
    'Freeze in seven labelled, airtight portions. Defrost overnight in the fridge '
    'and use within 24 hours of fully defrosting. Reheat only once until steaming '
    'hot throughout. Stir or turn during microwave reheating. Oven or air-fryer '
    'reheating gives potatoes and patties a firmer finish; microwaving softens them.'
)


def batch(slug, name, category, ingredients, method, tip=''):
    return meal('freezer-' + slug, name, category, 7,
                [(name, grams * 7) for name, grams in ingredients],
                NOTES + '\n\n' + method, FREEZER + ('\n\n' + tip if tip else ''))


RECIPES = [
    batch('chicken-egg-hash', 'Chicken and egg potato hash', 'Lunch',
          [(CHICKEN, 150), (EGG, 100), (POTATO, 200), ('Peppers (trimmed)', 100),
           (ONION, 50), (OIL, 5), (PAPRIKA, 2)],
          'Heat oven to 200°C fan. Dice potatoes and toss with half the oil and paprika. '
          'Roast for about 30–40 minutes until tender, turning halfway. Cook diced chicken, '
          'peppers and onion in the remaining oil in batches until chicken is cooked through. '
          'Scramble the beaten eggs until set, then combine with chicken and potatoes. '
          'Use approximately 14 medium eggs for the batch, checking their shell-free weight.'),
    batch('pork-patties-mash', 'Pork patties, mash and green beans', 'Lunch',
          [(PORK, 200), (POTATO, 250), (MILK, 30), ('Green beans', 200),
           (ONION, 40), (OIL, 5), (HERBS, 1)],
          'Finely grate and squeeze the onion. Mix with pork and herbs, then shape into '
          '14 patties. Brush with the oil and bake at 200°C fan for about 20–25 minutes, '
          'turning once, until cooked through. Boil potato chunks until tender, drain and '
          'mash with the milk. Cook green beans according to the packet. Pack two patties per portion.'),
    batch('shawarma-potatoes', 'Chicken shawarma potato box', 'Lunch',
          [(CHICKEN, 180), (POTATO, 250), ('Carrots (trimmed)', 200), (ONION, 40),
           (OIL, 10), ('Shawarma spice mix (generic estimate)', 3)],
          'Heat oven to 200°C fan. Cut potatoes into wedges, carrots into batons and onions '
          'into wedges. Toss with half the oil and roast for 35–45 minutes until tender. '
          'Coat chicken strips in the remaining oil and spices; roast on a separate tray '
          'for about 20–25 minutes until cooked through. Use multiple trays to avoid overcrowding.'),
    batch('tuna-fishcakes', 'Tuna fishcakes and peas', 'Lunch',
          [('Tuna in spring water (drained)', 150), (POTATO, 250), (EGG, 25),
           ('Peas', 150), (ONION, 30), (OIL, 5), (HERBS, 1)],
          'Boil potatoes until tender, drain well and let steam escape, then mash without '
          'milk. Soften finely chopped onion in a little of the measured oil. Cool the mash '
          'and onion promptly, then mix with drained tuna, herbs and beaten egg. Weigh '
          '175g beaten egg for the batch. Shape into 14 fishcakes, brush with remaining oil '
          'and bake at 200°C fan for about 25–30 minutes, turning carefully, until set and '
          'steaming hot through the centre. Cook peas following the packet. Pack two cakes per portion.',
          'No breadcrumb coating. Freeze cooled fishcakes in a single layer before packing to prevent sticking.'),
    batch('turkey-burgers', 'Turkey burgers, potatoes and broccoli', 'Lunch',
          [('Turkey mince 7% fat (raw)', 200), (POTATO, 250), ('Broccoli', 200),
           (ONION, 40), (OIL, 5), (HERBS, 1)],
          'Mix turkey with finely grated, squeezed onion and herbs. Shape into 14 small '
          'burgers. Cut potatoes into chunks and toss with the oil; roast at 200°C fan '
          'for 35–45 minutes. Bake burgers on a separate lined tray for about 20–25 minutes '
          'until cooked through, turning once. Cook broccoli following the packet. Pack two burgers per portion.',
          'No bun is included in this recipe.'),
    batch('paprika-roast', 'Paprika chicken roast box', 'Dinner',
          [(CHICKEN, 180), (POTATO, 250), ('Carrots (trimmed)', 150), ('Peas', 100),
           (OIL, 10), (PAPRIKA, 3)],
          'Heat oven to 200°C fan. Cut potatoes and carrots into similar-sized pieces, '
          'toss with half the oil and roast for 35–45 minutes until tender. Coat chicken '
          'with remaining oil and paprika and roast separately for about 20–30 minutes '
          'until cooked through. Cook peas according to the packet. Divide all components equally.'),
    batch('pork-koftas', 'Pork koftas, wedges and green beans', 'Dinner',
          [(PORK, 215), (POTATO, 300), ('Green beans', 200), (ONION, 40), (OIL, 7),
           ('Cumin and paprika mix (generic estimate)', 3)],
          'Finely grate and squeeze onion, mix with pork and spices, and form 21 small '
          'koftas without skewers. Cut potatoes into wedges, toss with most of the oil '
          'and roast at 200°C fan for 35–45 minutes. Brush koftas with remaining oil and '
          'bake on a separate tray for about 20–25 minutes until cooked through. Cook '
          'green beans according to the packet. Pack three koftas per portion.'),
    batch('garlic-meatballs', 'Garlic-and-herb meatballs with mash', 'Dinner',
          [(PORK, 200), (POTATO, 250), (MILK, 30), ('Broccoli', 100),
           ('Carrots (trimmed)', 100), (ONION, 40), (OIL, 5), ('Garlic (peeled)', 3), (HERBS, 1)],
          'Mix pork with finely grated, squeezed onion, crushed garlic and herbs. Shape '
          'into 28 meatballs, brush with oil and bake at 200°C fan for about 20–25 minutes '
          'until cooked through. Boil potatoes until tender, drain and mash with milk. '
          'Steam carrots and broccoli until tender. Pack four meatballs per portion.'),
    batch('tandoori-potatoes', 'Tandoori-style chicken and spiced potatoes', 'Dinner',
          [(CHICKEN, 180), (POTATO, 250), ('High-protein plain yoghurt', 50),
           ('Cauliflower', 150), ('Peas', 100), (OIL, 10), ('Curry spices (generic estimate)', 3)],
          'Coat chicken in yoghurt and two-thirds of the spices; keep refrigerated until '
          'cooking. Toss diced potatoes and cauliflower in oil and remaining spices. '
          'Roast potatoes at 200°C fan for 35–45 minutes, adding cauliflower for the final '
          '20–25 minutes. Bake chicken on a separate lined tray for about 20–30 minutes '
          'until cooked through. Cook peas according to the packet.',
          'Yoghurt is included; cheese is not. Cook the yoghurt coating onto the chicken before freezing.'),
    batch('chicken-pitta', 'Chicken kebab pitta box', 'Dinner',
          [(CHICKEN, 180), ('Wholemeal pitta', 80), ('Peppers (trimmed)', 150),
           (ONION, 75), ('Broccoli', 150), (OIL, 10), ('Kebab spice mix (generic estimate)', 3)],
          'Slice chicken, peppers and onions; toss with oil and spices. Spread over trays '
          'and roast at 200°C fan for about 20–25 minutes until chicken is cooked through. '
          'Cook broccoli according to the packet. Portion the filling and broccoli.',
          'Freeze 80g pitta per serving SEPARATELY from the filling. Reheat filling until '
          'steaming hot, toast or warm pitta separately and assemble just before eating. '
          'Do not freeze wet sauces or salad inside the bread.'),
    batch('pork-sweet-potato', 'Pork and sweet-potato patties', 'Dinner',
          [(PORK, 200), ('Sweet potato (raw, edible portion)', 250), (EGG, 25),
           ('Peas', 100), ('Broccoli', 150), (ONION, 30), (OIL, 5), (PAPRIKA, 2)],
          'Roast sweet potato chunks until tender at 200°C fan, then mash and cool promptly. '
          'Mix with raw pork, 175g beaten egg for the batch, finely chopped onion and paprika. '
          'Shape into 21 patties on lined trays, brush with oil and bake at 200°C fan for '
          'about 25–30 minutes until set and pork is cooked through. Cook peas and broccoli '
          'according to their packets. Pack three patties per portion.',
          'Freeze cooled patties in a single layer before packing. These have no breadcrumb coating.'),
]


def main():
    FOODS.update(EXTRA_FOODS)
    db_path = Path(database.DATABASE).resolve()
    if not db_path.is_file():
        raise RuntimeError('Existing workout database not found; no database was created.')
    backup_path = db_path.with_name('workouts.before-freezer-recipes-' +
                                   datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.db')
    with closing(database.get_db()) as conn:
        with closing(sqlite3.connect(backup_path)) as backup:
            conn.backup(backup)
        before = conn.execute('SELECT COUNT(*) FROM recipes').fetchone()[0]
        ids = [save_meal(conn, recipe) for recipe in RECIPES]
        after = conn.execute('SELECT COUNT(*) FROM recipes').fetchone()[0]
        assert len(ids) == len(set(ids)) == 11
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
        for recipe_id in ids:
            row = conn.execute('''SELECT r.name, r.servings, COUNT(ri.id),
                ROUND(SUM(f.calories * ri.grams / 100) / r.servings),
                ROUND(SUM(f.protein_g * ri.grams / 100) / r.servings)
                FROM recipes r JOIN recipe_ingredients ri ON ri.recipe_id = r.id
                JOIN foods f ON f.id = ri.food_id WHERE r.id = ? GROUP BY r.id''',
                (recipe_id,)).fetchone()
            assert row is not None and row[1] == 7 and row[2] > 0
            print(f'{recipe_id}: {row[0]} | {row[1]:g} servings | {row[3]:g} kcal | {row[4]:g}g protein')
    print(f'Added {after - before} recipes. Backup: {backup_path}')


if __name__ == '__main__':
    main()
