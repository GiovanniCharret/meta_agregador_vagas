"""Testes de src/normaliza.py."""


def test_slug_troca_espaco_por_hifen():
    """Por que este teste existe: o termo de busca entra no caminho da URL do BNE.
    Espaco cru quebraria o endereco e a coleta traria zero vaga."""
    from src.normaliza import para_slug
    assert para_slug("cientista de dados") == "cientista-de-dados"


def test_slug_remove_acento():
    """Por que este teste existe: 'cirurgiao-dentista' com til na URL vira escape
    percentual e deixa de casar com o caminho que a fonte publica."""
    from src.normaliza import para_slug
    assert para_slug("cirurgião-dentista") == "cirurgiao-dentista"


def test_slug_e_minusculo_e_sem_pontuacao():
    """Por que este teste existe: o usuario escreve o termo a mao, com maiuscula e
    pontuacao. Normalizar aqui evita URL diferente para o mesmo termo."""
    from src.normaliza import para_slug
    assert para_slug("Analista Financeiro (Pleno)") == "analista-financeiro-pleno"


def test_slug_nao_deixa_hifen_sobrando_nas_pontas():
    """Por que este teste existe: hifen no comeco ou no fim da URL costuma virar 404, e
    o erro seria dificil de enxergar - a coleta so viria vazia."""
    from src.normaliza import para_slug
    assert para_slug("  dentista!  ") == "dentista"


def test_slug_do_mesmo_termo_e_sempre_igual():
    """Por que este teste existe: determinismo e regra do projeto. Slug instavel faria
    a mesma busca gerar URLs diferentes entre execucoes."""
    from src.normaliza import para_slug
    assert para_slug("Cirurgião  Dentista") == para_slug("cirurgiao dentista")
