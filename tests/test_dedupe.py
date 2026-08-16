"""Testes de src/dedupe.py - a chave canonica que agrupa copias da mesma vaga.

O desenho da chave esta no DESIGN.md D3, e foi revisado duas vezes. A segunda revisao veio
de medicao, nao de teoria: a chave anterior, sem a descricao, fundia 88 das 269 vagas
reais em grupos errados - o pior deles juntava 8 vagas distintas num card so.
"""


def vaga(**mudancas):
    """Devolve uma vaga no formato do projeto."""
    base = {
        "fonte": "bne",
        "id_na_fonte": "1000",
        "titulo_bruto": "dentista",
        "empresa_bruta": "Clinica Sorriso",
        "cidade": "Florianopolis",
        "uf": "SC",
        "descricao": "atende ortodontia e endodontia",
    }
    base.update(mudancas)
    return base


def test_a_mesma_vaga_republicada_recebe_a_mesma_chave():
    """Por que este teste existe: e a razao de ser da deduplicacao. O anunciante
    republica a vaga e a fonte da um identificador novo; sem a chave, o feed mostraria a
    mesma vaga duas vezes. Medido no acervo real: 4 grupos de republicacao em 269 vagas."""
    from src.dedupe import chave_canonica
    # Mesma vaga, identificador diferente - exatamente o caso da republicacao.
    assert chave_canonica(vaga(id_na_fonte="1")) == chave_canonica(vaga(id_na_fonte="2"))


def test_pontuacao_e_acento_nao_mudam_a_chave():
    """Por que este teste existe: no acervo real, duas republicacoes da IVI Digital
    diferiam so por "Requisitos:" contra "Requisitos.". Sem normalizacao agressiva, um
    ponto final faria a vaga parecer nova."""
    from src.dedupe import chave_canonica
    a = vaga(descricao="Requisitos: experiência na área.")
    b = vaga(descricao="Requisitos. experiencia na area")
    assert chave_canonica(a) == chave_canonica(b)


def test_espacamento_diferente_nao_muda_a_chave():
    """Por que este teste existe: a fonte manda `\\n` no meio do texto e espacos duplos.
    Sem colapsar, a mesma vaga mudaria de chave conforme o espacamento."""
    from src.dedupe import chave_canonica
    assert chave_canonica(vaga(descricao="atende   ortodontia\ne endodontia")) == \
           chave_canonica(vaga(descricao="atende ortodontia e endodontia"))


def test_descricoes_diferentes_geram_chaves_diferentes():
    """Por que este teste existe: e o outro lado, e o mais importante. Duas vagas da
    mesma clinica, na mesma cidade, com o mesmo cargo generico, precisam continuar
    separadas quando o trabalho e outro - uma de ortodontia e outra de clinico geral."""
    from src.dedupe import chave_canonica
    orto = vaga(descricao="especialista em ortodontia")
    clinico = vaga(descricao="clinico geral para atendimento adulto")
    assert chave_canonica(orto) != chave_canonica(clinico)


def test_empresa_diferente_gera_chave_diferente():
    """Por que este teste existe: manter a empresa na chave foi decisao sua, contra a
    minha proposta de troca-la pelo subtitulo. Sem ela, duas clinicas diferentes da mesma
    cidade com descricoes parecidas se fundiriam."""
    from src.dedupe import chave_canonica
    assert chave_canonica(vaga(empresa_bruta="Clinica A")) != \
           chave_canonica(vaga(empresa_bruta="Clinica B"))


def test_cidade_diferente_gera_chave_diferente():
    """Por que este teste existe: a mesma rede contrata em varias cidades, e sao vagas
    distintas. Fundir por cidade destruiria justamente o eixo geografico que importa."""
    from src.dedupe import chave_canonica
    assert chave_canonica(vaga(cidade="Recife", uf="PE")) != \
           chave_canonica(vaga(cidade="Curitiba", uf="PR"))


def test_sem_descricao_o_identificador_de_origem_entra_como_ultimo_recurso():
    """Por que este teste existe: 25% das vagas do BNE vem com empresa "Confidencial", e
    vaga ainda nao enriquecida nao tem descricao. Sem nada que a identifique, o
    identificador de origem e a unica honestidade possivel - senao todas as vagas
    anonimas da mesma cidade virariam um card so."""
    from src.dedupe import chave_canonica
    a = vaga(empresa_bruta="Confidencial", descricao=None, id_na_fonte="1")
    b = vaga(empresa_bruta="Confidencial", descricao=None, id_na_fonte="2")
    assert chave_canonica(a) != chave_canonica(b)


def test_sem_descricao_a_mesma_vaga_continua_com_a_mesma_chave():
    """Por que este teste existe: o outro lado do anterior. O recurso ao identificador
    nao pode fazer a vaga mudar de chave entre duas coletas."""
    from src.dedupe import chave_canonica
    sem = vaga(descricao=None)
    assert chave_canonica(sem) == chave_canonica(dict(sem))


def test_enriquecer_muda_a_chave_da_vaga_sem_descricao():
    """Por que este teste existe: e uma consequencia incomoda que precisa ficar visivel.
    Vaga sem descricao usa o identificador; depois do enriquecimento passa a usar o hash
    do texto. A chave MUDA - e quem consome precisa recalcular, nao assumir estabilidade
    eterna. Melhor um teste que documenta isso do que a descoberta no meio da S8."""
    from src.dedupe import chave_canonica
    antes = chave_canonica(vaga(descricao=None))
    depois = chave_canonica(vaga(descricao="atende ortodontia"))
    assert antes != depois


def test_a_chave_e_estavel_entre_execucoes():
    """Por que este teste existe: determinismo e regra do projeto. Chave que varia entre
    execucoes reagruparia o acervo inteiro a cada rodada."""
    from src.dedupe import chave_canonica
    assert chave_canonica(vaga()) == chave_canonica(vaga())


def test_a_chave_e_curta_o_bastante_para_virar_indice():
    """Por que este teste existe: a chave vai para uma coluna indexada do banco. Guardar
    a descricao inteira concatenada faria o indice inchar sem ganho nenhum."""
    from src.dedupe import chave_canonica
    longa = vaga(descricao="palavra " * 500)
    assert len(chave_canonica(longa)) <= 64
