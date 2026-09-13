"""Gera o arquivo de importacao do dialog skill do CardioIA (watsonx Assistant).

Este script e a fonte de verdade do conteudo conversacional: intencoes, entidades e
arvore de dialogo sao descritas aqui em Python legivel, e o JSON de importacao e
gerado a partir delas (parent / previous_sibling calculados automaticamente).

Parte do conteudo e **derivada dos datasets da Fase 2**, para que o chatbot e a
camada de conhecimento clinica falem o mesmo vocabulario:

* `datasets/mapa_conhecimento.csv` -> sinonimos das entidades @sintoma, @contexto
  e @fator_risco. Todo termo do CSV precisa ter destino declarado em
  TERMOS_FASE2 ou justificativa em TERMOS_IGNORADOS; se a Fase 2 ganhar um termo
  novo, a geracao falha avisando qual ficou sem classificacao.
* `datasets/sintomas_pacientes.txt` -> exemplos de treino reais das intencoes,
  conforme a classificacao em RELATOS_FASE2.

Executar:
    python app/watson/gerar_skill_json.py

Saida:
    app/watson/cardioia_dialog_skill.json
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

SAIDA = Path(__file__).parent / "cardioia_dialog_skill.json"
DATASETS = Path(__file__).resolve().parents[2] / "datasets"
ARQUIVO_MAPA = DATASETS / "mapa_conhecimento.csv"
ARQUIVO_RELATOS = DATASETS / "sintomas_pacientes.txt"

AVISO = "Sou um protótipo acadêmico do CardioIA e não substituo avaliação médica."

# Exemplos marcados como irrelevantes. Sem eles o Watson classifica ruído de teclado
# como saudação ou despedida (confianças acima de 0,6 observadas na instância real) e
# o fallback escalonado nunca chega a rodar.
CONTRAEXEMPLOS = [
    "asdfgh", "xpto blablabla", "zzz qqq www", "kkkkkk", "aaaa bbbb cccc",
    "teste 123", "qwerty", "lorem ipsum dolor", "1234567", "??????",
    "quanto custa o bitcoin", "qual a receita de bolo de cenoura",
    "quem ganhou o jogo ontem", "qual a previsão do tempo",
]

# ---------------------------------------------------------------------------
# Intenções — o que o paciente quer dizer
# ---------------------------------------------------------------------------

INTENCOES: dict[str, list[str]] = {
    "saudacao": [
        "oi", "olá", "bom dia", "boa tarde", "boa noite", "e aí",
        "oi, tudo bem?", "olá, preciso de ajuda", "oi cardioia",
        "quero começar o atendimento",
    ],
    "capacidades_assistente": [
        "o que você faz", "como você pode me ajudar", "quais são suas funções",
        "você é um médico", "com o que você me ajuda",
        "para que serve esse assistente", "você dá diagnóstico",
        "o que eu posso perguntar aqui",
    ],
    "emergencia_cardiaca": [
        "estou com uma dor muito forte no peito agora",
        "dor no peito que irradia para o braço esquerdo",
        "sinto um aperto forte no peito e suor frio",
        "acho que estou tendo um infarto",
        "meu pai desmaiou e está pálido",
        "dor no peito forte com falta de ar e enjoo",
        "estou passando muito mal do coração",
        "dor esmagadora no peito há vinte minutos",
        "peito apertado e não consigo respirar",
        "socorro, dor no peito muito forte",
    ],
    "relatar_sintoma": [
        "estou sentindo falta de ar",
        "sinto o coração acelerado às vezes",
        "tenho sentido cansaço quando subo escadas",
        "minhas pernas estão inchadas",
        "sinto tontura quando levanto rápido",
        "ando com palpitações à noite",
        "sinto um desconforto no peito quando caminho",
        "tenho me cansado muito ultimamente",
        "acordo com falta de ar",
        "meu coração dispara do nada",
        "sinto dor no peito leve de vez em quando",
        "sinto dor no peito e falta de ar quando subo escadas",
        "tenho falta de ar e cansaço quando caminho rápido",
        "sinto um aperto no peito no esforço que passa com o repouso",
        "queria falar sobre um sintoma",
    ],
    "duvida_fator_risco": [
        "minha pressão está 150 por 100, é ruim?",
        "colesterol alto faz mal ao coração",
        "diabetes aumenta o risco cardíaco?",
        "fumar prejudica o coração",
        "sou obeso, tenho mais risco de infarto?",
        "meu pai teve infarto, eu tenho risco?",
        "o que é hipertensão",
        "estresse causa problema no coração",
        "sedentarismo é fator de risco",
        "quais são os fatores de risco cardiovascular",
    ],
    "prevencao_habitos": [
        "como prevenir doenças do coração",
        "que exercício posso fazer",
        "qual dieta é boa para o coração",
        "quanto de sal eu posso comer",
        "como melhorar minha saúde cardiovascular",
        "dicas para cuidar do coração",
        "caminhada ajuda o coração",
        "o que fazer para baixar o colesterol",
    ],
    "duvida_exame": [
        "para que serve o eletrocardiograma",
        "o que é um ecocardiograma",
        "como é o teste ergométrico",
        "preciso jejuar para o exame de sangue",
        "o que o holter mede",
        "como me preparo para o teste de esforço",
        "quanto tempo demora o resultado do exame",
        "esse exame dói",
    ],
    "duvida_medicamento": [
        "posso parar de tomar o remédio da pressão",
        "esqueci de tomar meu remédio",
        "qual é a dose do meu medicamento",
        "posso tomar dois comprimidos juntos",
        "esse remédio tem efeito colateral",
        "posso beber tomando esse remédio",
        "posso trocar meu remédio por outro",
    ],
    "agendar_consulta": [
        "quero marcar uma consulta",
        "preciso agendar com o cardiologista",
        "como marco um retorno",
        "tem horário para essa semana",
        "quero agendar atendimento",
        "gostaria de marcar uma avaliação",
    ],
    "monitoramento_dispositivo": [
        "o que significam os dados do meu monitor",
        "meu batimento está em 130",
        "como funciona o monitoramento contínuo",
        "meu dispositivo mostrou um alerta",
        "qual batimento é considerado normal",
        "minha frequência cardíaca está alta",
    ],
    "falar_com_humano": [
        "quero falar com um atendente",
        "me passa para uma pessoa",
        "preciso falar com um médico de verdade",
        "quero atendimento humano",
        "você não está me ajudando, chama alguém",
        "tem alguém aí para conversar",
    ],
    "agradecimento": [
        "obrigado", "obrigada", "valeu", "muito obrigado pela ajuda",
        "você me ajudou bastante", "agradeço",
    ],
    "despedida": [
        "tchau", "até logo", "encerrar atendimento", "é só isso",
        "pode encerrar", "até mais", "adeus",
    ],
}

# ---------------------------------------------------------------------------
# Entidades — informações clínicas extraídas da fala
# ---------------------------------------------------------------------------

ENTIDADES: dict[str, dict[str, list[str]]] = {
    "sintoma": {
        "dor_no_peito": [
            "dor no peito", "dor torácica", "aperto no peito", "aperto no tórax",
            "peso no peito", "queimação no peito", "desconforto no peito",
            "dor no coração",
        ],
        "falta_de_ar": [
            "falta de ar", "sem fôlego", "dificuldade para respirar", "ofegante",
            "não consigo respirar", "respiração curta",
        ],
        "palpitacao": [
            "palpitação", "coração acelerado", "coração disparado", "taquicardia",
            "coração batendo forte", "batimentos disparados",
        ],
        "batimentos_irregulares": [
            "batimentos irregulares", "coração descompassado", "batidas falhando",
            "coração fora do ritmo", "arritmia",
        ],
        "aperto_na_garganta": [
            "aperto na garganta", "nó na garganta", "garganta apertada",
            "queimação na garganta",
        ],
        "zumbido_ouvido": ["zumbido no ouvido", "zunido no ouvido", "apito no ouvido"],
        "febre": ["febre", "febril", "temperatura alta", "corpo quente"],
        "tontura": ["tontura", "tonteira", "vertigem", "cabeça leve", "zonzo"],
        "cansaco": [
            "cansaço", "fadiga", "canso fácil", "sem energia", "cansaço extremo",
            "fraqueza",
        ],
        "inchaco_pernas": [
            "inchaço nas pernas", "pernas inchadas", "pé inchado", "edema",
            "tornozelo inchado", "inchaço nos tornozelos", "inchaço",
        ],
        "sudorese": ["suor frio", "sudorese", "suando muito", "suor excessivo"],
        "dor_no_braco": [
            "dor no braço", "dor no braço esquerdo", "formigamento no braço",
            "dor irradiando para o braço", "irradiando para o braço",
            "irradia para o braço", "braço esquerdo",
        ],
        "desmaio": [
            "desmaio", "desmaiei", "desmaiou", "desmaiado", "perdi a consciência",
            "perdeu a consciência", "apaguei", "quase desmaiei", "síncope",
        ],
    },
    "intensidade": {
        "forte": [
            "forte", "muito forte", "insuportável", "intensa", "esmagadora",
            "não aguento", "terrível",
        ],
        "moderada": ["moderada", "média", "incomoda", "atrapalha"],
        "leve": ["leve", "fraca", "suave", "levinha", "quase nada"],
    },
    "duracao": {
        "agora": [
            "agora", "neste momento", "começou agora", "há minutos",
            "há poucos minutos", "acabou de começar",
        ],
        "horas": [
            "há horas", "desde hoje de manhã", "desde ontem à noite", "algumas horas",
        ],
        "dias": ["há dias", "faz dias", "desde a semana passada", "alguns dias"],
        "semanas": ["há semanas", "faz meses", "há muito tempo", "várias semanas"],
    },
    "fator_risco": {
        "hipertensao": [
            "pressão alta", "hipertensão", "hipertenso", "pressão está alta",
            "pressão descontrolada", "pressão elevada", "pressão nas alturas",
            "pressão subiu", "pressão arterial",
        ],
        "colesterol_alto": [
            "colesterol", "colesterol alto", "colesterol elevado", "dislipidemia",
            "triglicérides", "triglicérides alto", "gordura no sangue",
        ],
        "diabetes": ["diabetes", "diabético", "glicemia alta", "açúcar alto no sangue"],
        "tabagismo": ["fumo", "fumante", "cigarro", "tabagismo"],
        "obesidade": ["obesidade", "obeso", "acima do peso", "sobrepeso"],
        "sedentarismo": [
            "sedentarismo", "sedentário", "não faço exercício", "parado o dia todo",
        ],
        "historico_familiar": [
            "histórico familiar", "meu pai teve infarto",
            "minha mãe tem problema no coração", "doença de família",
        ],
    },
    # Situação em que o sintoma aparece — é o que separa angina estável (esforço),
    # angina instável (repouso) e pericardite (deitar/inclinar) no mapa da Fase 2.
    "contexto": {
        "esforco": [
            "esforço", "esforço físico", "subir escadas", "escada", "carregar peso",
            "correr", "caminhar rápido", "atividades simples", "me apressar",
            "fazer força",
        ],
        "repouso": [
            "repouso", "em repouso", "descansar", "descanso", "parado", "sentado",
            "sem fazer nada",
        ],
        "deitado": [
            "deitar", "ao deitar", "deitado", "travesseiros", "quando me deito",
            "ao dormir",
        ],
        "inclinar_corpo": [
            "inclinar", "inclinar o corpo", "inclinado para frente",
            "quando me inclino",
        ],
    },
    # Característica da dor — NÃO entra no slot "em que situação ocorre". Irradiação
    # é sinal de alarme de síndrome coronariana: precisa disparar a emergência, não
    # ser consumida como resposta de uma pergunta da triagem.
    "caracteristica": {
        "irradiacao": [
            "irradia", "irradiando", "irradiada", "espalha para", "vai para o braço",
            "desce pelo braço", "sobe para o pescoço", "vai para a mandíbula",
        ],
    },
    "turno": {
        "manhã": ["de manhã", "pela manhã", "cedo", "matutino"],
        "tarde": ["à tarde", "de tarde", "depois do almoço", "vespertino"],
    },
    "exame": {
        "eletrocardiograma": ["eletrocardiograma", "eletro", "ecg"],
        "ecocardiograma": ["ecocardiograma", "eco do coração", "ultrassom do coração"],
        "teste_ergometrico": ["teste ergométrico", "teste de esforço", "esteira"],
        "holter": ["holter", "monitor de 24 horas", "holter 24h"],
        "exame_sangue": [
            "exame de sangue", "colesterol total", "troponina", "hemograma",
            "perfil lipídico",
        ],
    },
}


# ---------------------------------------------------------------------------
# Derivação a partir dos datasets da Fase 2
# ---------------------------------------------------------------------------

# Destino de cada termo de `mapa_conhecimento.csv` nas entidades do skill.
# Manter esta tabela é o que impede o chatbot e a camada de conhecimento clínica
# de divergirem: um termo novo na Fase 2 quebra a geração até ser classificado.
TERMOS_FASE2: dict[str, tuple[str, str]] = {
    # sintomas
    "dor no peito": ("sintoma", "dor_no_peito"),
    "aperto no tórax": ("sintoma", "dor_no_peito"),
    "peso no peito": ("sintoma", "dor_no_peito"),
    "falta de ar": ("sintoma", "falta_de_ar"),
    "cansaço": ("sintoma", "cansaco"),
    "cansaço extremo": ("sintoma", "cansaco"),
    "palpitações": ("sintoma", "palpitacao"),
    "batimentos disparados": ("sintoma", "palpitacao"),
    "batimentos irregulares": ("sintoma", "batimentos_irregulares"),
    "tontura": ("sintoma", "tontura"),
    "tonteira": ("sintoma", "tontura"),
    "desmaio": ("sintoma", "desmaio"),
    "inchaço": ("sintoma", "inchaco_pernas"),
    "aperto na garganta": ("sintoma", "aperto_na_garganta"),
    "zumbido no ouvido": ("sintoma", "zumbido_ouvido"),
    "febre": ("sintoma", "febre"),
    "braço esquerdo": ("sintoma", "dor_no_braco"),
    # situação em que o sintoma ocorre
    "esforço": ("contexto", "esforco"),
    "esforço físico": ("contexto", "esforco"),
    "subir escadas": ("contexto", "esforco"),
    "escada": ("contexto", "esforco"),
    "carregar peso": ("contexto", "esforco"),
    "correr": ("contexto", "esforco"),
    "atividades simples": ("contexto", "esforco"),
    "repouso": ("contexto", "repouso"),
    "descansar": ("contexto", "repouso"),
    "deitar": ("contexto", "deitado"),
    "travesseiros": ("contexto", "deitado"),
    "inclinar": ("contexto", "inclinar_corpo"),
    "irradia": ("caracteristica", "irradiacao"),
    # fator de risco
    "pressão arterial elevada": ("fator_risco", "hipertensao"),
}

# Termos do CSV deixados de fora de propósito, com o motivo.
TERMOS_IGNORADOS: dict[str, str] = {
    "aperto": "isolado é ambíguo; coberto por 'aperto no tórax' e 'aperto na garganta'",
    "peito": "isolado é ambíguo; coberto por 'dor no peito' e 'peso no peito'",
    "tórax": "isolado é ambíguo; coberto por 'aperto no tórax'",
    "pressão": "ambíguo entre pressão arterial e sensação de pressão no peito",
    "medo": "estado emocional; o assistente não faz triagem psíquica",
}

# Classificação dos 10 relatos de `sintomas_pacientes.txt` como exemplos de treino.
# None = fora do treino, com justificativa ao lado.
RELATOS_FASE2: dict[int, str | None] = {
    1: "relatar_sintoma",
    2: "relatar_sintoma",
    3: "emergencia_cardiaca",  # aperto no tórax irradiando para o braço esquerdo
    4: "relatar_sintoma",
    5: "relatar_sintoma",
    6: "relatar_sintoma",
    # Síncope postural: o encaminhamento já é garantido por @sintoma:desmaio na
    # condição de emergência. Treinar a intenção com este relato ensinaria o
    # classificador a tratar desmaio ora como urgência, ora como triagem comum.
    7: None,
    8: "relatar_sintoma",
    9: "relatar_sintoma",
    10: "relatar_sintoma",
}


# Qualificadores que o paciente insere no meio do sintoma: "aperto FORTE no tórax".
# O motor local trata isso por regex (`texto_clinico.QUALIFICADORES`), mas o Watson
# compara sinônimo por sinônimo — então as variantes precisam existir no skill, ou
# `@sintoma:dor_no_peito` não é reconhecido e a regra de emergência nunca dispara.
QUALIFICADORES_SINONIMO = ("forte", "muito forte", "leve", "intensa", "insuportável")
PREPOSICOES = (" no ", " na ", " nos ", " nas ")


def expandir_qualificadores(sinonimos: list[str]) -> list[str]:
    """Para cada sinônimo do tipo 'X no Y', gera 'X <qualificador> no Y'."""
    novos: list[str] = []
    for sinonimo in sinonimos:
        for preposicao in PREPOSICOES:
            if preposicao not in sinonimo:
                continue
            antes, _, depois = sinonimo.partition(preposicao)
            for qualificador in QUALIFICADORES_SINONIMO:
                variante = f"{antes} {qualificador}{preposicao}{depois}"
                if variante not in sinonimos:
                    novos.append(variante)
            break
    return novos


def aplicar_qualificadores() -> int:
    """Enriquece @sintoma com as variantes qualificadas. Devolve quantas foram criadas."""
    total = 0
    for valor, sinonimos in ENTIDADES["sintoma"].items():
        novos = expandir_qualificadores(sinonimos)
        sinonimos.extend(novos)
        total += len(novos)
    return total


def termos_do_mapa() -> list[str]:
    """Termos distintos de `mapa_conhecimento.csv` (colunas sintoma_1 e sintoma_2)."""
    if not ARQUIVO_MAPA.exists():
        raise FileNotFoundError(f"Dataset da Fase 2 não encontrado: {ARQUIVO_MAPA}")

    termos: set[str] = set()
    with ARQUIVO_MAPA.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            for coluna in ("sintoma_1", "sintoma_2"):
                valor = (linha.get(coluna) or "").strip()
                if valor:
                    termos.add(valor)
    return sorted(termos)


def aplicar_sinonimos_do_mapa() -> tuple[int, int]:
    """Acrescenta os termos da Fase 2 aos sinônimos das entidades.

    Devolve (termos aproveitados, sinônimos efetivamente novos). Levanta erro se
    algum termo do CSV não estiver classificado — é o alarme de divergência.
    """
    termos = termos_do_mapa()
    sem_destino = [
        t for t in termos if t not in TERMOS_FASE2 and t not in TERMOS_IGNORADOS
    ]
    if sem_destino:
        raise ValueError(
            "Termos de mapa_conhecimento.csv sem classificação em TERMOS_FASE2 "
            f"ou TERMOS_IGNORADOS: {sem_destino}"
        )

    novos = 0
    aproveitados = 0
    for termo in termos:
        destino = TERMOS_FASE2.get(termo)
        if destino is None:
            continue
        entidade, valor = destino
        aproveitados += 1
        sinonimos = ENTIDADES[entidade][valor]
        if termo not in sinonimos and termo != valor:
            sinonimos.append(termo)
            novos += 1
    return aproveitados, novos


def aplicar_relatos_como_exemplos() -> int:
    """Usa os relatos reais da Fase 2 como exemplos de treino das intenções."""
    if not ARQUIVO_RELATOS.exists():
        raise FileNotFoundError(f"Dataset da Fase 2 não encontrado: {ARQUIVO_RELATOS}")

    relatos = [
        linha.strip()
        for linha in ARQUIVO_RELATOS.read_text(encoding="utf-8").splitlines()
        if linha.strip()
    ]
    if len(relatos) != len(RELATOS_FASE2):
        raise ValueError(
            f"{ARQUIVO_RELATOS.name} tem {len(relatos)} relatos, mas RELATOS_FASE2 "
            f"classifica {len(RELATOS_FASE2)}. Atualize a classificação."
        )

    adicionados = 0
    for numero, relato in enumerate(relatos, start=1):
        intencao = RELATOS_FASE2[numero]
        if intencao is None:
            continue
        if relato not in INTENCOES[intencao]:
            INTENCOES[intencao].append(relato)
            adicionados += 1
    return adicionados


# ---------------------------------------------------------------------------
# Helpers de construção da árvore de diálogo
# ---------------------------------------------------------------------------


# Condição única de emergência: usada no nó de urgência e como guarda dentro de cada
# slot, para que um sinal de alarme nunca seja engolido por uma coleta em andamento.
CONDICAO_EMERGENCIA = (
    "#emergencia_cardiaca "
    "|| @sintoma:desmaio "
    "|| (@sintoma:dor_no_peito && @intensidade:forte) "
    "|| (@sintoma:dor_no_peito && @duracao:agora) "
    "|| (@sintoma:dor_no_peito && @sintoma:sudorese) "
    "|| (@sintoma:dor_no_peito && @sintoma:dor_no_braco) "
    "|| (@sintoma:dor_no_peito && @caracteristica:irradiacao)"
)


def texto(*frases: str) -> dict:
    """Resposta em texto: cada frase vira um balão exibido em sequência."""
    return {
        "generic": [
            {
                "response_type": "text",
                "values": [{"text": frase}],
                "selection_policy": "sequential",
            }
            for frase in frases
        ]
    }


def variantes(*frases: str) -> dict:
    """Resposta única sorteada entre alternativas — evita repetição literal."""
    return {
        "generic": [
            {
                "response_type": "text",
                "values": [{"text": frase} for frase in frases],
                "selection_policy": "random",
            }
        ]
    }


def no(
    id_no: str,
    condicoes: str | None = None,
    resposta: dict | None = None,
    *,
    titulo: str | None = None,
    tipo: str = "standard",
    contexto: dict | None = None,
    proximo_passo: dict | None = None,
    filhos: list[dict] | None = None,
    variavel: str | None = None,
    evento: str | None = None,
    descricao: str | None = None,
    digressao_entra: str | None = None,
    digressao_sai: str | None = None,
    digressao_sai_slots: str | None = None,
) -> dict:
    """Descreve um nó de diálogo; parent/previous_sibling são resolvidos depois.

    Os três parâmetros de digressão controlam o que acontece quando o paciente muda
    de assunto no meio de uma coleta por slots. **Sem eles o Watson prende a conversa
    dentro do frame** — inclusive diante de um relato de emergência.
    """
    return {
        "_id": id_no,
        "_filhos": filhos or [],
        "type": tipo,
        "title": titulo,
        "conditions": condicoes,
        "output": resposta if resposta is not None else {},
        "context": contexto,
        "next_step": proximo_passo,
        "variable": variavel,
        "event_name": evento,
        "description": descricao,
        "digress_in": digressao_entra,
        "digress_out": digressao_sai,
        "digress_out_slots": digressao_sai_slots,
    }


# Assuntos que interrompem uma coleta em andamento: o paciente pergunta outra coisa,
# o assistente responde e retoma a coleta no turno seguinte (o `fluxo` continua no
# contexto). Emergência não está aqui porque encerra a coleta em vez de pausá-la.
INTENCOES_DIGRESSAO = (
    "duvida_exame",
    "duvida_fator_risco",
    "prevencao_habitos",
    "duvida_medicamento",
    "monitoramento_dispositivo",
    "capacidades_assistente",
    "falar_com_humano",
    "despedida",
)


def captura(campos: dict[str, str], preservar: bool) -> dict[str, str]:
    """Contexto que grava as entidades ditas neste turno.

    `preservar=True` mantém o que já havia sido informado (turnos seguintes da
    coleta); `preservar=False` zera o campo quando a entidade não veio — é o que
    limpa os resíduos de um atendimento anterior ao iniciar uma coleta nova.
    """
    anterior = "$%s" if preservar else "null"
    return {
        variavel: f"<? @{entidade} != null ? @{entidade}.value : "
        f"{anterior % variavel if preservar else 'null'} ?>"
        for variavel, entidade in campos.items()
    }


def perguntas_pendentes(prefixo: str, campos: list[tuple[str, str]]) -> list[dict]:
    """Um nó por campo ainda vazio: o primeiro que casar faz a pergunta."""
    return [
        no(f"{prefixo}_pergunta_{variavel}", f"${variavel} == null", texto(pergunta))
        for variavel, pergunta in campos
    ]


def coleta(
    id_base: str,
    condicao_inicio: str,
    fluxo: str,
    campos: dict[str, str],
    perguntas: list[tuple[str, str]],
    resposta_final: dict,
    titulo: str,
) -> tuple[dict, dict, list[dict]]:
    """Monta uma coleta multi-turno como nós irmãos na raiz.

    Devolve (captura, inicio, perguntas+final):

    * **captura** — fica logo depois da emergência. Reconhece que há uma coleta em
      andamento, grava o que foi dito neste turno e salta para a primeira pergunta
      ainda pendente.
    * **inicio** — fica na posição temática. Abre a coleta zerando resíduos do
      atendimento anterior e salta para o mesmo lugar.
    * **perguntas/final** — ficam no fim da árvore, depois dos nós temáticos, para
      que uma digressão seja atendida antes de a pergunta pendente ser repetida.
    """
    primeira_pergunta = f"{id_base}_pergunta_{perguntas[0][0]}"
    salto = {
        "behavior": "jump_to",
        "dialog_node": primeira_pergunta,
        "selector": "condition",
    }

    # A coleta só retoma se o turno não trouxer outro assunto claro. Sem esta
    # negação, o nó de captura (que vem antes dos temáticos) responderia "pergunta
    # pendente" a quem perguntou sobre um exame no meio da triagem.
    digressoes = " ".join(f"&& !#{i} " for i in INTENCOES_DIGRESSAO).strip()

    captura_no = no(
        f"{id_base}_em_andamento",
        f"$fluxo == '{fluxo}' {digressoes}",
        titulo=f"{titulo} (em andamento)",
        contexto={**captura(campos, preservar=True), "falhas": 0},
        proximo_passo=salto,
    )
    inicio_no = no(
        id_base,
        condicao_inicio,
        titulo=titulo,
        contexto={**captura(campos, preservar=False), "fluxo": fluxo, "falhas": 0},
        proximo_passo=salto,
    )
    nos_pergunta = [
        no(
            f"{id_base}_pergunta_{variavel}",
            f"$fluxo == '{fluxo}' && ${variavel} == null",
            texto(pergunta),
            titulo=f"{titulo}: {variavel}",
        )
        for variavel, pergunta in perguntas
    ]
    final = no(
        f"{id_base}_final",
        f"$fluxo == '{fluxo}'",
        resposta_final,
        titulo=f"{titulo}: resumo",
        contexto={"fluxo": ""},
    )
    return captura_no, inicio_no, [*nos_pergunta, final]


def achatar(nos: list[dict], pai: str | None = None) -> list[dict]:
    """Converte a árvore declarativa na lista plana esperada pelo Watson."""
    saida: list[dict] = []
    anterior: str | None = None
    for item in nos:
        filhos = item.pop("_filhos", [])
        id_no = item.pop("_id")
        registro = {k: v for k, v in item.items() if v is not None}
        registro["dialog_node"] = id_no
        registro["parent"] = pai
        registro["previous_sibling"] = anterior
        registro.setdefault("output", {})
        saida.append(registro)
        anterior = id_no
        if filhos:
            saida.extend(achatar(filhos, pai=id_no))
    return saida


# ---------------------------------------------------------------------------
# Árvore de diálogo (a ordem dos nós raiz é a ordem de avaliação no Watson)
# ---------------------------------------------------------------------------

CONTEXTO_LIMPO = {"falhas": 0}

# --- Coleta 1: triagem de sintoma -----------------------------------------

CAMPOS_TRIAGEM = {
    "sintoma": "sintoma",
    "contexto_sintoma": "contexto",
    "duracao": "duracao",
    "intensidade": "intensidade",
}

PERGUNTAS_TRIAGEM = [
    ("sintoma", "Qual sintoma você está sentindo? (por exemplo: dor no peito, "
                "falta de ar, palpitação, tontura, cansaço ou inchaço nas pernas)"),
    # A situação em que o sintoma aparece é o que diferencia angina estável
    # (esforço), instável (repouso) e pericardite (deitar, inclinar) no mapa de
    # conhecimento da Fase 2.
    ("contexto_sintoma", "Em que situação isso costuma acontecer: durante esforço "
                         "(caminhar, subir escadas), em repouso, ou quando você se deita?"),
    ("duracao", "Há quanto tempo isso acontece? (começou agora, há horas, há dias "
                "ou há semanas)"),
    ("intensidade", "Como você classifica a intensidade: leve, moderada ou forte?"),
]

RESUMO_TRIAGEM = texto(
    # .replace tira o sublinhado do valor da entidade: "dor_no_peito" → "dor no peito".
    "Obrigado por relatar. Registrei: sintoma <? $sintoma.replace('_', ' ') ?>, "
    "situação em que ocorre <? $contexto_sintoma.replace('_', ' ') ?>, "
    "duração <? $duracao ?>, intensidade <? $intensidade ?>.\n\n"
    "O que observar nos próximos dias:\n"
    "• se o sintoma passou a aparecer também em repouso, e não só ao esforço;\n"
    "• se piora, muda de intensidade ou vem acompanhado de outros sinais;\n"
    "• sua pressão arterial e frequência cardíaca nos episódios.\n\n"
    "Procure atendimento imediato (SAMU 192) se surgir dor forte no peito, "
    "falta de ar intensa, suor frio ou desmaio.\n\n"
    f"Recomendo agendar avaliação com cardiologista. {AVISO}\n"
    "Quer que eu abra uma solicitação de consulta?"
)

TRIAGEM_CAPTURA, TRIAGEM_INICIO, TRIAGEM_PERGUNTAS = coleta(
    "triagem_sintoma",
    "#relatar_sintoma || @sintoma",
    "triagem",
    CAMPOS_TRIAGEM,
    PERGUNTAS_TRIAGEM,
    RESUMO_TRIAGEM,
    "Triagem de sintoma",
)

# --- Coleta 2: agendamento de consulta ------------------------------------

CAMPOS_AGENDAMENTO = {"turno": "turno"}

PERGUNTAS_AGENDAMENTO = [
    ("turno", "Você prefere atendimento no período da manhã ou da tarde?"),
]

CONFIRMACAO_AGENDAMENTO = texto(
    "Solicitação registrada para o período da <? $turno ?>.\n\n"
    "A equipe do CardioIA entrará em contato para confirmar data e horário. "
    "Esta é uma simulação acadêmica de agendamento."
)

AGENDAMENTO_CAPTURA, AGENDAMENTO_INICIO, AGENDAMENTO_PERGUNTAS = coleta(
    "agendamento",
    "#agendar_consulta",
    "agendamento",
    CAMPOS_AGENDAMENTO,
    PERGUNTAS_AGENDAMENTO,
    CONFIRMACAO_AGENDAMENTO,
    "Agendamento de consulta",
)


def arvore() -> list[dict]:
    return [
        no(
            "boas_vindas",
            "welcome",
            texto(
                "Olá! Eu sou o CardioIA, assistente virtual de orientação cardiológica. "
                "Posso ajudar com sintomas, fatores de risco, exames, prevenção e agendamento.",
                f"{AVISO} Em caso de emergência, ligue 192 (SAMU). Como posso ajudar?",
            ),
            titulo="Boas-vindas",
            contexto={"falhas": 0, "atendimento": "iniciado"},
        ),
        # Emergência precisa ser avaliada antes de qualquer outro nó.
        no(
            "emergencia",
            CONDICAO_EMERGENCIA,
            texto(
                "⚠️ ATENÇÃO: os sinais que você descreveu podem indicar uma emergência cardíaca.\n\n"
                "1. Ligue AGORA para o SAMU (192) ou vá ao pronto-socorro mais próximo.\n"
                "2. Não dirija — peça ajuda a alguém.\n"
                "3. Fique em repouso, sentado ou deitado, e afrouxe roupas apertadas.\n"
                "4. Não tome nenhum medicamento por conta própria.\n\n"
                "Não vou seguir com a triagem: procure atendimento imediato."
            ),
            titulo="Emergência cardíaca",
            # `fluxo` zerado: nenhuma coleta continua depois de um encaminhamento
            # de urgência — a triagem foi encerrada de propósito.
            contexto={"prioridade": "emergencia", "falhas": 0, "fluxo": ""},
            descricao="Encerra a triagem e encaminha para atendimento de urgência.",
            # Interrompe qualquer coleta em andamento e não devolve a conversa a ela:
            # depois de orientar SAMU 192 não faz sentido voltar a perguntar duração.
            digressao_entra="does_not_return",
        ),
        # As coletas em andamento vêm logo depois da emergência: qualquer turno
        # reavalia a urgência primeiro e só então retoma o que estava sendo coletado.
        TRIAGEM_CAPTURA,
        AGENDAMENTO_CAPTURA,
        # Limiar explícito nos nós sociais: sem ele, ruído de teclado é classificado
        # como saudação/despedida com confiança baixa e nunca chega ao fallback.
        no(
            "saudacao",
            "#saudacao && intents[0].confidence > 0.5",
            texto(
                "Olá! Que bom falar com você. Posso orientar sobre sintomas, fatores de risco, "
                "exames, hábitos de prevenção e agendamento. Sobre o que quer conversar?"
            ),
            titulo="Saudação",
            contexto=CONTEXTO_LIMPO,
        ),
        no(
            "capacidades",
            "#capacidades_assistente",
            texto(
                "Sou um assistente virtual educacional do projeto CardioIA. Posso:\n"
                "• registrar e organizar sintomas que você relatar;\n"
                "• explicar fatores de risco (pressão, colesterol, diabetes, tabagismo);\n"
                "• esclarecer para que servem os exames cardiológicos;\n"
                "• dar orientações gerais de prevenção;\n"
                "• abrir uma solicitação de consulta.\n\n"
                f"O que eu NÃO faço: diagnóstico, prescrição ou ajuste de medicamento. {AVISO}"
            ),
            titulo="Capacidades do assistente",
            contexto=CONTEXTO_LIMPO,
            digressao_entra="returns",
        ),
        # Triagem de sintomas com preenchimento de slots.
        TRIAGEM_INICIO,
        no(
            "fator_risco",
            "#duvida_fator_risco || @fator_risco",
            titulo="Fatores de risco",
            contexto=CONTEXTO_LIMPO,
            digressao_entra="returns",
            proximo_passo={"behavior": "skip_user_input"},
            filhos=[
                no("fr_hipertensao", "@fator_risco:hipertensao", texto(
                    "A hipertensão é o principal fator de risco modificável para doença "
                    "cardiovascular. Valores acima de 140/90 mmHg em medidas repetidas merecem "
                    "avaliação médica.\n\n"
                    "O que ajuda: reduzir sal, manter peso saudável, atividade física regular, "
                    "evitar álcool em excesso e medir a pressão com frequência.\n\n"
                    f"O ajuste de medicação é sempre decisão médica. {AVISO}"
                )),
                no("fr_colesterol", "@fator_risco:colesterol_alto", texto(
                    "O colesterol elevado favorece o acúmulo de placas nas artérias e está "
                    "associado a infarto e AVC.\n\n"
                    "O que ajuda: reduzir gordura saturada e frituras, aumentar fibras, "
                    "praticar exercício e repetir o perfil lipídico no intervalo orientado "
                    f"pelo seu médico. {AVISO}"
                )),
                no("fr_diabetes", "@fator_risco:diabetes", texto(
                    "O diabetes aproximadamente dobra o risco cardiovascular e pode tornar os "
                    "sintomas de infarto menos típicos.\n\n"
                    "Controle da glicemia, da pressão e do colesterol caminham juntos. "
                    f"Mantenha acompanhamento regular. {AVISO}"
                )),
                no("fr_tabagismo", "@fator_risco:tabagismo", texto(
                    "O tabagismo lesiona o endotélio dos vasos e aumenta muito o risco de "
                    "infarto. É o fator de risco com maior benefício ao ser eliminado: parte do "
                    "risco cai já nos primeiros meses após parar.\n\n"
                    f"O SUS oferece programa gratuito de cessação do tabagismo. {AVISO}"
                )),
                no("fr_obesidade", "@fator_risco:obesidade", texto(
                    "O excesso de peso, sobretudo a gordura abdominal, associa-se a hipertensão, "
                    "diabetes e dislipidemia.\n\n"
                    "Perdas de 5% a 10% do peso já trazem benefício mensurável para o coração. "
                    f"Busque orientação nutricional profissional. {AVISO}"
                )),
                no("fr_sedentarismo", "@fator_risco:sedentarismo", texto(
                    "O sedentarismo reduz a capacidade funcional do coração. A recomendação "
                    "geral é de 150 minutos semanais de atividade moderada.\n\n"
                    f"Antes de iniciar, faça avaliação médica — principalmente após os 40 anos. {AVISO}"
                )),
                no("fr_familiar", "@fator_risco:historico_familiar", texto(
                    "Histórico familiar de doença cardíaca precoce (homens antes dos 55 anos, "
                    "mulheres antes dos 65) é fator de risco não modificável e indica "
                    "rastreamento mais atento.\n\n"
                    f"Vale informar isso ao seu cardiologista na consulta. {AVISO}"
                )),
                no("fr_geral", "true", texto(
                    "Os principais fatores de risco cardiovascular são: hipertensão, colesterol "
                    "alto, diabetes, tabagismo, obesidade, sedentarismo, estresse e histórico "
                    "familiar.\n\n"
                    "Sobre qual deles você quer saber mais?"
                )),
            ],
        ),
        no(
            "prevencao",
            "#prevencao_habitos",
            texto(
                "Orientações gerais de prevenção cardiovascular:\n"
                "• Atividade física: cerca de 150 minutos semanais de intensidade moderada.\n"
                "• Alimentação: mais frutas, verduras, grãos integrais e peixes; menos sal, "
                "ultraprocessados e frituras.\n"
                "• Sal: até cerca de 5 g por dia (uma colher de chá).\n"
                "• Não fumar e moderar o álcool.\n"
                "• Sono regular e manejo do estresse.\n"
                "• Medir pressão, glicemia e colesterol periodicamente.\n\n"
                f"São recomendações gerais de saúde pública. {AVISO}"
            ),
            titulo="Prevenção e hábitos",
            contexto=CONTEXTO_LIMPO,
            digressao_entra="returns",
        ),
        no(
            "exames",
            "#duvida_exame || @exame",
            titulo="Exames cardiológicos",
            contexto=CONTEXTO_LIMPO,
            digressao_entra="returns",
            proximo_passo={"behavior": "skip_user_input"},
            filhos=[
                no("ex_eletro", "@exame:eletrocardiograma", texto(
                    "O eletrocardiograma (ECG) registra a atividade elétrica do coração em "
                    "repouso. Dura poucos minutos, é indolor e não exige preparo especial.\n\n"
                    "Ajuda a identificar arritmias, sobrecarga das câmaras e sinais de isquemia."
                )),
                no("ex_eco", "@exame:ecocardiograma", texto(
                    "O ecocardiograma é um ultrassom do coração: mostra as câmaras, as válvulas "
                    "e a força de contração (fração de ejeção). É indolor, usa gel e dura cerca "
                    "de 20 a 30 minutos.\n\n"
                    "É o mesmo tipo de imagem que o CardioIA analisou na Fase 4 do projeto."
                )),
                no("ex_ergometrico", "@exame:teste_ergometrico", texto(
                    "O teste ergométrico avalia o coração durante o esforço, geralmente na "
                    "esteira.\n\n"
                    "Preparo habitual: roupas e tênis confortáveis, evitar refeição pesada e "
                    "cafeína antes, e confirmar com o médico quais medicamentos suspender."
                )),
                no("ex_holter", "@exame:holter", texto(
                    "O Holter registra o ritmo cardíaco por 24 horas ou mais, durante a rotina "
                    "normal.\n\n"
                    "É útil quando os sintomas são intermitentes, como palpitações e tonturas. "
                    "Mantenha um diário dos horários em que sentir algo."
                )),
                no("ex_sangue", "@exame:exame_sangue", texto(
                    "Os exames de sangue cardiológicos mais comuns são o perfil lipídico "
                    "(colesterol e triglicérides), a glicemia e, em quadros agudos, a troponina.\n\n"
                    "O jejum, quando necessário, costuma ser de 8 a 12 horas — confirme na "
                    "orientação do pedido médico."
                )),
                no("ex_geral", "true", texto(
                    "Posso explicar eletrocardiograma, ecocardiograma, teste ergométrico, Holter "
                    "e exames de sangue. Sobre qual deles você quer saber?"
                )),
            ],
        ),
        no(
            "medicamento",
            "#duvida_medicamento",
            texto(
                "Não posso orientar dose, troca ou interrupção de medicamento — isso é decisão "
                "exclusiva do profissional que prescreveu.\n\n"
                "O que posso dizer com segurança:\n"
                "• nunca interrompa remédio de pressão ou anticoagulante por conta própria;\n"
                "• em caso de dose esquecida, siga a bula ou consulte seu médico ou farmacêutico;\n"
                "• leve a lista atualizada dos seus medicamentos em toda consulta.\n\n"
                "Quer que eu abra uma solicitação de consulta para esclarecer isso?"
            ),
            titulo="Dúvida sobre medicamento",
            contexto=CONTEXTO_LIMPO,
            digressao_entra="returns",
        ),
        AGENDAMENTO_INICIO,
        no(
            "monitoramento",
            "#monitoramento_dispositivo",
            texto(
                "O módulo de monitoramento do CardioIA (Fase 3) acompanha frequência cardíaca e "
                "temperatura de forma contínua.\n\n"
                "Faixas de referência em repouso para adultos:\n"
                "• frequência cardíaca: cerca de 60 a 100 bpm;\n"
                "• acima de 120 bpm em repouso, ou abaixo de 50 bpm com sintomas, merece "
                "avaliação.\n\n"
                "Valores isolados dizem pouco: o que importa é a tendência e como você se sente. "
                f"{AVISO}"
            ),
            titulo="Monitoramento e dispositivo",
            contexto=CONTEXTO_LIMPO,
            digressao_entra="returns",
        ),
        no(
            "atendimento_humano",
            "#falar_com_humano",
            texto(
                "Sem problema. Vou registrar seu pedido de atendimento humano.\n\n"
                "Um profissional da equipe CardioIA dará continuidade — nesta simulação "
                "acadêmica, o encaminhamento é apenas demonstrativo.\n\n"
                "Se for urgente, ligue 192 (SAMU)."
            ),
            titulo="Atendimento humano",
            contexto={"falhas": 0, "encaminhado_humano": True},
            digressao_entra="does_not_return",
        ),
        no(
            "agradecimento",
            "#agradecimento && intents[0].confidence > 0.5",
            variantes(
                "Fico feliz em ajudar! Quer falar sobre mais alguma coisa?",
                "Por nada. Posso ajudar em algo mais?",
                "Imagina! Precisa de mais alguma orientação?",
            ),
            titulo="Agradecimento",
            contexto=CONTEXTO_LIMPO,
        ),
        no(
            "despedida",
            "#despedida && intents[0].confidence > 0.5",
            texto(
                "Cuide-se bem! Lembre-se de manter o acompanhamento cardiológico em dia. "
                f"{AVISO} Até logo."
            ),
            titulo="Despedida",
            contexto=CONTEXTO_LIMPO,
        ),
        # As perguntas das coletas ficam depois dos nós temáticos: assim uma dúvida
        # feita no meio da triagem é respondida antes de a pergunta ser repetida.
        *TRIAGEM_PERGUNTAS,
        *AGENDAMENTO_PERGUNTAS,
        # Tratamento de exceção: conta falhas consecutivas e escala o atendimento.
        no(
            "fora_de_escopo",
            "anything_else",
            titulo="Fora de escopo (fallback)",
            contexto={"falhas": "<? ($falhas == null ? 0 : $falhas) + 1 ?>"},
            proximo_passo={"behavior": "skip_user_input"},
            descricao="Tratamento de exceção com contagem de falhas consecutivas.",
            filhos=[
                no("fallback_escalar", "$falhas > 2", texto(
                    "Continuo sem entender e não quero te deixar sem resposta.\n\n"
                    "Vou encaminhar para atendimento humano da equipe CardioIA. "
                    "Se for urgente, ligue 192 (SAMU)."
                ), contexto={"falhas": 0, "encaminhado_humano": True}),
                no("fallback_menu", "$falhas == 2", texto(
                    "Desculpe, ainda não consegui entender. Posso ajudar com:\n"
                    "• sintomas (dor no peito, falta de ar, palpitação);\n"
                    "• fatores de risco (pressão, colesterol, diabetes);\n"
                    "• exames cardiológicos;\n"
                    "• prevenção e hábitos;\n"
                    "• agendamento de consulta.\n\n"
                    "Qual desses assuntos você quer?"
                )),
                no("fallback_reformular", "true", texto(
                    "Não tenho certeza de que entendi. Pode reformular com outras palavras?"
                )),
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Montagem do workspace
# ---------------------------------------------------------------------------


def montar_workspace() -> dict:
    # O conteúdo escrito à mão é enriquecido com os datasets da Fase 2 antes de
    # virar JSON, para que as duas camadas compartilhem o mesmo vocabulário.
    aproveitados, novos_sinonimos = aplicar_sinonimos_do_mapa()
    novos_exemplos = aplicar_relatos_como_exemplos()
    # Depois de incorporar os termos da Fase 2, gera as variantes com qualificador.
    variantes = aplicar_qualificadores()

    intencoes = [
        {
            "intent": nome,
            "description": None,
            "examples": [{"text": exemplo} for exemplo in exemplos],
        }
        for nome, exemplos in INTENCOES.items()
    ]

    entidades = [
        {
            "entity": nome,
            # Desligado de propósito: o fuzzy match casava @contexto:repouso em
            # "aperto forte no tórax irradiando para o braço esquerdo". Os sinônimos
            # já cobrem as variações reais, e sem ele o Watson e o motor local
            # reconhecem exatamente as mesmas entidades.
            "fuzzy_match": False,
            "values": [
                {"type": "synonyms", "value": valor, "synonyms": sinonimos}
                for valor, sinonimos in valores.items()
            ],
        }
        for nome, valores in ENTIDADES.items()
    ]

    return {
        "_fase2": {
            "termos_mapa_aproveitados": aproveitados,
            "sinonimos_novos": novos_sinonimos,
            "relatos_como_exemplos": novos_exemplos,
            "variantes_qualificadas": variantes,
        },
        "name": "CardioIA - Assistente Cardiologico",
        "description": (
            "Assistente conversacional de orientacao cardiologica do projeto CardioIA "
            "(FIAP, Fase 5). Prototipo academico: nao realiza diagnostico nem prescricao."
        ),
        "language": "pt-br",
        "workspace_id": "",
        "learning_opt_out": False,
        "status": "Available",
        "intents": intencoes,
        "entities": entidades,
        "dialog_nodes": achatar(arvore()),
        "counterexamples": [{"text": t} for t in CONTRAEXEMPLOS],
        "metadata": {"api_version": {"major_version": "v2", "minor_version": "2018-11-08"}},
        # Atenção: nem todo recurso de system_settings existe em pt-br. O upload do
        # skill é recusado ("Off Topic not supported for pt-br") se vierem declarados
        # `off_topic` ou `spelling_auto_correct`, que a IBM só oferece em inglês.
        # O tratamento de fora de escopo do CardioIA não depende deles: é feito pelo
        # nó `anything_else` com contagem de falhas, que funciona em qualquer idioma.
        # Desambiguação DESLIGADA de propósito. Numa triagem o paciente responde
        # com falas curtas ("leve", "há dias"), e nelas as intenções empatam por
        # falta de contexto — o Watson devolvia um menu "Qual destes assuntos você
        # quer tratar?" em vez da próxima pergunta da coleta. O tratamento de
        # ambiguidade do CardioIA é o nó `anything_else`, que escalona.
        "system_settings": {
            "disambiguation": {"enabled": False},
        },
    }


def main() -> None:
    workspace = montar_workspace()
    # Metadado de acompanhamento; não faz parte do formato do Watson.
    fase2 = workspace.pop("_fase2")

    SAIDA.write_text(
        json.dumps(workspace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Arquivo gerado: {SAIDA}")
    print(f"  intenções.....: {len(workspace['intents'])}")
    print(f"  exemplos......: {sum(len(i['examples']) for i in workspace['intents'])}")
    print(f"  entidades.....: {len(workspace['entities'])}")
    print(f"  valores.......: {sum(len(e['values']) for e in workspace['entities'])}")
    print(f"  nós de diálogo: {len(workspace['dialog_nodes'])}")
    print("\nDerivado dos datasets da Fase 2:")
    print(f"  termos de mapa_conhecimento.csv aproveitados: {fase2['termos_mapa_aproveitados']}"
          f" (ignorados por ambiguidade: {len(TERMOS_IGNORADOS)})")
    print(f"  sinônimos acrescentados às entidades........: {fase2['sinonimos_novos']}")
    print(f"  relatos de sintomas_pacientes.txt no treino.: {fase2['relatos_como_exemplos']}")
    print(f"  variantes com qualificador geradas em @sintoma: {fase2['variantes_qualificadas']}")


if __name__ == "__main__":
    main()
