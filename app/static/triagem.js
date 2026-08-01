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
