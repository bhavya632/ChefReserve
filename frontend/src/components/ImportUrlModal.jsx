import { useState } from "react";
import { importRecipeFromUrl } from "../lib/api";

export default function ImportUrlModal({ onClose, onImported }) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleImport() {
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await importRecipeFromUrl(url.trim());
      onImported(data.recipe);
      onClose();
    } catch (e) {
      setError(e.response?.data?.error || "Failed to import recipe. The site may not be supported.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl">
        <h2 className="text-xl font-bold text-stone-800 mb-1">Import Recipe from URL</h2>
        <p className="text-stone-500 text-sm mb-5">
          Paste a link from AllRecipes, Food Network, NYT Cooking, or any recipe site that uses schema.org markup.
        </p>

        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.allrecipes.com/recipe/..."
          className="w-full border-2 border-stone-200 rounded-xl px-4 py-3 text-stone-800 focus:outline-none focus:border-amber-400 text-sm mb-3"
        />

        {error && (
          <p className="text-red-500 text-xs mb-3">{error}</p>
        )}

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border border-stone-200 text-stone-600 py-3 rounded-xl font-medium hover:bg-stone-50"
          >
            Cancel
          </button>
          <button
            onClick={handleImport}
            disabled={loading || !url.trim()}
            className="flex-1 bg-amber-500 hover:bg-amber-600 disabled:bg-stone-200 disabled:text-stone-400 text-white py-3 rounded-xl font-semibold"
          >
            {loading ? "Importing…" : "Import"}
          </button>
        </div>
      </div>
    </div>
  );
}
