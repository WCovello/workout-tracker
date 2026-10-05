"""Editable starter meals; generic nutrition estimates, not retailer labels."""

# kcal, protein, carbohydrate and fat per 100g, in the named weighing state.
FOODS = {
    'Porridge oats (dry)': (370, 12, 60, 8),
    'Plain skyr': (63, 11, 4, 0.2),
    'Semi-skimmed milk': (47, 3.6, 4.8, 1.7),
    'Mixed berries': (45, 1, 8, 0.5),
    'Eggs (without shells)': (143, 12.6, 0.7, 9.5),
    'Wholemeal bread': (240, 10, 40, 3.5),
    'Mushrooms': (22, 3, 0.5, 0.3),
    'Tomatoes': (18, 0.9, 3, 0.2),
    'Olive oil': (900, 0, 0, 100),
    'Apple (cored)': (52, 0.3, 12, 0.2),
    'Walnuts': (654, 15, 7, 65),
    'Chicken breast (raw, skinless)': (110, 24, 0, 1.5),
    'Peppers (trimmed)': (26, 1, 5, 0.3),
    'Onion (peeled)': (40, 1.1, 8, 0.1),
    'Rice (dry)': (355, 7, 78, 1),
    'Black beans (drained)': (100, 7, 14, 0.5),
    'Salsa': (35, 1, 6, 0.5),
    'Lemon or lime juice': (25, 0.4, 6, 0.1),
    'Tuna in spring water (drained)': (110, 25, 0, 1),
    'Wholewheat pasta (dry)': (350, 13, 65, 2.5),
    'Chickpeas (drained)': (120, 6.5, 16, 2),
    'Cucumber': (15, 0.7, 2, 0.1),
    'Beef mince 5% fat (raw)': (137, 21, 0, 5),
    'Kidney beans (drained)': (100, 7, 14, 0.5),
    'Tinned chopped tomatoes': (22, 1, 3.5, 0.2),
    'Spinach': (23, 2.9, 1.6, 0.4),
    'Salmon fillet (raw)': (208, 20, 0, 13),
    'Baby potatoes (raw)': (77, 2, 17, 0.1),
    'Broccoli': (34, 2.8, 4, 0.4),
    'Garlic (peeled)': (149, 6, 30, 0.5),
    'Ground spices': (300, 10, 40, 10),
}

ESTIMATE_NOTE = ('Nutrition is estimated from generic ingredients, not verified Sainsbury\'s '
                 'product labels. Weigh meat raw, grains dry and tinned beans/tuna drained. '
                 'For product-specific tracking, add your label values in Foods and swap '
                 'those ingredients using Edit Recipe.')
STORAGE = ('Cool cooked leftovers and refrigerate within 1–2 hours. Eat within 48 hours '
           'or freeze portions for later. Cool rice ideally within 1 hour; keep refrigerated '
           'for no more than 24 hours. Reheat only once, until steaming hot throughout. '
           'Defrost in the fridge and use within 24 hours of defrosting.')


def meal(slug, name, category, servings, ingredients, method, tip):
    return dict(slug=slug, name=name, category=category, servings=servings,
                ingredients=ingredients, method=method, tip=tip)


MEALS = [
    meal('berry-oats', 'Berry overnight oats', 'Breakfast', 2,
         [('Porridge oats (dry)', 80), ('Plain skyr', 400),
          ('Semi-skimmed milk', 160), ('Mixed berries', 200)],
         'Mix oats, skyr and milk, divide between two covered pots and add berries. '
         'Chill overnight. Follow berry packaging instructions, including cooking if required.',
         'Prepare two breakfasts at a time. Keep refrigerated and use within 48 hours or sooner if the dairy label requires.'),
    meal('eggs-toast', 'Eggs on toast with mushrooms and tomatoes', 'Breakfast', 1,
         [('Eggs (without shells)', 150), ('Wholemeal bread', 80),
          ('Mushrooms', 100), ('Tomatoes', 100), ('Olive oil', 5)],
         'Cook sliced mushrooms and tomatoes in the oil. Scramble the eggs until set '
         'and serve with toasted bread. 150g egg is approximately three medium eggs; weigh without shells.',
         'Best cooked fresh; slice the vegetables ahead to save time.'),
    meal('apple-skyr', 'Apple and cinnamon yoghurt bowl', 'Breakfast', 1,
         [('Plain skyr', 250), ('Apple (cored)', 150), ('Porridge oats (dry)', 30),
          ('Walnuts', 10), ('Ground spices', 1)],
         'Spoon skyr into a bowl. Top with chopped apple, oats, walnuts and cinnamon.',
         'Keep nuts and oats separate until serving for crunch.'),
    meal('fajita-bowls', 'Chicken fajita bowls', 'Lunch', 4,
         [('Chicken breast (raw, skinless)', 600), ('Peppers (trimmed)', 400),
          ('Onion (peeled)', 200), ('Rice (dry)', 200), ('Black beans (drained)', 240),
          ('Salsa', 120), ('Plain skyr', 160), ('Lemon or lime juice', 30),
          ('Olive oil', 15), ('Ground spices', 8)],
         'Slice chicken, peppers and onion. Toss with oil, paprika and cumin. Roast at '
         '200°C fan for about 20–25 minutes, until chicken is cooked through (75°C in the centre '
         'for 30 seconds). Cook rice following the packet and heat beans. Divide into four portions. '
         'Mix skyr with lime juice; keep dressing and salsa separate until serving.',
         'Freeze later portions promptly; cooked rice has a shorter fridge life than the chicken.'),
    meal('tuna-pasta', 'Tuna and chickpea pasta salad', 'Lunch', 2,
         [('Tuna in spring water (drained)', 240), ('Wholewheat pasta (dry)', 120),
          ('Chickpeas (drained)', 120), ('Cucumber', 150), ('Tomatoes', 200),
          ('Plain skyr', 100), ('Lemon or lime juice', 20)],
         'Cook pasta following the packet, drain and cool promptly. Mix with drained tuna '
         'and chickpeas, diced cucumber and tomatoes. Stir together skyr and lemon juice '
         'for the dressing. Divide into two covered lunchboxes and refrigerate.',
         'Eat within 48 hours. Keep chilled during transport; no microwave needed.'),
    meal('beef-chilli', 'Lean beef and kidney bean chilli', 'Dinner', 4,
         [('Beef mince 5% fat (raw)', 500), ('Kidney beans (drained)', 480),
          ('Tinned chopped tomatoes', 800), ('Peppers (trimmed)', 300),
          ('Onion (peeled)', 200), ('Rice (dry)', 200), ('Olive oil', 10),
          ('Garlic (peeled)', 10), ('Ground spices', 10)],
         'Soften chopped onion and peppers in oil. Add mince and brown thoroughly. '
         'Stir in garlic, cumin, paprika and chilli powder, then tomatoes and drained beans. '
         'Simmer for 25–30 minutes, stirring and adding water if needed. Cook rice following '
         'the packet. Divide chilli and rice into four equal portions.',
         'Freeze chilli separately for flexibility. If swapping beef for turkey, update the ingredient for accurate tracking.'),
    meal('chicken-curry', 'Chicken, chickpea and spinach curry', 'Dinner', 4,
         [('Chicken breast (raw, skinless)', 600), ('Chickpeas (drained)', 240),
          ('Tinned chopped tomatoes', 800), ('Spinach', 300), ('Onion (peeled)', 200),
          ('Rice (dry)', 200), ('Plain skyr', 160), ('Olive oil', 15),
          ('Garlic (peeled)', 10), ('Ground spices', 12)],
         'Soften chopped onion in oil. Add diced chicken, garlic and curry powder. '
         'Stir in tomatoes and drained chickpeas, then simmer for 20–25 minutes until '
         'chicken is cooked through (75°C in the centre for 30 seconds). Add spinach and '
         'cook until wilted. Cook rice following the packet. Divide into four servings '
         'and add skyr to each serving after reheating.',
         'Freeze curry without the skyr and add it when serving.'),
    meal('salmon-traybake', 'Lemon salmon traybake', 'Dinner', 2,
         [('Salmon fillet (raw)', 300), ('Baby potatoes (raw)', 500), ('Broccoli', 400),
          ('Lemon or lime juice', 30), ('Garlic (peeled)', 10), ('Olive oil', 10)],
         'Halve potatoes, toss with half the oil and roast at 200°C fan for 25 minutes. '
         'Add broccoli, salmon, garlic, remaining oil and lemon juice. Roast for another '
         '15–20 minutes, until potatoes are tender and salmon is opaque and flakes easily. '
         'Divide into two portions.',
         'Cook for dinner and keep the second portion for lunch the following day.'),
]


def nutrition(meal):
    return {key: sum(FOODS[name][index] * grams / 100 for name, grams in meal['ingredients'])
            / meal['servings']
            for index, key in enumerate(('calories', 'protein_g', 'carbs_g', 'fat_g'))}


def save_meal(conn, meal):
    """Import atomically; stable keys avoid duplicates even after recipe renaming."""
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        existing = conn.execute('SELECT recipe_id FROM starter_meal_imports WHERE slug = ?',
                                (meal['slug'],)).fetchone()
        if existing:
            return existing['recipe_id']
        instructions = '\n\n'.join((ESTIMATE_NOTE, meal['method'], meal['tip'], STORAGE))
        recipe_id = conn.execute('INSERT INTO recipes (name, servings, instructions) VALUES (?, ?, ?)',
                                 (meal['name'], meal['servings'], instructions)).lastrowid
        for name, grams in meal['ingredients']:
            brand = 'Meal ideas • generic estimate'
            conn.execute('''INSERT OR IGNORE INTO foods
                (name, brand, calories, protein_g, carbs_g, fat_g, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)''', (name, brand, *FOODS[name], ESTIMATE_NOTE))
            food_id = conn.execute('SELECT id FROM foods WHERE name = ? AND brand = ?',
                                   (name, brand)).fetchone()['id']
            conn.execute('INSERT INTO recipe_ingredients (recipe_id, food_id, grams) VALUES (?, ?, ?)',
                         (recipe_id, food_id, grams))
        conn.execute('INSERT INTO starter_meal_imports (slug, recipe_id) VALUES (?, ?)',
                     (meal['slug'], recipe_id))
    return recipe_id
