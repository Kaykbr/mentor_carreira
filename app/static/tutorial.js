// Tour guiado de primeira visita (onboarding por página).
//
// COMO DECLARAR PASSOS — em qualquer elemento da página:
//   data-tut="1"                     ordem do passo (número)
//   data-tut-titulo="Título curto"
//   data-tut-texto="O que o aluno deve fazer/entender aqui."
//
// A página se identifica por `data-tut-pagina` no <main> (bloco `tut_pagina`
// em base.html). Passos invisíveis (seções condicionais) são ignorados.
//
// ESTADO (localStorage, por aluno):
//   tut:<aluno>:<pagina>    -> "1" quando a página já foi apresentada
//   tut:<aluno>:desativado  -> "1" quando o aluno desligou o tutorial no app todo
// O botão flutuante "?" reexibe o tour da página (e reativa, se desligado).

(function () {
    "use strict";

    const main = document.querySelector("main[data-tut-pagina]");
    const pagina = main && main.dataset.tutPagina.trim();
    if (!pagina) return;

    const aluno = document.body.dataset.alunoId || "anon";
    const CHAVE_PAGINA = `tut:${aluno}:${pagina}`;
    const CHAVE_DESATIVADO = `tut:${aluno}:desativado`;

    // localStorage pode falhar (modo privado/cookies bloqueados) — degrada sem quebrar.
    const store = {
        get(k) { try { return localStorage.getItem(k); } catch { return null; } },
        set(k, v) { try { localStorage.setItem(k, v); } catch { /* ignora */ } },
        del(k) { try { localStorage.removeItem(k); } catch { /* ignora */ } },
    };

    function coletarPassos() {
        return Array.from(document.querySelectorAll("[data-tut]"))
            .filter((el) => el.getClientRects().length > 0)   // só o que está visível
            .sort((a, b) => Number(a.dataset.tut) - Number(b.dataset.tut));
    }

    if (!coletarPassos().length) return;

    // --- Elementos do tour -------------------------------------------------
    const foco = document.createElement("div");
    foco.className = "tut-foco";
    foco.hidden = true;

    const balao = document.createElement("div");
    balao.className = "tut-balao";
    balao.setAttribute("role", "dialog");
    balao.setAttribute("aria-modal", "false");
    balao.setAttribute("aria-live", "polite");
    balao.hidden = true;
    balao.innerHTML = `
        <p class="tut-progresso"></p>
        <h4 class="tut-titulo"></h4>
        <p class="tut-texto"></p>
        <div class="tut-acoes">
            <button type="button" class="tut-link tut-desativar">Não mostrar mais</button>
            <div class="tut-acoes-dir">
                <button type="button" class="botao botao-secundario botao-sm tut-pular">Pular</button>
                <button type="button" class="botao botao-sm tut-proximo">Próximo</button>
            </div>
        </div>`;

    const ajuda = document.createElement("button");
    ajuda.type = "button";
    ajuda.className = "tut-ajuda";
    ajuda.title = "Ver o tutorial desta página";
    ajuda.setAttribute("aria-label", "Ver o tutorial desta página");
    ajuda.textContent = "?";

    document.body.append(foco, balao, ajuda);

    const elProgresso = balao.querySelector(".tut-progresso");
    const elTitulo = balao.querySelector(".tut-titulo");
    const elTexto = balao.querySelector(".tut-texto");
    const btnProximo = balao.querySelector(".tut-proximo");
    const btnPular = balao.querySelector(".tut-pular");
    const btnDesativar = balao.querySelector(".tut-desativar");

    let passos = [];
    let indice = 0;
    let ativo = false;

    // --- Posicionamento ----------------------------------------------------
    function posicionar() {
        const alvo = passos[indice];
        if (!alvo) return;
        const r = alvo.getBoundingClientRect();
        const m = 10;

        foco.style.top = `${r.top - 6}px`;
        foco.style.left = `${r.left - 6}px`;
        foco.style.width = `${r.width + 12}px`;
        foco.style.height = `${r.height + 12}px`;

        const b = balao.getBoundingClientRect();
        let top = r.bottom + m;
        if (top + b.height > window.innerHeight - 8) {
            const acima = r.top - b.height - m;
            top = acima >= 8 ? acima : Math.max(8, window.innerHeight - b.height - 8);
        }
        let left = r.left + r.width / 2 - b.width / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - b.width - 8));

        balao.style.top = `${top}px`;
        balao.style.left = `${left}px`;
    }

    // --- Navegação ---------------------------------------------------------
    function mostrar(i) {
        indice = i;
        const alvo = passos[indice];
        if (!alvo) return concluir();

        elProgresso.textContent = `Passo ${indice + 1} de ${passos.length}`;
        elTitulo.textContent = alvo.dataset.tutTitulo || "";
        elTexto.textContent = alvo.dataset.tutTexto || "";
        btnProximo.textContent = indice === passos.length - 1 ? "Concluir" : "Próximo";
        btnPular.hidden = indice === passos.length - 1;

        alvo.scrollIntoView({ behavior: "smooth", block: "center" });
        setTimeout(posicionar, 300);   // deixa o scroll assentar antes de medir
        posicionar();
        btnProximo.focus({ preventScroll: true });
    }

    function iniciar() {
        passos = coletarPassos();
        if (!passos.length) return;
        ativo = true;
        foco.hidden = false;
        balao.hidden = false;
        document.body.classList.add("tut-rodando");
        mostrar(0);
    }

    function encerrar() {
        ativo = false;
        foco.hidden = true;
        balao.hidden = true;
        document.body.classList.remove("tut-rodando");
        ajuda.hidden = false;
    }

    /** Fecha o tour desta página e marca como já apresentada. */
    function concluir() {
        store.set(CHAVE_PAGINA, "1");
        encerrar();
    }

    /** Desliga o tutorial em todas as páginas (reversível pelo botão "?"). */
    function desativarTudo() {
        store.set(CHAVE_DESATIVADO, "1");
        concluir();
    }

    btnProximo.addEventListener("click", () => mostrar(indice + 1));
    btnPular.addEventListener("click", concluir);
    btnDesativar.addEventListener("click", desativarTudo);

    ajuda.addEventListener("click", () => {
        store.del(CHAVE_DESATIVADO);   // reativa se o aluno tinha desligado
        ajuda.hidden = true;
        iniciar();
    });

    document.addEventListener("keydown", (ev) => {
        if (!ativo) return;
        if (ev.key === "Escape") { ev.preventDefault(); concluir(); }
        else if (ev.key === "ArrowRight") { ev.preventDefault(); mostrar(indice + 1); }
        else if (ev.key === "ArrowLeft" && indice > 0) { ev.preventDefault(); mostrar(indice - 1); }
    });

    window.addEventListener("resize", () => ativo && posicionar());
    window.addEventListener("scroll", () => ativo && posicionar(), { passive: true });

    // --- Arranque ----------------------------------------------------------
    const jaViu = store.get(CHAVE_PAGINA) === "1";
    const desativado = store.get(CHAVE_DESATIVADO) === "1";

    if (!jaViu && !desativado) {
        setTimeout(iniciar, 450);   // dá tempo do layout/HTMX assentar
    } else {
        ajuda.hidden = false;
    }
}());
