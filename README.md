# Ieri & Oggi

Piccola web app per una galleria di profili di persone che si conoscevano da
giovani. Ogni profilo ha dati anagrafici e due tipi di foto: **da giovane** e
**recente**. La galleria è pubblica; una **passphrase** condivisa serve solo per
aggiungere, modificare o eliminare un profilo.

Interfaccia in italiano, minimale e responsive (mobile + desktop). Le foto sono
salvate come BLOB dentro un unico file SQLite — niente storage esterno.

## Stack

- **Python + Flask** (pagine renderizzate lato server, nessun build frontend)
- **SQLAlchemy + SQLite** (interfaccia dati astratta, DB in un file)
- **Pillow** (ridimensiona/comprime le foto e genera le miniature)
- Dipendenze gestite dal **flake Nix**

## Avvio (sviluppo)

```sh
nix develop                       # entra nella devShell con Python e dipendenze
flask --app app run --debug       # avvia il server di sviluppo
```

Apri <http://127.0.0.1:5000>. La galleria si apre senza login; premi
**"Aggiungi profilo"** e inserisci la passphrase per caricare i dati.

## Configurazione (variabili d'ambiente)

| Variabile      | Default                | Descrizione                                  |
|----------------|------------------------|----------------------------------------------|
| `PASSPHRASE`   | `nonni2026`            | passphrase per caricare/modificare           |
| `SECRET_KEY`   | generata a ogni avvio  | firma dei cookie di sessione (impostala in produzione) |
| `DATABASE_URL` | `sqlite:///data/app.db`| URL del database                             |
| `MAX_UPLOAD_MB`| `250`                  | dimensione massima totale di un upload (MB)  |

Esempio:

```sh
PASSPHRASE="mia-frase-segreta" SECRET_KEY="$(openssl rand -hex 32)" \
  flask --app app run
```

## Produzione (opzionale)

```sh
SECRET_KEY="$(openssl rand -hex 32)" PASSPHRASE="…" \
  gunicorn --bind 0.0.0.0:8000 'app:app'
```

Il database è il file in `data/app.db`: per un backup basta copiarlo.
