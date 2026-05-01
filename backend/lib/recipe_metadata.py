import re


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
