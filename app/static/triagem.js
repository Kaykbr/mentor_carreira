// Chat de triagem — integração HTMX + scroll automático.
// O envio/resposta é gerenciado por HTMX (hx-post, hx-target, hx-swap).
// Este arquivo cuida apenas de: scroll, limpar input pós-resposta e contador de chars.

document.addEventListener("DOMContentLoaded", () => {
    const chat = document.getElementById("chat");
    if (chat) chat.scrollTop = chat.scrollHeight;

    // Contador de caracteres no campo de mensagem
    const campo = document.getElementById("campo-mensagem");
    const contador = document.getElementById("msg-contador");
    if (campo && contador) {
        const max = parseInt(campo.maxLength, 10) || 5000;
        const atualizar = () => {
            const r = max - campo.value.length;
            contador.textContent = r < 200 ? `${r} caracteres restantes` : "";
        };
        campo.addEventListener("input", atualizar);
    }
});

// Após HTMX inserir o fragmento de resposta no #chat
document.addEventListener("htmx:afterSwap", (evt) => {
    if (!evt.detail.target || evt.detail.target.id !== "chat") return;

    // Remove aviso de boas-vindas se ainda visível
    const vazio = document.getElementById("chat-vazio");
    if (vazio) vazio.remove();

    // Scroll para a nova mensagem
    const chat = document.getElementById("chat");
    if (chat) chat.scrollTop = chat.scrollHeight;
});

// Após HTMX finalizar a requisição: limpa input e devolve foco
document.addEventListener("htmx:afterRequest", (evt) => {
    if (!evt.detail.elt || evt.detail.elt.id !== "form-mensagem") return;
    const campo = document.getElementById("campo-mensagem");
    if (campo) {
        campo.value = "";
        campo.focus();
        // Dispara evento input para atualizar o contador
        campo.dispatchEvent(new Event("input"));
    }
});

// HTMX ignora respostas 4xx/5xx por padrão (não faz swap). Sem tratamento, o aluno
// perde a mensagem digitada e nada aparece na tela — parece que o site quebrou.
// Aqui interceptamos o erro e injetamos uma bolha vermelha no chat com a explicação.
function _mensagemDeErro(status) {
    if (status === 429) {
        return "Você enviou muitas mensagens em pouco tempo. Aguarde alguns minutos e tente novamente.";
    }
    if (status === 503) {
        return "O mentor (IA) está indisponível no momento. Tente novamente em instantes.";
    }
    if (status === 502 || status === 504) {
        return "A resposta demorou demais. Verifique sua conexão e tente enviar novamente.";
    }
    return "Não foi possível enviar sua mensagem agora. Tente novamente em alguns segundos.";
}

document.addEventListener("htmx:responseError", (evt) => {
    if (!evt.detail.elt || evt.detail.elt.id !== "form-mensagem") return;
    const chat = document.getElementById("chat");
    if (!chat) return;
    const status = evt.detail.xhr ? evt.detail.xhr.status : 0;
    const bolha = document.createElement("div");
    bolha.className = "mensagem mensagem-erro mensagem-nova";
    bolha.setAttribute("role", "alert");
    // textContent evita XSS caso a mensagem venha do backend futuramente.
    const span = document.createElement("span");
    span.textContent = "⚠️ " + _mensagemDeErro(status);
    bolha.appendChild(span);
    chat.appendChild(bolha);
    chat.scrollTop = chat.scrollHeight;
});

// Erro de rede/timeout no cliente (sem resposta HTTP) — mesma UX.
document.addEventListener("htmx:sendError", (evt) => {
    if (!evt.detail.elt || evt.detail.elt.id !== "form-mensagem") return;
    const chat = document.getElementById("chat");
    if (!chat) return;
    const bolha = document.createElement("div");
    bolha.className = "mensagem mensagem-erro mensagem-nova";
    bolha.setAttribute("role", "alert");
    const span = document.createElement("span");
    span.textContent = "⚠️ Sem conexão com o servidor. Verifique sua internet e tente novamente.";
    bolha.appendChild(span);
    chat.appendChild(bolha);
    chat.scrollTop = chat.scrollHeight;
});
