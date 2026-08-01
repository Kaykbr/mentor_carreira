// Comportamentos compartilhados por todas as páginas (carregado em base.html).
// 1) Estado de "processando" em formulários lentos (data-loading).
// 2) Mostrar/ocultar senha (botões .toggle-senha com data-target).
// 3) Confirmação de senha (input[data-match] aponta para o id do campo original).
// 4) Alpine.js components: toastManager, confirmModal.

/* ---- Alpine.js components (registrados antes da inicialização do Alpine) -- */
document.addEventListener("alpine:init", () => {
    /* Toast notifications globais */
    Alpine.data("toastManager", () => ({
        toasts: [],
        _cnt: 0,
        init(flashes) {
            (Array.isArray(flashes) ? flashes : []).forEach((f) =>
                this.add(f.tipo, f.msg)
            );
        },
        add(tipo, msg) {
            const id = ++this._cnt;
            this.toasts.push({ id, tipo, msg, visible: true });
            setTimeout(() => this.dismiss(id), 5000);
        },
        dismiss(id) {
            const t = this.toasts.find((t) => t.id === id);
            if (t) t.visible = false;
            setTimeout(() => {
                this.toasts = this.toasts.filter((t) => t.id !== id);
            }, 350);
        },
    }));

    /* Modal de confirmação global — disparado via Custom Event.
       Dois modos: `action` (monta form e faz POST/GET) ou `onConfirm` (callback
       client-side, usado por editor.js/kanban.js para remoções locais). */
    Alpine.data("confirmModal", () => ({
        visible: false,
        message: "",
        action: "",
        method: "POST",
        perigo: false,
        confirmLabel: "Confirmar",
        _onConfirm: null,
        open(detail) {
            this.message = detail.message || "Confirmar?";
            this.action = detail.action || "";
            this.method = (detail.method || "POST").toUpperCase();
            this.perigo = !!detail.perigo;
            this.confirmLabel = detail.confirmLabel || "Confirmar";
            this._onConfirm = typeof detail.onConfirm === "function" ? detail.onConfirm : null;
            this.visible = true;
        },
        close() {
            this.visible = false;
            this._onConfirm = null;
        },
        confirm() {
            if (this._onConfirm) {
                this._onConfirm();
            } else if (this.action) {
                const f = document.createElement("form");
                f.method = this.method === "GET" ? "GET" : "POST";
                f.action = this.action;
                document.body.appendChild(f);
                f.submit();
            }
            this.visible = false;
            this._onConfirm = null;
        },
    }));

});

/* ---- Comportamentos DOM-ready ------------------------------------------ */
document.addEventListener("DOMContentLoaded", () => {
    /* 1) Estado de loading em POSTs lentos: botão vira spinner + overlay em tela
          cheia com uma "caixinha" explicando o que está acontecendo. Isso deixa
          claro para o aluno que gerações (perfil/PDI/currículo/análise de vaga)
          estão em curso, mesmo que demorem 30-60s. */
    function mostrarOverlayLoading(mensagem) {
        if (document.getElementById("loading-overlay")) return;
        const overlay = document.createElement("div");
        overlay.id = "loading-overlay";
        overlay.className = "loading-overlay";
        overlay.setAttribute("role", "status");
        overlay.setAttribute("aria-live", "polite");
        overlay.innerHTML = `
            <div class="loading-caixa">
                <div class="loading-spinner" aria-hidden="true"></div>
                <p class="loading-mensagem">${mensagem}</p>
                <p class="loading-dica">Pode levar até 1 minuto. Não feche esta página.</p>
            </div>`;
        document.body.appendChild(overlay);
    }

    document.querySelectorAll("form[data-loading]").forEach((form) => {
        form.addEventListener("submit", () => {
            const botao = form.querySelector('button[type="submit"], button:not([type])');
            if (!botao || botao.dataset.loadingAtivo) return;
            botao.dataset.loadingAtivo = "1";
            botao.dataset.textoOriginal = botao.textContent;
            botao.classList.add("botao-carregando");
            botao.textContent = form.dataset.loading || "Processando…";
            setTimeout(() => { botao.disabled = true; }, 0);
            mostrarOverlayLoading(form.dataset.loading || "Processando…");
        });
    });

    /* 2) Mostrar/ocultar senha */
    document.querySelectorAll(".toggle-senha").forEach((botao) => {
        const alvo = document.getElementById(botao.dataset.target);
        if (!alvo) return;
        botao.addEventListener("click", () => {
            const mostrando = alvo.type === "text";
            alvo.type = mostrando ? "password" : "text";
            botao.setAttribute("aria-pressed", String(!mostrando));
            botao.textContent = mostrando ? "Mostrar" : "Ocultar";
            botao.setAttribute("aria-label", mostrando ? "Mostrar senha" : "Ocultar senha");
        });
    });

    /* 3) Confirmação de senha (validação client-side) */
    document.querySelectorAll("input[data-match]").forEach((confirma) => {
        const original = document.getElementById(confirma.dataset.match);
        if (!original) return;
        const validar = () => {
            confirma.setCustomValidity(
                confirma.value && confirma.value !== original.value
                    ? "As senhas não coincidem."
                    : ""
            );
        };
        confirma.addEventListener("input", validar);
        original.addEventListener("input", validar);
    });

    /* 4) Contador de caracteres */
    document.querySelectorAll(
        "input[maxlength][aria-describedby], textarea[maxlength][aria-describedby]"
    ).forEach((campo) => {
        const alvo = document.getElementById(campo.getAttribute("aria-describedby"));
        if (!alvo) return;
        const max = parseInt(campo.maxLength, 10);
        const atualizar = () => {
            const r = max - campo.value.length;
            alvo.textContent =
                r < 100 ? `${r} caracteres restantes` : `Máx. ${max} caracteres`;
        };
        campo.addEventListener("input", atualizar);
        atualizar();
    });
});
