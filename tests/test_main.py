"""Testes de src/main.py - o executavel unico do projeto."""

import json

# Reaproveita os utilitarios de escrita de configuracao dos outros testes.
from tests.test_config import escreve_config, CONFIG_VALIDA


def test_config_valida_devolve_codigo_zero(tmp_path):
    """Por que este teste existe: o codigo de saida e o unico jeito de um .bat ou um
    agendador saber se a rodada funcionou. Zero significa sucesso."""
    from src.main import main
    caminho = escreve_config(tmp_path, CONFIG_VALIDA)
    # main recebe o caminho explicito para o teste nao depender do arquivo real.
    assert main(caminho, banco=tmp_path / "b.sqlite") == 0


def test_config_invalida_devolve_codigo_um(tmp_path):
    """Por que este teste existe: erro de dado precisa terminar o programa com codigo
    1, e nao com zero, senao um agendador trataria a falha como sucesso."""
    from src.main import main
    # Configuracao sem perfil nenhum: erro de dado, nao bug de programa.
    caminho = escreve_config(tmp_path, {"perfis": []})
    assert main(caminho, banco=tmp_path / "b.sqlite") == 1


def test_erro_de_dado_escreve_mensagem_limpa_sem_traceback(tmp_path, capsys):
    """Por que este teste existe: esta e a regra central do projeto sobre falhas. O
    usuario final precisa ler uma frase que ele consiga agir, e nao um traceback. Se
    alguem trocar o `except` por um `raise`, este teste quebra."""
    from src.main import main
    caminho = escreve_config(tmp_path, {"perfis": []})
    # Executa e captura o que foi escrito nas duas saidas.
    main(caminho, banco=tmp_path / "b.sqlite")
    capturado = capsys.readouterr()
    # A mensagem de erro vai para a saida de erro, nao para a saida padrao.
    assert "perfil" in capturado.err.lower()
    # E nao pode conter as marcas de um traceback vazado.
    assert "Traceback" not in capturado.err
    assert "File \"" not in capturado.err


def pagina_com_vagas():
    """HTML da fixture com tres vagas reais do BNE."""
    from pathlib import Path
    return (Path(__file__).resolve().parent / "fixtures" / "bne_pagina.html").read_text(
        encoding="utf-8"
    )


def config_com_bne():
    """Configuracao valida cuja unica fonte ativa e o BNE."""
    copia = json.loads(json.dumps(CONFIG_VALIDA))
    copia["fontes_ativas"] = ["bne"]
    return copia


def test_grava_o_json_normalizado_com_as_vagas_coletadas(tmp_path):
    """Por que este teste existe: e a entrega da subfase S1 - da configuracao ate um
    arquivo JSON com vagas no formato do projeto, passando por coleta e traducao."""
    from src.main import main
    caminho = escreve_config(tmp_path, config_com_bne())
    destino = tmp_path / "vagas.json"
    # Buscador falso: toda URL devolve a mesma pagina de fixture.
    assert main(caminho, buscador=lambda url: pagina_com_vagas(), destino=destino, banco=tmp_path / "b.sqlite") == 0
    # O arquivo tem que existir e conter as tres vagas da fixture.
    vagas = json.loads(destino.read_text(encoding="utf-8"))
    assert len(vagas) == 3
    assert {v["uf"] for v in vagas} == {"MS", "RJ", "SP"}


def test_json_gravado_e_deterministico(tmp_path):
    """Por que este teste existe: a subfase S2 vai exigir HTML identico byte a byte
    entre duas execucoes. Se o JSON que alimenta o HTML ja variar, aquele teste se
    torna impossivel de cumprir."""
    from src.main import main
    caminho = escreve_config(tmp_path, config_com_bne())
    primeiro = tmp_path / "a.json"
    segundo = tmp_path / "b.json"
    main(caminho, buscador=lambda url: pagina_com_vagas(), destino=primeiro, banco=tmp_path / "b.sqlite")
    main(caminho, buscador=lambda url: pagina_com_vagas(), destino=segundo, banco=tmp_path / "b.sqlite")
    # Byte a byte, e nao apenas equivalente como estrutura.
    assert primeiro.read_bytes() == segundo.read_bytes()


def test_fonte_sem_coletor_vira_aviso_e_nao_derruba_a_rodada(tmp_path, capsys):
    """Por que este teste existe: `fontes_ativas` lista o que se pretende coletar, e
    varias fontes ainda nao tem coletor. Derrubar a rodada por causa delas impediria a
    coleta das que ja funcionam - mas ignorar em silencio esconderia um erro de
    digitacao. Aviso visivel resolve os dois."""
    from src.main import main
    configuracao = json.loads(json.dumps(CONFIG_VALIDA))
    configuracao["fontes_ativas"] = ["bne", "catho"]
    caminho = escreve_config(tmp_path, configuracao)
    destino = tmp_path / "vagas.json"
    # A rodada termina bem, apesar da fonte sem coletor.
    assert main(caminho, buscador=lambda url: pagina_com_vagas(), destino=destino, banco=tmp_path / "b.sqlite") == 0
    saida = capsys.readouterr().out
    # O aviso tem que citar a fonte pulada.
    assert "AVISO" in saida and "catho" in saida
    # E as vagas do BNE continuam sendo coletadas.
    assert len(json.loads(destino.read_text(encoding="utf-8"))) == 3


def test_grava_o_feed_html_com_as_vagas(tmp_path):
    """Por que este teste existe: e a entrega da subfase S2 - a primeira vez que as
    vagas viram uma pagina que voce abre no navegador."""
    from src.main import main
    caminho = escreve_config(tmp_path, config_com_bne())
    feed = tmp_path / "feed.html"
    main(caminho, buscador=lambda url: pagina_com_vagas(),
         destino=tmp_path / "v.json", destino_feed=feed, banco=tmp_path / "b.sqlite")
    html = feed.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    # As tres vagas da fixture aparecem, com suas cidades.
    for cidade in ("Anastácio", "Rio das Ostras", "São José do Rio Preto"):
        assert cidade in html


def test_feed_marca_as_cidades_desejadas_do_config(tmp_path):
    """Por que este teste existe: `cidades_desejadas` so tem efeito se chegar ate a
    tela. Se o feed ignorasse a lista, ela seria uma opcao que existe no arquivo e nao
    no produto - o pior tipo de funcionalidade."""
    from src.main import main
    configuracao = config_com_bne()
    configuracao["cidades_desejadas"] = ["Rio das Ostras"]
    caminho = escreve_config(tmp_path, configuracao)
    feed = tmp_path / "feed.html"
    main(caminho, buscador=lambda url: pagina_com_vagas(),
         destino=tmp_path / "v.json", destino_feed=feed, banco=tmp_path / "b.sqlite")
    html = feed.read_text(encoding="utf-8")
    assert "cidade desejada" in html
    # E a vaga da cidade desejada sobe ao topo, antes das outras.
    assert html.index("Rio das Ostras") < html.index("Anastácio")


def test_feed_e_deterministico_quando_o_horario_e_o_mesmo(tmp_path):
    """Por que este teste existe: e a exigencia do D8 no nivel do programa inteiro, e
    nao so da funcao de montagem. O horario entra como parte da entrada de proposito -
    com ele fixo, dois arquivos tem que ser identicos byte a byte."""
    from src.main import main
    caminho = escreve_config(tmp_path, config_com_bne())
    a, b = tmp_path / "a.html", tmp_path / "b.html"
    for saida in (a, b):
        main(caminho, buscador=lambda url: pagina_com_vagas(),
             destino=tmp_path / "v.json", destino_feed=saida, banco=tmp_path / "b.sqlite",
             gerado_em="16/08/2026 21:30")
    assert a.read_bytes() == b.read_bytes()


def test_coleta_persiste_as_vagas_no_banco(tmp_path):
    """Por que este teste existe: e a entrega da S3 - o que foi coletado tem que
    sobreviver ao fim da execucao, senao nao ha o que marcar."""
    import sqlite3
    from src.main import main
    from src.armazena import listar_vagas
    caminho = escreve_config(tmp_path, config_com_bne())
    banco = tmp_path / "vagas.sqlite"
    main(caminho, buscador=lambda url: pagina_com_vagas(),
         destino=tmp_path / "v.json", destino_feed=tmp_path / "f.html", banco=banco)
    conexao = sqlite3.connect(banco)
    try:
        assert len(listar_vagas(conexao)) == 3
    finally:
        conexao.close()


def test_segunda_coleta_nao_duplica_no_banco(tmp_path):
    """Por que este teste existe: o horizonte e continuo, entao a coleta roda todo dia e
    reencontra as mesmas vagas. Duplicar faria o banco crescer sem limite e toda
    contagem mentir mais a cada rodada."""
    import sqlite3
    from src.main import main
    from src.armazena import listar_vagas
    caminho = escreve_config(tmp_path, config_com_bne())
    banco = tmp_path / "vagas.sqlite"
    for _ in range(2):
        main(caminho, buscador=lambda url: pagina_com_vagas(),
             destino=tmp_path / "v.json", destino_feed=tmp_path / "f.html", banco=banco)
    conexao = sqlite3.connect(banco)
    try:
        assert len(listar_vagas(conexao)) == 3
    finally:
        conexao.close()


def test_estado_marcado_sobrevive_a_nova_coleta(tmp_path):
    """Por que este teste existe: e o pior defeito possivel desta subfase. Se a coleta
    do dia seguinte apagasse as marcacoes, todo descarte teria que ser refeito toda vez
    e a ferramenta seria pior do que nao ter ferramenta."""
    import sqlite3
    from src.main import main
    from src.armazena import marcar, listar_vagas
    caminho = escreve_config(tmp_path, config_com_bne())
    banco = tmp_path / "vagas.sqlite"
    argumentos = dict(buscador=lambda url: pagina_com_vagas(),
                      destino=tmp_path / "v.json", destino_feed=tmp_path / "f.html",
                      banco=banco)

    main(caminho, **argumentos)
    # Descarta uma vaga entre as duas coletas.
    conexao = sqlite3.connect(banco)
    primeira = listar_vagas(conexao)[0]
    marcar(conexao, primeira["id_canonico"], quem="meu",
           estado="descartada", motivo="cidade", agora="2026-08-16T11:00:00")
    conexao.close()

    main(caminho, **argumentos)

    conexao = sqlite3.connect(banco)
    try:
        depois = [v for v in listar_vagas(conexao, quem="meu")
                  if v["id_na_fonte"] == primeira["id_na_fonte"]][0]
        assert depois["estado"] == "descartada"
        assert depois["motivo"] == "cidade"
    finally:
        conexao.close()


def pagina_de_detalhe():
    """HTML da fixture de pagina de detalhe, com JSON-LD JobPosting real."""
    from pathlib import Path
    return (Path(__file__).resolve().parent / "fixtures"
            / "bne_detalhe_com_responsabilidades.html").read_text(encoding="utf-8")


def buscador_com_detalhe():
    """Buscador falso que devolve listagem ou detalhe conforme a URL pedida.

    Por que existe: o enriquecimento busca URLs diferentes das da coleta. Um buscador que
    devolvesse sempre a mesma pagina nao exercitaria a diferenca, que e o ponto da S3b.
    """
    def busca(url):
        # As URLs de vaga individual do BNE tem "/vaga-de-emprego" no caminho.
        if "/vaga-de-emprego" in url:
            return pagina_de_detalhe()
        return pagina_com_vagas()
    return busca


def test_enriquecimento_preenche_o_subtitulo(tmp_path):
    """Por que este teste existe: e a entrega da S3b. O titulo do BNE e generico -
    "dentista" para todas - e o subtitulo e o que devolve informacao ao card. Se o
    detalhe nao chegasse ao banco, a subfase inteira nao teria efeito nenhum."""
    import sqlite3
    from src.main import main
    from src.armazena import listar_vagas
    caminho = escreve_config(tmp_path, config_com_bne())
    banco = tmp_path / "vagas.sqlite"
    main(caminho, buscador=buscador_com_detalhe(), destino=tmp_path / "v.json",
         destino_feed=tmp_path / "f.html", banco=banco)
    conexao = sqlite3.connect(banco)
    try:
        vagas = listar_vagas(conexao)
        assert all(v["enriquecido_em"] for v in vagas)
        assert "ortodontia" in vagas[0]["subtitulo"].lower()
        # A fixture traz a faixa de preenchimento padrao do BNE, entao o salario tem que
        # continuar vazio - mostrar aquela faixa seria pior do que nao mostrar nada.
        assert vagas[0]["salario_texto"] is None
    finally:
        conexao.close()


def test_segunda_rodada_nao_busca_detalhe_de_novo(tmp_path):
    """Por que este teste existe: e a razao de a S3b vir depois da persistencia.
    Enriquecer custa uma requisicao por vaga; refazer isso toda madrugada pesaria sobre
    a fonte sem trazer nada novo."""
    from src.main import main
    caminho = escreve_config(tmp_path, config_com_bne())
    banco = tmp_path / "vagas.sqlite"

    visitadas = []
    base = buscador_com_detalhe()

    def buscador(url):
        visitadas.append(url)
        return base(url)

    argumentos = dict(destino=tmp_path / "v.json", destino_feed=tmp_path / "f.html",
                      banco=banco)
    main(caminho, buscador=buscador, **argumentos)
    detalhes_primeira = sum(1 for u in visitadas if "/vaga-de-emprego" in u)

    visitadas.clear()
    main(caminho, buscador=buscador, **argumentos)
    detalhes_segunda = sum(1 for u in visitadas if "/vaga-de-emprego" in u)

    # A primeira rodada busca as tres; a segunda nao busca nenhuma.
    assert detalhes_primeira == 3
    assert detalhes_segunda == 0


def test_detalhe_sem_dado_estruturado_vira_aviso_e_nao_derruba(tmp_path, capsys):
    """Por que este teste existe: pagina de detalhe fora do padrao nao pode interromper o
    enriquecimento das outras. Era o criterio escrito no plano da subfase."""
    from src.main import main
    caminho = escreve_config(tmp_path, config_com_bne())

    def buscador(url):
        if "/vaga-de-emprego" in url:
            return "<html><body>sem dado estruturado</body></html>"
        return pagina_com_vagas()

    assert main(caminho, buscador=buscador, destino=tmp_path / "v.json",
                destino_feed=tmp_path / "f.html", banco=tmp_path / "b.sqlite") == 0
    assert "AVISO" in capsys.readouterr().out


def test_fonte_indisponivel_vira_aviso_e_a_rodada_continua(tmp_path, capsys):
    """Por que este teste existe: um termo do config pode simplesmente nao existir
    naquela fonte, e o site responde 404. Isso e ausencia de resultado, nao defeito -
    derrubar a rodada por causa disso faria um termo mal escolhido apagar a coleta
    inteira. Vale igual para 403, que e a resposta de quem bloqueia."""
    from src.main import main
    from src.erros import FonteIndisponivel

    caminho = escreve_config(tmp_path, config_com_bne())
    destino = tmp_path / "vagas.json"

    def buscador_que_falha(url):
        # Simula o 404 que o site devolve para um termo que ele nao conhece.
        raise FonteIndisponivel("bne respondeu 404 em {}".format(url))

    # A rodada termina bem, com zero vaga, em vez de estourar.
    assert main(caminho, buscador=buscador_que_falha, destino=destino, banco=tmp_path / "b.sqlite") == 0
    saida = capsys.readouterr().out
    assert "AVISO" in saida and "404" in saida
    # O arquivo e gravado mesmo vazio, para o passo seguinte do pipeline nao quebrar.
    assert json.loads(destino.read_text(encoding="utf-8")) == []


def test_bug_de_programa_nao_e_engolido(tmp_path):
    """Por que este teste existe: o `except EntradaInvalida` nao pode virar um
    `except Exception` com o tempo. Se virar, um bug nosso passaria a ser mostrado ao
    usuario como se fosse erro de dado dele, e nos perderiamos o traceback."""
    import pytest
    from src.main import main
    # None nao tem o metodo exists(), entao a chamada levanta AttributeError - que e
    # um bug de programa e precisa vazar como traceback normal.
    with pytest.raises(AttributeError):
        main(None, usar_padrao=False)
