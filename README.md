# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href= "https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Admnistração Paulista" border="0" width=40% height=40%></a>
</p>

<br>

# CardioIA - Fase 1 – Batimentos de Dados

## Grupo

## 👨‍🎓 Integrantes: 
- <a href="#">Diogo Rebello</a>
- <a href="#">Vera Chaves</a>

## 👩‍🏫 Professores:
### Tutor(a) 
- <a href="#">Caique Nonato da Silva Bezerra</a>
### Coordenador(a)
- <a href="#">André Godoi Chiovato</a>


## 📜 Descrição

Este repositório corresponde à **Fase 1 – Batimentos de Dados** do projeto **CardioIA**: a base de dados que alimentará os módulos inteligentes da plataforma ao longo das 7 fases do curso. Aqui atuamos como cientistas de dados hospitalares, levantando, organizando e documentando três tipos de dados cardiológicos:

- **Dados numéricos (Parte 1):** dataset de pacientes com variáveis clínicas (idade, sexo, pressão arterial, colesterol, sintomas, frequência cardíaca e diagnóstico), em CSV e XLSX, com links no Google Drive.
- **Dados textuais (Parte 2):** textos em português sobre doenças cardiovasculares, prevenção e fatores de risco, na pasta `assets/docs/`, para uso em NLP nas fases seguintes.
- **Dados visuais (Parte 3):** imagens de exames cardiológicos (a serem integradas conforme o enunciado), com justificativa de uso em visão computacional.

O foco é a **relevância clínica** das informações e a **governança de dados** em IA, preparando a base para triagem, diagnósticos assistidos, monitoramento e soluções inovadoras no ecossistema de cardiologia inteligente do CardioIA.


## 📁 Estrutura de pastas

Estrutura atual do repositório (Fase 1 – Batimentos de Dados):

```
cap1-a-busca-de-dados-inteligencia-cardiologica/
├── README.md
├── .gitattributes
├── .gitignore
├── datasets/
│   ├── dataset_cardiologia.xlsx
│   └── dataset_cardiologia.csv
└── assets/
    └── docs/
        ├── a_promocao_da_saude_e_a_prevencao_integrada_dos_fatores_de_risco_para_doencas_cardiovasculares.txt
        └── fatores_associados_as_doencas_cardiovasculares_na_populacao_adulta_brasileira_pesquisa_nacional_de_saude.txt
```

| Pasta/arquivo | Descrição |
|--------------|-----------|
| **README.md** | Guia e explicação geral do projeto (este arquivo). |
| **datasets/** | Dados numéricos da Parte 1 (dataset de pacientes cardiológicos em CSV). |
| **assets/** | Elementos não estruturados: imagens, logos e arquivos de apoio. |
| **assets/docs/** | Textos da Parte 2 (NLP): artigos sobre DCV, prevenção e fatores de risco em saúde cardiovascular. |

Conforme o andamento das fases do CardioIA, poderão ser criadas pastas como **config**, **document**, **scripts** e **src** para configurações, documentos, scripts auxiliares e código-fonte.


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


## 🔧 Como executar o código

*Acrescentar as informações necessárias sobre pré-requisitos (IDEs, serviços, bibliotecas etc.) e instalação básica do projeto, descrevendo eventuais versões utilizadas. Colocar um passo a passo de como o leitor pode baixar o seu código e executá-lo a partir de sua máquina ou seu repositório. Considere a explicação organizada em fase.*


## 🗃 Histórico de lançamentos

* 0.1.0 - 04/03/2026
    *

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>


