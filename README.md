# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href= "https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Administração Paulista" border="0" width=40% height=40%></a>
</p>

<br>

# CardioIA

## Grupo

## 👨‍🎓 Integrantes: 
- <a href="#">Diogo Rebello</a>
- <a href="#">Vera Chaves</a>

## 👩‍🏫 Professores:
### Tutor(a) 
- <a href="#">Caique Nonato da Silva Bezerra</a>
### Coordenador(a)
- <a href="#">André Godoi Chiovato</a>


## 📁 Estrutura de pastas

```
cap1-a-busca-de-dados-inteligencia-cardiologica/
├── README.md
├── .gitattributes
├── .gitignore
├── datasets/
│   ├── dataset_cardiologia.csv      # Fase 1 (Cleveland); reutilizado na Fase 2 alinhado às frases
│   ├── frases_risco.csv             # Fase 2 — frases rotuladas (alto/baixo risco)
│   ├── mapa_conhecimento.csv        # Fase 2 — pares de sintomas → doença (regras)
│   └── sintomas_pacientes.txt       # Fase 2 — relatos fictícios (uma frase por linha)
├── notebooks/
│   └── fase2_cardioia_estetoscopio_digital.ipynb
└── assets/
    └── docs/
        ├── a_promocao_da_saude_e_a_prevencao_integrada_dos_fatores_de_risco_para_doencas_cardiovasculares.txt
        └── fatores_associados_as_doencas_cardiovasculares_na_populacao_adulta_brasileira_pesquisa_nacional_de_saude.txt
```

| Pasta / arquivo | Descrição |
|-----------------|-----------|
| **README.md** | Guia geral do repositório, Fases 1 e 2 e referências. |
| **datasets/** | Bases em CSV e TXT: Cleveland (Fase 1), mapa de sintomas, relatos e frases de risco (Fase 2). O XLSX do Cleveland, quando usado, segue o link da Parte 1 (Google Drive). |
| **notebooks/** | Notebook único da **Fase 2** (Colab ou Jupyter): Parte 1 por regras + Parte 2 com TF-IDF, modelo híbrido e árvore de decisão. |
| **assets/** | Logos e materiais de apoio ao README. |
| **assets/docs/** | Textos em português para NLP na Fase 1 (DCV, prevenção, fatores de risco). |

---

# FASE 1 — Batimentos de Dados

## 📜 Descrição

Este repositório corresponde à **Fase 1 – Batimentos de Dados** do projeto **CardioIA**: a base de dados que alimentará os módulos inteligentes da plataforma ao longo das 7 fases do curso. Aqui atuamos como cientistas de dados hospitalares, levantando, organizando e documentando três tipos de dados cardiológicos:

- **Dados numéricos (Parte 1):** dataset de pacientes com variáveis clínicas (idade, sexo, pressão arterial, colesterol, sintomas, frequência cardíaca e diagnóstico), em CSV e XLSX, com links no Google Drive.
- **Dados textuais (Parte 2):** textos em português sobre doenças cardiovasculares, prevenção e fatores de risco, na pasta `assets/docs/`, para uso em NLP nas fases seguintes.
- **Dados visuais (Parte 3):** imagens de ecocardiograma (dataset CAMUS), com link no Google Drive e justificativa de uso em visão computacional.

O foco é a **relevância clínica** das informações e a **governança de dados** em IA, preparando a base para triagem, diagnósticos assistidos, monitoramento e soluções inovadoras no ecossistema de cardiologia inteligente do CardioIA.


## 📜 Parte 1 – Dados Numéricos (IoT)

O dataset de pacientes cardiológicos está organizado neste repositório na pasta **`datasets/`** e também disponível em nuvem para acesso e correção:

- **CSV:** [Google Drive – dataset em CSV](https://drive.google.com/file/d/15dhiXDzmEJjdpJG1xdCrk7TOjHyNuDax/view?usp=sharing)
- **XLSX:** [Google Drive – dataset em XLSX](https://docs.google.com/spreadsheets/d/1fZkHUJpJik-BF6JHHbcRObQJmbDb8T1n/edit?usp=sharing&ouid=104955316596639670804&rtpof=true&sd=true)

### Origem dos dados

Os dados são **reais e anonimizados**, provenientes do **UCI Machine Learning Repository** – base **Heart Disease (Cleveland)**. Identificadores e números de segurança social foram substituídos por valores dummy, conforme documentação do repositório. O arquivo utilizado é o *processed Cleveland*, com 303 registros e 14 atributos utilizados em experimentos de ML.

### Variáveis mais relevantes do ponto de vista clínico e importância para IA em saúde

| Variável | Relevância clínica | Justificativa para IA em saúde |
|----------|--------------------|--------------------------------|
| **idade** | Fator de risco clássico para doença cardiovascular. | Modelos de risco e triagem dependem da faixa etária para calibração e prevenção. |
| **sexo** | Diferenças de prevalência e manifestação entre sexos (ex.: sintomas em mulheres). | Permite avaliar e mitigar viés do modelo e personalizar alertas. |
| **pressão arterial** | Hipertensão é um dos principais fatores de risco modificáveis. | Entrada fundamental em scores de risco e sistemas de triagem digital. |
| **colesterol** | Dislipidemia associada a eventos cardiovasculares. | Usada em modelos preditivos e recomendações de estilo de vida. |
| **sintomas (tipo de dor no peito)** | Sintoma cardinal para suspeita de doença coronariana. | Base para classificação automática e priorização na triagem. |
| **frequência cardíaca máxima** | Reflete capacidade funcional e resposta ao esforço. | Indicador de isquemia e capacidade de exercício em modelos de prognóstico. |
| **histórico/resultado (diagnóstico)** | Desfecho clínico (angiografia): ausência ou gravidade da doença. | Variável alvo para classificação binária ou multiclasse em modelos de ML. |

### Legenda dos códigos (enumeradores)

As colunas categóricas do dataset usam códigos numéricos. Significado conforme documentação do UCI Heart Disease:

**sexo**

| Valor | Significado |
|-------|-------------|
| 0 | Feminino |
| 1 | Masculino |

**sintomas_tipo_dor_peito** (tipo de dor no peito)

| Valor | Significado |
|-------|-------------|
| 1 | Angina típica |
| 2 | Angina atípica |
| 3 | Dor não anginosa |
| 4 | Assintomático |

**historico_doenca_cardiaca** (diagnóstico angiográfico)

| Valor | Significado |
|-------|-------------|
| 0 | Sem doença significativa (estreitamento &lt; 50% do diâmetro do vaso) |
| 1 | Doença presente (estreitamento ≥ 50% em pelo menos um vaso principal) |
| 2, 3, 4 | Maior extensão/gravidade da doença |


Essas variáveis permitem treinar modelos de triagem, diagnóstico assistido e estimativa de risco, alinhados ao ecossistema de cardiologia inteligente do CardioIA.


## 📜 Parte 2 – Dados Textuais (NLP)

Os textos utilizados nesta etapa estão no repositório na subpasta **`assets/docs/`**:

- `a_promocao_da_saude_e_a_prevencao_integrada_dos_fatores_de_risco_para_doencas_cardiovasculares.txt`
- `fatores_associados_as_doencas_cardiovasculares_na_populacao_adulta_brasileira_pesquisa_nacional_de_saude.txt`

### Como os textos podem ser explorados por algoritmos de NLP

- **Análise de sentimentos:** avaliar tom e preocupação em trechos sobre fatores de risco e políticas de saúde, úteis para monitorar discurso em materiais educativos ou em redes.
- **Extração de sintomas e entidades:** identificar termos clínicos (hipertensão, diabetes, tabagismo, obesidade, DCV) e relações com fatores de risco, permitindo construir bases de conhecimento e resumos automáticos.
- **Classificação de tópicos:** separar trechos por tema (prevenção, vigilância, Programa Saúde da Família, PNS, fatores sociodemográficos), facilitando indexação e busca em acervos de saúde pública.

### Relevância dessas análises para IA aplicada à saúde

Essas técnicas permitem estruturar conhecimento a partir de literatura e relatórios em português, apoiar chatbots com respostas baseadas em evidências, triagem de dúvidas de pacientes e produção de material educativo personalizado — alinhado ao suporte digital ao paciente e à governança de informação em saúde no projeto CardioIA.


## 📜 Parte 3 – Dados Visuais (Visão Computacional)

O conjunto de imagens de exames cardiológicos está disponível em nuvem (acesso público para correção):

- **Imagens (900 imagens):** [Google Drive – imagens de ecocardiogramas](https://drive.google.com/drive/folders/1d7L5sZIY1Y5VbKkFY0_aMOXQfmE7zFQj?usp=sharing) *(formato .png)*

### Tipo de exame e conteúdo

**Ecocardiograma** (ultrassom cardíaco 2D). As imagens são do dataset **CAMUS (Cardiac Acquisitions for Multi-structure Ultrasound Segmentation)**, versão disponível no Kaggle como [CAMUS - Echocardiography Image Dataset](https://www.kaggle.com/datasets/parsakh/camus-echocardiography-image-dataset), com vistas em apical 4 câmaras e 2 câmaras. O conjunto atende ao mínimo de 100 imagens em formato .jpg ou .png para análise por algoritmos de Visão Computacional.

### Como as imagens podem ser analisadas por algoritmos de Visão Computacional

As imagens de ecocardiograma (ultrassom cardíaco em escala de cinza, vista em leque) contêm câmaras cardíacas, paredes do miocárdio e estruturas como valvas, com variação de intensidade entre regiões anecóicas (sangue) e tecido ecogênico (musculatura). Essas características permitem:

- **Detecção de padrões:** redes neurais convolucionais (CNNs) podem aprender a morfologia típica das câmaras e do miocárdio, a textura do tecido e a configuração anatômica de cada vista (apical 4 câmaras, 2 câmaras), permitindo classificação automática da vista e triagem com base em padrões de normalidade ou alteração.
- **Identificação de bordas e estruturas:** técnicas de processamento de imagem (filtros, segmentação semântica, ex.: U-Net) permitem delimitar bordas endocárdicas e epicárdicas, segmentar câmaras e paredes e obter medições automáticas de espessura de parede, volumes e fração de ejeção, essenciais para laudos assistidos.
- **Reconhecimento de anomalias:** modelos treinados com imagens anotadas podem sinalizar desvios em relação ao padrão esperado — como alterações de tamanho ou forma de câmaras, espessamento ou adelgaçamento de paredes, presença de derrame ou massas — e priorizar exames suspeitos para revisão humana, apoiando o diagnóstico na Fase 4 do CardioIA.

### Importância dessas análises para projetos de IA aplicados à área da saúde

A análise automática de imagens de ecocardiograma permite padronizar medições (reduzindo variabilidade entre observadores), escalar a triagem, auxiliar no diagnóstico precoce de alterações cardíacas e apoiar médicos com sugestões de achados — sem substituir o julgamento clínico. No CardioIA, esse conjunto alimentará o módulo **Coração em Imagens (Fase 4)**, alinhado a uma cardiologia inteligente e acessível.


---

# FASE 2 — Estetoscópio Digital

## 📜 Descrição

Na **Fase 2**, o CardioIA simula um **estetoscópio digital**: apoio à triagem e à leitura de relatos em linguagem natural, com **governança** e limites explícitos (protótipo educacional, sem substituir avaliação médica).

O trabalho está concentrado no notebook **`notebooks/fase2_cardioia_estetoscopio_digital.ipynb`**, pensado para rodar no **Google Colab** ou localmente, com a pasta **`datasets/`** acessível (raiz do repositório, pasta pai ou `/content/datasets` no Colab).

## 📜 Parte 1 — Relatos, mapa de conhecimento e sugestão por regras

- **`sintomas_pacientes.txt`:** relatos fictícios (uma linha por caso).
- **`mapa_conhecimento.csv`:** colunas `sintoma_1`, `sintoma_2`, `doenca_associada`.
- O notebook **cruza** sintomas do mapa com o texto, **pontua** coincidências e sugere **diagnóstico principal** e hipóteses alternativas em tabela.

Isto **não** é aprendizado de máquina: são **regras fixas** derivadas do mapa — úteis para discutir transparência, incerteza e revisão humana.

## 📜 Parte 2 — Classificação de risco com texto e dados da Fase 1

- **`frases_risco.csv`:** colunas `frase` e `situacao` (`alto risco` / `baixo risco`).
- **`dataset_cardiologia.csv`:** mesma **ordem de linhas** que `frases_risco.csv`, para alinhar idade, sexo, tipo de dor no peito, pressão arterial, colesterol e frequência cardíaca a cada frase.
- **TF-IDF** (unigramas e bigramas) vetoriza o texto.
- **Modelo híbrido:** regressão logística sobre **TF-IDF + variáveis numéricas** (via `scipy.sparse.hstack` e escalonamento).
- **Comparações no notebook:** regressão **só com TF-IDF**; **árvore de decisão** no mesmo vetor híbrido e referência com árvore só em TF-IDF.
- **Métricas:** acurácia, relatório de classificação, matriz de confusão; exemplos no conjunto de teste e frases coloquiais para discutir *domain shift*.

### Dependências (Colab)

Na primeira execução da sessão, o notebook instala explicitamente: `pandas`, `scikit-learn`, `scipy`.

## 🎬 Vídeo da entrega

Conforme o enunciado da disciplina, a entrega inclui um vídeo (até ~4 min) no YouTube como **não listado**. **Inclua o link abaixo após publicar:**

- **YouTube (não listado):** *(cole o link aqui)*

---

## 🗃 Histórico de lançamentos

* **0.2.0** — 28/03/2026 — Fase 2: notebook único, bases `frases_risco`, `mapa_conhecimento`, `sintomas_pacientes`; README atualizado.
* **0.1.0** — 04/03/2026 — Fase 1: dados numéricos, textos em `assets/docs/` e referência a imagens CAMUS.

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>


