"""Testes do assistente CardioIA — executáveis sem instalar nada além do backend.

    cd app
    python testar_assistente.py

Cobrem os três pontos que sustentam a entrega da Fase 5:

1. **Segurança clínica** — sinais de emergência sempre encaminham para o SAMU, e
   relatos de sintoma crônico nunca são tratados como emergência (falso alarme).
2. **Fluxo conversacional** — coleta por slots, digressão quando o paciente muda de
   assunto e escalonamento do fallback após falhas seguidas.
3. **Integração** — os endpoints da API respondem, validam entrada e persistem a
   conversa no SQLite.
"""

from __future__ import annotations

import sys

import config
from assistente.motor_local import MotorLocal

motor = MotorLocal(config.CAMINHO_SKILL_JSON)

falhas: list[str] = []
total = 0


def verificar(condicao: bool, descricao: str) -> None:
    global total
    total += 1
    if condicao:
        print(f"  ✓ {descricao}")
    else:
        print(f"  ✗ {descricao}")
        falhas.append(descricao)


def responder(fala: str, contexto: dict | None = None) -> dict:
    return motor.responder(fala, contexto or {})


def eh_emergencia(resposta: dict) -> bool:
    return "192" in resposta["texto"] and "emergência" in resposta["texto"].lower()


def secao(titulo: str) -> None:
    print(f"\n{titulo}\n" + "-" * len(titulo))


# --- 1. Segurança clínica --------------------------------------------------

secao("1. Emergências reconhecidas (encaminham para o SAMU)")
for fala in [
    "estou com uma dor muito forte no peito agora",
    "acho que estou tendo um infarto",
    "dor no peito com suor frio",
    "aperto no peito irradiando para o braço esquerdo",
    "minha mãe desmaiou",
    "socorro, dor no peito muito forte",
    "peito apertado e não consigo respirar",
]:
    verificar(eh_emergencia(responder(fala)), repr(fala))

secao("2. Sintomas crônicos NÃO viram alarme de emergência")
for fala in [
    "sinto dor no peito e falta de ar ao subir escadas",
    "sinto dor no peito leve às vezes",
    "minhas pernas estão inchadas",
    "ando com palpitações à noite",
    "tenho me cansado muito ultimamente",
]:
    verificar(not eh_emergencia(responder(fala)), repr(fala))

# --- 2. NLU ----------------------------------------------------------------

secao("3. Entidades reconhecidas com plural e palavras intercaladas")
casos_entidade = [
    ("minhas pernas estão inchadas", "sintoma", "inchaco_pernas"),
    ("ando com palpitações à noite", "sintoma", "palpitacao"),
    ("sinto muitas dores no peito", "sintoma", "dor_no_peito"),
    ("meu colesterol está alto", "fator_risco", "colesterol_alto"),
    ("minha pressão está alta", "fator_risco", "hipertensao"),
    ("o que o holter mede", "exame", "holter"),
]
for fala, entidade, valor in casos_entidade:
    achadas = {(e["entity"], e["value"]) for e in motor.detectar_entidades(fala)}
    verificar((entidade, valor) in achadas, f"{fala!r} → @{entidade}:{valor}")

secao("4. Falas sem conteúdo clínico não casam entidades")
for fala in ["quero dormir melhor", "bom dia, tudo bem?", "qual o valor da consulta"]:
    verificar(not motor.detectar_entidades(fala), repr(fala))

secao("5. Intenções classificadas corretamente")
casos_intencao = [
    ("oi, tudo bem?", "saudacao"),
    ("o que você faz?", "capacidades_assistente"),
    ("quero marcar uma consulta", "agendar_consulta"),
    ("para que serve o eletrocardiograma", "duvida_exame"),
    ("posso parar de tomar o remédio da pressão", "duvida_medicamento"),
    ("quero falar com um atendente", "falar_com_humano"),
    ("obrigado pela ajuda", "agradecimento"),
    ("tchau", "despedida"),
]
for fala, esperada in casos_intencao:
    obtida, _ = motor.classificar_intencao(fala)
    verificar(obtida == esperada, f"{fala!r} → #{esperada} (obtido: {obtida})")

# --- 3. Fluxo conversacional ----------------------------------------------

secao("6. Triagem completa preenchendo os quatro slots")
contexto: dict = {}
r1 = responder("estou sentindo falta de ar", contexto)
contexto = r1["contexto"]
verificar("situação" in r1["texto"].lower(), "após o sintoma, pergunta a situação")

r2 = responder("quando faço esforço", contexto)
contexto = r2["contexto"]
verificar("tempo" in r2["texto"].lower(), "depois pergunta a duração")

r3 = responder("há dias", contexto)
contexto = r3["contexto"]
verificar("intensidade" in r3["texto"].lower(), "depois pergunta a intensidade")

r4 = responder("moderada", contexto)
contexto = r4["contexto"]
verificar("Registrei" in r4["texto"], "fecha a triagem com o resumo estruturado")
verificar("falta de ar" in r4["texto"], "o resumo cita o sintoma coletado")
verificar("esforco" in r4["texto"] or "esforço" in r4["texto"], "o resumo cita a situação")
verificar("_frame" not in contexto, "o frame é encerrado ao final da coleta")

secao("6b. Sinal de alarme no meio da coleta não é engolido pelo slot")
contexto = responder("sinto falta de ar")["contexto"]
r = responder("aperto forte no tórax irradiando para o braço esquerdo", contexto)
verificar(eh_emergencia(r), "irradiação durante a triagem dispara emergência")
verificar(
    not any(e["entity"] == "contexto" for e in motor.detectar_entidades("irradiando para o braço")),
    "irradiação não é lida como @contexto (não pode preencher o slot de situação)",
)

secao("6c. Relato completo numa frase só não repete perguntas")
r = responder("sinto falta de ar leve ao subir escadas há dias")
verificar("Registrei" in r["texto"], "quatro slots preenchidos de uma vez fecham a triagem")

secao("7. Digressão: o paciente muda de assunto no meio da coleta")
contexto = responder("tenho sentido cansaço", {})["contexto"]
r = responder("para que serve o holter?", contexto)
verificar("Holter" in r["texto"], "responde sobre o exame em vez de insistir na pergunta")

secao("8. Emergência interrompe um fluxo em andamento")
contexto = responder("quero marcar uma consulta", {})["contexto"]
r = responder("estou com uma dor muito forte no peito agora", contexto)
verificar(eh_emergencia(r), "agendamento é abandonado diante da emergência")

secao("9. Agendamento pede só o turno (minimização de dados)")
r1 = responder("quero marcar uma consulta")
verificar("manhã" in r1["texto"] or "tarde" in r1["texto"], "pergunta o turno")
r2 = responder("prefiro de manhã", r1["contexto"])
verificar("registrada" in r2["texto"].lower(), "confirma a solicitação")
verificar("manhã" in r2["texto"], "a confirmação cita o turno escolhido")
verificar(
    "nome" not in r1["texto"].lower(),
    "não pede nome do paciente — dado pessoal desnecessário no protótipo",
)

secao("10. Fallback escalona após falhas seguidas")
contexto = {}
r1 = responder("xpto blablabla", contexto)
contexto = r1["contexto"]
verificar("reformular" in r1["texto"].lower(), "1ª falha: pede para reformular")
r2 = responder("asdfgh", contexto)
contexto = r2["contexto"]
verificar("Posso ajudar com" in r2["texto"], "2ª falha: oferece o menu de assuntos")
r3 = responder("zzz qqq www", contexto)
verificar("humano" in r3["texto"].lower(), "3ª falha: encaminha para atendimento humano")

secao("11. Nunca orienta medicação")
r = responder("qual é a dose do meu remédio?")
verificar("Não posso orientar dose" in r["texto"], "recusa orientar dose e encaminha")

# --- 4. Conhecimento da Fase 2 --------------------------------------------

secao("12. Vocabulário derivado do mapa_conhecimento.csv (Fase 2)")
import csv  # noqa: E402

termos_mapa: set[str] = set()
with open(config.CAMINHO_DATASETS / "mapa_conhecimento.csv", encoding="utf-8", newline="") as arq:
    for linha in csv.DictReader(arq):
        for coluna in ("sintoma_1", "sintoma_2"):
            if linha.get(coluna):
                termos_mapa.add(linha[coluna].strip())

# Só os cinco termos isolados e ambíguos podem ficar de fora (ver TERMOS_IGNORADOS).
AMBIGUOS = {"aperto", "peito", "tórax", "pressão", "medo"}
nao_cobertos = {t for t in termos_mapa if not motor.detectar_entidades(t)}
verificar(
    nao_cobertos == AMBIGUOS,
    f"{len(termos_mapa) - len(nao_cobertos)}/{len(termos_mapa)} termos do mapa viram entidade "
    f"(fora: {sorted(nao_cobertos)})",
)

secao("13. Os 10 relatos reais de sintomas_pacientes.txt (Fase 2)")
relatos = [
    linha.strip()
    for linha in (config.CAMINHO_DATASETS / "sintomas_pacientes.txt")
    .read_text(encoding="utf-8")
    .splitlines()
    if linha.strip()
]
verificar(len(relatos) == 10, "os 10 relatos foram carregados")

# Relato 3: aperto no tórax irradiando para o braço esquerdo — síndrome coronariana.
# Relato 7: síncope. Ambos precisam de encaminhamento imediato.
EMERGENCIAS_ESPERADAS = {3, 7}
for numero, relato in enumerate(relatos, start=1):
    resultado = responder(relato)
    esperado = numero in EMERGENCIAS_ESPERADAS
    verificar(
        eh_emergencia(resultado) == esperado,
        f"relato {numero}: {'emergência' if esperado else 'triagem'} — {relato[:48]}…",
    )

# Sintomas que só existem no vocabulário depois da derivação do dataset.
for relato_texto, entidade, valor in [
    ("sinto inchaço nos tornozelos ao fim do dia", "sintoma", "inchaco_pernas"),
    ("sinto aperto na garganta quando corro", "sintoma", "aperto_na_garganta"),
    ("tenho zumbido no ouvido e tonteira", "sintoma", "zumbido_ouvido"),
    ("dor no peito com febre há cinco dias", "sintoma", "febre"),
    ("sinto batimentos irregulares", "sintoma", "batimentos_irregulares"),
    ("a dor piora quando subo escadas", "contexto", "esforco"),
    ("sinto falta de ar quando me deito", "contexto", "deitado"),
    ("o desconforto aparece mesmo em repouso", "contexto", "repouso"),
]:
    achadas = {(e["entity"], e["value"]) for e in motor.detectar_entidades(relato_texto)}
    verificar((entidade, valor) in achadas, f"{relato_texto!r} → @{entidade}:{valor}")

secao("14. Mapa de conhecimento e classificador de risco (Fase 2)")
from assistente.conhecimento import analisar  # noqa: E402 — depende do config já lido

analise = analisar("minhas pernas estão inchadas e sinto falta de ar ao deitar")
doencas = [h["doenca"] for h in analise["hipoteses"]]
verificar(
    any("Insuficiência" in d for d in doencas),
    f"relato de congestão sugere insuficiência cardíaca (obtido: {doencas[:2]})",
)
analise = analisar("dor no peito quando subo escadas")
verificar(
    any("Angina" in h["doenca"] for h in analise["hipoteses"]),
    "dor ao esforço sugere angina",
)
verificar(
    analise["risco"] is not None and "risco" in analise["risco"]["classe"],
    "classificador de risco responde alto/baixo risco",
)

# --- 5. API ----------------------------------------------------------------

secao("15. Endpoints da API")
from app import criar_app  # noqa: E402

cliente = criar_app().test_client()

saude = cliente.get("/api/saude").get_json()
verificar(saude["status"] == "ok", "GET /api/saude responde ok")
verificar(saude["intencoes"] == 13, f"skill carregado com 13 intenções (obtido: {saude['intencoes']})")
verificar(saude["entidades"] == 8, f"skill carregado com 8 entidades (obtido: {saude['entidades']})")

verificar(cliente.get("/").status_code == 200, "GET / entrega a interface")

sessao = cliente.post("/api/sessao").get_json()
verificar("sessao_id" in sessao, "POST /api/sessao cria a sessão")
verificar("CardioIA" in sessao["mensagem"], "sessão começa com a saudação do assistente")

sessao_id = sessao["sessao_id"]
resposta = cliente.post(
    "/api/mensagem", json={"sessao_id": sessao_id, "texto": "sinto falta de ar"}
).get_json()
verificar("resposta" in resposta, "POST /api/mensagem devolve a resposta")
verificar(resposta["intencao"] == "relatar_sintoma", "a intenção volta no payload")

historico = cliente.get(f"/api/historico/{sessao_id}").get_json()
verificar(len(historico["mensagens"]) >= 3, "conversa persistida no SQLite")

verificar(
    cliente.post("/api/mensagem", json={"texto": "   "}).status_code == 400,
    "mensagem vazia é rejeitada com 400",
)
verificar(
    cliente.post("/api/mensagem", json={"texto": "a" * 1001}).status_code == 400,
    "mensagem acima do limite é rejeitada com 400",
)

# --- resultado -------------------------------------------------------------

print("\n" + "=" * 60)
if falhas:
    print(f"FALHOU: {len(falhas)} de {total} verificações")
    for descricao in falhas:
        print(f"  - {descricao}")
    sys.exit(1)
print(f"OK: {total} verificações passaram")
