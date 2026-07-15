# Ieri & Oggi

A small, vibe-coded web app I built for my granddad and his old *naia* buddies
(the friends from his military service). It's a gallery of profiles of people
who knew each other when they were young. Each profile has some personal
details and two kinds of photos: **young** (*da giovane*) and **recent**
(*recente*). The gallery is public; a shared **passphrase** is only needed to
add, edit, or delete a profile.

Italian interface, minimal and responsive (mobile + desktop). Photos are stored
as BLOBs inside a single SQLite file — no external storage.

## Stack

- **Python + Flask** (server-rendered pages, no frontend build)
- **SQLAlchemy + SQLite** (abstract data layer, DB in a single file)
- **Pillow** (resizes/compresses photos and generates thumbnails)
- Dependencies managed by the **Nix flake**

## Getting started (development)

```sh
nix develop                       # enter the devShell with Python and dependencies
flask --app app run --debug       # start the development server
```

Open <http://127.0.0.1:5000>. The gallery opens without login; click
**"Aggiungi profilo"** ("Add profile") and enter the passphrase to upload data.

## Configuration (environment variables)

| Variable       | Default                | Description                                  |
|----------------|------------------------|----------------------------------------------|
| `PASSPHRASE`   | `nonni2026`            | passphrase to upload/edit                    |
| `SECRET_KEY`   | generated on each start| signs session cookies (set it in production) |
| `DATABASE_URL` | `sqlite:///data/app.db`| database URL                                 |
| `MAX_UPLOAD_MB`| `250`                  | maximum total size of a single upload (MB)   |

Example:

```sh
PASSPHRASE="my-secret-phrase" SECRET_KEY="$(openssl rand -hex 32)" \
  flask --app app run
```

## Production (optional)

```sh
SECRET_KEY="$(openssl rand -hex 32)" PASSPHRASE="…" \
  gunicorn --bind 0.0.0.0:8000 'app:app'
```

The database is the file at `data/app.db`: to back it up, just copy it.
