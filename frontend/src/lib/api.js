import axios from "axios";

const BASE = process.env.REACT_APP_BACKEND_URL || "http://localhost:5000";

// Search recipes by pantry ingredients
export async function searchRecipes(pantry, minMatch = 10) {
  const { data } = await axios.post(`${BASE}/api/search`, {
    pantry,
    min_match: minMatch,
  });
  return data; // { recipes: [...], total: N }
}

// Rerank with Groq using user preferences
export async function rerankRecipes(recipes, preferences, pantry = []) {
  const { data } = await axios.post(`${BASE}/api/rerank`, {
    recipes,
    preferences,
    pantry,
  });
  return data; // { ranked_recipes: [...] }
}

// Import a recipe by URL (BS4 scraper)
export async function importRecipeFromUrl(url) {
  const { data } = await axios.post(`${BASE}/api/scrape`, { url });
  return data; // { recipe: {...}, message: "..." }
}
