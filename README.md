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
nix develop                              # enter the devShell with Python and dependencies
flask --app ieri_oggi.wsgi run --debug   # start the development server
```

Open <http://127.0.0.1:5000>. The gallery opens without login; click
**"Aggiungi profilo"** ("Add profile") and enter the passphrase to upload data.

The app lives in the `ieri_oggi/` Python package; `ieri_oggi.wsgi:app` is the
WSGI entry point used by both the dev server and gunicorn.

## Run the packaged app

```sh
nix build .#default            # -> ./result/bin/ieri-oggi
PASSPHRASE_FILE=/path/to/pass nix run .#default   # serves via gunicorn on 127.0.0.1:8000
```

`nix run` honours `BIND` (default `127.0.0.1:8000`) and `WEB_CONCURRENCY`
(default `2`).

## Configuration (environment variables)

| Variable          | Default                 | Description                                        |
|-------------------|-------------------------|----------------------------------------------------|
| `PASSPHRASE`      | `nonni2026`             | passphrase to upload/edit                          |
| `PASSPHRASE_FILE` | —                       | path to a file with the passphrase (wins over `PASSPHRASE`) |
| `SECRET_KEY`      | generated on each start | signs session cookies (set it in production)       |
| `SECRET_KEY_FILE` | —                       | path to a file with the secret key (wins over `SECRET_KEY`) |
| `DATABASE_URL`    | `sqlite:///data/app.db` | database URL                                       |
| `MAX_UPLOAD_MB`   | `250`                   | maximum total size of a single upload (MB)         |
| `COOKIE_SECURE`   | `0`                     | set `1` to mark session cookies `Secure` (HTTPS)   |

Example:

```sh
echo "my-secret-phrase" > /run/og-pass
PASSPHRASE_FILE=/run/og-pass SECRET_KEY="$(openssl rand -hex 32)" \
  flask --app ieri_oggi.wsgi run
```

## Production (optional)

```sh
SECRET_KEY="$(openssl rand -hex 32)" PASSPHRASE_FILE=/run/og-pass \
  gunicorn --bind 0.0.0.0:8000 'ieri_oggi.wsgi:app'
```

The database is the file at `data/app.db` (or wherever `DATABASE_URL` points):
to back it up, just copy it.

## Deploy on NixOS

The flake exposes `nixosModules.default`, which runs the app as a hardened
systemd service (`DynamicUser`, private `/var/lib/ieri-oggi` state dir,
`ProtectSystem=strict`, syscall filtering, etc.). The passphrase is read from a
file you point to and delivered via systemd `LoadCredential` — it never lands
in the Nix store or the process environment.

```nix
# flake.nix of your system config
{
  inputs.ieri-oggi.url = "github:you/ieri-oggi";   # or path:/…

  outputs = { nixpkgs, ieri-oggi, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ieri-oggi.nixosModules.default
        {
          services.ieri-oggi = {
            enable = true;
            passphraseFile = "/run/keys/ieri-oggi-pass";   # you provide this file
            # cookieSecure = true;   # when served over HTTPS
            # bind = "127.0.0.1:8000"; workers = 2; maxUploadMb = 250;
          };
        }
      ];
    };
  };
}
```

The `SECRET_KEY` is generated once and persisted at
`/var/lib/ieri-oggi/secret_key` (override with `secretKeyFile`). The SQLite DB
lives at `/var/lib/ieri-oggi/app.db`.

### Behind nginx

Not problematic — gunicorn listens on `127.0.0.1:8000` and nginx proxies to it.
The one gotcha: nginx's default `client_max_body_size` is **1 MB**, so raise it
to match `maxUploadMb` or uploads fail with 413 before reaching the app.

```nix
services.nginx.virtualHosts."ieri.example.org" = {
  enableACME = true;
  forceSSL = true;
  locations."/" = {
    proxyPass = "http://127.0.0.1:8000";
    extraConfig = ''
      client_max_body_size 250m;   # match services.ieri-oggi.maxUploadMb
    '';
  };
};
# and set services.ieri-oggi.cookieSecure = true;
```

`proxyPass` already sets sensible `Host`/`X-Forwarded-*` headers. Redirects are
relative and login is scheme-agnostic, so Flask `ProxyFix` is not needed unless
you later require the real client IP or external URL building.
