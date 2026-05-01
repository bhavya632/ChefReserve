import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import RecipeCard from "../components/RecipeCard";
import PreferenceModal from "../components/PreferenceModal";
import { rerankRecipes } from "../lib/api";

const PAGE_SIZE = 20;

export default function Results() {
  const { state } = useLocation();
  const navigate = useNavigate();

  const [recipes] = useState(state?.recipes || []);
  const [pantry] = useState(state?.pantry || []);
  const [showPrefs, setShowPrefs] = useState(false);
  const [reranking, setReranking] = useState(false);
  const [filtered, setFiltered] = useState(null); // null = show all
  const [page, setPage] = useState(1);

  const displayRecipes = filtered ?? recipes;
  const totalPages = Math.max(1, Math.ceil(displayRecipes.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedRecipes = displayRecipes.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE,
  );

  async function handlePrefsSubmit(prefs) {
    setShowPrefs(false);
    setReranking(true);
    try {
      const data = await rerankRecipes(recipes, prefs, pantry);
      setFiltered(data.ranked_recipes);
      setPage(1);
    } catch (e) {
      console.error("Rerank failed:", e);
    } finally {
      setReranking(false);
    }
  }

  function handlePrefsSkip() {
    setShowPrefs(false);
  }

  return (
    <div className="min-h-screen bg-stone-50 flex flex-col">
      {/* Header */}
      <header className="sticky top-0 bg-white border-b border-stone-100 z-10 px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate("/")}
          className="text-stone-500 hover:text-stone-800 text-sm"
        >
          ← Back
        </button>
        <div className="flex-1">
          <h1 className="font-bold text-stone-800 text-sm">
            {displayRecipes.length} recipe{displayRecipes.length !== 1 ? "s" : ""} found
          </h1>
          <p className="text-xs text-stone-400 truncate">
            Pantry: {pantry.slice(0, 5).join(", ")}{pantry.length > 5 ? ` +${pantry.length - 5} more` : ""}
          </p>
          {displayRecipes.length > 0 && (
            <p className="text-xs text-stone-400">
              Page {currentPage} of {totalPages}
            </p>
          )}
        </div>
        <button
          onClick={() => setShowPrefs(true)}
          className="text-xs bg-amber-100 text-amber-700 px-3 py-1.5 rounded-full font-medium"
        >
          Refine ✦
        </button>
      </header>

      {/* Loading state */}
      {reranking && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="text-3xl mb-3 animate-spin">✦</div>
            <p className="text-stone-500 text-sm">Groq is ranking your recipes…</p>
          </div>
        </div>
      )}

      {/* Recipe list */}
      {!reranking && (
        <main className="flex-1 px-4 py-4 max-w-xl mx-auto w-full space-y-4">
          {displayRecipes.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-4xl mb-3">🥲</div>
              <p className="text-stone-500">No recipes found with those ingredients.</p>
              <button
                onClick={() => navigate("/")}
                className="mt-4 text-amber-600 text-sm font-medium hover:underline"
              >
                Try different ingredients
              </button>
            </div>
          ) : (
            pagedRecipes.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} />
            ))
          )}
          {displayRecipes.length > PAGE_SIZE && (
            <div className="flex items-center justify-between pt-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="text-sm text-amber-700 disabled:text-stone-300"
              >
                ← Previous
              </button>
              <span className="text-xs text-stone-400">
                {currentPage} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="text-sm text-amber-700 disabled:text-stone-300"
              >
                Next →
              </button>
            </div>
          )}
        </main>
      )}

      {/* Preference modal */}
      {showPrefs && (
        <PreferenceModal
          onSubmit={handlePrefsSubmit}
          onSkip={handlePrefsSkip}
        />
      )}
    </div>
  );
}
