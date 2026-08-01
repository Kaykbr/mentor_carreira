// Microanimações globais — carregado em todas as páginas via base.html.
// Reveal-on-scroll leve: elementos abaixo da dobra recebem fade+slide ao entrar
// na viewport. Respeita "prefers-reduced-motion" e funciona sem JS extra nos
// templates (basta a classe já existir no CSS de cada página).

(function () {
    "use strict";

    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const SELETOR = ".cartao, .cartao-etapa, .kanban-col, .exp-card, .competencia-item, " +
                    ".timeline-item, .repeat-item, .stat-card";

    if (!("IntersectionObserver" in window)) return;

    // Gate do CSS: .reveal só esconde dentro de html.anima — sem JS/IO, tudo visível.
    document.documentElement.classList.add("anima");

    const elementos = Array.from(document.querySelectorAll(SELETOR));
    if (!elementos.length) return;

    const alturaJanela = window.innerHeight || document.documentElement.clientHeight;
    elementos.forEach((el) => {
        if (el.getBoundingClientRect().top > alturaJanela) el.classList.add("reveal");
    });

    const observador = new IntersectionObserver((entradas, obs) => {
        entradas.forEach((entrada) => {
            if (entrada.isIntersecting) {
                entrada.target.classList.add("in-view");
                obs.unobserve(entrada.target);
            }
        });
    }, { threshold: 0.1, rootMargin: "0px 0px -40px 0px" });

    elementos.forEach((el) => el.classList.contains("reveal") && observador.observe(el));
})();
