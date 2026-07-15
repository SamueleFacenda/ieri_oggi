"""Avvio del server di produzione (gunicorn) come entry point.

Serve `ieri_oggi.wsgi:app` tramite l'API programmatica di gunicorn, così che
il binario `ieri-oggi` prodotto dal pacchetto sia autosufficiente (usato sia da
`nix run` sia dal servizio systemd). Configurabile via ambiente:

    BIND             indirizzo di ascolto (default 127.0.0.1:8000)
    WEB_CONCURRENCY  numero di worker      (default 2)
"""

from __future__ import annotations

import os

from gunicorn.app.base import BaseApplication

from .wsgi import app


class _Server(BaseApplication):
    def __init__(self, application, options: dict):
        self.application = application
        self.options = options
        super().__init__()

    def load_config(self):
        for chiave, valore in self.options.items():
            self.cfg.set(chiave, valore)

    def load(self):
        return self.application


def main() -> None:
    opzioni = {
        "bind": os.environ.get("BIND", "127.0.0.1:8000"),
        "workers": int(os.environ.get("WEB_CONCURRENCY", "2")),
    }
    _Server(app, opzioni).run()


if __name__ == "__main__":
    main()
