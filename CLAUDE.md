# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**Allora & Oggi** — a small, KISS web app hosting profiles of elderly people who knew each other when young. Each profile has personal data and two photo categories: **`giovane`** (young) and **`recente`** (recent). The gallery is public; a single shared **passphrase** gates create/edit/delete only. UI is in **Italian**, minimal and responsive. Photos are stored as **BLOBs inside SQLite** (resized/compressed on upload) — no external storage.

Dependencies are managed by the **Nix flake** (`flake.nix` devShell): Flask, SQLAlchemy, Pillow, gunicorn.

## Commands

```sh
nix develop                         # enter devShell with Python + deps
flask --app app run --debug         # dev server at http://127.0.0.1:5000
gunicorn --bind 0.0.0.0:8000 app:app  # production
```

Config via env vars: `PASSPHRASE` (default `nonni2026`), `SECRET_KEY` (random if unset — set in prod), `DATABASE_URL` (default `sqlite:///data/app.db`), `MAX_UPLOAD_MB` (default 250, caps the total request body). There is no test suite; verify by driving the app (see README).

## Architecture

Server-rendered Flask, no frontend build. Four source files at the repo root:

- **`app.py`** — `crea_app()` factory: config, engine + `scoped_session` (removed on teardown), the `@richiede_accesso` decorator (redirects to `/accedi` when `session['autenticato']` is unset), and all routes. Public: `/` (gallery with `?q=` ILIKE search over nome/cognome/descrizione/indirizzo), `/persona/<id>`, `/foto/<id>` + `/foto/<id>/thumb` (serve BLOBs). Protected: `/nuovo`, `/persona/<id>/modifica`, `/persona/<id>/elimina`, plus `/accedi` and `/esci`. Passphrase checked with `secrets.compare_digest`.
- **`models.py`** — SQLAlchemy 2.0 declarative models. `Person` (nome/cognome required, rest optional) and `Photo` (`categoria` ∈ {`giovane`,`recente`}, `is_cover`, `dati`, `thumb`, `mime`). `Person.foto` cascades delete-orphan. Helpers `cover()`, `cover_gallery()` (recent preferred), `foto_categoria()` drive templating. `make_engine()` enables SQLite `PRAGMA foreign_keys=ON`.
- **`images.py`** — `processa(bytes) -> (jpeg, thumb_jpeg)`: EXIF-transpose, flatten to RGB on white, resize long side to 1600px / 400px, JPEG q85. Raises `ImmagineNonValida` on non-images (caller flashes an error and skips that file).
- **`templates/`** (`base`, `gallery`, `dettaglio`, `form`, `accedi`) + **`static/style.css`** — vanilla CSS, large fonts / tap targets, responsive grid.

## Conventions

- Code, routes, UI text, and DB columns are in **Italian**; keep new code consistent.
- One cover photo per (person, category) is enforced in the save logic in `app.py`, not by a DB constraint.
- `data/` (the SQLite file) and `__pycache__/` are gitignored; back up by copying `data/app.db`.
