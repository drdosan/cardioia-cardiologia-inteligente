# CardioIA — Fase 5: Assistente Cardiológico Conversacional

Backend Flask + interface web de chat, integrados ao **IBM watsonx Assistant**.

```
interface HTML ──POST /api/mensagem──▶ Flask
                                        ├─▶ watsonx Assistant  (intents, entities, dialog nodes)
                                        │     └─ indisponível? motor local (mesmo skill)
                                        ├─▶ conhecimento da Fase 2 (regras + risco)
                                        └─▶ SQLite (histórico da conversa)
```

## Como executar

```bash
cd app
pip install -r requirements.txt
python app.py
```

Abra <http://127.0.0.1:5000>.

Sem credenciais do Watson a aplicação **já funciona**: o motor local interpreta o
mesmo dialog skill e a etiqueta no topo mostra *motor local*. Para conectar à nuvem,
siga [`watson/COMO_CONFIGURAR.md`](watson/COMO_CONFIGURAR.md) e preencha o `.env`
(modelo em [`.env.example`](.env.example)).

## Testes

```bash
cd app
python testar_assistente.py
```

83 verificações cobrindo segurança clínica (emergências reconhecidas e falsos alarmes
evitados), NLU (intenções, entidades com plural e palavras intercaladas), fluxo
conversacional (slots, digressão, fallback escalonado), o vocabulário derivado da
Fase 2, os 10 relatos reais de `sintomas_pacientes.txt` e os endpoints da API.

## Estrutura

| Caminho | Papel |
|---------|-------|
| [`app.py`](app.py) | rotas Flask e orquestração de uma mensagem |
| [`config.py`](config.py) | configuração e credenciais via `.env` |
| [`assistente/watson_cliente.py`](assistente/watson_cliente.py) | chamada à API v2 do watsonx Assistant (stateless) |
| [`assistente/motor_local.py`](assistente/motor_local.py) | interpretador local do mesmo dialog skill |
| [`assistente/conhecimento.py`](assistente/conhecimento.py) | mapa de conhecimento e classificador de risco da Fase 2 |
| [`assistente/texto_clinico.py`](assistente/texto_clinico.py) | casamento de termos clínicos em PT-BR |
| [`assistente/banco.py`](assistente/banco.py) | persistência das conversas em SQLite |
| [`watson/gerar_skill_json.py`](watson/gerar_skill_json.py) | fonte de verdade do conteúdo conversacional |
| [`watson/cardioia_dialog_skill.json`](watson/cardioia_dialog_skill.json) | arquivo de importação do assistente |
| [`templates/`](templates/), [`static/`](static/) | interface de chat |
| [`testar_assistente.py`](testar_assistente.py) | suíte de testes |

## API

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | interface de chat |
| `POST` | `/api/sessao` | abre a sessão e devolve a saudação |
| `POST` | `/api/mensagem` | `{sessao_id, texto}` → resposta + intenção + entidades + análise |
| `GET` | `/api/historico/<sessao_id>` | mensagens gravadas da sessão |
| `GET` | `/api/saude` | motor ativo, tamanho do skill e contadores do banco |

Exemplo:

```bash
curl -X POST http://127.0.0.1:5000/api/mensagem \
  -H "Content-Type: application/json" \
  -d '{"texto":"sinto dor no peito ao subir escadas"}'
```

## O conteúdo conversacional

13 intenções · 116 exemplos · 8 entidades · 39 valores · 41 nós de diálogo · 14 contraexemplos.

**Parte do conteúdo é derivada dos datasets da Fase 2**, para que o chatbot e a camada
de conhecimento clínica falem o mesmo vocabulário:

| Dataset | O que alimenta |
|---------|----------------|
| `mapa_conhecimento.csv` | sinônimos de `@sintoma`, `@contexto` e `@fator_risco` — **31 dos 36 termos**; os 5 restantes (`aperto`, `peito`, `tórax`, `pressão`, `medo`) ficam de fora por ambiguidade, com justificativa declarada |
| `sintomas_pacientes.txt` | **9 dos 10 relatos** viram exemplos de treino das intenções |

A tabela `TERMOS_FASE2` no gerador é a ponte: se a Fase 2 ganhar um termo novo, a
geração **falha** apontando qual ficou sem classificação — é o alarme que impede as
duas camadas de divergirem em silêncio.

**Intenções:** saudação, capacidades, emergência cardíaca, relato de sintoma, dúvida
sobre fator de risco, prevenção, dúvida sobre exame, dúvida sobre medicamento,
agendamento, monitoramento, atendimento humano, agradecimento, despedida.

**Entidades:** `@sintoma` (13 valores), `@contexto` (4), `@caracteristica`,
`@intensidade`, `@duracao`, `@fator_risco` (7), `@exame` (5), `@turno`.

`@contexto` é a situação em que o sintoma aparece — esforço, repouso, deitado,
inclinar o corpo, irradiação. É o que separa angina estável (esforço) de angina
instável (repouso) e pericardite (deitar/inclinar) no mapa da Fase 2.

Três decisões que sustentam o fluxo:

1. **Emergência é avaliada primeiro** e interrompe qualquer coleta em andamento —
   por intenção ou por combinações clínicas (`dor no peito + suor frio`,
   `dor no peito + dor irradiando para o braço`, desmaio).
2. **Coleta em nós condicionais** na triagem (sintoma → situação → duração →
   intensidade) e no agendamento (turno), com digressão: se o paciente muda de
   assunto, o assistente responde e retoma a coleta no turno seguinte. Não são usados
   *slots* — dentro deles o Watson consome a fala antes de reavaliar a árvore, e um
   relato de emergência no meio da coleta era engolido.
3. **Fallback escalonado**: reformular → menu de assuntos → atendimento humano.

## Limites do protótipo

Não faz diagnóstico, não prescreve e não orienta dose ou troca de medicamento —
essas perguntas são recusadas e encaminhadas. Todo atendimento exibe o aviso de
protótipo acadêmico e a orientação de ligar 192 em emergência. Os dados são
simulados; o SQLite guarda apenas o texto da conversa, sem identificadores reais.
