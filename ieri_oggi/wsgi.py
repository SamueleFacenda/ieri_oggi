"""Punto di ingresso WSGI.

Obiettivo per gunicorn e per `flask --app ieri_oggi.wsgi run`:

    gunicorn ieri_oggi.wsgi:app
"""

from .app import crea_app

app = crea_app()
