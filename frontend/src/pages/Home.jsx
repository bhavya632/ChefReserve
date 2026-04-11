import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PantryInput from "../components/PantryInput";
import ImportUrlModal from "../components/ImportUrlModal";
import { searchRecipes } from "../lib/api";

export default function Home() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showImport, setShowImport] = useState(false);

  async function handleSearch(ingredients) {
    if (!ingredients.length) return;
    setLoading(true);
    setError("");
    try {
      const data = await searchRecipes(ingredients);
      // Pass results to Results page via router state
      navigate("/results", {
        state: { recipes: data.recipes, pantry: ingredients },
      });
    } catch (e) {
      const serverMessage = e?.response?.data?.error;
      if (serverMessage) {
        setError(`Server error: ${serverMessage}`);
      } else if (e?.code === "ERR_NETWORK") {
        setError("Could not reach the server. Make sure the backend is running.");
      } else {
        setError("Request failed. Check backend logs for details.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-stone-50 flex flex-col">
      {/* Header */}
      <header className="pt-12 pb-6 px-4 text-center">
        <div className="text-4xl mb-2">🍴</div>
        <h1 className="text-3xl font-bold text-stone-800 tracking-tight">ChefReserve</h1>
        <p className="text-stone-500 mt-1 text-sm">Tell us what's in your pantry. We'll handle the rest.</p>
      </header>

      {/* Main */}
      <main className="flex-1 px-4 pb-8 max-w-xl mx-auto w-full">
        <PantryInput onSearch={handleSearch} loading={loading} />

        {error && (
          <p className="text-red-500 text-sm text-center mt-4">{error}</p>
        )}

        {/* Import URL CTA */}
        <div className="mt-8 text-center">
          <p className="text-stone-400 text-xs mb-2">Have a specific recipe in mind?</p>
          <button
            onClick={() => setShowImport(true)}
            className="text-amber-600 text-sm font-medium hover:underline"
          >
            + Import recipe from URL
          </button>
        </div>
      </main>

      {showImport && (
        <ImportUrlModal
          onClose={() => setShowImport(false)}
          onImported={(recipe) => {
            // After import, show a success message
            setShowImport(false);
            alert(`"${recipe.name}" imported successfully! You can now search for it.`);
          }}
        />
      )}
    </div>
  );
}
