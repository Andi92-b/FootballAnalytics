---
name: "scaffold-app"
description: "Creates the full-stack skeleton: backend directory with FastAPI layout, frontend directory with Next.js 14 App Router, Tailwind CSS, TypeScript config, .env.example, and .gitignore."
version: 0.1.0
capabilities:
  - "backend/ folder with FastAPI app layout (main.py, routers/, services/)"
  - "frontend/ folder with Next.js 14 App Router layout (app/, components/)"
  - "Tailwind CSS configuration and TypeScript tsconfig.json"
  - "backend pyproject.toml with all required dependencies declared"
  - "frontend package.json with Next.js, React, TypeScript, Tailwind"
triggers:
  - "scaffold"
  - "create project structure"
  - "set up folders"
  - "initialise app"
  - "create skeleton"
last_updated: 2026-05-11
---

# Scaffold App

Creates the complete folder structure and config files for the FootballAnalytics web application.
Does NOT install dependencies — run the `install` skill after scaffolding.

---

## Step 1 — Create backend structure

Create `backend/app/main.py`, `backend/app/routers/`, `backend/app/services/`, `backend/pyproject.toml`.
Each file should be a minimal stub (empty imports, placeholder comments).

---

## Step 2 — Create frontend structure

Create `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`, `frontend/src/components/`.
Use Next.js 14 App Router conventions.

---

## Step 3 — Write backend pyproject.toml

Declare: fastapi, uvicorn[standard], python-dotenv, football-core (from .libs/).

---

## Step 4 — Write frontend package.json + config files

`package.json` with next, react, react-dom, typescript, tailwindcss, @types/react, @types/node.
`tailwind.config.ts`, `tsconfig.json`, `next.config.ts` — minimal valid configs.

---

## Step 5 — Create .cache/fbref/ directory placeholder

Add a `.gitkeep` so the cache directory is tracked in git as empty.

---

## Step 6 — Verify structure

List the created tree and confirm it matches the Project Structure in `CLAUDE.md`.
