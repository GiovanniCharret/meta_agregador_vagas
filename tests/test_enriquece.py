"""Testes de src/enriquece.py - a leitura da pagina de detalhe da vaga.

Por que esta subfase existe: a listagem do BNE nao traz descricao nem salario real - ela
manda 0.0 em 100% das vagas. A pagina de detalhe traz os dois, em JSON-LD JobPosting, que
e o padrao schema.org publicado para o Google Empregos. E ali que mora a especialidade
("dentista especialista em ortodontia"), que e o que discrimina duas vagas da mesma
clinica e o que faltava para a chave canonica da S4.

As fixtures vieram de paginas reais, reduzidas ao bloco JSON-LD que o codigo le.
"""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def html(nome):
    """Le uma fixture de pagina de detalhe."""
    return (FIXTURES / nome).read_text(encoding="utf-8")


def test_extrai_a_descricao_sem_marcacao_html():
    """Por que este teste existe: o campo `description` vem com HTML dentro. Se a
    marcacao chegasse crua ao card, o feed mostraria `<p>` na tela ou, pior, injetaria
    marcacao vinda de terceiro."""
    from src.enriquece import extrai_detalhe
    dados = extrai_detalhe(html("bne_detalhe.html"))
    assert "<p>" not in dados["descricao"]
    assert "secretaria municipal de saúde de anastácio" in dados["descricao"].lower()


def test_descricao_tem_quebras_normalizadas():
    """Por que este teste existe: a fonte manda `\\n` no meio do texto. Sem normalizar, o
    mesmo texto com espacamento diferente geraria hashes diferentes - e a chave canonica
    da S4 passaria a separar vagas identicas."""
    from src.enriquece import extrai_detalhe
    dados = extrai_detalhe(html("bne_detalhe.html"))
    assert "\n" not in dados["descricao"]
    assert "  " not in dados["descricao"]


def test_subtitulo_usa_responsabilidades_quando_existem():
    """Por que este teste existe: `responsibilities` e o campo mais especifico da fonte -
    e nele que aparece a especialidade. Quando existe, e ele que deve virar o subtitulo
    do card."""
    from src.enriquece import extrai_detalhe
    dados = extrai_detalhe(html("bne_detalhe_com_responsabilidades.html"))
    assert "ortodontia" in dados["subtitulo"].lower()


def test_subtitulo_descarta_o_boilerplate_do_template():
    """Por que este teste existe: o texto da fonte termina com um rabo de template -
    "o link para Site da empresa: (Informacao Confidencial)." - que aparece em toda vaga
    e nao informa nada. No subtitulo, ele ocuparia o espaco util do card; na chave
    canonica, seria ruido igual em todas."""
    from src.enriquece import extrai_detalhe
    dados = extrai_detalhe(html("bne_detalhe_com_responsabilidades.html"))
    assert "Informação Confidencial" not in dados["subtitulo"]
    assert "Site da empresa" not in dados["subtitulo"]
    # E o conteudo util sobrevive ao corte.
    assert "ortodontia" in dados["subtitulo"].lower()


def test_subtitulo_cai_para_a_descricao_quando_nao_ha_responsabilidades():
    """Por que este teste existe: `responsibilities` vem NULO em parte das vagas - foi
    medido na sondagem. Sem fallback, esses cards ficariam sem subtitulo justamente
    quando o titulo generico do BNE ja nao diz nada."""
    from src.enriquece import extrai_detalhe
    bruto = extrai_detalhe(html("bne_detalhe.html"))
    # A fixture tem responsibilities nulo, entao o subtitulo tem que vir da descricao.
    assert bruto["subtitulo"]
    assert "dentista" in bruto["subtitulo"].lower()


def test_subtitulo_nao_fica_longo_demais_para_um_card():
    """Por que este teste existe: descricao inteira como subtitulo transformaria o card
    num paragrafo e destruiria a leitura do feed. O texto completo continua guardado em
    `descricao`."""
    from src.enriquece import extrai_detalhe
    dados = extrai_detalhe(html("bne_detalhe.html"))
    assert len(dados["subtitulo"]) <= 200


def test_faixa_de_preenchimento_padrao_e_descartada():
    """Por que este teste existe: medicao real de 16/08/2026 - de 165 vagas enriquecidas,
    **163 traziam exatamente a mesma faixa, R$ 1.000 a R$ 15.000**. Nao e salario, e o
    valor que o formulario do BNE grava quando o anunciante nao informa nada.

    Mostrar isso no card seria pior do que nao mostrar salario nenhum, porque parece
    informacao e nao e. Pior ainda: entraria na comparacao de vagas como se distinguisse
    alguma coisa, quando na verdade e igual em 99% delas.

    A fixture veio justamente de uma vaga com essa faixa."""
    from src.enriquece import extrai_detalhe
    dados = extrai_detalhe(html("bne_detalhe.html"))
    assert dados["salario_texto"] is None


def test_salario_de_verdade_sobrevive_e_sai_em_formato_brasileiro():
    """Por que este teste existe: o descarte do preenchimento padrao nao pode levar junto
    o salario real das poucas vagas que informam - foram 2 em 165, e sao justamente as
    mais informativas do acervo. O formato e BR: ponto no milhar, virgula no decimal."""
    from src.enriquece import extrai_detalhe
    import json
    # Monta uma pagina com faixa diferente da padrao, mantendo o resto do formato real.
    bruto = html("bne_detalhe.html")
    pagina = bruto.replace('"minValue": 1000.0', '"minValue": 2000.0').replace(
        '"maxValue": 15000.0', '"maxValue": 5000.0')
    dados = extrai_detalhe(pagina)
    assert dados["salario_texto"] == "R$ 2.000,00 a R$ 5.000,00 por mes"


def test_pagina_sem_dado_estruturado_devolve_nada_em_vez_de_estourar():
    """Por que este teste existe: uma pagina de detalhe fora do padrao nao pode derrubar
    a rodada inteira. O plano da subfase dizia isso com todas as letras - vira aviso,
    nao falha."""
    from src.enriquece import extrai_detalhe
    assert extrai_detalhe(html("bne_detalhe_sem_jsonld.html")) is None


def test_extracao_e_deterministica():
    """Por que este teste existe: a descricao vai alimentar o hash da chave canonica da
    S4. Se a extracao variasse entre chamadas, a mesma vaga mudaria de chave sozinha."""
    from src.enriquece import extrai_detalhe
    pagina = html("bne_detalhe_com_responsabilidades.html")
    assert extrai_detalhe(pagina) == extrai_detalhe(pagina)


def test_traz_o_tipo_de_vinculo_quando_informado():
    """Por que este teste existe: `employmentType` separa efetivo de temporario, e a
    triagem ja mostrou que ruido de vinculo - franquia, comissionado - e um problema
    estrutural em odontologia. Guardar agora custa nada e alimenta o filtro 3.6."""
    from src.enriquece import extrai_detalhe
    dados = extrai_detalhe(html("bne_detalhe.html"))
    assert dados["tipo_vinculo"] == "FULL_TIME"
