from flask import Blueprint, request, jsonify
import requests
from bs4 import BeautifulSoup
from lib.firebase_client import db
import uuid
from datetime import datetime
from urllib.parse import urlparse

scraper_bp = Blueprint("scraper", __name__)
COLLECTION_NAME = "recipes"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def normalize_source_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return f"https://{url}"


def has_valid_source_url(url: str) -> bool:
    parsed = urlparse(normalize_source_url(url))
    return bool(parsed.scheme and parsed.netloc and "." in parsed.netloc)


def compute_ingredient_tokens(ingredients_list: list) -> list:
    tokens = []
    seen = set()
    for ingredient in ingredients_list:
        for token in str(ingredient).lower().replace(",", " ").split():
            cleaned = token.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                tokens.append(cleaned)
    return tokens


def parse_recipe_from_url(url: str) -> dict:
    """
    Attempts to extract recipe data from any URL using JSON-LD schema.org/Recipe.
    Falls back to basic HTML parsing if schema not found.
    """
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Try schema.org/Recipe JSON-LD first (works on most recipe sites) ---
    import json as _json
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = _json.loads(script.string)
            # Handle @graph wrapper
            if isinstance(data, dict) and "@graph" in data:
                data = next((d for d in data["@graph"] if "Recipe" in str(d.get("@type", ""))), {})
            if isinstance(data, list):
                data = next((d for d in data if "Recipe" in str(d.get("@type", ""))), {})

            if "Recipe" in str(data.get("@type", "")):
                # Extract ingredients
                raw_ingredients = data.get("recipeIngredient", [])
                ingredients_list = [i.strip().lower() for i in raw_ingredients]
                ingredients_flat = " ".join(ingredients_list)

                # Extract instructions
                instructions_raw = data.get("recipeInstructions", [])
                instructions = []
                for step in instructions_raw:
                    if isinstance(step, dict):
                        instructions.append(step.get("text", ""))
                    elif isinstance(step, str):
                        instructions.append(step)

                # Parse cook time (ISO 8601 duration like PT30M)
                cook_time_str = data.get("totalTime", data.get("cookTime", "PT0M"))
                cook_time_min = parse_iso_duration(cook_time_str)

                return {
                    "id": str(uuid.uuid4()),
                    "name": data.get("name", "Unknown Recipe"),
                    "source_url": normalize_source_url(url),
                    "cuisine": str(data.get("recipeCuisine", "")).lower(),
                    "meal_type": str(data.get("recipeCategory", "")).lower(),
                    "cook_time_min": cook_time_min,
                    "servings": parse_servings(data.get("recipeYield", "4")),
                    "difficulty": "",
                    "instructions": instructions,
                    "ingredients_list": ingredients_list,
                    "ingredient_tokens": compute_ingredient_tokens(ingredients_list),
                    "ingredients_flat": ingredients_flat,
                    "ingredients_map": {i: "" for i in ingredients_list},
                    "scraped_at": int(datetime.utcnow().timestamp()),
                }
        except Exception:
            continue

    raise ValueError("Could not extract a recipe from this URL. The site may not support schema.org/Recipe markup.")


def parse_iso_duration(duration: str) -> int:
    """Converts PT1H30M → 90 minutes."""
    import re
    hours = re.search(r"(\d+)H", duration)
    minutes = re.search(r"(\d+)M", duration)
    total = 0
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
    return total


def parse_servings(yield_val) -> int:
    if isinstance(yield_val, (int, float)):
        return int(yield_val)
    if isinstance(yield_val, list):
        yield_val = yield_val[0]
    import re
    match = re.search(r"\d+", str(yield_val))
    return int(match.group()) if match else 4


@scraper_bp.route("/scrape", methods=["POST"])
def scrape_recipe():
    """
    Body: { url: "https://www.allrecipes.com/recipe/..." }
    Parses the recipe, stores in Firebase, returns the recipe object.
    """
    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "url is required"}), 400

    try:
        recipe = parse_recipe_from_url(url)
    except Exception as e:
        return jsonify({"error": str(e)}), 422

    if not has_valid_source_url(recipe.get("source_url", "")):
        return jsonify({"error": "Recipe has no valid original URL"}), 422

    db.collection(COLLECTION_NAME).document(recipe["id"]).set(recipe)

    return jsonify({"recipe": recipe, "message": "Recipe imported successfully"})
