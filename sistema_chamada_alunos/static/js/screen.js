/*
 * Painel de TV (Screen).
 *
 * Roteamento por sala no cliente: o servidor sempre faz broadcast do
 * evento aluno_chamado para todas as telas (não existem "rooms" no
 * Socket.IO aqui). Esta TV só reage se CONFIG_SCREEN.salaNome não
 * estiver definido (TV "geral") OU se for igual a chamada.sala_nome.
 */
(function () {
    "use strict";

    var CONFIG = window.CONFIG_SCREEN || {};
    var socket = io();
    var palco = document.getElementById("screen-palco");
    var template = document.getElementById("screen-template-chamada");
    var listaRecentes = document.getElementById("screen-lista-recentes");
    var CHAVE_LOCALSTORAGE = "chamada_alunos_tv_sala_id";

    var linkTrocarSala = document.querySelector(".screen-trocar-sala");
    if (linkTrocarSala) {
        linkTrocarSala.addEventListener("click", function () {
            // Sem isso, /screen/ redirecionaria automaticamente de
            // volta para esta mesma sala (ver screen_selecionar.js).
            window.localStorage.removeItem(CHAVE_LOCALSTORAGE);
        });
    }

    function relevante(chamada) {
        if (!CONFIG.salaNome) return true; // TV geral: reage a tudo
        return chamada.sala_nome === CONFIG.salaNome;
    }

    function narrar(chamada) {
        if (!("speechSynthesis" in window)) return;
        var texto = chamada.aluno_nome + ". Dirija-se a " + (chamada.destino_chamada || "");
        var fala = new SpeechSynthesisUtterance(texto);
        fala.lang = "pt-BR";
        window.speechSynthesis.cancel(); // corta narração anterior, se houver
        window.speechSynthesis.speak(fala);
    }

    function montarUrlFoto(nomeArquivo) {
        if (!CONFIG.urlFotoBase || !nomeArquivo) return null;
        return CONFIG.urlFotoBase.replace("__ARQUIVO__", nomeArquivo);
    }

    function exibirChamada(chamada) {
        var clone = template.content.cloneNode(true);
        var imgEl = clone.getElementById("screen-foto-img");
        var inicialEl = clone.getElementById("screen-foto-inicial");
        var urlFoto = montarUrlFoto(chamada.foto);

        if (urlFoto) {
            imgEl.src = urlFoto;
            imgEl.style.display = "";
            inicialEl.style.display = "none";
        } else {
            imgEl.style.display = "none";
            inicialEl.textContent = (chamada.aluno_nome || "?").charAt(0).toUpperCase();
            inicialEl.style.display = "";
        }

        clone.getElementById("screen-chamada-nome").textContent = chamada.aluno_nome;
        clone.getElementById("screen-chamada-turma").textContent = chamada.turma || "";
        clone.getElementById("screen-chamada-destino").textContent = chamada.destino_chamada || "";

        palco.innerHTML = "";
        palco.appendChild(clone);
    }

    function prependRecente(chamada) {
        if (!listaRecentes) return;
        var item = document.createElement("div");
        item.className = "screen-recente-item";
        item.innerHTML = "<strong></strong><span></span>";
        item.querySelector("strong").textContent = chamada.aluno_nome;
        item.querySelector("span").textContent = chamada.sala_nome || "";
        listaRecentes.insertBefore(item, listaRecentes.firstChild);
        var itens = listaRecentes.querySelectorAll(".screen-recente-item");
        if (itens.length > 3) itens[itens.length - 1].remove();
    }

    socket.on("aluno_chamado", function (chamada) {
        if (!relevante(chamada)) return;
        exibirChamada(chamada);
        prependRecente(chamada);
        narrar(chamada);
    });

    // Alguns navegadores exigem uma primeira interação do usuário
    // antes de permitir áudio. Como a TV normalmente já teve um
    // clique ao escolher a sala, isso costuma bastar; mas deixamos
    // aqui como reforço.
    document.addEventListener("click", function inicializarAudio() {
        if ("speechSynthesis" in window) {
            window.speechSynthesis.getVoices();
        }
        document.removeEventListener("click", inicializarAudio);
    });
})();
