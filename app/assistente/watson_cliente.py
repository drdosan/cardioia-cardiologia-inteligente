"""Integração com o IBM watsonx Assistant (API v2, modo stateless).

Usamos `message_stateless`: o contexto da conversa fica sob nossa guarda (sessão do
Flask + SQLite) em vez de depender de uma sessão da nuvem que expira em minutos.
Isso simplifica a demonstração e deixa o histórico auditável do nosso lado.

Credenciais vêm de variáveis de ambiente (`.env`) — ver `config.py`.
"""

from __future__ import annotations

from typing import Any

import config


class ErroWatson(RuntimeError):
    """Falha ao falar com o watsonx Assistant."""


class ClienteWatson:
    """Envelopa o SDK `ibm-watson` e normaliza a resposta para o formato do app."""

    def __init__(self) -> None:
        import inspect

        from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
        from ibm_watson import AssistantV2

        self.assistant = AssistantV2(
            version=config.WATSON_VERSION,
            authenticator=IAMAuthenticator(config.WATSON_API_KEY),
        )
        self.assistant.set_service_url(config.WATSON_URL)
        self.assistant_id = config.WATSON_ASSISTANT_ID
        self.environment_id = config.WATSON_ENVIRONMENT_ID or config.WATSON_ASSISTANT_ID

        # A partir do ibm-watson 9, `message_stateless` exige `environment_id`; nas
        # versões anteriores o parâmetro nem existe. Detectamos uma vez, para o mesmo
        # código rodar nos dois SDKs.
        parametros = inspect.signature(self.assistant.message_stateless).parameters
        self.exige_environment = "environment_id" in parametros

    @staticmethod
    def _variaveis_do_contexto(contexto: dict[str, Any]) -> dict[str, Any]:
        """Só as variáveis que nós definimos no diálogo — para exibir e registrar.

        O resto do contexto é estado interno do Watson (nó atual, slots pendentes,
        `dialog_stack`) e não deve ser interpretado pela aplicação.
        """
        skills = (contexto or {}).get("skills") or {}
        for skill in skills.values():
            if isinstance(skill, dict) and "user_defined" in skill:
                return skill.get("user_defined") or {}
        return {}

    @staticmethod
    def _extrair_texto(resultado: dict[str, Any]) -> str:
        """Texto legível de qualquer tipo de resposta do Watson.

        `suggestion` e `option` precisam estar aqui: quando o Watson não decide
        entre duas intenções, ele devolve um menu em vez de texto. Ignorar esses
        tipos faz a resposta parecer vazia sem que nada tenha falhado.
        """
        partes = []
        for item in (resultado.get("output") or {}).get("generic", []):
            tipo = item.get("response_type")
            if tipo == "text":
                partes.append(item.get("text", ""))
            elif tipo in {"option", "suggestion"}:
                titulo = item.get("title", "")
                rotulos = [
                    f"• {opcao.get('label', '')}"
                    for opcao in item.get("options") or item.get("suggestions") or []
                    if opcao.get("label")
                ]
                partes.append("\n".join([titulo, *rotulos]).strip())
        return "\n\n".join(p for p in partes if p)

    def responder(
        self,
        texto: str,
        contexto: dict[str, Any] | None = None,
        usuario_id: str = "cardioia-web",
    ) -> dict[str, Any]:
        argumentos: dict[str, Any] = {
            "assistant_id": self.assistant_id,
            "input": {
                "message_type": "text",
                "text": texto,
                "options": {"return_context": True},
            },
            # O contexto vai e volta INTEIRO. Reenviar só o `user_defined` faria o
            # Watson esquecer em que nó a conversa parou e quais slots faltam —
            # cada turno recomeçaria do zero.
            "context": contexto or None,
            "user_id": usuario_id,
        }
        if self.exige_environment:
            argumentos["environment_id"] = self.environment_id

        try:
            resultado = self.assistant.message_stateless(**argumentos).get_result()
        except Exception as erro:  # noqa: BLE001 — qualquer falha cai no motor local
            raise ErroWatson(str(erro)) from erro

        saida = resultado.get("output") or {}
        intencoes = saida.get("intents") or []
        entidades = [
            {"entity": e.get("entity"), "value": e.get("value")}
            for e in saida.get("entities") or []
        ]
        contexto_novo = resultado.get("context") or {}

        return {
            "texto": self._extrair_texto(resultado) or "Não consegui formular a resposta.",
            "intencao": intencoes[0]["intent"] if intencoes else None,
            "confianca": round(intencoes[0]["confidence"], 3) if intencoes else None,
            "entidades": entidades,
            "contexto": contexto_novo,
            "variaveis": self._variaveis_do_contexto(contexto_novo),
            "motor": "watson",
        }


def criar_cliente() -> ClienteWatson | None:
    """Devolve o cliente pronto, ou None se não houver credenciais / SDK."""
    if config.FORCAR_MOTOR_LOCAL or not config.WATSON_CONFIGURADO:
        return None
    try:
        return ClienteWatson()
    except ImportError:
        print("[CardioIA] SDK ibm-watson não instalado — usando o motor local.")
    except Exception as erro:  # noqa: BLE001
        print(f"[CardioIA] Falha ao iniciar o cliente Watson ({erro}) — motor local.")
    return None
