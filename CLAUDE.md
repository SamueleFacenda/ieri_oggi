# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

**Ieri & Oggi** — a small, KISS web app hosting profiles of elderly people who knew each other when young. Each profile has personal data and two photo categories: **`giovane`** (young) and **`recente`** (recent). The gallery is public; a single shared **passphrase** gates create/edit/delete only. UI is in **Italian**, minimal and responsive. Photos are stored as **BLOBs inside SQLite** (resized/compressed on upload) — no external storage.

Dependencies are managed by the **Nix flake** (`flake.nix` devShell): Flask, SQLAlchemy, Pillow, gunicorn.

## Commands

```sh
nix develop                               # enter devShell with Python + deps
flask --app ieri_oggi.wsgi run --debug    # dev server at http://127.0.0.1:5000
nix build .#default && ./result/bin/ieri-oggi   # packaged app (gunicorn) on 127.0.0.1:8000
gunicorn --bind 0.0.0.0:8000 ieri_oggi.wsgi:app # production, manual
```

Config via env vars: `PASSPHRASE` / `PASSPHRASE_FILE`, `SECRET_KEY` / `SECRET_KEY_FILE` (the `*_FILE` variant reads the secret from a file and wins; random if neither set), `DATABASE_URL` (default `sqlite:///data/app.db`), `MAX_UPLOAD_MB` (default 250, caps the total request body), `COOKIE_SECURE` (`1` marks cookies Secure). The packaged entry point reads `BIND` / `WEB_CONCURRENCY`. There is no test suite; verify by driving the app (see README).

## Architecture

Server-rendered Flask, no frontend build. The app is the **`ieri_oggi/`** Python package (packaged as `buildPythonApplication`; `Flask(__name__)` resolves the bundled `templates/`/`static/`):

- **`ieri_oggi/app.py`** — `crea_app()` factory: config (incl. `_da_file_o_env()` for file-based secrets), engine + `scoped_session` (removed on teardown), the `@richiede_accesso` decorator (redirects to `/accedi` when `session['autenticato']` is unset), `percorso_locale_sicuro()` guarding the login `next` against open redirects, and all routes. Public: `/` (gallery `?q=` ILIKE search — nome/cognome/descrizione for the public, plus indirizzo/telefono when authenticated), `/persona/<id>`, `/privacy` (privacy statement), `/foto/<id>` + `/foto/<id>/thumb` (serve BLOBs). Protected: `/nuovo`, `/persona/<id>/modifica`, `/persona/<id>/elimina`, plus `/accedi` and `/esci`. Passphrase checked with `secrets.compare_digest`. **Personal details** (indirizzo, telefono, data_nascita) are gated: rendered in `dettaglio.html` only when authenticated, and excluded from public search.
- **`ieri_oggi/wsgi.py`** — `app = crea_app()`, the WSGI target (`ieri_oggi.wsgi:app`).
- **`ieri_oggi/__main__.py`** — `main()`: the `ieri-oggi` console script; serves `wsgi:app` via gunicorn's programmatic API (reads `BIND`, `WEB_CONCURRENCY`).
- **`ieri_oggi/models.py`** — SQLAlchemy 2.0 declarative models. `Person` (nome/cognome required; optional indirizzo, telefono, descrizione, data_nascita) and `Photo` (`categoria` ∈ {`giovane`,`recente`}, `is_cover`, `dati`, `thumb`, `mime`). `Person.foto` cascades delete-orphan. Helpers `cover()`, `cover_gallery()` (recent preferred), `foto_categoria()` drive templating. `make_engine()` enables SQLite `PRAGMA foreign_keys=ON`; `assicura_schema()` runs a light idempotent migration (adds columns like `telefono` to existing DBs, since `create_all` doesn't alter tables).
- **`ieri_oggi/images.py`** — `processa(bytes) -> (jpeg, thumb_jpeg)`: EXIF-transpose, flatten to RGB on white, resize long side to 1600px / 400px, JPEG q85. Raises `ImmagineNonValida` on non-images / decompression bombs (caller flashes an error and skips that file).
- **`ieri_oggi/templates/`** (`base` with a footer linking `/privacy`, `gallery`, `dettaglio`, `form`, `accedi`, `privacy`) + **`ieri_oggi/static/style.css`** — vanilla CSS, large fonts / tap targets, responsive grid.

Packaging & deploy live in **`pyproject.toml`** and **`nix/`**: `nix/package.nix` (the `buildPythonApplication`) and `nix/module.nix` (the hardened `services.ieri-oggi` NixOS module — DynamicUser, `/var/lib/ieri-oggi` StateDirectory, passphrase via `LoadCredential`). The flake exposes `packages.default`, `apps.default`, `nixosModules.default`, and `overlays.default`.

## Conventions

- Code, routes, UI text, and DB columns are in **Italian**; keep new code consistent.
- One cover photo per (person, category) is enforced in the save logic in `app.py`, not by a DB constraint.
- `data/` (the SQLite file) and `__pycache__/` are gitignored; back up by copying the DB file (`data/app.db` in dev, `/var/lib/ieri-oggi/app.db` under the NixOS service).
