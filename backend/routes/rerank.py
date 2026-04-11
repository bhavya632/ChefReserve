from flask import Blueprint, request, jsonify
from groq import Groq
import os
import json
from dotenv import load_dotenv

load_dotenv()

_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

rerank_bp = Blueprint("rerank", __name__)


def normalize_text(value) -> str:
    return str(value or "").strip().lower()


def matches_text_filter(recipe_value, preference_value) -> bool:
    preference = normalize_text(preference_value)
    if not preference or preference == "any":
        return True

    recipe_text = normalize_text(recipe_value)
    if not recipe_text:
        return True  # no metadata — don't filter out, let Gemini rank it

    return preference in recipe_text


def matches_cook_time_filter(recipe, preferences: dict) -> bool:
    max_cook_time = preferences.get("max_cook_time")
    if max_cook_time in (None, "", "any"):
        return True

    recipe_cook_time = recipe.get("cook_time_min")
    if not isinstance(recipe_cook_time, (int, float)) or recipe_cook_time <= 0:
        return True  # unknown cook time — don't filter out

    return int(recipe_cook_time) <= int(max_cook_time)


def preference_match_score(recipe, preferences: dict) -> int:
    score = 0

    if matches_text_filter(recipe.get("cuisine", ""), preferences.get("cuisine", "any")):
        score += 3
    if matches_text_filter(recipe.get("meal_type", ""), preferences.get("meal_type", "any")):
        score += 2
    if matches_text_filter(recipe.get("spice_level", ""), preferences.get("spice_level", "any")):
        score += 2
    if matches_text_filter(recipe.get("difficulty", ""), preferences.get("difficulty", "any")):
        score += 1
    if matches_cook_time_filter(recipe, preferences):
        score += 2

    return score


def local_rank_score(recipe, preferences: dict) -> tuple:
    cook_time = recipe.get("cook_time_min", 0) or 0

    return (
        preference_match_score(recipe, preferences),
        recipe.get("match_percent", 0),
        -cook_time,
    )


@rerank_bp.route("/rerank", methods=["POST"])
def rerank_recipes():
    """
    Body: {
        recipes: [...],           # top 50 from /search
        preferences: {
            spice_level: "medium",
            cuisine: "Italian",
            meal_type: "dinner",
            max_cook_time: 30,
            difficulty: "easy"
        }
    }
    Returns all applicable recipe IDs in ranked order.
    """
    data = request.get_json()
    recipes: list = data.get("recipes", [])
    preferences: dict = data.get("preferences", {})
    pantry: list = data.get("pantry", [])

    if not recipes:
        return jsonify({"error": "recipes list is required"}), 400

    filtered_recipes = [
        recipe for recipe in recipes
        if matches_text_filter(recipe.get("cuisine", ""), preferences.get("cuisine", "any"))
        and matches_text_filter(recipe.get("meal_type", ""), preferences.get("meal_type", "any"))
        and matches_text_filter(recipe.get("difficulty", ""), preferences.get("difficulty", "any"))
        and matches_text_filter(recipe.get("spice_level", ""), preferences.get("spice_level", "any"))
        and matches_cook_time_filter(recipe, preferences)
    ]

    # If hard filter eliminated everything, relax only cook time as a last resort
    if not filtered_recipes:
        filtered_recipes = [
            recipe for recipe in recipes
            if matches_text_filter(recipe.get("cuisine", ""), preferences.get("cuisine", "any"))
            and matches_text_filter(recipe.get("meal_type", ""), preferences.get("meal_type", "any"))
            and matches_text_filter(recipe.get("difficulty", ""), preferences.get("difficulty", "any"))
            and matches_text_filter(recipe.get("spice_level", ""), preferences.get("spice_level", "any"))
        ]

    # If still nothing, return all sorted by score so user sees something
    candidate_recipes = filtered_recipes or sorted(
        recipes,
        key=lambda recipe: local_rank_score(recipe, preferences),
        reverse=True,
    )

    # Send only lightweight metadata to Gemini — not full recipe text
    recipe_summaries = [
        {
            "id": r["id"],
            "name": r["name"],
            "cuisine": r.get("cuisine", "unknown"),
            "meal_type": r.get("meal_type", "unknown"),
            "cook_time_min": r.get("cook_time_min", 0),
            "servings": r.get("servings", 0),
            "difficulty": r.get("difficulty", "unknown"),
            "match_percent": r.get("match_percent", 0),
        }
        for r in candidate_recipes
    ]

    prompt = f"""
You are a recipe recommendation engine. Given a list of recipes and user preferences, 
return the IDs of the best matching recipes in ranked order (best first).

Prefer recipes that best match the user preferences and pantry ingredients.
If there are no perfect matches, rank the closest alternatives instead of returning nothing.
Do not invent IDs. Return all candidate recipe IDs in ranked order.

Pantry ingredients:
{json.dumps(pantry)}

User Preferences:
- Spice level: {preferences.get("spice_level", "any")}
- Cuisine: {preferences.get("cuisine", "any")}
- Meal type: {preferences.get("meal_type", "any")}
- Max cook time: {preferences.get("max_cook_time", "any")} minutes
- Difficulty: {preferences.get("difficulty", "any")}

Recipes to rank:
{json.dumps(recipe_summaries, indent=2)}

Respond ONLY with a JSON array of recipe IDs, ranked best to worst.
Example: ["id1", "id2", "id3", ...]
No explanation, no extra text, just the JSON array.
"""

    recipe_map = {r["id"]: r for r in candidate_recipes}

    try:
        response = _groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        ranked_ids: list = json.loads(raw)
        ranked_recipes = [recipe_map[rid] for rid in ranked_ids if rid in recipe_map]
    except Exception:
        ranked_recipes = []

    if not ranked_recipes:
        ranked_recipes = sorted(
            candidate_recipes,
            key=lambda recipe: local_rank_score(recipe, preferences),
            reverse=True,
        )

    # Keep Gemini's order, then append any filtered recipes it omitted.
    seen_ids = {recipe["id"] for recipe in ranked_recipes}
    remaining_recipes = [
        recipe for recipe in sorted(
            candidate_recipes,
            key=lambda recipe: local_rank_score(recipe, preferences),
            reverse=True,
        )
        if recipe["id"] not in seen_ids
    ]
    ranked_recipes = ranked_recipes + remaining_recipes

    return jsonify({"ranked_recipes": ranked_recipes})
