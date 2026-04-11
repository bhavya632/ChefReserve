import { useNavigate } from "react-router-dom";
import MatchBadge from "./MatchBadge";

export default function RecipeCard({ recipe }) {
  const navigate = useNavigate();

  const {
    id, name, match_percent, matched_ingredients, missing_ingredients,
    cook_time_min, servings, difficulty, cuisine, meal_type,
  } = recipe;

  const matchedList = Array.isArray(matched_ingredients) ? matched_ingredients : [];

  function openRecipe() {
    navigate(`/recipe/${id}`, { state: { recipe } });
  }

  return (
    <div
      className="bg-white rounded-2xl shadow-sm border border-stone-100 overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
      onClick={openRecipe}
    >
      <div className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-bold text-stone-800 text-base leading-tight capitalize">{name}</h3>
          <MatchBadge percent={match_percent} />
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-stone-500 mb-3">
          {cook_time_min > 0 && <span>⏱ {cook_time_min} min</span>}
          {servings > 0 && <span>👥 {servings} servings</span>}
          {difficulty && <span>💪 {difficulty}</span>}
          {cuisine && <span>🌍 {cuisine}</span>}
          {meal_type && <span>🍽 {meal_type}</span>}
        </div>

        {/* Matched ingredients */}
        {matchedList.length > 0 && (
          <div className="bg-green-50 rounded-xl px-3 py-2 mb-3">
            <p className="text-xs font-semibold text-green-700 mb-1">
              You have {matchedList.length} ingredient{matchedList.length > 1 ? "s" : ""}:
            </p>
            <p className="text-xs text-green-700 capitalize">{matchedList.join(", ")}</p>
          </div>
        )}

        {missing_ingredients?.length > 0 && (
          <div className="bg-red-50 rounded-xl px-3 py-2 mb-2">
            <p className="text-xs font-semibold text-red-600 mb-1">
              Missing {missing_ingredients.length} ingredient{missing_ingredients.length > 1 ? "s" : ""}:
            </p>
            <p className="text-xs text-red-500 capitalize">{missing_ingredients.join(", ")}</p>
          </div>
        )}

        <p className="text-xs text-amber-600 font-medium mt-2">Tap to view full recipe →</p>
      </div>
    </div>
  );
}
