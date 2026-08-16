"""Testes de src/feed.py - a montagem da pagina de saida."""

import pytest


def vaga(**mudancas):
    """Devolve uma vaga no formato do projeto, com os campos que o teste quiser mudar.

    Por que esta funcao existe: quase todo teste precisa de uma vaga valida com um
    campo diferente. Montar o dicionario inteiro em cada teste esconderia qual campo
    esta em jogo.

    Entrada -> os campos a sobrescrever.
    Fase 1  -> parte de uma vaga completa e plausivel.
    Fase 2  -> aplica as mudancas pedidas.
    Saida   -> o dicionario resultante.
    """
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


def test_pagina_mostra_os_campos_da_vaga():
    """Por que este teste existe: e o minimo que o feed precisa entregar - se um campo
    sumir da pagina, o card deixa de ser util para decidir se vale candidatar."""
    from src.feed import montar_feed
    html = montar_feed([vaga()])
    for esperado in ("dentista", "Clinica Sorriso", "Florianopolis", "SC",
                     "https://www.bne.com.br/vaga/1000"):
        assert esperado in html
    # A modalidade aparece com o rotulo que o humano le, e nao com o valor interno -
    # "Presencial" e nao "presencial". O card e tela, nao dump de dado.
    assert "Presencial" in html


def test_modalidade_remota_recebe_rotulo_e_destaque_proprios():
    """Por que este teste existe: remoto e categoria separada por decisao da pergunta 2
    da triagem, e nao um valor qualquer de modalidade. Se ele se parecer com presencial
    na tela, a distincao que voce pediu deixa de existir para quem le."""
    from src.feed import montar_feed
    html = montar_feed([vaga(modalidade="remoto")])
    assert "Remoto" in html
    # A classe propria e o que permite o CSS destacar remoto dos demais.
    assert "selo remoto" in html


def test_subtitulo_aparece_sob_o_titulo():
    """Por que este teste existe: e a razao de ser da S3b. O titulo do BNE e generico -
    "dentista" para todas - e o subtitulo e o que devolve informacao ao card. Se ele
    ficasse so no banco, a subfase inteira teria sido requisicao gasta a toa."""
    from src.feed import montar_feed
    html = montar_feed([vaga(subtitulo="Vaga para dentista especialista em ortodontia")])
    assert "especialista em ortodontia" in html


def test_subtitulo_ausente_nao_deixa_marcacao_vazia():
    """Por que este teste existe: vaga ainda nao enriquecida nao tem subtitulo. Um
    elemento vazio no HTML abriria um buraco no card sem motivo."""
    from src.feed import montar_feed
    html = montar_feed([vaga(subtitulo=None)])
    assert 'class="subtitulo"' not in html


def test_subtitulo_tambem_e_escapado():
    """Por que este teste existe: o subtitulo vem da descricao escrita pelo anunciante -
    e texto de terceiro como qualquer outro."""
    from src.feed import montar_feed
    html = montar_feed([vaga(subtitulo="atende <script>alert(1)</script>")])
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_texto_da_fonte_e_escapado():
    """Por que este teste existe: nome de empresa vem de terceiro e pode conter `&` ou
    `<`. Sem escape, o HTML quebra na melhor hipotese e injeta marcacao na pior."""
    from src.feed import montar_feed
    html = montar_feed([vaga(empresa_bruta="Silva & Cia <Odonto>")])
    # O texto aparece escapado, e nao como marcacao crua.
    assert "Silva &amp; Cia &lt;Odonto&gt;" in html
    assert "<Odonto>" not in html


def test_vaga_mais_recente_aparece_primeiro():
    """Por que este teste existe: o feed e cronologico por decisao da triagem. Ordem
    errada faz vaga velha ocupar o topo e a nova passar batido."""
    from src.feed import montar_feed
    antiga = vaga(id_na_fonte="1", data_publicacao="2026-01-01", titulo_bruto="vaga-antiga")
    nova = vaga(id_na_fonte="2", data_publicacao="2026-08-01", titulo_bruto="vaga-nova")
    html = montar_feed([antiga, nova])
    assert html.index("vaga-nova") < html.index("vaga-antiga")


def test_cidade_desejada_sobe_ao_topo_mesmo_com_vaga_mais_velha():
    """Por que este teste existe: a decisao 3.2 diz que cidade desejada sobe ao topo.
    Se a data vencesse a preferencia, a lista de cidades desejadas nao teria efeito
    nenhum - seria uma funcionalidade que existe no config e nao no produto."""
    from src.feed import montar_feed
    recente = vaga(id_na_fonte="1", cidade="Sao Paulo", data_publicacao="2026-08-01",
                   titulo_bruto="vaga-recente-sp")
    desejada = vaga(id_na_fonte="2", cidade="Curitiba", data_publicacao="2026-01-01",
                    titulo_bruto="vaga-velha-curitiba")
    html = montar_feed([recente, desejada], cidades_desejadas=["Curitiba"])
    assert html.index("vaga-velha-curitiba") < html.index("vaga-recente-sp")


def test_vaga_sem_data_nao_derruba_a_ordenacao():
    """Por que este teste existe: nem toda fonte informa data. Se a ordenacao estourar
    com None, uma vaga incompleta derrubaria a pagina inteira."""
    from src.feed import montar_feed
    html = montar_feed([vaga(id_na_fonte="1", data_publicacao=None, titulo_bruto="sem-data"),
                        vaga(id_na_fonte="2", titulo_bruto="com-data")])
    # As duas aparecem; a sem data vai para o fim, por ser a menos confiavel.
    assert "sem-data" in html and "com-data" in html
    assert html.index("com-data") < html.index("sem-data")


def test_mesma_entrada_gera_bytes_identicos():
    """Por que este teste existe: e a exigencia de determinismo do D8, escrita como
    teste. Duas execucoes com a mesma entrada tem que produzir a mesma pagina - senao
    nao da para saber se algo mudou porque o mercado mudou ou porque o programa varia."""
    from src.feed import montar_feed
    entrada = [vaga(id_na_fonte="1"), vaga(id_na_fonte="2", cidade="Recife", uf="PE")]
    assert montar_feed(entrada).encode("utf-8") == montar_feed(entrada).encode("utf-8")


def test_pagina_nao_carimba_horario_por_padrao():
    """Por que este teste existe: horario de geracao dentro do HTML quebraria o teste
    acima em silencio - ele passaria por acaso quando as duas chamadas caissem no mesmo
    segundo, e falharia de forma intermitente depois. Melhor o horario nunca entrar
    sozinho: quem quiser mostrar tem que passar."""
    from src.feed import montar_feed
    import re
    html = montar_feed([vaga()])
    # Nenhuma data no formato de carimbo de geracao pode aparecer sem ser pedida.
    assert not re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", html)


def test_horario_aparece_quando_informado():
    """Por que este teste existe: o carimbo e util para quem le - so nao pode ser
    automatico. Este teste garante que a saida existe quando pedida."""
    from src.feed import montar_feed
    html = montar_feed([vaga()], gerado_em="16/08/2026 21:30")
    assert "16/08/2026 21:30" in html


def test_pagina_vazia_explica_em_vez_de_ficar_em_branco():
    """Por que este teste existe: pagina em branco e indistinguivel de programa
    quebrado. A regra do projeto e que limitacao nunca seja silenciosa - e isso vale
    tambem para a tela."""
    from src.feed import montar_feed
    html = montar_feed([])
    assert "nenhuma vaga" in html.lower()


def test_contagem_de_vagas_aparece_no_topo():
    """Por que este teste existe: com centenas de vagas, o numero e a primeira coisa
    que diz se a coleta funcionou. Sem ele, so contando card na mao."""
    from src.feed import montar_feed
    html = montar_feed([vaga(id_na_fonte=str(n)) for n in range(3)])
    assert "3" in html


def test_saida_e_html_valido_o_bastante_para_abrir():
    """Por que este teste existe: e o contrato minimo do arquivo. Sem doctype e sem
    charset, o navegador adivinha a codificacao e os acentos quebram no Windows."""
    from src.feed import montar_feed
    html = montar_feed([vaga(cidade="Anastácio")])
    assert html.startswith("<!doctype html>")
    assert 'charset="utf-8"' in html
    assert html.rstrip().endswith("</html>")
    # O acento chega inteiro na pagina.
    assert "Anastácio" in html
