"""Testes de src/armazena.py - persistencia e estados das vagas."""

import sqlite3

import pytest


def vaga(**mudancas):
    """Devolve uma vaga no formato do projeto, com os campos que o teste quiser mudar."""
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
def banco():
    """Banco em memoria, ja com o esquema criado.

    Por que em memoria: o teste nao pode depender de arquivo em disco nem sujar o banco
    de verdade do projeto. Em memoria tambem e mais rapido e some sozinho no fim.
    """
    from src.armazena import criar_esquema
    conexao = sqlite3.connect(":memory:")
    criar_esquema(conexao)
    yield conexao
    conexao.close()


def test_criar_esquema_pode_rodar_duas_vezes(banco):
    """Por que este teste existe: o esquema e criado a cada execucao do programa. Se a
    segunda chamada estourasse, o programa so funcionaria na primeira vez da vida."""
    from src.armazena import criar_esquema
    # A segunda chamada sobre o mesmo banco nao pode levantar nada.
    criar_esquema(banco)


def test_salvar_grava_a_vaga(banco):
    """Por que este teste existe: e o minimo da persistencia - o que foi coletado tem
    que sobreviver ao fim da execucao."""
    from src.armazena import salvar_vagas, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    guardadas = listar_vagas(banco)
    assert len(guardadas) == 1
    assert guardadas[0]["cidade"] == "Florianopolis"


def test_salvar_a_mesma_vaga_duas_vezes_nao_duplica(banco):
    """Por que este teste existe: a coleta roda todo dia e reencontra as mesmas vagas.
    Sem chave primaria por origem, o banco cresceria sem limite e a contagem por cidade
    mentiria mais a cada rodada."""
    from src.armazena import salvar_vagas, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    salvar_vagas(banco, [vaga()], agora="2026-08-17T10:00:00")
    assert len(listar_vagas(banco)) == 1


def test_recoleta_preserva_a_primeira_vez_que_a_vaga_foi_vista(banco):
    """Por que este teste existe: `primeira_coleta` e o que permitira saber ha quanto
    tempo uma vaga esta no ar. Se a recoleta sobrescrevesse, toda vaga pareceria nova
    todo dia e esse dado se perderia para sempre."""
    from src.armazena import salvar_vagas, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    salvar_vagas(banco, [vaga()], agora="2026-08-20T10:00:00")
    guardada = listar_vagas(banco)[0]
    assert guardada["primeira_coleta"] == "2026-08-16T10:00:00"
    assert guardada["ultima_coleta"] == "2026-08-20T10:00:00"


def test_vaga_recem_coletada_comeca_como_nova(banco):
    """Por que este teste existe: e o estado inicial da decisao 3.8. Sem ele, o feed
    nao teria como separar o que ja foi visto do que acabou de chegar."""
    from src.armazena import salvar_vagas, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    assert listar_vagas(banco)[0]["estado"] == "nova"


def test_marcar_como_salva_persiste(banco):
    """Por que este teste existe: e a metade util da 3.8 - guardar o que interessa."""
    from src.armazena import salvar_vagas, marcar, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    marcar(banco, "bne", "1000", quem="meu", estado="salva", agora="2026-08-16T11:00:00")
    assert listar_vagas(banco, quem="meu")[0]["estado"] == "salva"


def test_descartar_sem_motivo_e_recusado(banco):
    """Por que este teste existe: e a decisao 4.1, que voce alterou na triagem - o
    motivo passou a ser obrigatorio. Sua justificativa foi direta: se voces dois nao
    responderem, a coleta de motivo vira esforco jogado fora."""
    from src.armazena import salvar_vagas, marcar
    from src.erros import EntradaInvalida
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    with pytest.raises(EntradaInvalida) as erro:
        marcar(banco, "bne", "1000", quem="meu", estado="descartada",
               agora="2026-08-16T11:00:00")
    assert "motivo" in str(erro.value).lower()


def test_descartar_com_motivo_fora_da_lista_e_recusado(banco):
    """Por que este teste existe: motivo em texto livre viraria dezenas de variacoes da
    mesma coisa, e a distribuicao de motivos - que e o dado de UX que vai guiar as
    proximas fases - ficaria inutil para contar."""
    from src.armazena import salvar_vagas, marcar
    from src.erros import EntradaInvalida
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    with pytest.raises(EntradaInvalida) as erro:
        marcar(banco, "bne", "1000", quem="meu", estado="descartada",
               motivo="nao gostei", agora="2026-08-16T11:00:00")
    mensagem = str(erro.value)
    # Cita o valor recusado e ensina os aceitos.
    assert "nao gostei" in mensagem
    assert "cidade" in mensagem


def test_descartar_com_motivo_valido_guarda_o_motivo(banco):
    """Por que este teste existe: o motivo e a materia-prima do dado de UX. Guardar o
    estado sem o motivo perderia justamente a parte que interessa."""
    from src.armazena import salvar_vagas, marcar, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    marcar(banco, "bne", "1000", quem="meu", estado="descartada",
           motivo="salario", agora="2026-08-16T11:00:00")
    guardada = listar_vagas(banco, quem="meu")[0]
    assert guardada["estado"] == "descartada"
    assert guardada["motivo"] == "salario"


def test_estado_de_cada_pessoa_e_independente(banco):
    """Por que este teste existe: sao duas pessoas com perfis diferentes olhando o mesmo
    feed. Se o estado fosse compartilhado, um descarte dela apagaria a vaga dele."""
    from src.armazena import salvar_vagas, marcar, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    marcar(banco, "bne", "1000", quem="meu", estado="salva", agora="2026-08-16T11:00:00")
    # Para ele esta salva; para ela continua nova, porque ela nao marcou nada.
    assert listar_vagas(banco, quem="meu")[0]["estado"] == "salva"
    assert listar_vagas(banco, quem="dela")[0]["estado"] == "nova"


def test_remarcar_sobrescreve_o_estado_anterior(banco):
    """Por que este teste existe: mudar de ideia e normal. Sem sobrescrita, o banco
    acumularia estados conflitantes da mesma vaga e o feed nao saberia qual vale."""
    from src.armazena import salvar_vagas, marcar, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    marcar(banco, "bne", "1000", quem="meu", estado="salva", agora="2026-08-16T11:00:00")
    marcar(banco, "bne", "1000", quem="meu", estado="descartada",
           motivo="cidade", agora="2026-08-16T12:00:00")
    guardadas = listar_vagas(banco, quem="meu")
    assert len(guardadas) == 1
    assert guardadas[0]["estado"] == "descartada"


def test_voltar_para_salva_limpa_o_motivo_antigo(banco):
    """Por que este teste existe: motivo pertence ao descarte. Se ele sobrevivesse a uma
    remarcacao para salva, a contagem de motivos incluiria vagas que nao foram
    descartadas - e o dado de UX ficaria errado sem ninguem notar."""
    from src.armazena import salvar_vagas, marcar, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    marcar(banco, "bne", "1000", quem="meu", estado="descartada",
           motivo="cidade", agora="2026-08-16T11:00:00")
    marcar(banco, "bne", "1000", quem="meu", estado="salva", agora="2026-08-16T12:00:00")
    assert listar_vagas(banco, quem="meu")[0]["motivo"] is None


def test_marcar_vaga_inexistente_e_recusado(banco):
    """Por que este teste existe: sem esta checagem, um identificador errado vindo da
    tela criaria estado orfao, apontando para vaga que nunca existiu - e o erro so
    apareceria muito depois, como contagem que nao fecha."""
    from src.armazena import marcar
    from src.erros import EntradaInvalida
    with pytest.raises(EntradaInvalida):
        marcar(banco, "bne", "9999", quem="meu", estado="salva", agora="2026-08-16T11:00:00")


def test_cada_marcacao_vira_evento(banco):
    """Por que este teste existe: a decisao 4.3 congelou a visualizacao do agregado, mas
    o dado precisa comecar a acumular desde ja - depois e impossivel recuperar. O evento
    e a materia-prima que vai responder, no futuro, qual filtro construir a seguir."""
    from src.armazena import salvar_vagas, marcar, listar_eventos
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    marcar(banco, "bne", "1000", quem="meu", estado="descartada",
           motivo="salario", agora="2026-08-16T11:00:00")
    eventos = listar_eventos(banco)
    assert len(eventos) == 1
    assert eventos[0]["tipo"] == "marcacao"
    # O evento guarda o suficiente para reconstruir a decisao depois.
    assert "salario" in eventos[0]["payload"]


def test_esquema_antigo_ganha_as_colunas_de_enriquecimento():
    """Por que este teste existe: o banco de verdade ja tem centenas de vagas gravadas
    com o esquema anterior. `CREATE TABLE IF NOT EXISTS` nao acrescenta coluna a tabela
    existente, entao sem migracao o enriquecimento so funcionaria em banco novo - e o
    banco de producao ficaria quebrado em silencio."""
    from src.armazena import criar_esquema
    conexao = sqlite3.connect(":memory:")
    # Recria a tabela como ela era antes desta subfase, sem as colunas novas.
    conexao.execute("""
        CREATE TABLE vaga (
            fonte TEXT NOT NULL, id_na_fonte TEXT NOT NULL, url TEXT,
            titulo_bruto TEXT, empresa_bruta TEXT, cidade TEXT, uf TEXT,
            modalidade TEXT, salario_texto TEXT, data_publicacao TEXT,
            primeira_coleta TEXT NOT NULL, ultima_coleta TEXT NOT NULL,
            PRIMARY KEY (fonte, id_na_fonte))
    """)
    conexao.commit()
    # A criacao do esquema tem que reparar a tabela antiga em vez de ignora-la.
    criar_esquema(conexao)
    colunas = {l[1] for l in conexao.execute("PRAGMA table_info(vaga)")}
    for nova in ("subtitulo", "descricao", "tipo_vinculo", "enriquecido_em"):
        assert nova in colunas
    conexao.close()


def test_lista_as_vagas_que_faltam_enriquecer(banco):
    """Por que este teste existe: enriquecer custa uma requisicao por vaga. Buscar
    detalhe do que ja foi buscado desperdicaria a rodada inteira e pesaria sobre a fonte
    sem motivo - foi justamente por isso que esta subfase veio depois da persistencia."""
    from src.armazena import salvar_vagas, vagas_sem_detalhe
    salvar_vagas(banco, [vaga(id_na_fonte="1"), vaga(id_na_fonte="2")],
                 agora="2026-08-16T10:00:00")
    pendentes = vagas_sem_detalhe(banco)
    assert {v["id_na_fonte"] for v in pendentes} == {"1", "2"}


def test_vaga_enriquecida_sai_da_fila(banco):
    """Por que este teste existe: e a outra metade do teste anterior. Sem marcar o que
    ja foi enriquecido, a fila nunca esvaziaria."""
    from src.armazena import salvar_vagas, salvar_detalhe, vagas_sem_detalhe
    salvar_vagas(banco, [vaga(id_na_fonte="1"), vaga(id_na_fonte="2")],
                 agora="2026-08-16T10:00:00")
    salvar_detalhe(banco, "bne", "1",
                   {"descricao": "atende ortodontia", "subtitulo": "ortodontia",
                    "salario_texto": "R$ 5.000,00 por mes", "tipo_vinculo": "FULL_TIME"},
                   agora="2026-08-16T11:00:00")
    assert {v["id_na_fonte"] for v in vagas_sem_detalhe(banco)} == {"2"}


def test_detalhe_guardado_aparece_na_listagem(banco):
    """Por que este teste existe: o enriquecimento so tem valor se chegar ao feed. Se os
    campos ficassem no banco sem serem lidos, seria requisicao gasta a toa."""
    from src.armazena import salvar_vagas, salvar_detalhe, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    salvar_detalhe(banco, "bne", "1000",
                   {"descricao": "clinica contrata para ortodontia",
                    "subtitulo": "especialista em ortodontia",
                    "salario_texto": "R$ 5.000,00 por mes", "tipo_vinculo": "PART_TIME"},
                   agora="2026-08-16T11:00:00")
    guardada = listar_vagas(banco)[0]
    assert guardada["subtitulo"] == "especialista em ortodontia"
    assert guardada["salario_texto"] == "R$ 5.000,00 por mes"
    assert guardada["tipo_vinculo"] == "PART_TIME"


def test_recoleta_nao_apaga_o_salario_enriquecido(banco):
    """Por que este teste existe: e a armadilha desta subfase. A LISTAGEM do BNE manda
    salario nulo em 100% das vagas; o DETALHE traz o valor real. Se a recoleta do dia
    seguinte sobrescrevesse o campo com o nulo da listagem, todo o enriquecimento seria
    desfeito toda madrugada - e o feed voltaria a dizer "salario nao informado" para
    vagas que informam, sem ninguem entender por que."""
    from src.armazena import salvar_vagas, salvar_detalhe, listar_vagas
    salvar_vagas(banco, [vaga(salario_texto=None)], agora="2026-08-16T10:00:00")
    salvar_detalhe(banco, "bne", "1000",
                   {"descricao": "x", "subtitulo": "y",
                    "salario_texto": "R$ 5.000,00 por mes", "tipo_vinculo": None},
                   agora="2026-08-16T11:00:00")
    # A rodada seguinte reencontra a vaga na listagem, de novo sem salario.
    salvar_vagas(banco, [vaga(salario_texto=None)], agora="2026-08-17T10:00:00")
    assert listar_vagas(banco)[0]["salario_texto"] == "R$ 5.000,00 por mes"


def test_recoleta_nao_apaga_a_descricao_enriquecida(banco):
    """Por que este teste existe: mesma armadilha do teste anterior, no campo que
    alimenta a chave canonica da S4. Perder a descricao faria a chave mudar sozinha a
    cada madrugada, e vagas identicas passariam a se separar."""
    from src.armazena import salvar_vagas, salvar_detalhe, listar_vagas
    salvar_vagas(banco, [vaga()], agora="2026-08-16T10:00:00")
    salvar_detalhe(banco, "bne", "1000",
                   {"descricao": "atende ortodontia e endodontia", "subtitulo": "orto",
                    "salario_texto": None, "tipo_vinculo": None},
                   agora="2026-08-16T11:00:00")
    salvar_vagas(banco, [vaga()], agora="2026-08-17T10:00:00")
    guardada = listar_vagas(banco)[0]
    assert guardada["descricao"] == "atende ortodontia e endodontia"
    # E a vaga nao volta para a fila de enriquecimento.
    assert guardada["enriquecido_em"] == "2026-08-16T11:00:00"


def test_listar_ordena_de_forma_estavel(banco):
    """Por que este teste existe: o feed le daqui. Ordem instavel no banco quebraria o
    determinismo do D8 mesmo com a montagem da pagina correta."""
    from src.armazena import salvar_vagas, listar_vagas
    salvar_vagas(banco, [vaga(id_na_fonte="3"), vaga(id_na_fonte="1"),
                         vaga(id_na_fonte="2")], agora="2026-08-16T10:00:00")
    ids = [v["id_na_fonte"] for v in listar_vagas(banco)]
    assert ids == sorted(ids)
