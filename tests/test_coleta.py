"""Testes da orquestracao da coleta.

Por que o buscador e injetado: coleta que so roda com internet ligada nao e testada, e
bater no site de verdade a cada execucao da suite seria abusivo com a fonte. Passando
uma funcao de busca falsa, os testes exercitam paginacao, deduplicacao e parada sem
nenhuma requisicao.
"""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def pagina_real():
    """Devolve o HTML da fixture com tres vagas reais do BNE."""
    return (FIXTURES / "bne_pagina.html").read_text(encoding="utf-8")


def pagina_vazia():
    """Devolve o HTML de uma pagina valida sem nenhuma vaga.

    Por que esta fixture existe separada da pagina sem o bloco: sao dois cenarios
    diferentes que nao podem ser confundidos. Pagina COM o bloco e lista vazia significa
    "acabaram os resultados" e encerra a paginacao em silencio. Pagina SEM o bloco
    significa "o site mudou de formato" e tem que falhar alto.
    """
    return (FIXTURES / "bne_vazia.html").read_text(encoding="utf-8")


def buscador_fixo(html_por_url):
    """Constroi um buscador falso que devolve HTML conforme a URL pedida.

    Por que esta funcao existe: cada teste precisa de um comportamento de rede
    diferente - uma pagina, duas paginas, pagina repetida - e escrever uma funcao nova
    em cada teste esconderia o cenario sendo testado.

    Entrada -> um dicionario de URL para HTML.
    Fase 1  -> guarda as URLs pedidas, para o teste poder conferir a paginacao.
    Saida   -> a funcao buscadora e a lista de URLs visitadas.
    """
    visitadas = []

    def busca(url):
        # Registra a visita antes de responder, para o teste ver a ordem das paginas.
        visitadas.append(url)
        # URL nao prevista devolve pagina valida e vazia - que e como o site responde
        # quando os resultados acabam, e nao uma pagina quebrada.
        return html_por_url.get(url, pagina_vazia())

    return busca, visitadas


def test_coleta_uma_pagina_e_devolve_vagas_mapeadas():
    """Por que este teste existe: e o caminho ponta a ponta da subfase S1 - da pagina
    bruta ate a vaga no formato do projeto."""
    from src.coleta import coletar_fonte
    url = "https://www.bne.com.br/vagas-de-emprego-para-dentista"
    busca, _ = buscador_fixo({url: pagina_real()})
    vagas = coletar_fonte("bne", "dentista", paginas=1, buscador=busca)
    # As tres vagas da fixture, ja traduzidas para o formato do projeto.
    assert len(vagas) == 3
    assert {v["fonte"] for v in vagas} == {"bne"}
    assert {v["uf"] for v in vagas} == {"MS", "RJ", "SP"}


def test_visita_a_segunda_pagina_com_o_parametro_certo():
    """Por que este teste existe: das tres formas de paginacao testadas na sondagem, so
    `?page=N` trouxe vagas ineditas. Usar a errada devolveria a primeira pagina de novo
    e a coleta pararia achando que acabou."""
    from src.coleta import coletar_fonte
    base = "https://www.bne.com.br/vagas-de-emprego-para-dentista"
    busca, visitadas = buscador_fixo({base: pagina_real()})
    coletar_fonte("bne", "dentista", paginas=2, buscador=busca)
    # A primeira pagina vem sem parametro; a segunda usa page=2.
    assert visitadas[0] == base
    assert visitadas[1] == base + "?page=2"


def test_vaga_repetida_entre_paginas_nao_duplica():
    """Por que este teste existe: paginas de busca costumam repetir item na virada. Sem
    deduplicacao por identificador de origem, a mesma vaga entraria duas vezes e a
    contagem por cidade mentiria."""
    from src.coleta import coletar_fonte
    base = "https://www.bne.com.br/vagas-de-emprego-para-dentista"
    # As duas paginas devolvem exatamente o mesmo conteudo.
    busca, _ = buscador_fixo({base: pagina_real(), base + "?page=2": pagina_real()})
    vagas = coletar_fonte("bne", "dentista", paginas=2, buscador=busca)
    # Continuam sendo tres, e nao seis.
    assert len(vagas) == 3


def test_para_de_paginar_quando_a_pagina_nao_traz_nada_novo():
    """Por que este teste existe: pedir dez paginas de uma busca que so tem duas faria
    oito requisicoes inuteis ao site de terceiro. Parar cedo e questao de nao abusar da
    fonte."""
    from src.coleta import coletar_fonte
    base = "https://www.bne.com.br/vagas-de-emprego-para-dentista"
    busca, visitadas = buscador_fixo({base: pagina_real(), base + "?page=2": pagina_real()})
    coletar_fonte("bne", "dentista", paginas=10, buscador=busca)
    # Visitou a 1 e a 2; ao ver que a 2 nao trouxe nada inedito, parou.
    assert len(visitadas) == 2


def test_resultado_sai_em_ordem_deterministica():
    """Por que este teste existe: determinismo e regra do projeto, e a S2 vai exigir
    HTML identico byte a byte. Ordem instavel aqui inviabilizaria aquele teste."""
    from src.coleta import coletar_fonte
    url = "https://www.bne.com.br/vagas-de-emprego-para-dentista"
    busca, _ = buscador_fixo({url: pagina_real()})
    primeira = coletar_fonte("bne", "dentista", paginas=1, buscador=busca)
    segunda = coletar_fonte("bne", "dentista", paginas=1, buscador=busca)
    # Duas coletas da mesma entrada produzem a mesma lista, na mesma ordem.
    assert primeira == segunda
    # E a ordem e a do identificador de origem, nao a que a fonte devolveu.
    assert [v["id_na_fonte"] for v in primeira] == sorted(v["id_na_fonte"] for v in primeira)


def test_pagina_valida_e_vazia_encerra_a_paginacao_sem_erro():
    """Por que este teste existe: pagina vazia e fim de resultado, nao defeito. Se o
    coletor tratasse os dois casos igual, ou toda busca curta viraria erro, ou site
    mudado passaria despercebido. Este teste trava a distincao."""
    from src.coleta import coletar_fonte
    base = "https://www.bne.com.br/vagas-de-emprego-para-dentista"
    # A pagina 1 tem vagas; a 2 volta valida e vazia, como o site responde no fim.
    busca, visitadas = buscador_fixo({base: pagina_real(), base + "?page=2": pagina_vazia()})
    vagas = coletar_fonte("bne", "dentista", paginas=5, buscador=busca)
    # As tres vagas da pagina 1 continuam la, sem excecao nenhuma.
    assert len(vagas) == 3
    # E a paginacao parou na 2, sem tentar a 3.
    assert len(visitadas) == 2


def test_pagina_sem_o_bloco_interrompe_a_coleta_com_erro():
    """Por que este teste existe: e o contraponto do teste anterior. Se o BNE mudar o
    layout, a coleta nao pode terminar em silencio como se nao houvesse vaga - o feed
    ficaria vazio e ninguem saberia por que."""
    from src.coleta import coletar_fonte
    from src.erros import EstruturaInesperada
    base = "https://www.bne.com.br/vagas-de-emprego-para-dentista"
    quebrada = (FIXTURES / "bne_sem_bloco.html").read_text(encoding="utf-8")
    busca, _ = buscador_fixo({base: quebrada})
    with pytest.raises(EstruturaInesperada):
        coletar_fonte("bne", "dentista", paginas=1, buscador=busca)


def test_a_vaga_guarda_de_qual_perfil_veio():
    """Por que este teste existe: hoje ha um perfil so, e o campo parece constante. Mas a
    decisao registrada em 16/08/2026 e explicita - os perfis dele voltam em dias ou meses,
    e nada da maquina de multiplos perfis deve ser simplificado.

    Guardar o perfil agora custa uma coluna; descobrir depois que o acervo inteiro nao
    sabe de onde veio custaria uma remigracao."""
    from src.coleta import coletar_fonte
    url = "https://www.bne.com.br/vagas-de-emprego-para-dentista"
    busca, _ = buscador_fixo({url: pagina_real()})
    vagas = coletar_fonte("bne", "dentista", paginas=1, buscador=busca, perfil="odonto")
    assert {v["perfil"] for v in vagas} == {"odonto"}


def test_sem_perfil_informado_a_vaga_fica_sem_perfil():
    """Por que este teste existe: o parametro e opcional para nao quebrar quem chama sem
    ele. Mas o campo tem que existir mesmo assim, senao o resto do pipeline precisaria
    checar a presenca da chave em todo lugar."""
    from src.coleta import coletar_fonte
    url = "https://www.bne.com.br/vagas-de-emprego-para-dentista"
    busca, _ = buscador_fixo({url: pagina_real()})
    assert coletar_fonte("bne", "dentista", paginas=1, buscador=busca)[0]["perfil"] is None


def test_fonte_desconhecida_e_recusada():
    """Por que este teste existe: `fontes_ativas` e escrita a mao no config. Um erro de
    digitacao ali faria a fonte ser ignorada em silencio, e o usuario acharia que ela
    simplesmente nao tinha vagas."""
    from src.coleta import coletar_fonte
    from src.erros import EntradaInvalida
    busca, _ = buscador_fixo({})
    with pytest.raises(EntradaInvalida) as erro:
        coletar_fonte("cathoo", "dentista", paginas=1, buscador=busca)
    # A mensagem cita o nome errado e as fontes que existem.
    assert "cathoo" in str(erro.value)
    assert "bne" in str(erro.value)
