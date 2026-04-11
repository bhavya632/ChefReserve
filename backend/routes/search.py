import json
from urllib.parse import urlparse

from flask import Blueprint, request, jsonify
from lib.firebase_client import db

_UNITS = {
    "cup", "cups", "c", "tbsp", "tsp", "tablespoon", "tablespoons",
    "teaspoon", "teaspoons", "oz", "ounce", "ounces", "lb", "lbs",
    "pound", "pounds", "g", "gram", "grams", "kg", "ml", "liter",
    "liters", "quart", "quarts", "pint", "pints", "stick", "sticks",
    "clove", "cloves", "can", "cans", "bunch", "bunches", "sprig",
    "sprigs", "pinch", "dash", "handful", "slice", "slices", "piece",
    "pieces", "package", "packages", "jar", "jars",
}


def parse_pantry_item(raw: str) -> dict:
    """
    Parse a pantry entry that may include a quantity.
      "eggs"          → name="eggs",  quantity=None, unit=None
      "3 eggs"        → name="eggs",  quantity=3,    unit=None
      "6 oz beans"    → name="beans", quantity=6,    unit="oz"
      "1/2 cup flour" → name="flour", quantity=0.5,  unit="cup"
    Returns {"name": str, "quantity": float|None, "unit": str|None, "raw": str}
    """
    words = raw.strip().lower().split()
    quantity = None
    unit = None
    start = 0

    if words:
        first = words[0].replace("½", "1/2").replace("¼", "1/4").replace("¾", "3/4")
        try:
            if "/" in first:
                n, d = first.split("/", 1)
                quantity = float(n) / float(d)
            else:
                quantity = float(first)
            start = 1
        except ValueError:
            pass

    if quantity is not None and start < len(words):
        candidate = words[start].rstrip(".")
        if candidate in _UNITS:
            unit = candidate
            start += 1

    name = " ".join(words[start:]).strip()
    return {"name": name or raw.strip().lower(), "quantity": quantity, "unit": unit, "raw": raw.strip()}

COLLECTION_NAME = "recipes"
BLOCKED_SOURCE_DOMAINS = {
    "cookbooks.com",
    "www.cookbooks.com",
}

search_bp = Blueprint("search", __name__)


def parse_ingredients_map(value, recipe_ingredients: list) -> dict:
    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {ingredient: "" for ingredient in recipe_ingredients}


def parse_ingredients_list(value, ingredients_map_value=None) -> list:
    if isinstance(value, list):
        parsed_list = [str(item).strip().lower() for item in value if str(item).strip()]
        if parsed_list:
            return parsed_list

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                parsed_list = [str(item).strip().lower() for item in parsed if str(item).strip()]
                if parsed_list:
                    return parsed_list
        except json.JSONDecodeError:
            pass

    parsed_map = parse_ingredients_map(ingredients_map_value, [])
    if parsed_map:
        return [str(key).strip().lower() for key in parsed_map.keys() if str(key).strip()]

    return []


def normalize_source_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return f"https://{url}"


def normalize_token(value: str) -> str:
    return str(value or "").strip().lower()


def normalize_tokens(values: list) -> list:
    tokens = []
    seen = set()
    for value in values:
        token = normalize_token(value)
        if token and token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def has_valid_source_url(url: str) -> bool:
    normalized = normalize_source_url(url)
    if not normalized:
        return False

    parsed = urlparse(normalized)
    return bool(
        parsed.scheme
        and parsed.netloc
        and "." in parsed.netloc
        and parsed.netloc.lower() not in BLOCKED_SOURCE_DOMAINS
    )


def pantry_name_tokens(pantry: list) -> set:
    """
    Extract ingredient name tokens from pantry items, stripping leading
    quantities and units so "3 eggs" and "6 oz beans" become {"eggs", "beans"}.
    """
    names = set()
    for item in pantry:
        parsed = parse_pantry_item(item)
        for word in parsed["name"].lower().split():
            names.add(word.strip(".,"))
    return names


def ingredient_matches_pantry(ingredient: str, pantry_names: set) -> bool:
    """
    Returns True if any pantry ingredient name appears as a word token
    inside the recipe ingredient string.
    "6 oz beans" matches "1 can (15 oz) black beans, drained" via token "beans".
    """
    tokens = set(ingredient.lower().replace(",", " ").replace("(", " ").replace(")", " ").split())
    return bool(tokens & pantry_names)


def compute_match_percent(recipe_ingredients: list, pantry: list) -> float:
    if not recipe_ingredients:
        return 0.0
    names = pantry_name_tokens(pantry)
    matched = sum(1 for ing in recipe_ingredients if ingredient_matches_pantry(ing, names))
    return round(matched / len(recipe_ingredients) * 100, 1)


def get_missing_ingredients(recipe_ingredients: list, pantry: list) -> list:
    names = pantry_name_tokens(pantry)
    return [i for i in recipe_ingredients if not ingredient_matches_pantry(i, names)]


def get_matched_ingredients(recipe_ingredients: list, pantry: list) -> list:
    names = pantry_name_tokens(pantry)
    return [i for i in recipe_ingredients if ingredient_matches_pantry(i, names)]


def serialize_recipe(doc_id: str, doc: dict, pantry: list):
    source_url = normalize_source_url(doc.get("source_url", ""))
    safe_source_url = source_url if has_valid_source_url(source_url) else ""

    recipe_ingredients = parse_ingredients_list(
        doc.get("ingredients_list", []),
        doc.get("ingredients_map", {}),
    )
    if not recipe_ingredients:
        return None

    ingredients_map = parse_ingredients_map(
        doc.get("ingredients_map", {}),
        recipe_ingredients,
    )
    match_pct = compute_match_percent(recipe_ingredients, pantry)

    return {
        "id": doc.get("id", doc_id),
        "name": doc.get("name", ""),
        "cuisine": doc.get("cuisine", ""),
        "meal_type": doc.get("meal_type", ""),
        "cook_time_min": doc.get("cook_time_min", 0),
        "servings": doc.get("servings", 0),
        "difficulty": doc.get("difficulty", ""),
        "ingredients_list": recipe_ingredients,
        "ingredients_map": ingredients_map,
        "instructions": doc.get("instructions", []),
        "match_percent": match_pct,
        "matched_ingredients": get_matched_ingredients(recipe_ingredients, pantry),
        "missing_ingredients": get_missing_ingredients(recipe_ingredients, pantry),
        "source_url": safe_source_url,
    }


def fetch_candidate_snapshots(pantry: list):
    # Use parsed ingredient names (not raw input) so "3 eggs" queries on "eggs"
    pantry_tokens = normalize_tokens(list(pantry_name_tokens(pantry)))
    if not pantry_tokens:
        return []

    snapshots_by_id = {}
    for i in range(0, len(pantry_tokens), 10):
        chunk = pantry_tokens[i:i + 10]
        query = db.collection(COLLECTION_NAME).where(
            "ingredient_tokens", "array_contains_any", chunk
        ).limit(150)
        for snapshot in query.stream():
            snapshots_by_id[snapshot.id] = snapshot

    if snapshots_by_id:
        return list(snapshots_by_id.values())

    return list(db.collection(COLLECTION_NAME).limit(150).stream())


@search_bp.route("/search", methods=["POST"])
def search_recipes():
    """
    Body: { pantry: ["chicken", "garlic", ...], min_match: 50 }
    Returns top 50 recipes with match % and missing ingredients.
    """
    data = request.get_json()
    pantry: list = data.get("pantry", [])
    min_match: float = data.get("min_match", 10.0)

    if not pantry:
        return jsonify({"error": "pantry is required"}), 400

    try:
        snapshots = fetch_candidate_snapshots(pantry)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    all_candidate_recipes = []
    for snapshot in snapshots:
        recipe = serialize_recipe(snapshot.id, snapshot.to_dict(), pantry)
        if recipe:
            all_candidate_recipes.append(recipe)

    matched_recipes = [
        recipe for recipe in all_candidate_recipes
        if recipe["match_percent"] >= min_match
    ]

    if not matched_recipes:
        matched_recipes = [
            recipe for recipe in all_candidate_recipes
            if recipe["match_percent"] > 0
        ]

    matched_recipes.sort(
        key=lambda recipe: (
            recipe["match_percent"],
            len(recipe["matched_ingredients"]),
            -len(recipe["missing_ingredients"]),
        ),
        reverse=True,
    )
    matched_recipes = matched_recipes[:50]

    return jsonify({"recipes": matched_recipes, "total": len(matched_recipes)})
