#!/usr/bin/env python3
"""
ChefReserve Web Crawler
Crawls recipe websites from homepage URLs, enriches each recipe with Groq
(cuisine, meal_type, difficulty, spice_level), and saves to Firestore.

Usage:
  python crawl_and_scrape.py <url1> [url2] ...

Examples:
  python crawl_and_scrape.py https://www.epicurious.com https://www.aparnas-kitchen.com

Tuning (env vars):
  CRAWL_DELAY=1.0        Seconds between requests         (default: 1.0)
  CRAWL_MAX_PAGES=500    Max pages visited per site        (default: 500)
  CRAWL_MAX_DEPTH=3      Max link depth from the homepage  (default: 3)

Requires:
  FIREBASE_SERVICE_ACCOUNT in .env (path to service-account JSON)
  GROQ_API_KEY in .env
"""

import json
import os
import re
import sys
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import firebase_admin
from groq import Groq
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
COLLECTION = "recipes"
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", "1.0"))
ENRICH_DELAY = float(os.getenv("ENRICH_DELAY", "3.0"))
MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", "500"))
MAX_DEPTH = int(os.getenv("CRAWL_MAX_DEPTH", "3"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------------------------
# Firebase
# ---------------------------------------------------------------------------

def init_firestore():
    if firebase_admin._apps:
        return firestore.client()
    path = os.getenv("FIREBASE_SERVICE_ACCOUNT", "").strip()
    if path:
        cred = credentials.Certificate(path)
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()
    return firestore.client()

# ---------------------------------------------------------------------------
# Groq enrichment
# ---------------------------------------------------------------------------

_groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

_CUISINE_ALIASES = {
    "american": {
        "american", "north american", "united states", "us", "u.s.", "usa",
        "u.s.a.", "us canada", "u.s. canada", "canada", "canadian",
        "southern", "cajun", "creole",
    },
    "italian": {"italian", "tuscan", "sicilian"},
    "mexican": {"mexican", "tex mex", "texmex"},
    "asian": {
        "asian", "asian inspired", "vietnamese", "filipino", "indonesian",
        "malaysian", "singaporean",
    },
    "mediterranean": {"mediterranean"},
    "indian": {"indian"},
    "french": {"french"},
    "middle eastern": {
        "middle eastern", "middle east", "lebanese", "turkish", "persian",
        "israeli",
    },
    "greek": {"greek"},
    "japanese": {"japanese"},
    "chinese": {"chinese", "cantonese", "hunan", "sichuan", "szechuan"},
    "thai": {"thai"},
    "korean": {"korean"},
    "spanish": {"spanish"},
    "other": {"other"},
}

_MEAL_TYPE_ALIASES = {
    "breakfast": {"breakfast", "brunch"},
    "lunch": {"lunch"},
    "dinner": {"dinner", "main course", "main dish", "entree", "supper"},
    "snack": {"snack"},
    "dessert": {"dessert", "sweet", "baking"},
    "appetizer": {"appetizer", "starter", "hors d oeuvre", "hors d'oeuvre"},
    "other": {"other"},
}

_DIFFICULTY_ALIASES = {
    "easy": {"easy", "beginner", "simple"},
    "medium": {"medium", "intermediate", "moderate"},
    "hard": {"hard", "advanced", "difficult"},
}

_SPICE_LEVEL_ALIASES = {
    "mild": {"mild", "not spicy"},
    "medium": {"medium", "moderate"},
    "hot": {"hot", "spicy", "very spicy"},
}

_ENRICH_PROMPT = """You are a recipe classifier. Given a recipe name and ingredients, return ONLY a JSON object with these exact keys:
- cuisine: one of [italian, mexican, asian, american, mediterranean, indian, french, middle eastern, greek, japanese, chinese, thai, korean, spanish, other]
- meal_type: one of [breakfast, lunch, dinner, snack, dessert, appetizer, other]
- difficulty: one of [easy, medium, hard]
- spice_level: one of [mild, medium, hot]

Recipe name: {name}
Ingredients: {ingredients}

Respond with only the JSON object, no explanation."""


def enrich_recipe(name: str, ingredients: list) -> dict:
    """
    Call Groq (Llama 3) to classify cuisine, meal_type, difficulty, spice_level.
    Returns a dict with those four keys, or empty strings on failure.
    """
    prompt = _ENRICH_PROMPT.format(
        name=name,
        ingredients=", ".join(ingredients[:20]),
    )
    try:
        response = _groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=128,
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        time.sleep(ENRICH_DELAY)
        return {
            "cuisine": result.get("cuisine", ""),
            "meal_type": result.get("meal_type", ""),
            "difficulty": result.get("difficulty", ""),
            "spice_level": result.get("spice_level", ""),
        }
    except Exception as e:
        print(f"\n  [enrich error] {e.__class__.__name__}: {e}")

    return {"cuisine": "", "meal_type": "", "difficulty": "", "spice_level": ""}


def _flatten_value(value) -> str:
    if isinstance(value, list):
        return " ".join(str(item or "") for item in value)
    return str(value or "")


def _normalize_variants(value) -> list[str]:
    raw = _flatten_value(value).strip().lower()
    if not raw:
        return []

    cleaned = raw.replace("&", " and ")
    parts = [
        part.strip()
        for part in re.split(r"[/,;|]|(?:\band\b)", cleaned)
        if part.strip()
    ]
    variants = []
    for part in parts or [cleaned]:
        normalized = re.sub(r"[^a-z0-9\s]", " ", part)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if normalized:
            variants.append(normalized)
    return variants


def _canonicalize(value, aliases: dict[str, set[str]], default: str = "") -> str:
    variants = _normalize_variants(value)
    if not variants:
        return default

    for variant in variants:
        for canonical, known_aliases in aliases.items():
            if variant == canonical or variant in known_aliases:
                return canonical

    for variant in variants:
        for canonical in aliases.keys():
            if canonical in variant:
                return canonical

    return default or variants[0]


def normalize_cuisine(value) -> str:
    return _canonicalize(value, _CUISINE_ALIASES, default="")


def normalize_meal_type(value) -> str:
    return _canonicalize(value, _MEAL_TYPE_ALIASES, default="")


def normalize_difficulty(value) -> str:
    return _canonicalize(value, _DIFFICULTY_ALIASES, default="")


def normalize_spice_level(value) -> str:
    return _canonicalize(value, _SPICE_LEVEL_ALIASES, default="")

# ---------------------------------------------------------------------------
# Recipe extraction helpers
# ---------------------------------------------------------------------------

def parse_iso_duration(duration: str) -> int:
    """Parse cook time from ISO 8601 (PT1H30M) or plain text (1 hr 30 min, 20 min, 1.5 hours)."""
    s = str(duration or "").strip()
    if not s:
        return 0

    # ISO 8601: PT1H30M
    if s.upper().startswith("PT"):
        hours = re.search(r"(\d+)H", s)
        mins = re.search(r"(\d+)M", s)
        return (int(hours.group(1)) if hours else 0) * 60 + (int(mins.group(1)) if mins else 0)

    # Plain text: "1 hr 30 min", "20 min", "1.5 hours", "1 hour"
    total = 0
    hour_match = re.search(r"([\d.]+)\s*h(?:ou?r?s?)?", s, re.IGNORECASE)
    min_match = re.search(r"([\d.]+)\s*m(?:in(?:utes?)?)?", s, re.IGNORECASE)
    if hour_match:
        total += int(float(hour_match.group(1)) * 60)
    if min_match:
        total += int(float(min_match.group(1)))
    return total


_NOISE_TOKENS = {
    # units
    "cup", "cups", "c", "tbsp", "tbsp.", "tsp", "tsp.", "tablespoon", "tablespoons",
    "teaspoon", "teaspoons", "oz", "oz.", "ounce", "ounces", "lb", "lb.", "lbs",
    "pound", "pounds", "g", "gram", "grams", "kg", "ml", "liter", "liters",
    "quart", "quarts", "pint", "pints", "gallon", "gallons", "stick", "sticks",
    "bunch", "bunches", "clove", "cloves", "slice", "slices", "piece", "pieces",
    "sprig", "sprigs", "pinch", "dash", "handful", "package", "packages",
    "can", "cans", "jar", "jars", "bag", "bags",
    # filler words
    "a", "an", "the", "of", "or", "and", "to", "for", "with", "plus",
    "more", "about", "into", "from", "at", "in", "per",
}


def compute_ingredient_tokens(ingredients: list) -> list:
    """
    Build a clean search index — strips numbers, measurement units, and filler
    words. Full strings with measurements stay in ingredients_list for display.
    """
    seen = set()
    tokens = []
    for ing in ingredients:
        for word in str(ing).lower().replace(",", " ").replace("(", " ").replace(")", " ").split():
            word = word.strip(".")
            if not word or word in _NOISE_TOKENS:
                continue
            if all(c.isdigit() or c in "./½¼¾⅓⅔⅛-" for c in word):
                continue
            if word not in seen:
                seen.add(word)
                tokens.append(word)
    return tokens


def extract_recipe(soup: BeautifulSoup, url: str) -> dict | None:
    """
    Scan all JSON-LD <script> blocks for a schema.org/Recipe object.
    Returns a Firestore-ready recipe dict (with Groq enrichment), or None.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(data, dict) and "@graph" in data:
            items = data["@graph"]
        elif isinstance(data, list):
            items = data
        else:
            items = [data]

        for item in items:
            if not isinstance(item, dict):
                continue
            rtype = item.get("@type", "")
            if isinstance(rtype, list):
                rtype = " ".join(rtype)
            if "Recipe" not in rtype:
                continue

            name = (item.get("name") or "").strip()
            raw_ings = item.get("recipeIngredient") or []
            ingredients_list = [str(i).strip().lower() for i in raw_ings if str(i).strip()]

            if not name or not ingredients_list:
                continue

            # Instructions
            instructions = []
            for step in item.get("recipeInstructions") or []:
                text = step.get("text", "").strip() if isinstance(step, dict) else str(step).strip()
                if text:
                    instructions.append(text)

            cook_time_min = parse_iso_duration(
                item.get("totalTime") or item.get("cookTime") or ""
            )

            recipe_yield = item.get("recipeYield", "4")
            if isinstance(recipe_yield, list):
                recipe_yield = recipe_yield[0] if recipe_yield else "4"
            nums = re.findall(r"\d+", str(recipe_yield))
            servings = int(nums[0]) if nums else 4

            # Use normalized site metadata where available, fill gaps with Groq.
            site_cuisine = normalize_cuisine(item.get("recipeCuisine") or "")
            site_meal_type = normalize_meal_type(item.get("recipeCategory") or "")

            enriched = enrich_recipe(name, ingredients_list)

            cuisine = site_cuisine or normalize_cuisine(enriched.get("cuisine", ""))
            meal_type = site_meal_type or normalize_meal_type(enriched.get("meal_type", ""))
            difficulty = normalize_difficulty(enriched.get("difficulty", ""))
            spice_level = normalize_spice_level(enriched.get("spice_level", ""))

            return {
                "id": str(uuid.uuid4()),
                "name": name,
                "source_url": url,
                "cuisine": cuisine,
                "meal_type": meal_type,
                "cook_time_min": cook_time_min,
                "servings": servings,
                "difficulty": difficulty,
                "spice_level": spice_level,
                "ingredients_list": ingredients_list,
                "ingredient_tokens": compute_ingredient_tokens(ingredients_list),
                "ingredients_flat": " ".join(ingredients_list),
                "ingredients_map": {i: "" for i in ingredients_list},
                "instructions": instructions,
                "scraped_at": int(datetime.now(timezone.utc).timestamp()),
            }

    return None

# ---------------------------------------------------------------------------
# Link crawling
# ---------------------------------------------------------------------------

def same_domain_links(soup: BeautifulSoup, page_url: str) -> list:
    """Return all same-domain absolute URLs found on the page."""
    base = urlparse(page_url)
    seen = set()
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(page_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != base.netloc:
            continue
        clean = parsed._replace(fragment="").geturl()
        if clean not in seen:
            seen.add(clean)
            links.append(clean)
    return links


def already_saved(db, source_url: str) -> bool:
    docs = db.collection(COLLECTION).where("source_url", "==", source_url).limit(1).stream()
    return any(True for _ in docs)

# ---------------------------------------------------------------------------
# Main crawler
# ---------------------------------------------------------------------------

def crawl_site(db, homepage: str, session: requests.Session) -> int:
    domain = urlparse(homepage).netloc
    print(f"\n{'─' * 64}")
    print(f"  Site : {domain}")
    print(f"  Seed : {homepage}")
    print(f"  Limit: {MAX_PAGES} pages  depth ≤ {MAX_DEPTH}  delay {CRAWL_DELAY}s")
    print(f"{'─' * 64}")

    queue: deque = deque([(homepage, 0)])
    visited: set = set()
    saved = skipped = errors = 0

    while queue and len(visited) < MAX_PAGES:
        url, depth = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        label = (url[:70] + "…") if len(url) > 70 else url
        print(f"  [{len(visited):>4}/{MAX_PAGES}] d={depth}  {label}", end=" ", flush=True)

        try:
            resp = session.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"✗ {e.__class__.__name__}")
            errors += 1
            time.sleep(CRAWL_DELAY)
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        if already_saved(db, url):
            print("⟳ already saved")
            skipped += 1
        else:
            recipe = extract_recipe(soup, url)
            if recipe:
                db.collection(COLLECTION).document(recipe["id"]).set(recipe)
                saved += 1
                tags = f"[{recipe['cuisine']} | {recipe['meal_type']} | {recipe['difficulty']} | {recipe['spice_level']}]"
                print(f"✓ {recipe['name'][:35]} {tags}")
            else:
                print("· no recipe")

        if depth < MAX_DEPTH:
            for link in same_domain_links(soup, url):
                if link not in visited:
                    queue.append((link, depth + 1))

        time.sleep(CRAWL_DELAY)

    print(
        f"\n  ✓ {saved} saved  "
        f"⟳ {skipped} already saved  "
        f"✗ {errors} errors  "
        f"({len(visited)} pages visited)"
    )
    return saved


def main(seed_urls: list):
    db = init_firestore()
    session = requests.Session()
    total = 0
    for raw in seed_urls:
        if not raw.startswith(("http://", "https://")):
            raw = "https://" + raw
        total += crawl_site(db, raw, session)

    print(f"\n{'=' * 64}")
    print(f"  Total recipes saved: {total}")
    print(f"{'=' * 64}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
