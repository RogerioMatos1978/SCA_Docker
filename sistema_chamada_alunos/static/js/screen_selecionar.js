/*
 * Tela de seleção de sala para a TV (auto-pareamento sala<->TV).
 *
 * O pareamento é guardado no localStorage do PRÓPRIO NAVEGADOR da TV
 * (não no servidor) — por isso cada TV física, ao ser configurada uma
 * vez, sempre abre direto na sua sala nas próximas vezes que a página
 * carregar (ex.: depois de a TV ser desligada/religada).
 */
(function () {
    "use strict";

    var CHAVE_LOCALSTORAGE = "chamada_alunos_tv_sala_id";

    // Se esta TV já foi pareada antes, pula a grade e vai direto para
    // a sala salva.
    var salaSalva = window.localStorage.getItem(CHAVE_LOCALSTORAGE);
    if (salaSalva) {
        window.location.href = "/screen/" + salaSalva;
        return;
    }

    document.querySelectorAll(".botao-escolher-sala").forEach(function (botao) {
        botao.addEventListener("click", function () {
            var salaId = botao.dataset.id;
            window.localStorage.setItem(CHAVE_LOCALSTORAGE, salaId);
            window.location.href = "/screen/" + salaId;
        });
    });
})();
