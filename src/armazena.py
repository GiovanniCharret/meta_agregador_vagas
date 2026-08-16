"""Persistencia das vagas e dos estados.

Por que este modulo existe: o feed precisa lembrar o que ja foi visto entre uma execucao
e outra. Sem isso, o horizonte continuo que voce escolheu na triagem - monitorar sempre,
sem teto de volume - faria a pagina reapresentar o acervo inteiro toda vez, e em poucos
dias ficaria impraticavel.

Por que SQLite e nao PostgreSQL: sao dois usuarios numa maquina so. Postgres seria mais
um servico para subir e manter, sem ganho nessa escala. A troca e assimetrica: sair de
SQLite para Postgres depois e migracao pequena.

Por que a conexao entra por parametro em vez de ser aberta aqui dentro: e o que permite
aos testes rodarem sobre um banco em memoria, sem tocar em disco nem sujar o banco real.

Limitacao conhecida desta fase: a chave usada e (fonte, id_na_fonte), a origem do
anuncio. A chave canonica do D3, que agrupa o mesmo anuncio vindo de fontes diferentes,
so existe a partir da S4 - e sera a migracao daquela subfase.
"""

# json serializa o conteudo do evento, que varia conforme o tipo.
import json

# sqlite3 e o banco; vem na biblioteca padrao, sem dependencia nova.
import sqlite3

# EntradaInvalida sinaliza o que o usuario pode corrigir.
from src.erros import EntradaInvalida

# Os tres estados da decisao 3.8.
ESTADOS = ("nova", "salva", "descartada")

# Os motivos de descarte da decisao 4.1. Lista fechada de proposito: motivo em texto
# livre viraria dezenas de variacoes da mesma coisa, e a distribuicao de motivos - que e
# o dado de UX que vai guiar as proximas fases - ficaria inutil para contar.
MOTIVOS = (
    "cidade",
    "salario",
    "requisito_que_nao_tenho",
    "modalidade",
    "empresa",
    "nao_e_minha_area",
    "vaga_velha_ou_fantasma",
)

# Colunas da vaga que vem do pipeline, na ordem usada nas escritas e leituras.
COLUNAS_VAGA = (
    "fonte", "id_na_fonte", "url", "titulo_bruto", "empresa_bruta",
    "cidade", "uf", "modalidade", "salario_texto", "data_publicacao",
)


def criar_esquema(conexao):
    """Cria as tabelas, se ainda nao existirem.

    Por que esta funcao existe e por que ela e idempotente: o esquema e garantido a cada
    execucao do programa. Se a segunda chamada estourasse, o programa so funcionaria na
    primeira vez da vida.

    Entrada -> uma conexao SQLite aberta.
    Fase 1  -> cria a tabela de vagas, com chave pela origem do anuncio.
    Fase 2  -> cria a tabela de estados, com chave por vaga e por pessoa.
    Fase 3  -> cria a tabela de eventos, que so cresce.
    Saida   -> nada; a funcao existe pelo efeito no banco.
    """
    # Fase 1: a chave primaria composta e o que impede a mesma vaga de entrar duas vezes
    # quando a coleta reencontra o anuncio no dia seguinte.
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS vaga (
            fonte           TEXT NOT NULL,
            id_na_fonte     TEXT NOT NULL,
            url             TEXT,
            titulo_bruto    TEXT,
            empresa_bruta   TEXT,
            cidade          TEXT,
            uf              TEXT,
            modalidade      TEXT,
            salario_texto   TEXT,
            data_publicacao TEXT,
            primeira_coleta TEXT NOT NULL,
            ultima_coleta   TEXT NOT NULL,
            PRIMARY KEY (fonte, id_na_fonte)
        )
    """)

    # Fase 2: `quem` entra na chave para que o estado de cada pessoa seja independente -
    # um descarte dela nao pode apagar a vaga dele.
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS estado_item (
            fonte       TEXT NOT NULL,
            id_na_fonte TEXT NOT NULL,
            quem        TEXT NOT NULL,
            estado      TEXT NOT NULL,
            motivo      TEXT,
            marcado_em  TEXT NOT NULL,
            PRIMARY KEY (fonte, id_na_fonte, quem)
        )
    """)

    # Fase 3: log que so cresce. E a materia-prima do dado de UX que a 4.3 vai consumir
    # no futuro; coletar agora custa pouco e recuperar depois e impossivel.
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS evento (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo        TEXT NOT NULL,
            fonte       TEXT,
            id_na_fonte TEXT,
            payload     TEXT,
            criado_em   TEXT NOT NULL
        )
    """)

    # Saida: confirma as tres criacoes de uma vez.
    conexao.commit()


def salvar_vagas(conexao, vagas, agora):
    """Grava as vagas coletadas, sem duplicar as que ja estavam la.

    Por que esta funcao existe: e a fronteira entre a coleta, que roda toda vez do zero,
    e o banco, que acumula. Ela e quem decide o que e novidade e o que e reencontro.

    Entrada -> a conexao, a lista de vagas do pipeline e o horario da rodada.
    Fase 1  -> insere a vaga com os dois carimbos iguais, quando ela for inedita.
    Fase 2  -> quando ja existir, atualiza os campos e o carimbo de ultima coleta, mas
               **preserva** o de primeira coleta - e o que permitira saber ha quanto
               tempo a vaga esta no ar.
    Saida   -> nada; a funcao existe pelo efeito no banco.
    """
    # A lista de colunas e montada uma vez para as duas fases usarem a mesma ordem.
    nomes = ", ".join(COLUNAS_VAGA)
    marcadores = ", ".join("?" for _ in COLUNAS_VAGA)

    # ON CONFLICT faz o insert virar atualizacao quando a chave ja existe. `excluded` e
    # a linha que teria sido inserida; usa-la aqui atualiza os campos com o dado novo.
    # `primeira_coleta` fica de fora da lista de atualizacao de proposito.
    atualizacoes = ", ".join(
        "{0} = excluded.{0}".format(coluna) for coluna in COLUNAS_VAGA[2:]
    )

    comando = """
        INSERT INTO vaga ({nomes}, primeira_coleta, ultima_coleta)
        VALUES ({marcadores}, ?, ?)
        ON CONFLICT (fonte, id_na_fonte) DO UPDATE SET
            {atualizacoes},
            ultima_coleta = excluded.ultima_coleta
    """.format(nomes=nomes, marcadores=marcadores, atualizacoes=atualizacoes)

    # Fase 1 e 2: uma passada so, deixando o banco decidir insercao ou atualizacao.
    for vaga in vagas:
        valores = [vaga.get(coluna) for coluna in COLUNAS_VAGA]
        conexao.execute(comando, valores + [agora, agora])

    # Saida: uma transacao por rodada, e nao por vaga.
    conexao.commit()


def listar_vagas(conexao, quem=None):
    """Devolve as vagas guardadas, ja com o estado da pessoa indicada.

    Por que esta funcao existe: o feed le daqui, e precisa de vaga e estado juntos. Fazer
    duas consultas e cruzar em Python seria mais codigo para o mesmo resultado.

    Entrada -> a conexao e, opcionalmente, de quem e o estado desejado.
    Fase 1  -> junta vaga com o estado daquela pessoa, se houver.
    Fase 2  -> vaga sem marcacao recebe o estado inicial `nova`, da decisao 3.8.
    Saida   -> a lista de dicionarios, em ordem estavel por fonte e identificador.
    """
    # LEFT JOIN porque a maioria das vagas nao tem marcacao nenhuma. A condicao de
    # `quem` entra no ON, e nao no WHERE, senao o LEFT JOIN viraria INNER JOIN.
    comando = """
        SELECT v.*, e.estado, e.motivo, e.marcado_em
        FROM vaga v
        LEFT JOIN estado_item e
               ON e.fonte = v.fonte
              AND e.id_na_fonte = v.id_na_fonte
              AND e.quem = ?
        ORDER BY v.fonte, v.id_na_fonte
    """
    # Ordem estavel e exigencia de determinismo: o feed le daqui.
    conexao.row_factory = sqlite3.Row
    linhas = conexao.execute(comando, (quem or "",)).fetchall()

    # Fase 2 e saida: o estado ausente vira `nova`, e nao None.
    resultado = []
    for linha in linhas:
        registro = dict(linha)
        registro["estado"] = registro["estado"] or "nova"
        resultado.append(registro)
    return resultado


def marcar(conexao, fonte, id_na_fonte, quem, estado, agora, motivo=None):
    """Registra o estado de uma vaga para uma pessoa.

    Por que esta funcao existe: concentra as regras da 3.8 e da 4.1 num lugar so. A
    validacao do motivo obrigatorio precisa acontecer antes da escrita, senao o banco
    aceitaria descarte sem motivo e a regra viraria decoracao.

    Entrada -> a conexao, a origem da vaga, quem marcou, o estado, o horario e o motivo.
    Fase 1  -> recusa estado que nao existe.
    Fase 2  -> exige motivo no descarte, e so um da lista fechada.
    Fase 3  -> recusa marcacao de vaga que nao esta no banco, para nao criar estado orfao.
    Fase 4  -> grava, sobrescrevendo marcacao anterior da mesma pessoa.
    Fase 5  -> registra o evento, materia-prima do dado de UX.
    Saida   -> nada; a funcao existe pelo efeito no banco.
    """
    # Fase 1: estado desconhecido so poderia vir de defeito na tela, mas a mensagem
    # ensina os validos de qualquer forma.
    if estado not in ESTADOS:
        raise EntradaInvalida(
            'Estado "{}" nao existe. Os estados sao: {}.'.format(
                estado, ", ".join(ESTADOS))
        )

    # Fase 2: a decisao 4.1, alterada por voce na triagem - o motivo passou a ser
    # obrigatorio, porque coleta de motivo que ninguem responde e esforco jogado fora.
    if estado == "descartada":
        if not motivo:
            raise EntradaInvalida(
                "Descarte exige motivo. Escolha um entre: {}.".format(", ".join(MOTIVOS))
            )
        if motivo not in MOTIVOS:
            raise EntradaInvalida(
                'O motivo "{}" nao esta na lista. Escolha um entre: {}.'.format(
                    motivo, ", ".join(MOTIVOS))
            )
    else:
        # Motivo pertence ao descarte. Mante-lo numa remarcacao para salva faria a
        # contagem de motivos incluir vaga que nao foi descartada.
        motivo = None

    # Fase 3: sem esta checagem, um identificador errado vindo da tela criaria estado
    # apontando para vaga que nunca existiu, e o erro so apareceria muito depois.
    existe = conexao.execute(
        "SELECT 1 FROM vaga WHERE fonte = ? AND id_na_fonte = ?",
        (fonte, id_na_fonte),
    ).fetchone()
    if existe is None:
        raise EntradaInvalida(
            "Vaga {}/{} nao esta no banco. Rode a coleta antes de marcar.".format(
                fonte, id_na_fonte)
        )

    # Fase 4: a chave inclui `quem`, entao a sobrescrita e por pessoa.
    conexao.execute("""
        INSERT INTO estado_item (fonte, id_na_fonte, quem, estado, motivo, marcado_em)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (fonte, id_na_fonte, quem) DO UPDATE SET
            estado = excluded.estado,
            motivo = excluded.motivo,
            marcado_em = excluded.marcado_em
    """, (fonte, id_na_fonte, quem, estado, motivo, agora))

    # Fase 5: o agregado da 4.3 esta congelado, mas o dado precisa acumular desde ja -
    # depois e impossivel recuperar.
    registrar_evento(
        conexao, "marcacao", fonte, id_na_fonte,
        {"quem": quem, "estado": estado, "motivo": motivo}, agora,
    )

    # Saida: uma transacao por marcacao, porque cada uma e uma decisao do usuario.
    conexao.commit()


def registrar_evento(conexao, tipo, fonte, id_na_fonte, payload, agora):
    """Acrescenta uma linha ao log de eventos.

    Por que esta funcao existe separada: o log e append-only e vai receber outros tipos
    de evento adiante - coleta, enriquecimento, alerta. Ter um unico ponto de escrita
    evita que cada um invente seu proprio formato.

    Entrada -> a conexao, o tipo do evento, a origem, um dicionario livre e o horario.
    Fase 1  -> serializa o conteudo variavel como JSON.
    Saida   -> nada; a funcao existe pelo efeito no banco.
    """
    # sort_keys deixa o texto estavel, o que ajuda a comparar eventos depois.
    conexao.execute(
        "INSERT INTO evento (tipo, fonte, id_na_fonte, payload, criado_em)"
        " VALUES (?, ?, ?, ?, ?)",
        (tipo, fonte, id_na_fonte,
         json.dumps(payload, ensure_ascii=False, sort_keys=True), agora),
    )


def listar_eventos(conexao):
    """Devolve os eventos gravados, do mais antigo para o mais novo."""
    # row_factory garante acesso por nome de coluna, como no resto do modulo.
    conexao.row_factory = sqlite3.Row
    return [dict(l) for l in conexao.execute("SELECT * FROM evento ORDER BY id")]
