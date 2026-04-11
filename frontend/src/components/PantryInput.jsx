import { useState } from "react";

const SUGGESTIONS = [
  "chicken breast", "garlic", "onion", "olive oil", "butter", "eggs",
  "flour", "salt", "pepper", "tomatoes", "potatoes", "rice", "pasta",
  "lemon", "cumin", "paprika", "ginger", "soy sauce", "cream", "milk",
  "cheddar", "parmesan", "spinach", "broccoli", "carrots", "bell pepper",
];

export default function PantryInput({ onSearch, loading }) {
  const [input, setInput] = useState("");
  const [ingredients, setIngredients] = useState([]);
  const [suggestions, setSuggestions] = useState([]);

  function handleInputChange(e) {
    const val = e.target.value;
    setInput(val);
    if (val.length > 1) {
      setSuggestions(
        SUGGESTIONS.filter(
          (s) => s.includes(val.toLowerCase()) && !ingredients.includes(s)
        ).slice(0, 5)
      );
    } else {
      setSuggestions([]);
    }
  }

  function addIngredient(name) {
    const clean = name.trim().toLowerCase();
    if (!clean || ingredients.includes(clean)) return;
    setIngredients((prev) => [...prev, clean]);
    setInput("");
    setSuggestions([]);
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addIngredient(input);
    }
  }

  function removeIngredient(name) {
    setIngredients((prev) => prev.filter((i) => i !== name));
  }

  return (
    <div className="w-full max-w-xl mx-auto">
      {/* Tag list */}
      <div className="flex flex-wrap gap-2 mb-3 min-h-[2.5rem]">
        {ingredients.map((ing) => (
          <span
            key={ing}
            className="flex items-center gap-1 bg-amber-100 text-amber-900 text-sm px-3 py-1 rounded-full font-medium"
          >
            {ing}
            <button
              onClick={() => removeIngredient(ing)}
              className="text-amber-500 hover:text-amber-800 leading-none ml-1"
            >
              ×
            </button>
          </span>
        ))}
      </div>

      {/* Input */}
      <div className="relative">
        <input
          type="text"
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder="Type an ingredient and press Enter..."
          className="w-full border-2 border-stone-200 rounded-xl px-4 py-3 text-stone-800 focus:outline-none focus:border-amber-400 text-base"
        />
        {/* Suggestions dropdown */}
        {suggestions.length > 0 && (
          <ul className="absolute z-10 w-full bg-white border border-stone-200 rounded-xl mt-1 shadow-md overflow-hidden">
            {suggestions.map((s) => (
              <li
                key={s}
                onClick={() => addIngredient(s)}
                className="px-4 py-2 hover:bg-amber-50 cursor-pointer text-stone-700 text-sm"
              >
                {s}
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="text-xs text-stone-400 mt-2">
        Press Enter or comma to add each ingredient
      </p>

      {/* Search button */}
      <button
        onClick={() => onSearch(ingredients)}
        disabled={ingredients.length === 0 || loading}
        className="mt-4 w-full bg-amber-500 hover:bg-amber-600 disabled:bg-stone-200 disabled:text-stone-400 text-white font-semibold py-3 rounded-xl transition-colors text-base"
      >
        {loading ? "Finding recipes…" : `Find Recipes (${ingredients.length} ingredients)`}
      </button>
    </div>
  );
}
