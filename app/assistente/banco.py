"""Persistência das conversas em SQLite.

Guarda sessões e mensagens para que o atendimento possa ser recuperado e auditado —
requisito de "armazenamento e recuperação das informações" da Fase 5.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import CAMINHO_BANCO

ESQUEMA = """
CREATE TABLE IF NOT EXISTS sessao (
    id          TEXT PRIMARY KEY,
    criada_em   TEXT NOT NULL,
    motor       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mensagem (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sessao_id    TEXT NOT NULL REFERENCES sessao(id),
    criada_em    TEXT NOT NULL,
    autor        TEXT NOT NULL CHECK (autor IN ('paciente', 'assistente')),
    texto        TEXT NOT NULL,
    intencao     TEXT,
    confianca    REAL,
    entidades    TEXT,
    nivel_risco  TEXT
);

CREATE INDEX IF NOT EXISTS idx_mensagem_sessao ON mensagem(sessao_id, id);
"""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _conectar() -> sqlite3.Connection:
    Path(CAMINHO_BANCO).parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    return conexao


def iniciar_banco() -> None:
    """Cria as tabelas na primeira execução."""
    with _conectar() as conexao:
        conexao.executescript(ESQUEMA)


def garantir_sessao(sessao_id: str, motor: str) -> None:
    with _conectar() as conexao:
        conexao.execute(
            "INSERT OR IGNORE INTO sessao (id, criada_em, motor) VALUES (?, ?, ?)",
            (sessao_id, _agora(), motor),
        )


def registrar_mensagem(
    sessao_id: str,
    autor: str,
    texto: str,
    *,
    intencao: str | None = None,
    confianca: float | None = None,
    entidades: list[dict[str, Any]] | None = None,
    nivel_risco: str | None = None,
) -> None:
    with _conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO mensagem
                (sessao_id, criada_em, autor, texto, intencao, confianca, entidades, nivel_risco)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sessao_id,
                _agora(),
                autor,
                texto,
                intencao,
                confianca,
                json.dumps(entidades, ensure_ascii=False) if entidades else None,
                nivel_risco,
            ),
        )


def historico(sessao_id: str, limite: int = 100) -> list[dict[str, Any]]:
    with _conectar() as conexao:
        linhas = conexao.execute(
            """
            SELECT criada_em, autor, texto, intencao, confianca, entidades, nivel_risco
            FROM mensagem
            WHERE sessao_id = ?
            ORDER BY id
            LIMIT ?
            """,
            (sessao_id, limite),
        ).fetchall()

    registros = []
    for linha in linhas:
        registro = dict(linha)
        if registro["entidades"]:
            registro["entidades"] = json.loads(registro["entidades"])
        registros.append(registro)
    return registros


def resumo() -> dict[str, int]:
    """Contadores simples para o endpoint de saúde da aplicação."""
    with _conectar() as conexao:
        sessoes = conexao.execute("SELECT COUNT(*) FROM sessao").fetchone()[0]
        mensagens = conexao.execute("SELECT COUNT(*) FROM mensagem").fetchone()[0]
    return {"sessoes": sessoes, "mensagens": mensagens}
