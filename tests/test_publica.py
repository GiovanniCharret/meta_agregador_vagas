"""Testes de src/publica.py - a preparacao dos arquivos que sobem por FTP.

Por que este modulo merece teste: ele edita arquivos que sao do SITE, e nao nossos. Uma
substituicao que nao encontra o alvo silenciosamente produziria um pacote de deploy que
parece pronto e nao muda nada - e o defeito so apareceria depois do upload.
"""

import pytest

# Trechos reais do index.html do presenterosa, reduzidos ao que a substituicao toca.
INDEX = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Presente Rosa</title>
<link rel="stylesheet" href="style.css"></head>
<body>
    <main id="home">
        <section id="apps" class="grid-apps">
            <div class="card">
                <h3>Lista de Bairros</h3>
                <p>Quase completo<br>Falta você julgar</p>
                <button class="btn-rosa btn-resultado" type="button">Acessar</button>
            </div>
            <div class="card">
                <h3>Aplicação 2</h3>
                <p>O que quer que você imagine, eu desenvolvo aqui.</p>
                <button class="btn-rosa" type="button">Acessar</button>
            </div>
        </section>
    </main>
</body>
</html>
"""

APP_JS = """document.addEventListener("DOMContentLoaded", () => {
  const resultadoButtons = document.querySelectorAll(".btn-resultado");
  resultadoButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const newTab = window.open("resultado2.html", "_blank", "noopener,noreferrer");
      if (!newTab) {
        window.location.href = "resultado2.html";
      }
    });
  });
});
"""


def test_o_card_muda_de_nome():
    """Por que este teste existe: e a mudanca que voce pediu - a pagina nova vive no lugar
    da Lista de Bairros, com o nome combinado."""
    from src.publica import index_atualizado
    novo = index_atualizado(INDEX)
    assert "<h3>Meta_Agregador de Vagas</h3>" in novo
    assert "Lista de Bairros" not in novo


def test_a_descricao_do_card_fala_do_que_a_pagina_faz():
    """Por que este teste existe: "Quase completo, falta você julgar" descrevia a lista de
    bairros. Deixar a descricao antiga com o titulo novo confundiria quem abre."""
    from src.publica import index_atualizado
    novo = index_atualizado(INDEX)
    assert "vagas" in novo.lower()
    assert "Falta você julgar" not in novo


def test_o_resto_do_index_fica_intacto():
    """Por que este teste existe: o index e do SITE, nao nosso. A edicao tem que ser
    cirurgica - se ela mexesse no segundo card ou no cabecalho, quebraria coisa que
    funciona e que nem estamos olhando."""
    from src.publica import index_atualizado
    novo = index_atualizado(INDEX)
    assert "<h3>Aplicação 2</h3>" in novo
    assert '<link rel="stylesheet" href="style.css">' in novo
    assert novo.count('class="card"') == 2


def test_index_sem_o_alvo_falha_alto():
    """Por que este teste existe: e o defeito mais perigoso deste modulo. Se voce mexer no
    index e o texto que procuramos sumir, a substituicao nao encontraria nada e devolveria
    o arquivo IGUAL - e voce subiria um pacote que parece pronto e nao muda nada.

    Falhar alto aqui e o que transforma um bug silencioso num erro obvio."""
    from src.publica import index_atualizado
    from src.erros import EntradaInvalida
    with pytest.raises(EntradaInvalida) as erro:
        index_atualizado("<html><body>outro site qualquer</body></html>")
    assert "Lista de Bairros" in str(erro.value)


def test_o_botao_passa_a_abrir_a_pagina_nova():
    """Por que este teste existe: trocar o nome do card sem trocar o destino levaria ela
    para a lista de bairros - o pior resultado possivel, porque parece que funcionou."""
    from src.publica import app_js_atualizado
    novo = app_js_atualizado(APP_JS)
    assert novo.count("vagas.html") == 2
    assert "resultado2.html" not in novo


def test_app_js_sem_o_alvo_falha_alto():
    """Por que este teste existe: mesma razao do index - substituicao que nao encontra
    alvo tem que gritar, e nao devolver o arquivo intacto."""
    from src.publica import app_js_atualizado
    from src.erros import EntradaInvalida
    with pytest.raises(EntradaInvalida):
        app_js_atualizado("console.log('outro script');")


def test_edicoes_sao_deterministicas():
    """Por que este teste existe: o pacote de deploy e gerado a cada atualizacao. Se a
    edicao variasse, voce nao conseguiria comparar dois pacotes para ver o que mudou."""
    from src.publica import index_atualizado, app_js_atualizado
    assert index_atualizado(INDEX) == index_atualizado(INDEX)
    assert app_js_atualizado(APP_JS) == app_js_atualizado(APP_JS)
