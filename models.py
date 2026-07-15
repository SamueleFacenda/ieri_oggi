"""Modelli dati e sessione SQLAlchemy per "Allora & Oggi".

Tutto in SQLite: dati anagrafici delle persone e foto salvate come BLOB.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

# Categorie di foto ammesse.
GIOVANE = "giovane"
RECENTE = "recente"
CATEGORIE = (GIOVANE, RECENTE)


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "persone"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    cognome: Mapped[str] = mapped_column(String(120), nullable=False)
    indirizzo: Mapped[str | None] = mapped_column(String(255))
    descrizione: Mapped[str | None] = mapped_column(Text)
    data_nascita: Mapped[dt.date | None] = mapped_column(Date)
    creato_il: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
    aggiornato_il: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    foto: Mapped[list["Photo"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
        order_by="Photo.ordine",
    )

    def cover(self, categoria: str) -> "Photo | None":
        """Foto di copertina per una categoria (o la prima disponibile)."""
        candidate = [f for f in self.foto if f.categoria == categoria]
        if not candidate:
            return None
        for f in candidate:
            if f.is_cover:
                return f
        return candidate[0]

    def cover_gallery(self) -> "Photo | None":
        """Foto mostrata nella gallery: recente se c'è, altrimenti giovane."""
        return self.cover(RECENTE) or self.cover(GIOVANE)

    def foto_categoria(self, categoria: str) -> list["Photo"]:
        return [f for f in self.foto if f.categoria == categoria]


class Photo(Base):
    __tablename__ = "foto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("persone.id", ondelete="CASCADE"), nullable=False, index=True
    )
    categoria: Mapped[str] = mapped_column(String(16), nullable=False)
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dati: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    thumb: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    mime: Mapped[str] = mapped_column(String(64), default="image/jpeg", nullable=False)
    ordine: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    persona: Mapped[Person] = relationship(back_populates="foto")


def make_engine(database_url: str):
    """Crea l'engine SQLAlchemy e assicura il supporto ai vincoli FK in SQLite."""
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    engine = create_engine(database_url, future=True, connect_args=connect_args)

    if database_url.startswith("sqlite"):
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _abilita_fk(dbapi_conn, _record):  # pragma: no cover - hook di connessione
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine
