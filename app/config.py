"""Configuração do backend CardioIA (Fase 5).

Todos os segredos vêm de variáveis de ambiente / arquivo .env — nunca do código.
Copie `.env.example` para `.env` e preencha com as credenciais da sua instância
do watsonx Assistant.
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ_APP = Path(__file__).resolve().parent
RAIZ_REPO = RAIZ_APP.parent

# Carrega o .env se python-dotenv estiver instalado (opcional).
try:
    from dotenv import load_dotenv

    load_dotenv(RAIZ_APP / ".env")
except ImportError:  # pragma: no cover - ambiente sem python-dotenv
    pass


def _bool(nome: str, padrao: bool = False) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "sim", "yes", "on"}


# --- watsonx Assistant -----------------------------------------------------
WATSON_API_KEY = os.getenv("WATSON_API_KEY", "").strip()
WATSON_URL = os.getenv("WATSON_URL", "").strip()
WATSON_ASSISTANT_ID = os.getenv("WATSON_ASSISTANT_ID", "").strip()
WATSON_VERSION = os.getenv("WATSON_VERSION", "2021-11-27").strip()

# Ambiente do assistente (draft/live). No plano Lite não existem ambientes separados
# e o próprio assistant_id funciona como environment_id — por isso o padrão.
WATSON_ENVIRONMENT_ID = os.getenv("WATSON_ENVIRONMENT_ID", "").strip()

# Com credenciais completas usamos o Watson; sem elas, o motor local assume.
WATSON_CONFIGURADO = bool(WATSON_API_KEY and WATSON_URL and WATSON_ASSISTANT_ID)

# Força o motor local mesmo com credenciais (útil para demonstrar offline).
FORCAR_MOTOR_LOCAL = _bool("FORCAR_MOTOR_LOCAL", False)

# --- Aplicação -------------------------------------------------------------
HOST = os.getenv("HOST", "127.0.0.1")
PORTA = int(os.getenv("PORTA", "5000"))
DEBUG = _bool("DEBUG", True)

# --- Caminhos --------------------------------------------------------------
CAMINHO_BANCO = Path(os.getenv("CAMINHO_BANCO", RAIZ_APP / "dados" / "cardioia.db"))
CAMINHO_DATASETS = RAIZ_REPO / "datasets"
CAMINHO_SKILL_JSON = RAIZ_APP / "watson" / "cardioia_dialog_skill.json"

AVISO_MEDICO = (
    "Protótipo acadêmico do projeto CardioIA (FIAP). Não realiza diagnóstico nem "
    "prescrição e não substitui avaliação médica. Em emergência, ligue 192 (SAMU)."
)
