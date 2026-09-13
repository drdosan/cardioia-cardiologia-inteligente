/**
 * CardioIA — Fase 5: interface de chat.
 *
 * Abre a sessão no backend, envia as mensagens do paciente para /api/mensagem e
 * mostra, ao lado da conversa, o que o assistente entendeu (intenção, entidades,
 * hipóteses do mapa de conhecimento e indício de risco).
 */

const conversa = document.getElementById("conversa");
const formulario = document.getElementById("formulario");
const campo = document.getElementById("campo-mensagem");
const botao = document.getElementById("botao-enviar");
const indicadorMotor = document.getElementById("indicador-motor");
const sugestoes = document.getElementById("sugestoes");

const analiseIntencao = document.getElementById("analise-intencao");
const analiseEntidades = document.getElementById("analise-entidades");
const analiseHipoteses = document.getElementById("analise-hipoteses");
const analiseRisco = document.getElementById("analise-risco");

let sessaoId = null;

/** Cria um balão na conversa. */
function adicionarBalao(texto, autor, emergencia = false) {
  const balao = document.createElement("div");
  balao.className = `balao balao-${autor}`;
  if (emergencia) balao.classList.add("balao-emergencia");
  balao.textContent = texto;
  conversa.appendChild(balao);
  conversa.scrollTop = conversa.scrollHeight;
  return balao;
}

function mostrarDigitando() {
  const balao = document.createElement("div");
  balao.className = "balao balao-assistente";
  balao.innerHTML = '<span class="digitando"><span></span><span></span><span></span></span>';
  conversa.appendChild(balao);
  conversa.scrollTop = conversa.scrollHeight;
  return balao;
}

function atualizarMotor(motor) {
  const rotulos = {
    watson: ["watsonx Assistant", "etiqueta etiqueta-watson"],
    local: ["motor local", "etiqueta etiqueta-local"],
  };
  const [texto, classe] = rotulos[motor] || ["desconhecido", "etiqueta etiqueta-neutra"];
  indicadorMotor.textContent = texto;
  indicadorMotor.className = classe;
}

function listaVazia(elemento) {
  elemento.innerHTML = '<li class="vazio">—</li>';
}

function atualizarAnalise(dados) {
  // Intenção + confiança
  if (dados.intencao) {
    const confianca = dados.confianca != null
      ? ` <span class="confianca">(${(dados.confianca * 100).toFixed(0)}% de confiança)</span>`
      : "";
    analiseIntencao.innerHTML = `<code>#${dados.intencao}</code>${confianca}`;
  } else {
    analiseIntencao.innerHTML = '<span class="vazio">não reconhecida</span>';
  }

  // Entidades
  const entidades = dados.entidades || [];
  if (entidades.length) {
    analiseEntidades.innerHTML = "";
    entidades.forEach((e) => {
      const item = document.createElement("li");
      item.textContent = `@${e.entity}: ${String(e.value).replace(/_/g, " ")}`;
      analiseEntidades.appendChild(item);
    });
  } else {
    listaVazia(analiseEntidades);
  }

  // Hipóteses do mapa de conhecimento (Fase 2)
  const hipoteses = (dados.analise && dados.analise.hipoteses) || [];
  if (hipoteses.length) {
    analiseHipoteses.innerHTML = "";
    hipoteses.forEach((h) => {
      const item = document.createElement("li");
      item.innerHTML = `${h.doenca} <span class="pontuacao">· ${h.sintomas.join(", ")}</span>`;
      analiseHipoteses.appendChild(item);
    });
  } else {
    listaVazia(analiseHipoteses);
  }

  // Indício de risco
  const risco = dados.analise && dados.analise.risco;
  if (risco) {
    const classe = risco.classe.includes("alto") ? "risco-alto" : "risco-baixo";
    analiseRisco.innerHTML =
      `<span class="${classe}">${risco.classe}</span>` +
      ` <span class="confianca">(${(risco.confianca * 100).toFixed(0)}%)</span>`;
  } else {
    analiseRisco.innerHTML = '<span class="vazio">—</span>';
  }
}

async function abrirSessao() {
  try {
    const resposta = await fetch("/api/sessao", { method: "POST" });
    const dados = await resposta.json();
    sessaoId = dados.sessao_id;
    atualizarMotor(dados.motor);
    adicionarBalao(dados.mensagem, "assistente");
  } catch (erro) {
    adicionarBalao("Não foi possível iniciar o atendimento. O servidor está no ar?", "erro");
  }
}

async function enviarMensagem(texto) {
  adicionarBalao(texto, "paciente");
  campo.value = "";
  botao.disabled = true;
  const digitando = mostrarDigitando();

  try {
    const resposta = await fetch("/api/mensagem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessao_id: sessaoId, texto }),
    });
    const dados = await resposta.json();
    digitando.remove();

    if (!resposta.ok) {
      adicionarBalao(dados.erro || "Erro ao processar a mensagem.", "erro");
      return;
    }

    sessaoId = dados.sessao_id;
    atualizarMotor(dados.motor);
    adicionarBalao(dados.resposta, "assistente", dados.intencao === "emergencia_cardiaca");
    atualizarAnalise(dados);
  } catch (erro) {
    digitando.remove();
    adicionarBalao("Falha de comunicação com o servidor.", "erro");
  } finally {
    botao.disabled = false;
    campo.focus();
  }
}

formulario.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const texto = campo.value.trim();
  if (texto) enviarMensagem(texto);
});

sugestoes.addEventListener("click", (evento) => {
  if (evento.target.classList.contains("sugestao")) {
    enviarMensagem(evento.target.textContent);
  }
});

abrirSessao();
