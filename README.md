# ChefReserve

A recipe finder that works from what you already have. Enter the ingredients in your pantry, and ChefReserve searches a database of real recipes, ranks them by how many ingredients you already own, and lets you refine by cuisine, meal type, difficulty, spice level, and cook time.

---

## How it works

1. **You enter your pantry** — type ingredients you have, optionally with quantities (e.g. `3 eggs`, `6 oz beans`)
2. **Search** — the backend queries Firestore for recipes that contain your ingredients, computes a match % for each, and returns the top 50
3. **Refine** — you can filter and rerank by cuisine, meal type, difficulty, spice level, and max cook time. Groq (Llama 3) reranks the filtered results
4. **Recipe page** — tap any recipe to see the full ingredient list (matched/missing highlighted), step-by-step instructions, and a link to the original source

---

## Stack

| Layer | Technology | Hosted on |
|---|---|---|
| Frontend | React + Tailwind CSS | Vercel |
| Backend | Python Flask | Railway |
| Database | Firebase Firestore | Firebase |
| AI — reranking | Groq API (Llama 3.1 8B) | Groq Cloud |
| AI — enrichment | Groq API (Llama 3.1 8B) | Groq Cloud |
| Web crawler | Python (requests + BeautifulSoup) | Run locally |

---

## Recipe data

Recipes are scraped from real cooking websites using the crawler in `scripts/crawl_and_scrape.py`. The crawler finds all recipe pages on a site by following links from the homepage, extracts structured data from `schema.org/Recipe` JSON-LD markup, and enriches each recipe with Groq to fill in cuisine, meal type, difficulty, and spice level.

**Sites scraped:**
- [Epicurious](https://www.epicurious.com)
- [Simply Recipes](https://www.simplyrecipes.com)
- [Serious Eats](https://www.seriouseats.com)
- [Budget Bytes](https://www.budgetbytes.com)

Each recipe is stored in Firestore with the following fields: name, source URL, cuisine, meal type, difficulty, spice level, cook time, servings, ingredients list, ingredient tokens (search index), and instructions.

---

## Project structure

```
chefreserve/
├── frontend/          React app (Vite)
│   └── src/
│       ├── pages/
│       │   ├── Home.jsx          Pantry input
│       │   ├── Results.jsx       Recipe list + preference modal
│       │   └── RecipePage.jsx    Full recipe detail
│       ├── components/
│       │   ├── RecipeCard.jsx    Recipe summary card
│       │   ├── PreferenceModal.jsx  Filter/refine UI
│       │   ├── PantryInput.jsx   Ingredient input
│       │   └── MatchBadge.jsx    Match % badge
│       └── lib/
│           ├── api.js            Backend API calls
│           └── firebase.js       Firestore client
│
├── backend/           Flask API
│   ├── routes/
│   │   ├── search.py    POST /api/search — pantry → candidate recipes
│   │   ├── rerank.py    POST /api/rerank — filter + Groq rerank
│   │   └── scraper.py   POST /api/scrape — single URL import
│   └── lib/
│       └── firebase_client.py
│
└── scripts/           Run locally
    ├── crawl_and_scrape.py   Bulk crawler + Groq enrichment
    └── requirements.txt
```

---

## Setup

### 1. Firebase
1. Create a project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable Firestore in Native mode
3. Go to Project Settings → Service Accounts → Generate new private key
4. Save the JSON file as `backend/firebase-service-account.json`
5. Copy your web config values to `frontend/.env.local`

### 2. Groq API key
1. Sign up at [console.groq.com](https://console.groq.com)
2. Generate a free API key
3. Add `GROQ_API_KEY=your_key` to both `backend/.env` and `scripts/.env`

### 3. Crawl recipes
```bash
cd scripts
pip install -r requirements.txt
python crawl_and_scrape.py https://www.epicurious.com https://www.simplyrecipes.com
```

Tuning options (set in `scripts/.env`):
```
CRAWL_MAX_PAGES=500    # max pages per site (default 500)
CRAWL_MAX_DEPTH=3      # link depth from homepage (default 3)
CRAWL_DELAY=1.0        # seconds between page fetches (default 1.0)
ENRICH_DELAY=3.0       # seconds between Groq calls (default 3.0)
```

### 4. Backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
flask run
```

### 5. Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in your Firebase config + backend URL
npm run dev
```

---

## Environment variables

**`backend/.env`**
```
FIREBASE_SERVICE_ACCOUNT=path/to/firebase-service-account.json
GROQ_API_KEY=your_groq_key
```

**`frontend/.env.local`**
```
REACT_APP_BACKEND_URL=http://localhost:5000
REACT_APP_FIREBASE_API_KEY=...
REACT_APP_FIREBASE_AUTH_DOMAIN=...
REACT_APP_FIREBASE_PROJECT_ID=...
```

**`scripts/.env`**
```
FIREBASE_SERVICE_ACCOUNT=path/to/firebase-service-account.json
GROQ_API_KEY=your_groq_key
```
