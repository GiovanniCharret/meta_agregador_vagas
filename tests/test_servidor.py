"""Testes do servidor local - a parte que torna a marcacao possivel.

Por que existe servidor num projeto que gera pagina estatica: marcar uma vaga como salva
ou descartada precisa GRAVAR, e HTML estatico nao grava. Foi o unico motivo que
justificou o FastAPI na decisao de stack.
"""

import sqlite3

import pytest
from fastapi.testclient import TestClient


def vaga(**mudancas):
    """Devolve uma vaga no formato do projeto."""
    base = {
        "fonte": "bne",
        "id_na_fonte": "1000",
        "url": "https://www.bne.com.br/vaga/1000",
        "titulo_bruto": "dentista",
        "empresa_bruta": "Clinica Sorriso",
        "cidade": "Florianopolis",
        "uf": "SC",
        "modalidade": "presencial",
        "salario_texto": None,
        "data_publicacao": "2026-08-10",
    }
    base.update(mudancas)
    return base


@pytest.fixture
def cliente(tmp_path):
    """Servidor apontado para um banco temporario, com duas vagas dentro.

    Por que banco temporario: o teste nao pode marcar vaga no banco de verdade do
    projeto, senao a suite passaria a alterar o estado do produto.
    """
    from src.armazena import criar_esquema, salvar_vagas
    from src.servidor import criar_app

    caminho = tmp_path / "teste.sqlite"
    conexao = sqlite3.connect(caminho)
    criar_esquema(conexao)
    salvar_vagas(conexao, [vaga(), vaga(id_na_fonte="2000", cidade="Curitiba", uf="PR")],
                 agora="2026-08-16T10:00:00")
    conexao.close()

    return TestClient(criar_app(caminho))


def test_pagina_inicial_serve_o_feed(cliente):
    """Por que este teste existe: e o contrato basico do servidor - abrir o endereco tem
    que mostrar as vagas, sem passo intermediario."""
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "Florianopolis" in resposta.text
    assert "Curitiba" in resposta.text


def test_marcar_como_salva_persiste_e_volta_para_o_feed(cliente):
    """Por que este teste existe: e o caminho feliz da 3.8 pela tela. Se a gravacao nao
    persistisse, o botao seria enfeite."""
    resposta = cliente.post(
        "/marcar",
        data={"fonte": "bne", "id_na_fonte": "1000", "quem": "meu", "estado": "salva"},
        follow_redirects=False,
    )
    # Redireciona de volta para o feed, para o navegador nao reenviar o formulario ao
    # atualizar a pagina.
    assert resposta.status_code == 303
    assert "quem=meu" in resposta.headers["location"]
    # E o estado sobreviveu.
    assert "salva" in cliente.get("/?quem=meu").text.lower()


def test_descarte_sem_motivo_e_recusado_com_mensagem_legivel(cliente):
    """Por que este teste existe: a regra da 4.1 so vale se valer tambem pela tela. Se o
    servidor aceitasse descarte sem motivo, a validacao do armazenamento viraria
    decoracao - bastaria usar o formulario para contorna-la."""
    resposta = cliente.post(
        "/marcar",
        data={"fonte": "bne", "id_na_fonte": "1000", "quem": "meu",
              "estado": "descartada"},
    )
    assert resposta.status_code == 400
    # A mensagem chega ao usuario, e nao so ao log.
    assert "motivo" in resposta.text.lower()
    # E nao pode vazar traceback para a tela.
    assert "Traceback" not in resposta.text


def test_descarte_com_motivo_valido_some_do_feed(cliente):
    """Por que este teste existe: descartar tem que TIRAR a vaga da frente - e a razao
    de existir da 3.8. Se a vaga descartada continuasse aparecendo, o horizonte continuo
    que voce escolheu deixaria o feed impraticavel em poucos dias."""
    cliente.post("/marcar", data={
        "fonte": "bne", "id_na_fonte": "1000", "quem": "meu",
        "estado": "descartada", "motivo": "cidade"})
    pagina = cliente.get("/?quem=meu").text
    # A vaga descartada saiu; a outra continua.
    assert "Florianopolis" not in pagina
    assert "Curitiba" in pagina


def test_descarte_de_uma_pessoa_nao_esconde_a_vaga_da_outra(cliente):
    """Por que este teste existe: sao duas pessoas com perfis diferentes olhando o mesmo
    feed. Se o descarte fosse compartilhado, um descarte dela apagaria a vaga dele - e a
    ferramenta viraria fonte de briga em vez de ajuda."""
    cliente.post("/marcar", data={
        "fonte": "bne", "id_na_fonte": "1000", "quem": "meu",
        "estado": "descartada", "motivo": "cidade"})
    assert "Florianopolis" not in cliente.get("/?quem=meu").text
    assert "Florianopolis" in cliente.get("/?quem=dela").text


def test_feed_traz_os_botoes_de_marcacao(cliente):
    """Por que este teste existe: a marcacao acontece por formulario HTML, sem
    JavaScript. Se os formularios sumissem, nao haveria como marcar nada pela tela."""
    pagina = cliente.get("/?quem=meu").text
    assert 'action="/marcar"' in pagina
    assert 'value="salva"' in pagina
    # E o seletor de motivo tem que oferecer a lista fechada.
    assert 'name="motivo"' in pagina
    assert "vaga_velha_ou_fantasma" in pagina


def test_vaga_inexistente_e_recusada_sem_estourar(cliente):
    """Por que este teste existe: identificador adulterado na URL nao pode derrubar o
    servidor nem criar estado orfao."""
    resposta = cliente.post("/marcar", data={
        "fonte": "bne", "id_na_fonte": "9999", "quem": "meu", "estado": "salva"})
    assert resposta.status_code == 400
    assert "Traceback" not in resposta.text


def test_contagem_de_descartadas_fica_visivel(cliente):
    """Por que este teste existe: esconder vaga sem dizer quantas foram escondidas seria
    limitacao silenciosa - voce nao saberia se o feed encolheu porque filtrou bem ou
    porque a coleta falhou."""
    cliente.post("/marcar", data={
        "fonte": "bne", "id_na_fonte": "1000", "quem": "meu",
        "estado": "descartada", "motivo": "salario"})
    pagina = cliente.get("/?quem=meu").text
    assert "descartada" in pagina.lower()
