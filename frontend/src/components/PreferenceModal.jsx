import { useState } from "react";

const SPICE_OPTIONS = ["mild", "medium", "hot", "any"];
const CUISINE_OPTIONS = [
  "any", "italian", "mexican", "asian", "american", "mediterranean",
  "indian", "french", "middle eastern", "greek", "japanese", "chinese",
  "thai", "korean", "spanish",
];
const MEAL_OPTIONS = ["any", "breakfast", "lunch", "dinner", "snack", "dessert", "appetizer"];
const DIFFICULTY_OPTIONS = ["any", "easy", "medium", "hard"];

const STORAGE_KEY = "chefreserve_prefs";
const DEFAULT_PREFS = {
  spice_level: "any",
  cuisine: "any",
  meal_type: "any",
  max_cook_time: 180,
  difficulty: "any",
};

function loadPrefs() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return { ...DEFAULT_PREFS, ...JSON.parse(saved) };
  } catch {}
  return DEFAULT_PREFS;
}

export default function PreferenceModal({ onSubmit, onSkip }) {
  const [prefs, setPrefs] = useState(loadPrefs);

  function set(key, val) {
    setPrefs((p) => ({ ...p, [key]: val }));
  }

  function handleSubmit() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch {}
    onSubmit(prefs);
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl">
        <h2 className="text-xl font-bold text-stone-800 mb-1">Refine your results</h2>
        <p className="text-stone-500 text-sm mb-5">Help us find the perfect recipe for you</p>

        {/* Spice level */}
        <Label>Spice level</Label>
        <ChipGroup options={SPICE_OPTIONS} value={prefs.spice_level} onChange={(v) => set("spice_level", v)} />

        {/* Cuisine */}
        <Label>Cuisine</Label>
        <ChipGroup options={CUISINE_OPTIONS} value={prefs.cuisine} onChange={(v) => set("cuisine", v)} />

        {/* Meal type */}
        <Label>Meal type</Label>
        <ChipGroup options={MEAL_OPTIONS} value={prefs.meal_type} onChange={(v) => set("meal_type", v)} />

        {/* Difficulty */}
        <Label>Difficulty</Label>
        <ChipGroup options={DIFFICULTY_OPTIONS} value={prefs.difficulty} onChange={(v) => set("difficulty", v)} />

        {/* Cook time */}
        <Label>Max cook time: {prefs.max_cook_time >= 180 ? "No limit" : `${prefs.max_cook_time} min`}</Label>
        <input
          type="range" min={10} max={180} step={5} value={prefs.max_cook_time}
          onChange={(e) => set("max_cook_time", Number(e.target.value))}
          className="w-full accent-amber-500 mb-5"
        />

        <div className="flex gap-3">
          <button
            onClick={onSkip}
            className="flex-1 border border-stone-200 text-stone-600 py-3 rounded-xl font-medium hover:bg-stone-50"
          >
            Skip
          </button>
          <button
            onClick={handleSubmit}
            className="flex-1 bg-amber-500 hover:bg-amber-600 text-white py-3 rounded-xl font-semibold"
          >
            Apply Preferences
          </button>
        </div>
      </div>
    </div>
  );
}

function Label({ children }) {
  return <p className="text-sm font-semibold text-stone-700 mb-2 mt-3">{children}</p>;
}

function ChipGroup({ options, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2 mb-1">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`px-3 py-1 rounded-full text-sm font-medium capitalize transition-colors ${
            value === opt
              ? "bg-amber-500 text-white"
              : "bg-stone-100 text-stone-600 hover:bg-amber-50"
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}
