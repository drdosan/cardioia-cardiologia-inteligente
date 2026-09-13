"""Camada de conhecimento clínico — reaproveita os ativos da Fase 2.

Duas funções complementam a resposta do assistente conversacional:

* `hipoteses_do_relato`  — cruza o texto do paciente com `mapa_conhecimento.csv`
  (31 pares sintoma → doença) e pontua as associações encontradas. É a mesma
  lógica por regras da Fase 2 — transparente e auditável, sem aprendizado.
* `classificar_risco`    — regressão logística sobre TF-IDF treinada com
  `frases_risco.csv` (303 relatos rotulados alto/baixo risco na Fase 2).

Ambas são **apoio à triagem**, nunca diagnóstico. O modelo é treinado uma única
vez, sob demanda, e mantido em memória.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from config import CAMINHO_DATASETS

from .texto_clinico import contem_termo, normalizar

ARQUIVO_MAPA = CAMINHO_DATASETS / "mapa_conhecimento.csv"
ARQUIVO_FRASES = CAMINHO_DATASETS / "frases_risco.csv"


@lru_cache(maxsize=1)
def _carregar_mapa() -> list[dict[str, str]]:
    import csv

    if not ARQUIVO_MAPA.exists():
        return []
    with ARQUIVO_MAPA.open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


def hipoteses_do_relato(texto: str, maximo: int = 3) -> list[dict[str, Any]]:
    """Hipóteses do mapa de conhecimento, ordenadas por número de sintomas casados.

    Duas coincidências (sintoma_1 e sintoma_2) valem mais que uma — mesma
    pontuação usada no notebook da Fase 2.
    """
    normalizado = normalizar(texto)
    pontuacoes: dict[str, dict[str, Any]] = {}

    for linha in _carregar_mapa():
        doenca = (linha.get("doenca_associada") or "").strip()
        if not doenca:
            continue
        casados = [
            linha[coluna].strip()
            for coluna in ("sintoma_1", "sintoma_2")
            if linha.get(coluna) and contem_termo(linha[coluna], normalizado)
        ]
        if not casados:
            continue

        registro = pontuacoes.setdefault(
            doenca, {"doenca": doenca, "pontuacao": 0, "sintomas": []}
        )
        registro["pontuacao"] += len(casados)
        for sintoma in casados:
            if sintoma not in registro["sintomas"]:
                registro["sintomas"].append(sintoma)

    ordenadas = sorted(pontuacoes.values(), key=lambda r: -r["pontuacao"])
    return ordenadas[:maximo]


@lru_cache(maxsize=1)
def _modelo_risco():
    """Treina (uma vez) o classificador de risco da Fase 2. None se indisponível."""
    try:
        import pandas as pd
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
    except ImportError:
        return None

    if not ARQUIVO_FRASES.exists():
        return None

    df = pd.read_csv(ARQUIVO_FRASES, encoding="utf-8")
    if {"frase", "situacao"} - set(df.columns) or df.empty:
        return None

    modelo = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, strip_accents="unicode"),
        LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced"),
    )
    modelo.fit(df["frase"].astype(str), df["situacao"].astype(str))
    return modelo


def classificar_risco(texto: str) -> dict[str, Any] | None:
    """Classifica o relato em alto/baixo risco. None se o modelo não estiver disponível.

    Atenção: o modelo foi treinado com relatos que **descrevem valores clínicos**
    (pressão, colesterol, frequência máxima). Numa frase coloquial curta a
    confiança tende a ser baixa — por isso a saída é sempre apresentada como
    indício, e não como conclusão.
    """
    modelo = _modelo_risco()
    if modelo is None or not texto.strip():
        return None

    classe = str(modelo.predict([texto])[0])
    probabilidade = float(max(modelo.predict_proba([texto])[0]))
    return {
        "classe": classe,
        "confianca": round(probabilidade, 3),
        "fonte": "regressão logística sobre TF-IDF (frases_risco.csv, Fase 2)",
    }


def analisar(texto: str) -> dict[str, Any]:
    """Análise completa de um relato: hipóteses por regras + classificação de risco."""
    return {
        "hipoteses": hipoteses_do_relato(texto),
        "risco": classificar_risco(texto),
    }
