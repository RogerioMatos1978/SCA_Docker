/*
 * Terminal Kiosk — fila de chamada.
 * Conecta ao Socket.IO, dispara chamar_aluno/rechamar_aluno e atualiza
 * a tela em tempo real conforme os eventos aluno_chamado/erro_chamada/
 * dados_atualizados chegam, sem nunca recarregar a página.
 */
(function () {
    "use strict";

    var socket = io();
    var listaEl = document.getElementById("kiosk-lista");
    var recentesEl = document.getElementById("kiosk-recentes-lista");
    var contagemEl = document.getElementById("kiosk-contagem");
    var alertaEl = document.getElementById("kiosk-alerta");
    var buscaEl = document.getElementById("kiosk-busca");

    function mostrarAlerta(mensagem) {
        alertaEl.textContent = mensagem;
        alertaEl.style.display = "block";
        setTimeout(function () {
            alertaEl.style.display = "none";
        }, 4000);
    }

    function atualizarContagem() {
        var restantes = listaEl.querySelectorAll(".kiosk-cartao-aluno").length;
        contagemEl.textContent = restantes;
        if (restantes === 0 && !listaEl.querySelector(".kiosk-vazio")) {
            var vazio = document.createElement("p");
            vazio.className = "kiosk-vazio";
            vazio.textContent = "Nenhum aluno aguardando no momento.";
            listaEl.appendChild(vazio);
        }
    }

    function chamar(alunoId) {
        socket.emit("chamar_aluno", { aluno_id: alunoId });
    }

    function rechamar(alunoId) {
        socket.emit("rechamar_aluno", { aluno_id: alunoId });
    }

    // Delegação de eventos: os cartões são recriados/removidos
    // dinamicamente, então ouvimos o clique no container.
    listaEl.addEventListener("click", function (evento) {
        var botao = evento.target.closest(".botao-chamar");
        if (botao) chamar(botao.dataset.id);
    });

    recentesEl.addEventListener("click", function (evento) {
        var botao = evento.target.closest(".botao-rechamar");
        if (botao) rechamar(botao.dataset.id);
    });

    if (buscaEl) {
        buscaEl.addEventListener("input", function () {
            var termo = buscaEl.value.trim().toLowerCase();
            listaEl.querySelectorAll(".kiosk-cartao-aluno").forEach(function (cartao) {
                var visivel = cartao.dataset.nome.indexOf(termo) !== -1;
                cartao.style.display = visivel ? "" : "none";
            });
        });
    }

    function prependRecente(chamada) {
        var vazio = recentesEl.querySelector(".kiosk-vazio");
        if (vazio) vazio.remove();

        var item = document.createElement("div");
        item.className = "kiosk-cartao-recente";
        item.innerHTML =
            '<div><strong></strong><span></span></div>' +
            '<button class="botao botao-rechamar"></button>';
        item.querySelector("strong").textContent = chamada.aluno_nome;
        item.querySelector("span").textContent = chamada.sala_nome || "";
        var botaoRechamar = item.querySelector(".botao-rechamar");
        botaoRechamar.textContent = "Rechamar";
        botaoRechamar.dataset.id = chamada.aluno_id;

        recentesEl.insertBefore(item, recentesEl.firstChild);
        // Mantém só os 5 mais recentes na tela.
        var itens = recentesEl.querySelectorAll(".kiosk-cartao-recente");
        if (itens.length > 5) itens[itens.length - 1].remove();
    }

    socket.on("aluno_chamado", function (chamada) {
        // Se o aluno estava na fila de espera aqui, remove o cartão
        // (chamada nova, não rechamada) — a fila é filtrada por
        // status='aguardando' no servidor.
        if (chamada.tipo === "chamada") {
            var cartao = listaEl.querySelector('.kiosk-cartao-aluno[data-id="' + chamada.aluno_id + '"]');
            if (cartao) {
                cartao.remove();
                atualizarContagem();
            }
        }
        prependRecente(chamada);
    });

    socket.on("erro_chamada", function (dados) {
        mostrarAlerta(dados.mensagem || "Não foi possível completar a chamada.");
    });

    // Aviso leve de que algo mudou no cadastro (sala/aluno criado,
    // editado...) em outra tela — evita que o terminal fique com uma
    // fila desatualizada por muito tempo, sem forçar reload no meio
    // de uma ação do operador.
    socket.on("dados_atualizados", function () {
        mostrarAlerta("A lista de alunos foi atualizada em outra tela. Atualize a página quando puder.");
    });
})();
