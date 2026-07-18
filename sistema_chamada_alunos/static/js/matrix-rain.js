/*
 * Efeito de "chuva digital" (estilo Matrix) desenhado num <canvas>
 * fixo atrás do conteúdo, em todas as páginas (ver templates/base.html).
 *
 * Cuidados de performance, já que o Kiosk e o Screen ficam ligados o
 * dia inteiro em terminais/TVs:
 *  - roda a ~20 quadros por segundo (setInterval), não a 60fps;
 *  - pausa sozinho quando a aba fica em segundo plano (visibilitychange);
 *  - respeita "prefers-reduced-motion" (não anima, fica só o fundo escuro);
 *  - poucas colunas (baseadas na largura da tela / 22px).
 */
(function () {
    "use strict";

    var canvas = document.getElementById("matrix-rain-canvas");
    if (!canvas || !canvas.getContext) return;

    var reduzirMovimento = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduzirMovimento) return;

    var ctx = canvas.getContext("2d");
    var CARACTERES = "アイウエオカキクケコサシスセソ0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    var TAMANHO_FONTE = 16;
    var colunas, gotas;
    var intervalo = null;

    function redimensionar() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        colunas = Math.floor(canvas.width / TAMANHO_FONTE);
        gotas = new Array(colunas).fill(0).map(function () {
            return Math.floor(Math.random() * -50);
        });
    }

    function desenhar() {
        ctx.fillStyle = "rgba(0, 0, 0, 0.08)";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.font = TAMANHO_FONTE + "px monospace";

        for (var i = 0; i < colunas; i++) {
            var caractere = CARACTERES.charAt(Math.floor(Math.random() * CARACTERES.length));
            var x = i * TAMANHO_FONTE;
            var y = gotas[i] * TAMANHO_FONTE;

            ctx.fillStyle = "#00ff41";
            ctx.fillText(caractere, x, y);

            if (y > canvas.height && Math.random() > 0.975) {
                gotas[i] = 0;
            }
            gotas[i]++;
        }
    }

    function iniciar() {
        if (intervalo) return;
        intervalo = setInterval(desenhar, 50);
    }

    function parar() {
        if (!intervalo) return;
        clearInterval(intervalo);
        intervalo = null;
    }

    window.addEventListener("resize", redimensionar);
    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            parar();
        } else {
            iniciar();
        }
    });

    redimensionar();
    iniciar();
})();
