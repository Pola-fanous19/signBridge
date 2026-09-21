# SignBridge v4

English → ASL gloss → 3D avatar. This version adds:

- ✅ **Full lexicon** (words / fixed / fingerspelling) bundled inside the project
- ✅ **Gemini API integration** with connection status icon
- ✅ **Avatar playback-speed control** (0.25× – 3×) with presets
- ✅ **REST-only architecture** — WebSocket & batch modes removed
- ✅ **More realistic avatar** — tapered fingers, fingernails, thickened palm,
  detailed face (hair, ears, eyes, brows) for deaf users
- ✅ **One-click launcher** (`run.bat` on Windows, `run.sh` on macOS/Linux)
- ✅ **`.env` file** with your Gemini key preloaded

## Quick start (Windows)

Just double-click **`run.bat`**. It will:

1. Verify Python 3.9+ and Node 18+ are installed
2. Create a Python virtualenv in `backend/.venv`
3. `pip install` backend deps (fastapi, uvicorn, google-generativeai, …)
4. `npm install` frontend deps
5. Start backend on `http://localhost:8000`
6. Start frontend on `http://localhost:5173`
7. Open the browser

## Quick start (macOS / Linux)

```bash
chmod +x run.sh
./run.sh
```

## Configuration

The **Gemini API key** is stored in `backend/.env`:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

The frontend polls `/api/gemini/status` when the Gemini backend is selected
and displays a colored dot next to the input:

- 🟢 green = connected
- 🔴 red   = offline / no API key
- 🟡 yellow = checking

## How translation works

1. **Text → gloss** using either the rule-based converter or Gemini.
2. **Gloss → pose clip** using the sequencer:
   - If the token is in the **lexicon** (`backend/data/lexicon/words` or
     `backend/data/lexicon/fixed`), play the stored ASL animation.
   - Otherwise, **fingerspell** it letter-by-letter using anatomically
     correct handshapes (26 letters, MediaPipe topology).
3. **Pose clip → avatar** — the frontend ticks frames at 30 FPS × your
   selected speed multiplier through a 3D avatar built with react-three-fiber.

## Lexicon contents

- **47** words in `words/` (BOOK, CAT, COFFEE, HELLO, LOVE, THANK-YOU, …)
- **22** fixed signs in `fixed/` (WHAT, WHERE, WHEN, IX-1, POSS-2, …)
- **26** fingerspelling letters in `fingerspelling/` (A–Z)

Add more `*.json` files to any of those folders to extend the vocabulary
(no code change required — the loader picks them up on startup).

## Manual dev workflow

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate         # or  .venv\Scripts\activate  on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev                       # opens http://localhost:5173
```

## Project structure

```
signbridge-v4/
├── .env                          ← (also present at backend/.env)
├── run.bat / run.sh              ← one-click launcher
├── stop.bat
├── backend/
│   ├── .env                      ← Gemini API key
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               FastAPI entrypoint
│   │   ├── config.py             loads .env
│   │   ├── api/routes.py         /api/translate, /api/gemini/status
│   │   ├── gloss/rule_based.py
│   │   ├── gloss/gemini_backend.py
│   │   └── pose/
│   │       ├── schema.py         85-landmark schema
│   │       ├── fingerspell.py    26 ASL letter handshapes
│   │       ├── lexicon.py        loads data/lexicon/*
│   │       └── sequencer.py      lexicon-hit-or-fingerspell logic
│   └── data/lexicon/
│       ├── words/                47 real ASL words
│       ├── fixed/                22 grammar signs
│       └── fingerspelling/       26 letter clips
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx               main app (REST only, speed control)
        ├── main.jsx
        ├── styles.css
        ├── components/
        │   ├── AvatarScene.jsx   realistic 3D avatar
        │   ├── AvatarCard.jsx    canvas + speed control
        │   ├── GeminiStatus.jsx  connection indicator
        │   ├── GlossPanel.jsx    gloss chips + stats
        │   └── HelpCard.jsx
        └── lib/
            ├── schema.js         must mirror backend/pose/schema.py
            ├── fingerspell.js    26 letter handshapes (client fallback)
            ├── posePlayer.js     RAF-driven ticker with speed multiplier
            └── api.js            REST client + Gemini status
```
