"""Casamento de termos clínicos em texto livre (PT-BR).

O paciente não escreve como o dicionário: diz "minhas pernas estão inchadas" onde o
termo cadastrado é "pernas inchadas", e "palpitações" onde o termo é "palpitação".
Comparar por substring exata perde os dois casos.

Este módulo constrói, para cada termo, uma expressão regular que tolera:

* **acentuação** — tudo é normalizado antes da comparação;
* **plural** — inclusive o irregular em "-ão" → "-ões" ("palpitação" → "palpitações");
* **conectores** entre as palavras do termo — só os da lista `CONECTORES`, para não
  casar coisas distantes ("dor ... peito" numa frase inteira).

É usado tanto pelo reconhecimento de entidades do motor local quanto pelo mapa de
conhecimento da Fase 2, para que os dois enxerguem a fala do paciente do mesmo jeito.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# Palavras que podem aparecer no meio de um termo sem mudar seu sentido.
#
# Os qualificadores importam para a segurança da triagem: o relato real
# "aperto FORTE no tórax" precisa casar o termo cadastrado "aperto no tórax",
# senão a regra de emergência (dor no peito + irradiação para o braço) não dispara.
QUALIFICADORES = (
    "forte|fortes|fraca|fraco|fracas|fracos|leve|leves|intensa|intenso|"
    "grande|grandes|pequena|pequeno|constante|constantes|frequente|frequentes|"
    "terrivel|insuportavel|subita|subito|repentina|repentino|persistente|"
    "estranha|estranho|esquisita|esquisito"
)

CONECTORES = (
    "estao|esta|estava|estavam|anda|andam|fica|ficam|muito|bem|meio|bastante|"
    "um|uma|uns|umas|o|a|os|as|de|do|da|dos|das|no|na|nos|nas|com|e|que|"
    f"meu|minha|meus|minhas|seu|sua|{QUALIFICADORES}"
)


def normalizar(texto: str) -> str:
    """Minúsculas sem acento — 'Palpitação' e 'palpitacao' passam a ser iguais."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def _flexionar(palavra: str) -> str:
    """Trecho de regex que aceita a palavra no singular e no plural."""
    if palavra.endswith("ao"):  # palpitacao → palpitacoes / palpitacaos
        return re.escape(palavra[:-2]) + "(?:ao|oes|aes|aos)"
    if palavra.endswith(("r", "z", "s", "l")):  # mulher → mulheres; mal → males
        return re.escape(palavra) + "(?:e?s)?"
    return re.escape(palavra) + "s?"


@lru_cache(maxsize=2048)
def padrao_do_termo(termo: str) -> re.Pattern[str]:
    """Compila o termo (já em forma livre) num padrão tolerante a plural e conectores."""
    palavras = [p for p in normalizar(termo).split() if p]
    if not palavras:
        return re.compile(r"(?!x)x")  # padrão que nunca casa
    ligacao = rf"(?:\s+(?:{CONECTORES}))*\s+"
    corpo = ligacao.join(_flexionar(p) for p in palavras)
    return re.compile(rf"\b{corpo}\b")


def contem_termo(termo: str, texto_normalizado: str) -> bool:
    """Diz se o termo aparece no texto (que já deve estar normalizado)."""
    return padrao_do_termo(termo).search(texto_normalizado) is not None
