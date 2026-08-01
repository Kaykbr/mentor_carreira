// Quadro Kanban do PDI — carregado apenas em pdi.html.
// O DOM é a fonte da verdade: mover/adicionar/editar/excluir altera os elementos e,
// a cada mudança, o estado completo do quadro é serializado e persistido no servidor.

(function () {
    "use strict";

    const board = document.getElementById("kanban");
    if (!board) return;

    const URL_QUADRO = board.dataset.url;
    const COLUNAS = ["a_fazer", "em_progresso", "concluido"];
    const template = document.getElementById("kanban-card-template");
    const progresso = document.getElementById("kanban-progresso");

    function novoId() {
        if (window.crypto && crypto.randomUUID) return crypto.randomUUID().slice(0, 8);
        return Math.random().toString(16).slice(2, 10);
    }

    function containerDe(coluna) {
        return board.querySelector(`.kanban-cards[data-coluna="${coluna}"]`);
    }

    // Lê o estado atual do DOM e devolve a lista de cards.
    function serializar() {
        const cards = [];
        COLUNAS.forEach((coluna) => {
            containerDe(coluna).querySelectorAll(".kanban-card").forEach((el) => {
                const tag = el.querySelector(".kanban-card-tag");
                const textoEl = el.querySelector(".kanban-card-texto") || el.querySelector(".kanban-card-textarea");
                cards.push({
                    id: el.dataset.id,
                    texto: (textoEl.textContent || textoEl.value || "").trim(),
                    coluna: coluna,
                    categoria: tag ? tag.textContent.trim() : "",
                });
            });
        });
        return cards;
    }

    function atualizarContadores() {
        let total = 0;
        let concluidos = 0;
        COLUNAS.forEach((coluna) => {
            const n = containerDe(coluna).querySelectorAll(".kanban-card").length;
            const contador = board.querySelector(`.kanban-col[data-coluna="${coluna}"] .kanban-count`);
            if (contador) contador.textContent = String(n);
            total += n;
            if (coluna === "concluido") concluidos = n;
        });
        if (progresso) {
            progresso.textContent = total ? `${concluidos} de ${total} concluídas.` : "";
        }
    }

    function mostrarAviso(texto) {
        if (!progresso) return;
        const original = progresso.textContent;
        progresso.textContent = texto;
        progresso.classList.add("kanban-erro");
        setTimeout(() => {
            progresso.classList.remove("kanban-erro");
            atualizarContadores();
            if (!progresso.textContent) progresso.textContent = original;
        }, 3000);
    }

    let salvando = false;
    let pendente = false;

    async function persistir() {
        if (salvando) {
            pendente = true;
            return;
        }
        salvando = true;
        if (progresso) progresso.textContent = "Salvando…";
        try {
            const res = await fetch(URL_QUADRO, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({ cards: serializar() }),
            });
            if (!res.ok) throw new Error("HTTP " + res.status);
            if (progresso) progresso.textContent = "✓ Salvo";
            setTimeout(atualizarContadores, 1400);
        } catch (e) {
            mostrarAviso("⚠ Não foi possível salvar — tente mover o card novamente.");
        } finally {
            salvando = false;
            if (pendente) {
                pendente = false;
                persistir();
            }
        }
    }

    function aplicarEstadoColuna(card, coluna) {
        card.dataset.coluna = coluna;
        card.classList.toggle("card-concluido", coluna === "concluido");
    }

    function moverCardTeclado(card, dir) {
        const atual = COLUNAS.indexOf(card.dataset.coluna);
        const destino = atual + (dir === "next" ? 1 : -1);
        if (destino < 0 || destino >= COLUNAS.length) return;
        const coluna = COLUNAS[destino];
        containerDe(coluna).appendChild(card);
        aplicarEstadoColuna(card, coluna);
        atualizarContadores();
        persistir();
        card.focus();
    }

    function autoGrow(textarea) {
        textarea.style.height = "auto";
        textarea.style.height = textarea.scrollHeight + "px";
    }

    // Clique no texto do card: troca o <p> por uma <textarea> editável.
    function iniciarEdicao(card) {
        if (card.classList.contains("editando")) return;
        const alvo = card.querySelector(".kanban-card-texto");
        if (!alvo) return;
        const textoOriginal = alvo.textContent.trim();

        const textarea = document.createElement("textarea");
        textarea.className = "kanban-card-textarea";
        textarea.maxLength = 500;
        textarea.rows = 1;
        textarea.value = textoOriginal;

        card.classList.add("editando");
        card.draggable = false;
        alvo.replaceWith(textarea);
        autoGrow(textarea);
        textarea.focus();
        textarea.select();

        let finalizado = false;
        function finalizar(salvar) {
            if (finalizado) return;
            finalizado = true;
            card.classList.remove("editando");
            card.draggable = true;
            let texto = textoOriginal;
            if (salvar) {
                const novo = textarea.value.trim().slice(0, 500);
                if (novo) texto = novo;
            }
            const p = document.createElement("p");
            p.className = "kanban-card-texto";
            p.textContent = texto;
            textarea.replaceWith(p);
            if (salvar && texto !== textoOriginal) persistir();
        }

        textarea.addEventListener("input", () => autoGrow(textarea));

        textarea.addEventListener("keydown", (ev) => {
            if (ev.key === "Enter" && !ev.shiftKey) {
                ev.preventDefault();
                finalizar(true);
                card.focus();
            } else if (ev.key === "Escape") {
                ev.preventDefault();
                finalizar(false);
                card.focus();
            }
        });

        textarea.addEventListener("blur", () => finalizar(true));
    }

    function excluirCard(card) {
        // Confirmação via modal global (open-confirm em app.js) — UI única no app.
        window.dispatchEvent(new CustomEvent("open-confirm", {
            detail: {
                message: "Excluir esta ação do quadro?",
                perigo: true,
                confirmLabel: "Excluir",
                onConfirm: () => {
                    card.remove();
                    atualizarContadores();
                    persistir();
                },
            },
        }));
    }

    // --- Clique no card: excluir (botão ×) ou editar (texto) — delegação p/ cards dinâmicos ---
    board.addEventListener("click", (ev) => {
        const botaoExcluir = ev.target.closest(".card-excluir");
        if (botaoExcluir) {
            const card = botaoExcluir.closest(".kanban-card");
            if (card) excluirCard(card);
            return;
        }
        const texto = ev.target.closest(".kanban-card-texto");
        if (texto) {
            const card = texto.closest(".kanban-card");
            if (card) iniciarEdicao(card);
        }
    });

    // --- Atalhos de teclado quando o foco está no card (não no botão excluir nem na textarea) ---
    board.addEventListener("keydown", (ev) => {
        const card = ev.target.closest(".kanban-card");
        if (!card || ev.target !== card || card.classList.contains("editando")) return;
        switch (ev.key) {
            case "Enter":
            case " ":
                ev.preventDefault();
                iniciarEdicao(card);
                break;
            case "ArrowLeft":
                ev.preventDefault();
                moverCardTeclado(card, "prev");
                break;
            case "ArrowRight":
                ev.preventDefault();
                moverCardTeclado(card, "next");
                break;
            case "Delete":
            case "Backspace":
                ev.preventDefault();
                excluirCard(card);
                break;
        }
    });

    // --- Adicionar card por coluna ---
    board.querySelectorAll(".kanban-add").forEach((form) => {
        form.addEventListener("submit", (ev) => {
            ev.preventDefault();
            const input = form.querySelector(".kanban-add-input");
            const texto = input.value.trim();
            if (!texto) return;
            const coluna = form.dataset.coluna;
            const card = template.content.firstElementChild.cloneNode(true);
            card.dataset.id = novoId();
            card.querySelector(".kanban-card-texto").textContent = texto.slice(0, 500);
            aplicarEstadoColuna(card, coluna);
            containerDe(coluna).appendChild(card);
            input.value = "";
            atualizarContadores();
            persistir();
        });
    });

    // --- Drag and drop ---
    let arrastado = null;

    board.addEventListener("dragstart", (ev) => {
        const card = ev.target.closest(".kanban-card");
        if (!card) return;
        arrastado = card;
        card.classList.add("arrastando");
        ev.dataTransfer.effectAllowed = "move";
    });

    board.addEventListener("dragend", () => {
        if (arrastado) arrastado.classList.remove("arrastando");
        arrastado = null;
        board.querySelectorAll(".kanban-cards.over").forEach((c) => c.classList.remove("over"));
    });

    board.querySelectorAll(".kanban-cards").forEach((container) => {
        container.addEventListener("dragover", (ev) => {
            ev.preventDefault();
            ev.dataTransfer.dropEffect = "move";
            container.classList.add("over");
        });
        container.addEventListener("dragleave", () => container.classList.remove("over"));
        container.addEventListener("drop", (ev) => {
            ev.preventDefault();
            container.classList.remove("over");
            if (!arrastado) return;
            container.appendChild(arrastado);
            aplicarEstadoColuna(arrastado, container.dataset.coluna);
            atualizarContadores();
            persistir();
        });
    });

    atualizarContadores();
})();
