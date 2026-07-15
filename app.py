"""Ieri & Oggi - applicazione web KISS per una galleria di profili.

Gallery pubblica; passphrase condivisa per aggiungere/modificare/eliminare.
Foto salvate come BLOB in SQLite. Tutto server-rendered con Jinja2.
"""

from __future__ import annotations

import datetime as dt
import os
import secrets
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.utils import secure_filename  # noqa: F401  (utile per futuri usi)

from images import ImmagineNonValida, MIME, processa
from models import CATEGORIE, GIOVANE, RECENTE, Base, Person, Photo, make_engine

# --- Configurazione -------------------------------------------------------

DEFAULT_DB = "sqlite:///" + os.path.join(os.path.dirname(__file__), "data", "app.db")


def crea_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        PASSPHRASE=os.environ.get("PASSPHRASE", "nonni2026"),
        DATABASE_URL=os.environ.get("DATABASE_URL", DEFAULT_DB),
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_UPLOAD_MB", "250")) * 1024 * 1024,
    )
    if config:
        app.config.update(config)

    # Assicura la cartella del DB sqlite.
    db_url = app.config["DATABASE_URL"]
    if db_url.startswith("sqlite:///"):
        db_path = db_url[len("sqlite:///"):]
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    engine = make_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = scoped_session(sessionmaker(bind=engine, future=True))
    app.extensions["db_session"] = SessionLocal

    @app.teardown_appcontext
    def _rimuovi_sessione(_exc=None):
        SessionLocal.remove()

    def db():
        return SessionLocal

    # --- Autenticazione ---------------------------------------------------

    def autenticato() -> bool:
        return bool(session.get("autenticato"))

    @app.context_processor
    def _inietta():
        return {"autenticato": autenticato(), "GIOVANE": GIOVANE, "RECENTE": RECENTE}

    def richiede_accesso(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not autenticato():
                flash("Inserisci la passphrase per continuare.", "info")
                return redirect(url_for("accedi", next=request.full_path))
            return view(*args, **kwargs)

        return wrapper

    # --- Helper -----------------------------------------------------------

    def get_persona(pid: int) -> Person:
        persona = db().get(Person, pid)
        if persona is None:
            abort(404)
        return persona

    def parse_data(valore: str | None) -> dt.date | None:
        valore = (valore or "").strip()
        if not valore:
            return None
        # Accetta il formato italiano gg/mm/aaaa; ISO come ripiego.
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(valore, fmt).date()
            except ValueError:
                continue
        return None

    def salva_foto_caricate(persona: Person, categoria: str) -> int:
        """Salva i file caricati per una categoria. Ritorna quanti salvati."""
        campo = "foto_" + categoria
        files = [f for f in request.files.getlist(campo) if f and f.filename]
        # Ordine di partenza dopo le foto già presenti nella categoria.
        base_ordine = len(persona.foto_categoria(categoria))
        gia_cover = any(f.is_cover for f in persona.foto_categoria(categoria))
        salvati = 0
        for i, storage in enumerate(files):
            raw = storage.read()
            if not raw:
                continue
            try:
                dati, thumb = processa(raw)
            except ImmagineNonValida:
                flash(f"Il file «{storage.filename}» non è un'immagine valida.", "error")
                continue
            foto = Photo(
                categoria=categoria,
                is_cover=(not gia_cover and salvati == 0),
                dati=dati,
                thumb=thumb,
                mime=MIME,
                ordine=base_ordine + i,
            )
            persona.foto.append(foto)
            salvati += 1
        return salvati

    # --- Route pubbliche --------------------------------------------------

    @app.route("/")
    def gallery():
        q = (request.args.get("q") or "").strip()
        stmt = select(Person).order_by(Person.cognome, Person.nome)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Person.nome.ilike(like),
                    Person.cognome.ilike(like),
                    Person.descrizione.ilike(like),
                    Person.indirizzo.ilike(like),
                )
            )
        persone = db().scalars(stmt).all()
        return render_template("gallery.html", persone=persone, q=q)

    @app.route("/persona/<int:pid>")
    def dettaglio(pid: int):
        persona = get_persona(pid)
        return render_template("dettaglio.html", persona=persona)

    @app.route("/foto/<int:fid>")
    def foto(fid: int):
        ph = db().get(Photo, fid)
        if ph is None:
            abort(404)
        return _rispondi_immagine(ph.dati, ph.mime)

    @app.route("/foto/<int:fid>/thumb")
    def foto_thumb(fid: int):
        ph = db().get(Photo, fid)
        if ph is None:
            abort(404)
        return _rispondi_immagine(ph.thumb, ph.mime)

    def _rispondi_immagine(blob: bytes, mime: str):
        from flask import Response

        resp = Response(blob, mimetype=mime)
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp

    # --- Route protette ---------------------------------------------------

    @app.route("/nuovo", methods=["GET", "POST"])
    @richiede_accesso
    def nuovo():
        if request.method == "POST":
            nome = (request.form.get("nome") or "").strip()
            cognome = (request.form.get("cognome") or "").strip()
            if not nome or not cognome:
                flash("Nome e cognome sono obbligatori.", "error")
                return render_template("form.html", persona=None, form=request.form)

            persona = Person(
                nome=nome,
                cognome=cognome,
                indirizzo=(request.form.get("indirizzo") or "").strip() or None,
                descrizione=(request.form.get("descrizione") or "").strip() or None,
                data_nascita=parse_data(request.form.get("data_nascita")),
            )
            db().add(persona)
            db().flush()
            for cat in CATEGORIE:
                salva_foto_caricate(persona, cat)
            db().commit()
            flash("Profilo aggiunto.", "success")
            return redirect(url_for("dettaglio", pid=persona.id))
        return render_template("form.html", persona=None, form={})

    @app.route("/persona/<int:pid>/modifica", methods=["GET", "POST"])
    @richiede_accesso
    def modifica(pid: int):
        persona = get_persona(pid)
        if request.method == "POST":
            nome = (request.form.get("nome") or "").strip()
            cognome = (request.form.get("cognome") or "").strip()
            if not nome or not cognome:
                flash("Nome e cognome sono obbligatori.", "error")
                return render_template("form.html", persona=persona, form=request.form)

            persona.nome = nome
            persona.cognome = cognome
            persona.indirizzo = (request.form.get("indirizzo") or "").strip() or None
            persona.descrizione = (request.form.get("descrizione") or "").strip() or None
            persona.data_nascita = parse_data(request.form.get("data_nascita"))

            # Rimozione foto selezionate.
            da_rimuovere = set(request.form.getlist("rimuovi"))
            if da_rimuovere:
                for ph in list(persona.foto):
                    if str(ph.id) in da_rimuovere:
                        persona.foto.remove(ph)

            # Nuove foto.
            for cat in CATEGORIE:
                salva_foto_caricate(persona, cat)

            # Impostazione copertina esplicita, se richiesta.
            for cat in CATEGORIE:
                scelta = request.form.get("cover_" + cat)
                foto_cat = persona.foto_categoria(cat)
                if scelta:
                    for ph in foto_cat:
                        ph.is_cover = str(ph.id) == scelta
                elif foto_cat and not any(f.is_cover for f in foto_cat):
                    foto_cat[0].is_cover = True

            db().commit()
            flash("Profilo aggiornato.", "success")
            return redirect(url_for("dettaglio", pid=persona.id))
        return render_template("form.html", persona=persona, form=None)

    @app.route("/persona/<int:pid>/elimina", methods=["POST"])
    @richiede_accesso
    def elimina(pid: int):
        persona = get_persona(pid)
        db().delete(persona)
        db().commit()
        flash("Profilo eliminato.", "success")
        return redirect(url_for("gallery"))

    # --- Sessione ---------------------------------------------------------

    @app.route("/accedi", methods=["GET", "POST"])
    def accedi():
        if request.method == "POST":
            passphrase = request.form.get("passphrase") or ""
            atteso = app.config["PASSPHRASE"]
            if secrets.compare_digest(passphrase, atteso):
                session["autenticato"] = True
                flash("Accesso effettuato.", "success")
                nxt = request.form.get("next") or url_for("gallery")
                if not nxt.startswith("/"):
                    nxt = url_for("gallery")
                return redirect(nxt)
            flash("Passphrase errata.", "error")
        nxt = request.args.get("next") or request.form.get("next") or ""
        return render_template("accedi.html", next=nxt)

    @app.route("/esci", methods=["POST"])
    def esci():
        session.pop("autenticato", None)
        flash("Sei uscito.", "info")
        return redirect(url_for("gallery"))

    # --- Errori -----------------------------------------------------------

    @app.errorhandler(413)
    def _troppo_grande(_e):
        limite = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        flash(
            f"Le foto caricate superano il limite di {limite} MB in totale. "
            "Carica meno foto per volta.",
            "error",
        )
        return redirect(request.referrer or url_for("gallery")), 413

    return app


# Istanza per `flask --app app run`.
app = crea_app()


if __name__ == "__main__":
    app.run(debug=True)
