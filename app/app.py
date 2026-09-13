"""CardioIA — Fase 5: backend Flask do assistente cardiológico conversacional.

Fluxo de uma mensagem:

    interface HTML ──POST /api/mensagem──▶ Flask
                                            ├─▶ watsonx Assistant (NLU + diálogo)
                                            │     └─ indisponível? motor local
                                            ├─▶ camada de conhecimento (Fase 2)
                                            └─▶ SQLite (histórico da sessão)

Executar:
    cd app && python app.py     →  http://127.0.0.1:5000
"""

from __future__ import annotations

import uuid
from typing import Any

from flask import Flask, jsonify, render_template, request

import config
from assistente import banco
from assistente.conhecimento import analisar
from assistente.motor_local import MotorLocal
from assistente.watson_cliente import ErroWatson, criar_cliente

app = Flask(__name__)

motor_local = MotorLocal(config.CAMINHO_SKILL_JSON)
cliente_watson = criar_cliente()

# Contexto conversacional por sessão (o histórico persistente fica no SQLite).
CONTEXTOS: dict[str, dict[str, Any]] = {}

# Intenções em que faz sentido enriquecer a resposta com o conhecimento da Fase 2.
INTENCOES_CLINICAS = {"relatar_sintoma", "emergencia_cardiaca"}


def motor_ativo() -> str:
    return "watson" if cliente_watson else "local"


def _responder(texto: str, contexto: dict[str, Any]) -> dict[str, Any]:
    """Consulta o Watson e, em caso de falha, cai para o motor local."""
    if cliente_watson:
        try:
            return cliente_watson.responder(texto, contexto)
        except ErroWatson as erro:
            app.logger.warning("Watson indisponível (%s) — usando motor local.", erro)
    return motor_local.responder(texto, contexto)


def _deve_analisar(resposta: dict[str, Any]) -> bool:
    if resposta.get("intencao") in INTENCOES_CLINICAS:
        return True
    return any(e.get("entity") == "sintoma" for e in resposta.get("entidades") or [])


@app.get("/")
def pagina_inicial():
    return render_template("index.html", aviso=config.AVISO_MEDICO)


@app.post("/api/sessao")
def abrir_sessao():
    """Cria a sessão e devolve a mensagem de boas-vindas do assistente."""
    sessao_id = str(uuid.uuid4())
    banco.garantir_sessao(sessao_id, motor_ativo())

    saudacao = motor_local.mensagem_inicial()
    CONTEXTOS[sessao_id] = saudacao["contexto"]
    banco.registrar_mensagem(sessao_id, "assistente", saudacao["texto"])

    return jsonify(
        {
            "sessao_id": sessao_id,
            "mensagem": saudacao["texto"],
            "motor": motor_ativo(),
            "aviso": config.AVISO_MEDICO,
        }
    )


@app.post("/api/mensagem")
def enviar_mensagem():
    dados = request.get_json(silent=True) or {}
    texto = (dados.get("texto") or "").strip()
    sessao_id = dados.get("sessao_id") or str(uuid.uuid4())

    if not texto:
        return jsonify({"erro": "Mensagem vazia."}), 400
    if len(texto) > 1000:
        return jsonify({"erro": "Mensagem muito longa (máximo 1000 caracteres)."}), 400

    banco.garantir_sessao(sessao_id, motor_ativo())
    contexto = CONTEXTOS.get(sessao_id, {})

    resposta = _responder(texto, contexto)
    CONTEXTOS[sessao_id] = resposta.get("contexto") or {}

    # Enriquecimento com a base de conhecimento da Fase 2 (regras + risco).
    analise = analisar(texto) if _deve_analisar(resposta) else {"hipoteses": [], "risco": None}
    nivel_risco = (analise.get("risco") or {}).get("classe")

    banco.registrar_mensagem(
        sessao_id,
        "paciente",
        texto,
        intencao=resposta.get("intencao"),
        confianca=resposta.get("confianca"),
        entidades=resposta.get("entidades"),
        nivel_risco=nivel_risco,
    )
    banco.registrar_mensagem(sessao_id, "assistente", resposta["texto"])

    return jsonify(
        {
            "sessao_id": sessao_id,
            "resposta": resposta["texto"],
            "intencao": resposta.get("intencao"),
            "confianca": resposta.get("confianca"),
            "entidades": resposta.get("entidades"),
            "motor": resposta.get("motor"),
            "analise": analise,
        }
    )


@app.get("/api/historico/<sessao_id>")
def ver_historico(sessao_id: str):
    return jsonify({"sessao_id": sessao_id, "mensagens": banco.historico(sessao_id)})


@app.get("/api/saude")
def saude():
    """Diagnóstico rápido da aplicação (útil na demonstração e na correção)."""
    return jsonify(
        {
            "status": "ok",
            "motor": motor_ativo(),
            "watson_configurado": config.WATSON_CONFIGURADO,
            "forcar_motor_local": config.FORCAR_MOTOR_LOCAL,
            "intencoes": len(motor_local.skill["intents"]),
            "entidades": len(motor_local.skill["entities"]),
            "nos_dialogo": len(motor_local.skill["dialog_nodes"]),
            "banco": banco.resumo(),
        }
    )


def criar_app() -> Flask:
    banco.iniciar_banco()
    return app


if __name__ == "__main__":
    criar_app()
    print(f"[CardioIA] Motor conversacional: {motor_ativo()}")
    print(f"[CardioIA] http://{config.HOST}:{config.PORTA}")
    app.run(host=config.HOST, port=config.PORTA, debug=config.DEBUG)
