---
name: "install"
description: "Sets up the complete Python and Node.js environment for the FootballAnalytics project."
version: 0.1.0
capabilities:
  - "Python virtual environment with football_core library installed in editable mode"
  - "FastAPI, uvicorn, soccerdata, mplsoccer, scipy, pandas installed"
  - "Next.js 14 frontend dependencies installed"
  - "Verification that all required tools and imports are available"
triggers:
  - "set up environment"
  - "install dependencies"
  - "first time setup"
  - "soccerdata not found"
  - "python library missing"
  - "npm install"
last_updated: 2026-05-11
---

# Install

Sets up the full FootballAnalytics environment: Python venv + library, FastAPI backend, Next.js frontend.
Run once when the project is first cloned, or when dependencies change.

---

## Step 1 — Check prerequisites

Verify Python 3.11+, Node.js 18+, and npm are available.
If any are missing, tell the operator which to install before continuing.

---

## Step 2 — Create Python virtual environment

Create `.venv/` at the repo root.

---

## Step 3 — Install football_core library

Install `.libs/football_core` in editable mode into the venv.
Confirm `football_core` is importable.

---

## Step 4 — Install backend dependencies

Install backend `pyproject.toml` dependencies into the venv.
Confirm `fastapi`, `uvicorn`, `soccerdata`, `mplsoccer`, `scipy`, `aiohttp` are importable.

**Note on optional Tier B/C dependencies:**
- `understat` library: **not installable on Python 3.13** (aiohttp build failure). The pipeline uses direct `aiohttp` HTTP calls to Understat's API instead — no `pip install understat` needed.
- `selenium` + `undetected-chromedriver`: optional, for WhoScored Tier C. Install only when promoting the WhoScored stub: `pip install selenium undetected-chromedriver`. Not needed in V1.

---

## Step 5 — Install frontend dependencies

Run `npm install` in `frontend/`.
Confirm `next` CLI is available.

---

## Step 6 — Verify installation

Run a quick import check for each key package and report pass/fail for each.
