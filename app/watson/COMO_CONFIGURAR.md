# Configurar o assistente no IBM watsonx Assistant

Passo a passo para importar o CardioIA na sua instância e conectar o backend Flask.
Você já tem a conta IBM Cloud criada e o watsonx Assistant provisionado.

---

## 1. Ativar o Dialog (intents, entities e dialog nodes)

O watsonx Assistant abre por padrão no editor de **Actions**. A Fase 5 pede
**intents, entities e dialog nodes** — que ficam no editor **Dialog**, o clássico.

1. Abra o serviço → **Launch watsonx Assistant**.
2. No menu lateral, vá em **Assistant settings**.
3. Role até **Activate dialog** e clique em **Activate dialog**.
4. O item **Dialog** passa a aparecer no menu lateral (junto de Actions).

> Se a sua instância não oferecer essa opção, veja a seção *Plano B* no fim.

---

## 2. Importar o skill do CardioIA

O arquivo já está pronto no repositório: **`app/watson/cardioia_dialog_skill.json`**
(13 intents · 116 exemplos · 8 entities · 39 valores · 41 dialog nodes · 14 contraexemplos).
Parte do vocabulário é derivada dos datasets da Fase 2 — ver `gerar_skill_json.py`.

### Caminho A — instância com página de Skills

1. Menu lateral → **Skills** (ou **Assistants → seu assistente → Skills**).
2. **Create skill → Dialog skill → Upload skill**.
3. Selecione `cardioia_dialog_skill.json` e confirme.
4. Aguarde o treinamento (alguns minutos; o status fica **Training** e depois some).

### Caminho B — importar o assistente inteiro

1. **Assistant settings → Download/Upload files → Upload**.
2. Envie o mesmo JSON e confirme a substituição do conteúdo de diálogo.

Depois de importar, confira em **Dialog** que a árvore aparece nesta ordem — a ordem
importa, porque o Watson avalia os nós de cima para baixo:

```
Boas-vindas → Emergência cardíaca
→ Triagem (em andamento) → Agendamento (em andamento)      ← retomam a coleta
→ Saudação → Capacidades → Triagem de sintoma → Fatores de risco → Prevenção
→ Exames → Medicamento → Agendamento → Monitoramento → Atendimento humano
→ Agradecimento → Despedida
→ perguntas da triagem e do agendamento → Fora de escopo
```

---

## 3. Testar dentro do Watson

Use o **Try it** (canto superior direito) com estas falas:

| Fala | Esperado |
|------|----------|
| `oi` | saudação e menu de assuntos |
| `sinto falta de ar` | pergunta situação → duração → intensidade → resumo estruturado |
| `falta de ar leve ao subir escadas há dias` | preenche os 4 campos de uma vez e já entrega o resumo |
| `aperto forte no tórax irradiando para o braço esquerdo` | alerta de emergência (regra por entidades, mesmo no meio da coleta) |
| `estou com uma dor muito forte no peito agora` | alerta de emergência com SAMU 192 |
| `minha pressão está alta` | orientação sobre hipertensão |
| `quero marcar uma consulta` | pergunta o turno → protocolo simulado |
| `asdfgh` (3×) | reformular → menu de assuntos → encaminhar para humano |

---

## 4. Pegar as credenciais da API

1. **Assistant settings → API details** (ou a aba **Service credentials** do recurso).
2. Anote:
   - **API Key** → `WATSON_API_KEY`
   - **Service URL/Instance URL** → `WATSON_URL`
     (ex.: `https://api.us-south.assistant.watson.cloud.ibm.com/instances/xxxxxxxx`)
   - **Assistant ID** (ou **Environment ID** do ambiente *draft*/*live*)
     → `WATSON_ASSISTANT_ID`

> Use o **Environment ID do ambiente draft** enquanto estiver desenvolvendo: ele
> reflete as alterações imediatamente, sem precisar publicar.

---

## 5. Conectar o backend

```bash
cd app
cp .env.example .env      # no Windows: copy .env.example .env
```

Preencha o `.env` com os três valores e rode:

```bash
python app.py
```

O terminal deve mostrar `[CardioIA] Motor conversacional: watson`, e a etiqueta no
topo da interface muda para **watsonx Assistant**. Confirme também em
<http://127.0.0.1:5000/api/saude> que `"motor": "watson"`.

---

## 6. Regerar o skill depois de alterar o conteúdo

O JSON **não é editado à mão**: ele é gerado a partir de
[`gerar_skill_json.py`](gerar_skill_json.py), que descreve intents, entities e a
árvore de diálogo em Python legível e resolve `parent` / `previous_sibling` sozinho.

```bash
python app/watson/gerar_skill_json.py
```

Depois reimporte o arquivo no Watson (passo 2). Alterações feitas direto na interface
do Watson **não voltam** para o repositório — se editar por lá, baixe o skill e
reflita a mudança no gerador para as duas fontes não divergirem.

---

## Armadilhas já resolvidas (não reintroduzir)

Estas foram encontradas importando e testando numa instância real (plano Lite, pt-br):

| Sintoma | Causa | Como está resolvido |
|---------|-------|---------------------|
| Upload recusado: *"Off Topic not supported for pt-br"* | `off_topic` e `spelling_auto_correct` só existem em inglês | não são declarados no `system_settings` |
| Resposta parece vazia em falas curtas ("leve", "há dias") | `disambiguation` devolve `response_type: "suggestion"` | desligada; e o cliente passou a saber ler esse tipo |
| Emergência ignorada no meio da triagem | *slots* consomem a fala antes de reavaliar a árvore | coleta feita com nós condicionais, sem slots |
| Ruído ("asdfgh") vira `#saudacao` | classificador sem exemplos negativos | 14 contraexemplos + `intents[0].confidence > 0.5` nos nós sociais |
| `list_assistants` / ambientes falham | não existem no plano Lite | `assistant_id` serve como `environment_id`; skill atualizado pela API v1 |

## Atualizar o skill pela API (sem passar pela interface)

```python
from ibm_watson import AssistantV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import json

skill = json.load(open("app/watson/cardioia_dialog_skill.json", encoding="utf-8"))
v1 = AssistantV1(version="2021-11-27", authenticator=IAMAuthenticator(API_KEY))
v1.set_service_url(URL)
v1.update_workspace(workspace_id=WORKSPACE_ID, append=False, **{
    c: skill[c] for c in ("name", "description", "language", "intents", "entities",
                          "dialog_nodes", "counterexamples", "metadata",
                          "learning_opt_out", "system_settings")})
```

O `workspace_id` sai de `v1.list_workspaces()`. Depois do envio o status fica
`Training` por alguns minutos; espere `Available` antes de testar.

## Plano B — sem o Dialog disponível

Se a instância não permitir ativar o Dialog, a aplicação continua funcionando: o
backend cai automaticamente no **motor local** (`app/assistente/motor_local.py`), que
interpreta o **mesmo** arquivo `cardioia_dialog_skill.json` — mesmas intenções,
entidades, nós e respostas. A etiqueta na interface passa a mostrar *motor local*.

Para demonstrar esse modo mesmo com credenciais configuradas, use `FORCAR_MOTOR_LOCAL=1`
no `.env`.
