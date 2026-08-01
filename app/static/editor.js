// Utilitários dos formulários de edição (perfil, PDI) e da edição inline do currículo.
// 1) Linhas repetíveis: [data-add] clona um <template> e anexa à lista indicada.
// 2) Remover linha: botão .repeat-remover remove o .repeat-item mais próximo.
// 3) Toggle de edição: [data-toggle] alterna a classe .oculto dos ids informados.

(function () {
    "use strict";

    // 1) Adicionar linha repetível ---------------------------------------
    document.querySelectorAll("[data-add]").forEach((botao) => {
        botao.addEventListener("click", () => {
            const tpl = document.getElementById(botao.dataset.add);
            const lista = document.getElementById(botao.dataset.lista);
            if (!tpl || !lista) return;
            const novo = tpl.content.firstElementChild.cloneNode(true);
            lista.appendChild(novo);
            const foco = novo.querySelector("input, textarea, select");
            if (foco) foco.focus();
        });
    });

    // 2) Remover linha repetível (delegação) -----------------------------
    // Confirmação via modal global (open-confirm em app.js) — UI única no app.
    document.addEventListener("click", (ev) => {
        const remover = ev.target.closest(".repeat-remover");
        if (!remover) return;
        const item = remover.closest(".repeat-item");
        if (!item) return;
        const msg = remover.dataset.confirm;
        if (msg) {
            window.dispatchEvent(new CustomEvent("open-confirm", {
                detail: { message: msg, perigo: true, confirmLabel: "Remover", onConfirm: () => item.remove() },
            }));
        } else {
            item.remove();
        }
    });

    // 3) Alternar modo de edição -----------------------------------------
    // <button data-toggle="ids,separados,por,virgula"> alterna .oculto neles.
    document.querySelectorAll("[data-toggle]").forEach((botao) => {
        botao.addEventListener("click", () => {
            botao.dataset.toggle.split(",").forEach((id) => {
                const alvo = document.getElementById(id.trim());
                if (alvo) alvo.classList.toggle("oculto");
            });
        });
    });

    // 4) Contadores de caracteres ----------------------------------------
    // <span class="char-count" data-for="id-do-campo"> atualiza em tempo real.
    document.querySelectorAll(".char-count[data-for]").forEach((span) => {
        const target = document.getElementById(span.dataset.for);
        if (!target) return;
        const max = parseInt(target.getAttribute("maxlength") || "0", 10);
        const atualizar = () => {
            const len = target.value.length;
            span.textContent = max ? `${len}/${max}` : String(len);
            span.classList.toggle("char-count-aviso", max > 0 && len >= max * 0.9);
        };
        target.addEventListener("input", atualizar);
        atualizar();
    });

    // 5) Aviso de alterações não salvas ----------------------------------
    const _form = document.querySelector("form.form-edicao");
    if (_form) {
        let _alterado = false;
        _form.addEventListener("change", () => { _alterado = true; });
        _form.querySelector("[type=submit]")?.addEventListener("click", () => { _alterado = false; });
        window.addEventListener("beforeunload", (e) => { if (_alterado) e.preventDefault(); });
    }

    // 6) Destaque dos títulos de seção do currículo (sem innerHTML) -------
    // <pre class="curriculo-pre" data-destacar-secoes> tem os títulos ATS em
    // maiúsculas transformados em <strong> — compartilhado pelo currículo geral
    // e pelos currículos por vaga.
    document.querySelectorAll("pre.curriculo-pre[data-destacar-secoes]").forEach((pre) => {
        const secoes = new Set(["RESUMO", "FORMAÇÃO", "EXPERIÊNCIAS", "PROJETOS",
                        "SKILLS TÉCNICAS", "SKILLS COMPORTAMENTAIS", "CERTIFICAÇÕES"]);
        const linhas = pre.textContent.split("\n");
        pre.textContent = "";
        linhas.forEach((linha, i) => {
            if (secoes.has(linha.trim())) {
                const destaque = document.createElement("strong");
                destaque.style.fontSize = "0.8rem";
                destaque.style.letterSpacing = "0.08em";
                destaque.style.color = "#102a43";
                destaque.textContent = linha;
                pre.appendChild(destaque);
            } else {
                pre.appendChild(document.createTextNode(linha));
            }
            if (i < linhas.length - 1) pre.appendChild(document.createTextNode("\n"));
        });
    });

    // 7) Abrir accordion via ?abrir= -------------------------------------
    (function () {
        const p = new URLSearchParams(location.search).get("abrir");
        if (!p) return;
        document.querySelectorAll(".secao-form[open]").forEach((el) => el.removeAttribute("open"));
        const alvo = document.getElementById(p);
        if (alvo) {
            alvo.setAttribute("open", "");
            setTimeout(() => alvo.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
        }
    }());
})();
