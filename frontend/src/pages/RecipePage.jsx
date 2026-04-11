import { useLocation, useNavigate } from "react-router-dom";
import MatchBadge from "../components/MatchBadge";

export default function RecipePage() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const recipe = state?.recipe;

  if (!recipe) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-stone-500 mb-4">Recipe not found.</p>
          <button onClick={() => navigate(-1)} className="text-amber-600 font-medium hover:underline">
            ← Go back
          </button>
        </div>
      </div>
    );
  }

  const {
    name, match_percent, matched_ingredients, missing_ingredients,
    cook_time_min, servings, difficulty, cuisine, meal_type,
    instructions, ingredients_list, ingredients_map, source_url,
  } = recipe;

  const safeIngredientsMap =
    ingredients_map && typeof ingredients_map === "object" && !Array.isArray(ingredients_map)
      ? ingredients_map : {};
  const normalizedSourceUrl =
    source_url && !source_url.startsWith("http://") && !source_url.startsWith("https://")
      ? `https://${source_url}` : source_url;
  const ingredientKeys = Object.keys(safeIngredientsMap);
  const fallbackIngredients = Array.isArray(ingredients_list) ? ingredients_list : [];
  const visibleIngredients = ingredientKeys.length > 0
    ? ingredientKeys.map((ing) => ({ name: ing, amount: safeIngredientsMap[ing] }))
    : fallbackIngredients.map((ing) => ({ name: ing, amount: "" }));
  const matchedSet = new Set(matched_ingredients || []);
  const missingSet = new Set(missing_ingredients || []);

  return (
    <div className="min-h-screen bg-stone-50">
      {/* Header */}
      <header className="sticky top-0 bg-white border-b border-stone-100 z-10 px-4 py-3 flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-stone-500 hover:text-stone-800 text-sm">
          ← Back
        </button>
        <h1 className="font-bold text-stone-800 text-sm flex-1 truncate capitalize">{name}</h1>
        <MatchBadge percent={match_percent} />
      </header>

      <main className="max-w-xl mx-auto px-4 py-6 space-y-6">
        {/* Meta */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-stone-500">
          {cook_time_min > 0 && <span>⏱ {cook_time_min} min</span>}
          {servings > 0 && <span>👥 {servings} servings</span>}
          {difficulty && <span>💪 {difficulty}</span>}
          {cuisine && <span>🌍 {cuisine}</span>}
          {meal_type && <span>🍽 {meal_type}</span>}
        </div>

        {/* Matched ingredients */}
        {matched_ingredients?.length > 0 && (
          <div className="bg-green-50 rounded-xl px-4 py-3">
            <p className="text-sm font-semibold text-green-700 mb-1">
              You have {matched_ingredients.length} ingredient{matched_ingredients.length > 1 ? "s" : ""}:
            </p>
            <p className="text-sm text-green-700 capitalize">{matched_ingredients.join(", ")}</p>
          </div>
        )}

        {/* Missing ingredients */}
        {missing_ingredients?.length > 0 && (
          <div className="bg-red-50 rounded-xl px-4 py-3">
            <p className="text-sm font-semibold text-red-600 mb-1">
              Missing {missing_ingredients.length} ingredient{missing_ingredients.length > 1 ? "s" : ""}:
            </p>
            <p className="text-sm text-red-500 capitalize">{missing_ingredients.join(", ")}</p>
          </div>
        )}

        {/* Ingredients */}
        <div>
          <h2 className="font-bold text-stone-800 text-base mb-3">Ingredients</h2>
          <ul className="space-y-2">
            {visibleIngredients.map(({ name: ing, amount }) => (
              <li
                key={ing}
                className={`text-sm flex items-center gap-2 capitalize ${
                  missingSet.has(ing) ? "text-red-400 line-through" : "text-stone-600"
                }`}
              >
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                  matchedSet.has(ing) ? "bg-green-400" : missingSet.has(ing) ? "bg-red-300" : "bg-stone-300"
                }`} />
                {ing}
                {amount && <span className="text-stone-400 text-xs">— {amount}</span>}
              </li>
            ))}
          </ul>
        </div>

        {/* Instructions */}
        {instructions?.length > 0 && (
          <div>
            <h2 className="font-bold text-stone-800 text-base mb-3">Instructions</h2>
            <ol className="space-y-4">
              {instructions.map((step, i) => (
                <li key={i} className="flex gap-3">
                  <span className="font-bold text-amber-500 flex-shrink-0 text-sm mt-0.5">{i + 1}.</span>
                  <span className="text-sm text-stone-600">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Source link */}
        {normalizedSourceUrl && (
          <a
            href={normalizedSourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block text-sm text-amber-500 hover:underline"
          >
            View original recipe →
          </a>
        )}
      </main>
    </div>
  );
}
