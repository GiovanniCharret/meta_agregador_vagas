"""Testes do coletor da fonte BNE.

Por que estes testes usam fixture e nao rede: coletor que so pode ser testado com a
internet ligada nao e testado. A fixture foi gerada a partir de tres vagas reais do
BNE, reduzidas aos campos que o coletor usa e reembrulhadas no mesmo formato da pagina
- entao o formato veio da fonte de verdade, nao de uma invencao nossa.
"""

from pathlib import Path

import pytest

# Os arquivos de apoio ficam ao lado deste arquivo de teste.
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def html_da_pagina():
    """Le a fixture da pagina de resultados do BNE.

    Por que esta funcao existe: quase todo teste precisa do mesmo HTML, e repetir a
    leitura em cada um esconderia o que o teste esta de fato verificando.

    Entrada -> nada.
    Fase 1  -> monta o caminho da fixture ao lado dos testes.
    Saida   -> o conteudo do arquivo como texto.
    """
    # UTF-8 explicito porque os nomes de cidade tem acento.
    return (FIXTURES / "bne_pagina.html").read_text(encoding="utf-8")


def test_extrai_todas_as_vagas_da_pagina():
    """Por que este teste existe: o BNE guarda a lista inteira de vagas num input
    escondido, em JSON escapado. Se a extracao pegar so a primeira, ou nenhuma, a
    coleta perde vaga em silencio."""
    from src.fontes.bne import extrai_vagas
    registros = extrai_vagas(html_da_pagina())
    # A fixture tem exatamente tres vagas, uma de cada estado.
    assert len(registros) == 3


def test_extracao_preserva_acento_da_cidade():
    """Por que este teste existe: o JSON vem escapado dentro de um atributo HTML, e o
    console do Windows e cp1252. Se o desescape falhar, "Anastacio" chega quebrado e a
    cidade deixa de casar com a lista de cidades bloqueadas."""
    from src.fontes.bne import extrai_vagas
    registros = extrai_vagas(html_da_pagina())
    cidades = [(r.get("City") or {}).get("Name") for r in registros]
    assert "Anastácio" in cidades


def test_termo_inexistente_na_fonte_nao_e_confundido_com_mudanca_de_formato():
    """Por que este teste existe: o BNE responde 200 e serve a PAGINA INICIAL quando o
    slug de funcao nao existe na taxonomia dele - um soft 404. Aconteceu de verdade na
    primeira execucao real, em 16/08/2026: 'cirurgiao-dentista' e
    'administrador-financeiro' nao existem la, embora 'dentista' e 'analista-financeiro'
    existam.

    Tratar isso como mudanca de formato produz tres avisos gritando que o site mudou
    quando ele nao mudou nada. Alarme falso destroi a confianca no aviso - no dia em que
    o formato mudar de verdade, ninguem vai olhar."""
    from src.fontes.bne import extrai_vagas
    from src.erros import FonteIndisponivel
    html = (FIXTURES / "bne_termo_inexistente.html").read_text(encoding="utf-8")
    with pytest.raises(FonteIndisponivel) as erro:
        extrai_vagas(html, url="https://www.bne.com.br/vagas-de-emprego-para-x")
    mensagem = str(erro.value)
    # A mensagem tem que ensinar o que fazer: o termo e que precisa mudar.
    assert "termo" in mensagem.lower()


def test_pagina_sem_o_bloco_esperado_levanta_erro():
    """Por que este teste existe: se o BNE mudar o layout, a extracao passaria a
    devolver zero vagas. Zero vaga e indistinguivel de 'nao ha vaga hoje', e o feed
    ficaria vazio sem ninguem entender por que - limitacao silenciosa."""
    from src.fontes.bne import extrai_vagas
    from src.erros import EstruturaInesperada
    html = (FIXTURES / "bne_sem_bloco.html").read_text(encoding="utf-8")
    with pytest.raises(EstruturaInesperada) as erro:
        extrai_vagas(html)
    # A mensagem tem que dizer qual fonte mudou, para o diagnostico ser direto.
    assert "bne" in str(erro.value).lower()


def registro_por_id(identificador):
    """Devolve o registro cru da fixture com o Id pedido."""
    from src.fontes.bne import extrai_vagas
    # Percorre os registros procurando o identificador exato.
    for registro in extrai_vagas(html_da_pagina()):
        if registro.get("Id") == identificador:
            return registro
    # Falhar aqui significa que a fixture mudou, e o teste precisa saber.
    raise AssertionError("Id {} nao esta na fixture".format(identificador))


def test_mapeia_os_campos_essenciais_da_vaga():
    """Por que este teste existe: e o contrato entre a fonte e o resto do pipeline. Se
    um campo mudar de nome aqui, normalizacao, dedupe e feed quebram juntos."""
    from src.fontes.bne import para_vaga
    vaga = para_vaga(registro_por_id(6079614))
    assert vaga["fonte"] == "bne"
    assert vaga["id_na_fonte"] == "6079614"
    assert vaga["empresa_bruta"] == "Prefeitura de Anastácio"
    assert vaga["cidade"] == "Anastácio"
    assert vaga["titulo_bruto"] == "dentista"
    assert vaga["url"].startswith("https://www.bne.com.br/")


def test_uf_vem_do_topo_do_registro_e_nao_de_dentro_de_city():
    """Por que este teste existe: o BNE tem DOIS campos de UF. O que fica dentro de
    City vem nulo em 100% das vagas medidas; o do topo vem preenchido em 100%. Ler o
    errado faria o filtro de estado reprovar o Brasil inteiro."""
    from src.fontes.bne import para_vaga
    bruto = registro_por_id(6079614)
    # Confirma a premissa: o campo de dentro de City e mesmo inutil.
    assert (bruto.get("City") or {}).get("StateAbbreviation") is None
    # E o mapeamento usa o do topo, que tem valor.
    assert para_vaga(bruto)["uf"] == "MS"


def test_cada_vaga_da_fixture_tem_uf_de_um_estado_diferente():
    """Por que este teste existe: a fixture foi montada de proposito com tres estados
    para que o mapeamento nao passe por coincidencia de todas serem iguais."""
    from src.fontes.bne import extrai_vagas, para_vaga
    ufs = {para_vaga(r)["uf"] for r in extrai_vagas(html_da_pagina())}
    assert ufs == {"MS", "RJ", "SP"}


def test_home_office_falso_vira_modalidade_presencial():
    """Por que este teste existe: modalidade alimenta a decisao 2 da triagem, em que
    remoto e categoria separada e nao coringa. Errar o mapeamento faria vaga presencial
    ser tratada como remota e vice-versa."""
    from src.fontes.bne import para_vaga
    bruto = registro_por_id(6079618)
    # Confirma a premissa do dado antes de afirmar sobre o mapeamento.
    assert bruto.get("Home_Office") is False
    assert para_vaga(bruto)["modalidade"] == "presencial"


def test_home_office_verdadeiro_vira_modalidade_remoto():
    """Por que este teste existe: a fixture so tem vagas presenciais, entao o caminho
    do remoto precisa ser exercitado com um registro montado - senao ele nunca roda."""
    from src.fontes.bne import para_vaga
    bruto = dict(registro_por_id(6079618))
    # Altera so a modalidade, mantendo o resto do registro real.
    bruto["Home_Office"] = True
    assert para_vaga(bruto)["modalidade"] == "remoto"


def test_salario_zerado_vira_nao_informado():
    """Por que este teste existe: o BNE manda 0.0 quando a empresa nao informou
    salario. Deixar passar como zero faria o feed anunciar vagas de R$ 0,00, que e pior
    do que nao mostrar nada."""
    from src.fontes.bne import para_vaga
    bruto = registro_por_id(6080201)
    # Confirma a premissa: os dois campos vem zerados na fonte.
    assert bruto.get("MinSalary") == 0.0 and bruto.get("MaxSalary") == 0.0
    assert para_vaga(bruto)["salario_texto"] is None


def test_data_de_publicacao_vira_data_simples():
    """Por que este teste existe: o BNE manda timestamp com fuso e milissegundo. O feed
    mostra data, e guardar o resto so criaria diferenca falsa entre duas coletas da
    mesma vaga."""
    from src.fontes.bne import para_vaga
    vaga = para_vaga(registro_por_id(6079614))
    # Apenas a parte de data, no formato ISO.
    assert vaga["data_publicacao"] == "2026-07-09"


def test_mapeamento_nao_carimba_horario_de_coleta():
    """Por que este teste existe: determinismo e regra do projeto. Se o mapeamento
    carimbasse a hora, duas execucoes da mesma entrada produziriam saidas diferentes e
    o teste de HTML identico byte a byte da S2 se tornaria impossivel."""
    from src.fontes.bne import para_vaga
    bruto = registro_por_id(6079614)
    # Mapear duas vezes o mesmo registro tem que dar exatamente o mesmo resultado.
    assert para_vaga(bruto) == para_vaga(bruto)
    # E nenhum campo pode se chamar algo como capturado_em nesta camada.
    assert "capturado_em" not in para_vaga(bruto)
