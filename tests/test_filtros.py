"""Testes de src/filtros.py - o que nao chega ao feed, e por que.

Os dois filtros vem de decisoes diferentes da triagem:
  3.2 - geografico, com lista BRANCA de estados e lista NEGRA de cidades;
  3.6 - palavras que reprovam a vaga na hora.
"""


def vaga(**mudancas):
    """Devolve uma vaga no formato do projeto."""
    base = {
        "titulo_bruto": "dentista",
        "empresa_bruta": "Clinica Sorriso",
        "cidade": "Florianopolis",
        "uf": "SC",
        "subtitulo": "clinico geral",
        "descricao": "contrata dentista para atendimento adulto",
    }
    base.update(mudancas)
    return base


def test_estado_fora_da_lista_branca_nao_passa():
    """Por que este teste existe: e a decisao 3.2. A lista de estados e o filtro mais
    importante para ela - vaga em estado onde ela nao moraria vale zero, por melhor que
    seja."""
    from src.filtros import passa_no_geografico
    assert not passa_no_geografico(vaga(uf="AC"), ["SC", "PR"], [])


def test_estado_na_lista_branca_passa():
    """Por que este teste existe: o outro lado do anterior - a lista nao pode reprovar
    quem deveria passar."""
    from src.filtros import passa_no_geografico
    assert passa_no_geografico(vaga(uf="SC"), ["SC", "PR"], [])


def test_comparacao_de_estado_ignora_caixa():
    """Por que este teste existe: a configuracao normaliza para maiuscula na leitura, mas
    a fonte pode mandar minuscula. Se as duas nao casassem, o estado inteiro sumiria do
    feed em silencio - o pior tipo de falha."""
    from src.filtros import passa_no_geografico
    assert passa_no_geografico(vaga(uf="sc"), ["SC"], [])


def test_cidade_bloqueada_nao_passa_mesmo_com_estado_liberado():
    """Por que este teste existe: as duas listas trabalham juntas. Bloquear a capital sem
    bloquear o estado inteiro e justamente o caso que a lista negra de cidades resolve."""
    from src.filtros import passa_no_geografico
    assert not passa_no_geografico(
        vaga(cidade="Florianopolis", uf="SC"), ["SC"], ["Florianopolis"])


def test_comparacao_de_cidade_ignora_acento_e_caixa():
    """Por que este teste existe: a lista e escrita a mao e a fonte manda acento como
    quiser. "Anastacio" e "Anastácio" tem que ser a mesma cidade, senao o bloqueio nao
    pega e a vaga aparece assim mesmo."""
    from src.filtros import passa_no_geografico
    assert not passa_no_geografico(
        vaga(cidade="Anastácio", uf="MS"), ["MS"], ["anastacio"])


def test_lista_branca_vazia_desliga_o_filtro_de_estado():
    """Por que este teste existe: precisa haver uma resposta explicita para lista vazia,
    e as duas possiveis sao ruins de jeitos diferentes. Vazia significando "nenhum estado
    passa" esvaziaria o feed inteiro; significando "todos passam" nao filtra nada.

    Escolhi "todos passam" por um motivo concreto: a leitura da configuracao JA RECUSA
    lista vazia, com mensagem propria. Entao o unico jeito de chegar aqui com lista vazia
    e defeito no nosso codigo - e nesse caso e melhor o feed aparecer inteiro, que se
    percebe na hora, do que aparecer vazio, que parece "nao tem vaga hoje"."""
    from src.filtros import passa_no_geografico
    assert passa_no_geografico(vaga(uf="AC"), [], [])
    # E a lista negra de cidades continua valendo mesmo sem lista branca.
    assert not passa_no_geografico(vaga(cidade="Rio Branco", uf="AC"), [], ["Rio Branco"])


def test_vaga_sem_estado_nao_passa_quando_ha_lista_branca():
    """Por que este teste existe: vaga sem UF nao pode driblar a lista branca. Se
    passasse, bastaria a fonte omitir o estado para furar o filtro."""
    from src.filtros import passa_no_geografico
    assert not passa_no_geografico(vaga(uf=None), ["SC"], [])


def test_termo_de_reprovacao_no_texto_reprova():
    """Por que este teste existe: e a decisao 3.6. A pesquisa apontou o ruido de franquia
    e comissionamento como problema estrutural em odontologia."""
    from src.filtros import termo_que_reprova
    reprovada = vaga(descricao="vaga para socio em franquia odontologica")
    assert termo_que_reprova(reprovada, ["franquia"]) == "franquia"


def test_reprovacao_devolve_o_termo_para_a_mensagem_poder_explicar():
    """Por que este teste existe: esconder vaga sem dizer por que seria limitacao
    silenciosa. Devolver o termo permite explicar - e permite voce descobrir que um termo
    esta reprovando demais."""
    from src.filtros import termo_que_reprova
    assert termo_que_reprova(vaga(descricao="trabalho voluntario"), ["voluntario"]) \
        == "voluntario"


def test_vaga_limpa_nao_e_reprovada():
    """Por que este teste existe: o filtro so vale se deixar passar o que presta."""
    from src.filtros import termo_que_reprova
    assert termo_que_reprova(vaga(), ["franquia", "estagio"]) is None


def test_reprovacao_ignora_acento():
    """Por que este teste existe: a lista e escrita a mao, sem acento por convencao do
    projeto, e a fonte escreve com acento. Sem normalizar, "estágio" passaria batido."""
    from src.filtros import termo_que_reprova
    assert termo_que_reprova(vaga(descricao="vaga de estágio"), ["estagio"]) == "estagio"


def test_reprovacao_casa_palavra_inteira_e_nao_pedaco():
    """Por que este teste existe: MEDIDO no acervo real em 16/08/2026. O termo "mei"
    casava dentro de "meio dia" e reprovava 4 vagas boas por acidente.

    Busca por pedaco de palavra e uma armadilha classica: quanto mais curto o termo, mais
    dano ela causa. E o filtro que reprova errado e pior que filtro nenhum, porque some
    com a vaga sem deixar rastro."""
    from src.filtros import termo_que_reprova
    horario = vaga(descricao="atendimento das 08h00 ao meio dia")
    assert termo_que_reprova(horario, ["mei"]) is None
    # E continua pegando a palavra inteira.
    assert termo_que_reprova(vaga(descricao="contrato como MEI"), ["mei"]) == "mei"


def test_reprovacao_olha_titulo_subtitulo_e_descricao():
    """Por que este teste existe: o termo pode aparecer em qualquer um dos tres. Olhar so
    a descricao deixaria passar a vaga cujo TITULO ja diz "estagio"."""
    from src.filtros import termo_que_reprova
    assert termo_que_reprova(vaga(titulo_bruto="estagio em odontologia"), ["estagio"])
    assert termo_que_reprova(vaga(subtitulo="vaga de estagio"), ["estagio"])


def test_termo_com_mais_de_uma_palavra_funciona():
    """Por que este teste existe: metade da lista tem expressao, nao palavra - "seja um
    franqueado", "percentual de producao". Se so palavra unica funcionasse, essas
    entradas seriam decoracao no arquivo de configuracao."""
    from src.filtros import termo_que_reprova
    texto = vaga(descricao="remuneracao por percentual de producao")
    assert termo_que_reprova(texto, ["percentual de producao"]) == "percentual de producao"


def test_aplicar_separa_o_que_passa_do_que_nao_passa():
    """Por que este teste existe: o feed precisa das duas coisas ao mesmo tempo - a lista
    filtrada e a contagem do que sumiu. Fazer duas passadas separadas abriria espaco para
    as duas discordarem."""
    from src.filtros import aplicar
    entrada = [
        vaga(cidade="Florianopolis", uf="SC"),
        vaga(cidade="Rio Branco", uf="AC"),
        vaga(descricao="vaga para socio em franquia"),
    ]
    visiveis, resumo = aplicar(entrada, ["SC"], [], ["franquia"])
    assert len(visiveis) == 1
    assert resumo["fora_do_mapa"] == 1
    assert resumo["reprovadas"]["franquia"] == 1


def test_aplicar_conta_por_termo_para_voce_poder_calibrar():
    """Por que este teste existe: sem saber QUAL termo reprovou quanto, nao da para
    perceber que um deles esta pegando demais. Foi assim que descobrimos que "mei" casava
    dentro de "meio dia" - contando."""
    from src.filtros import aplicar
    entrada = [
        vaga(descricao="franquia odontologica"),
        vaga(descricao="outra franquia"),
        vaga(descricao="trabalho voluntario"),
    ]
    _, resumo = aplicar(entrada, ["SC"], [], ["franquia", "voluntario"])
    assert resumo["reprovadas"]["franquia"] == 2
    assert resumo["reprovadas"]["voluntario"] == 1


def test_aplicar_preserva_a_ordem_de_entrada():
    """Por que este teste existe: a ordenacao do feed acontece depois. Se o filtro
    embaralhasse, o determinismo do D8 morreria aqui, antes de a montagem comecar."""
    from src.filtros import aplicar
    entrada = [vaga(cidade="A", uf="SC"), vaga(cidade="B", uf="SC"),
               vaga(cidade="C", uf="SC")]
    visiveis, _ = aplicar(entrada, ["SC"], [], [])
    assert [v["cidade"] for v in visiveis] == ["A", "B", "C"]


def test_vaga_sem_texto_nenhum_nao_quebra():
    """Por que este teste existe: vaga ainda nao enriquecida tem so o titulo generico.
    O filtro precisa atravessar isso sem estourar."""
    from src.filtros import termo_que_reprova
    assert termo_que_reprova(
        {"titulo_bruto": None, "subtitulo": None, "descricao": None}, ["estagio"]) is None
