"""Motor conversacional local — contingência quando o watsonx Assistant não responde.

Executa o **mesmo** conteúdo do dialog skill (`cardioia_dialog_skill.json`): as
intenções são classificadas por TF-IDF sobre os exemplos de treino, as entidades são
reconhecidas pelos sinônimos declarados e a árvore de nós é percorrida com um
subconjunto da linguagem de condições do Watson (`#intenção`, `@entidade:valor`,
`$variável`, `&&`, `||`, `!`, parênteses).

Serve para dois cenários: demonstrar a aplicação sem credenciais na nuvem e manter o
atendimento de pé se a API estiver fora do ar. A plataforma oficial da entrega
continua sendo o watsonx Assistant.
"""

from __future__ import annotations

import json
import random
import re
from typing import Any

from .texto_clinico import contem_termo, normalizar

LIMIAR_INTENCAO = 0.38

# A intenção de emergência interrompe qualquer fluxo, então exige mais evidência
# para não ser disparada por semelhança superficial ("há dias" ~ "há vinte minutos").
# Emergências descritas com sintoma explícito continuam sendo pegas pelas entidades.
LIMIAR_EMERGENCIA = 0.62
INTENCAO_EMERGENCIA = "emergencia_cardiaca"


# ---------------------------------------------------------------------------
# Avaliador de condições (subconjunto da sintaxe do Watson)
# ---------------------------------------------------------------------------

TOKENS = re.compile(
    r"""
      (?P<abre>\()
    | (?P<fecha>\))
    | (?P<ou>\|\|)
    | (?P<e>&&)
    | (?P<nao>!)
    | (?P<comprimento>input\.text\.length\s*(?:>=|<=|==|>|<)\s*\d+)
    | (?P<confianca>intents\[0\]\.confidence\s*(?:>=|<=|==|>|<)\s*[\d.]+)
    | (?P<intencao>\#[\w.]+)
    | (?P<entidade>@[\w-]+(?::[\w-]+)?)
    | (?P<variavel>\$[\w]+\s*(?:>=|<=|==|!=|>|<)\s*[\w"']+)
    | (?P<verdadeiro>\btrue\b)
    | (?P<falso>\bfalse\b)
    | (?P<especial>\banything_else\b|\bwelcome\b|\bconversation_start\b)
    """,
    re.VERBOSE,
)

COMPARADORES = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


class Avaliador:
    """Parser recursivo descendente: expr := termo ('||' termo)*."""

    def __init__(self, condicao: str, ambiente: dict[str, Any]):
        self.tokens = [m for m in TOKENS.finditer(condicao)]
        self.pos = 0
        self.ambiente = ambiente

    def avaliar(self) -> bool:
        if not self.tokens:
            return False
        resultado = self._expr()
        return bool(resultado)

    def _atual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _expr(self) -> bool:
        valor = self._termo()
        while (t := self._atual()) and t.lastgroup == "ou":
            self.pos += 1
            valor = self._termo() or valor
        return valor

    def _termo(self) -> bool:
        valor = self._fator()
        while (t := self._atual()) and t.lastgroup == "e":
            self.pos += 1
            valor = self._fator() and valor
        return valor

    def _fator(self) -> bool:
        token = self._atual()
        if token is None:
            return False
        tipo = token.lastgroup
        self.pos += 1

        if tipo == "nao":
            return not self._fator()
        if tipo == "abre":
            valor = self._expr()
            if (t := self._atual()) and t.lastgroup == "fecha":
                self.pos += 1
            return valor
        if tipo == "fecha":
            return False
        return self._atomo(tipo, token.group())

    def _atomo(self, tipo: str, texto: str) -> bool:
        amb = self.ambiente
        if tipo == "verdadeiro":
            return True
        if tipo == "falso":
            return False
        if tipo == "especial":
            return texto == amb.get("evento")
        if tipo == "intencao":
            return amb.get("intencao") == texto[1:]
        if tipo == "entidade":
            corpo = texto[1:]
            if ":" in corpo:
                entidade, valor = corpo.split(":", 1)
                return (entidade, valor) in amb["entidades_pares"]
            return corpo in amb["entidades_nomes"]
        if tipo == "confianca":
            operador = re.search(r"(>=|<=|==|>|<)", texto).group(1)
            limite = float(re.search(r"([\d.]+)$", texto).group(1))
            return COMPARADORES[operador](float(amb.get("confianca") or 0.0), limite)
        if tipo == "comprimento":
            operador = re.search(r"(>=|<=|==|>|<)", texto).group(1)
            numero = int(re.search(r"(\d+)$", texto).group(1))
            return COMPARADORES[operador](len(amb.get("texto", "")), numero)
        if tipo == "variavel":
            nome, operador, alvo = re.match(
                r"\$(\w+)\s*(>=|<=|==|!=|>|<)\s*(.+)", texto
            ).groups()
            atual = amb["contexto"].get(nome)
            alvo = alvo.strip().strip("\"'")

            # `$campo == null` é o que decide qual pergunta da coleta ainda falta.
            # Vazio conta como ausente: o Watson devolve "" quando a entidade não
            # veio, e aqui os dois precisam significar a mesma coisa.
            if alvo == "null":
                ausente = atual is None or atual == ""
                return ausente if operador == "==" else not ausente

            try:
                atual_num = float(atual if atual is not None else 0)
                return COMPARADORES[operador](atual_num, float(alvo))
            except (TypeError, ValueError):
                return COMPARADORES[operador](str(atual or ""), alvo)
        return False


def condicao_atendida(condicao: str | None, ambiente: dict[str, Any]) -> bool:
    if not condicao:
        return False
    return Avaliador(condicao, ambiente).avaliar()


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------


class MotorLocal:
    """Interpreta o dialog skill exportado, sem depender da nuvem."""

    def __init__(self, caminho_skill):
        self.skill = json.loads(caminho_skill.read_text(encoding="utf-8"))
        self.nos = {n["dialog_node"]: n for n in self.skill["dialog_nodes"]}
        self.raizes = [n for n in self.skill["dialog_nodes"] if not n.get("parent")]
        self._indexar_entidades()
        self._treinar_intencoes()

    # --- preparação --------------------------------------------------------

    def _indexar_entidades(self) -> None:
        self.sinonimos: list[tuple[str, str, str]] = []
        for entidade in self.skill["entities"]:
            for valor in entidade["values"]:
                termos = [valor["value"].replace("_", " ")] + valor.get("synonyms", [])
                for termo in termos:
                    self.sinonimos.append(
                        (entidade["entity"], valor["value"], normalizar(termo))
                    )
        # Termos mais longos primeiro: "dor no braço esquerdo" antes de "dor no braço".
        self.sinonimos.sort(key=lambda s: -len(s[2]))

    def _treinar_intencoes(self) -> None:
        self.exemplos: list[str] = []
        self.rotulos: list[str] = []
        for intencao in self.skill["intents"]:
            for exemplo in intencao["examples"]:
                self.exemplos.append(exemplo["text"])
                self.rotulos.append(intencao["intent"])

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self.vetorizador = TfidfVectorizer(
                ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True
            )
            self.matriz = self.vetorizador.fit_transform(self.exemplos)
        except ImportError:  # fallback sem scikit-learn
            self.vetorizador = None
            self.matriz = None

    # --- NLU ---------------------------------------------------------------

    def detectar_entidades(self, texto: str) -> list[dict[str, Any]]:
        normalizado = normalizar(texto)
        encontradas: list[dict[str, Any]] = []
        vistos: set[tuple[str, str]] = set()
        for entidade, valor, termo in self.sinonimos:
            if (entidade, valor) in vistos:
                continue
            if contem_termo(termo, normalizado):
                encontradas.append({"entity": entidade, "value": valor, "literal": termo})
                vistos.add((entidade, valor))
        return encontradas

    def classificar_intencao(self, texto: str) -> tuple[str | None, float]:
        if not texto.strip():
            return None, 0.0

        if self.vetorizador is not None:
            from sklearn.metrics.pairwise import cosine_similarity

            similaridades = cosine_similarity(
                self.vetorizador.transform([texto]), self.matriz
            )[0]
            melhor = int(similaridades.argmax())
            confianca = float(similaridades[melhor])
        else:
            alvo = set(normalizar(texto).split())
            pontuacoes = [
                len(alvo & set(normalizar(e).split())) / max(len(alvo), 1)
                for e in self.exemplos
            ]
            melhor = max(range(len(pontuacoes)), key=pontuacoes.__getitem__)
            confianca = pontuacoes[melhor]

        intencao = self.rotulos[melhor]
        limiar = (
            LIMIAR_EMERGENCIA if intencao == INTENCAO_EMERGENCIA else LIMIAR_INTENCAO
        )
        if confianca < limiar:
            return None, round(confianca, 3)
        return intencao, round(confianca, 3)

    # --- navegação na árvore ----------------------------------------------

    def _filhos(self, id_pai: str) -> list[dict]:
        return [n for n in self.skill["dialog_nodes"] if n.get("parent") == id_pai]

    def _irmaos_a_partir_de(self, id_no: str) -> list[dict]:
        """O nó e os irmãos que vêm depois dele, na ordem de avaliação."""
        no_alvo = self.nos.get(id_no)
        if no_alvo is None:
            return []
        pai = no_alvo.get("parent")
        irmaos = [n for n in self.skill["dialog_nodes"] if n.get("parent") == pai]
        posicao = next(
            (i for i, n in enumerate(irmaos) if n["dialog_node"] == id_no), None
        )
        return irmaos[posicao:] if posicao is not None else []

    def _texto_do_no(self, no: dict, contexto: dict) -> str:
        """Junta os blocos de resposta; dentro de um bloco, escolhe uma variante."""
        partes = []
        for bloco in (no.get("output") or {}).get("generic") or []:
            valores = [v.get("text", "") for v in bloco.get("values", []) if v.get("text")]
            if not valores:
                continue
            partes.append(random.choice(valores) if len(valores) > 1 else valores[0])
        return self._resolver_variaveis("\n\n".join(partes), contexto)

    @staticmethod
    def _resolver_variaveis(texto: str, contexto: dict) -> str:
        def troca(match: re.Match) -> str:
            nome = match.group(1)
            valor = contexto.get(nome)
            if valor in (None, ""):
                return "não informado"
            return str(valor).replace("_", " ")

        return re.sub(r"<\?\s*\$(\w+)(?:\.replace\([^)]*\))?\s*\?>", troca, texto)

    # `<? @entidade != null ? @entidade.value : $variavel ?>` (preserva o já dito)
    # e `... : null ?>` (zera quando a entidade não veio, no início de uma coleta).
    CAPTURA = re.compile(
        r"<\?\s*@(\w+)\s*!=\s*null\s*\?\s*@\1\.value\s*:\s*(\$(\w+)|null)\s*\?>"
    )

    def _aplicar_contexto(self, no: dict, contexto: dict, ambiente: dict) -> None:
        for chave, valor in (no.get("context") or {}).items():
            if isinstance(valor, str):
                captura = self.CAPTURA.fullmatch(valor.strip())
                if captura:
                    entidade, _, anterior = captura.groups()
                    achado = next(
                        (
                            e["value"]
                            for e in ambiente["entidades"]
                            if e["entity"] == entidade
                        ),
                        None,
                    )
                    if achado is not None:
                        valor = achado
                    elif anterior:
                        continue  # mantém o que já estava no contexto
                    else:
                        valor = ""  # início de coleta: limpa resíduo anterior
                elif valor.startswith("@"):
                    achado = next(
                        (
                            e["value"]
                            for e in ambiente["entidades"]
                            if e["entity"] == valor[1:]
                        ),
                        None,
                    )
                    if achado is None:
                        continue
                    valor = achado
                elif "input.text" in valor:
                    valor = ambiente["texto"]
                elif "$falhas" in valor and "+ 1" in valor:
                    valor = int(contexto.get("falhas") or 0) + 1
            contexto[chave] = valor

    def _resolver(
        self, no: dict, contexto: dict, ambiente: dict, saltos: int = 0
    ) -> dict | None:
        """Aplica o contexto do nó e segue para filhos ou para o alvo de um salto."""
        self._aplicar_contexto(no, contexto, ambiente)
        proximo = no.get("next_step") or {}
        comportamento = proximo.get("behavior")

        if comportamento == "jump_to" and saltos < 5:
            destino = proximo.get("dialog_node", "")
            if proximo.get("selector") == "condition":
                # Salta para o nó e, se a condição dele não bater, segue avaliando os
                # irmãos seguintes — é assim que a coleta encontra a pergunta pendente.
                for candidato in self._irmaos_a_partir_de(destino):
                    if condicao_atendida(candidato.get("conditions"), ambiente):
                        return self._resolver(candidato, contexto, ambiente, saltos + 1)
                return None
            alvo = self.nos.get(destino)
            if alvo is not None:
                return self._resolver(alvo, contexto, ambiente, saltos + 1)

        if comportamento == "skip_user_input":
            for filho in self._filhos(no["dialog_node"]):
                if condicao_atendida(filho.get("conditions"), ambiente):
                    return self._resolver(filho, contexto, ambiente, saltos)
            return None
        return no

    # --- ponto de entrada --------------------------------------------------

    def responder(self, texto: str, contexto: dict | None = None) -> dict[str, Any]:
        contexto = dict(contexto or {})
        entidades = self.detectar_entidades(texto)
        intencao, confianca = self.classificar_intencao(texto)

        ambiente = {
            "texto": texto,
            "intencao": intencao,
            "entidades": entidades,
            "entidades_nomes": {e["entity"] for e in entidades},
            "entidades_pares": {(e["entity"], e["value"]) for e in entidades},
            "contexto": contexto,
            "confianca": confianca,
            "evento": None,
        }

        resposta: str | None = None

        # Mesma regra do Watson: a árvore é percorrida de cima para baixo a cada
        # turno, então o nó de emergência (o primeiro) é sempre avaliado — inclusive
        # no meio de uma coleta.
        for no in self.raizes:
            condicao = no.get("conditions")
            if condicao in {"welcome", "conversation_start", "anything_else"}:
                continue
            if not condicao_atendida(condicao, ambiente):
                continue
            alvo = self._resolver(no, contexto, ambiente)
            resposta = self._texto_do_no(alvo, contexto) if alvo else None
            break

        if resposta is None:
            fallback = self.nos.get("fora_de_escopo")
            alvo = self._resolver(fallback, contexto, ambiente)
            resposta = self._texto_do_no(alvo, contexto) if alvo else (
                "Não entendi. Pode reformular?"
            )

        contexto.pop("_evento", None)
        return {
            "texto": resposta,
            "intencao": intencao,
            "confianca": confianca,
            "entidades": entidades,
            "contexto": contexto,
            "motor": "local",
        }

    def mensagem_inicial(self) -> dict[str, Any]:
        contexto: dict[str, Any] = {}
        no = self.nos.get("boas_vindas")
        self._aplicar_contexto(no, contexto, {"entidades": [], "texto": ""})
        return {
            "texto": self._texto_do_no(no, contexto),
            "intencao": None,
            "confianca": None,
            "entidades": [],
            "contexto": contexto,
            "motor": "local",
        }
