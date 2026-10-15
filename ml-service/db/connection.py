"""Conexão SQLAlchemy + registro do tipo pgvector."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_database_url() -> Optional[str]:
    """Retorna DATABASE_URL se configurada."""
    return os.getenv("DATABASE_URL") or None


def init_engine(database_url: Optional[str] = None) -> Optional[Engine]:
    """
    Inicializa o engine global. Retorna None se não houver DATABASE_URL
    (o serviço sobe e /health responde; /analyze devolve 503).
    """
    global _engine, _SessionLocal
    url = database_url or get_database_url()
    if not url:
        return None

    # pgvector registra o tipo Vector nas colunas dos modelos
    from pgvector.sqlalchemy import Vector  # noqa: F401

    _engine = create_engine(url, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_engine() -> Optional[Engine]:
    if _engine is None:
        return init_engine()
    return _engine


def session_scope() -> Session:
    """Abre uma sessão (caller deve fechar ou usar context)."""
    if _SessionLocal is None:
        init_engine()
    if _SessionLocal is None:
        raise RuntimeError("DATABASE_URL não configurada.")
    return _SessionLocal()
