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

# chave_canonica decide se duas vagas sao a mesma vaga.
from src.dedupe import chave_canonica

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

# Colunas que so a pagina de detalhe preenche (subfase S3b). Ficam separadas porque a
# recoleta NAO pode sobrescreve-las: a listagem nao tem esses dados, e gravar o nulo
# dela por cima desfaria o enriquecimento a cada madrugada.
COLUNAS_DETALHE = ("subtitulo", "descricao", "tipo_vinculo", "enriquecido_em",
                   "id_canonico")

# Campos que a listagem manda vazios mas o detalhe preenche. Na recoleta eles recebem
# COALESCE, para o valor vindo do detalhe sobreviver ao nulo da listagem.
COLUNAS_PRESERVADAS = ("salario_texto",)


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
            subtitulo       TEXT,
            descricao       TEXT,
            tipo_vinculo    TEXT,
            enriquecido_em  TEXT,
            PRIMARY KEY (fonte, id_na_fonte)
        )
    """)

    # Migracao das colunas de enriquecimento. `CREATE TABLE IF NOT EXISTS` nao mexe em
    # tabela que ja existe, entao o banco de producao - com centenas de vagas gravadas
    # antes desta subfase - ficaria sem as colunas novas e quebraria em silencio.
    existentes = {linha[1] for linha in conexao.execute("PRAGMA table_info(vaga)")}
    for coluna in COLUNAS_DETALHE:
        if coluna not in existentes:
            # ADD COLUMN e barato e nao reescreve a tabela; os valores nascem nulos, que
            # e exatamente o que significa "ainda nao enriquecida".
            conexao.execute("ALTER TABLE vaga ADD COLUMN {} TEXT".format(coluna))

    # Fase 2: o estado pertence ao GRUPO, e nao a uma copia. Se ficasse preso a copia,
    # descartar a vaga faria a republicacao dela reaparecer amanha como se fosse nova.
    # `quem` entra na chave para que o estado de cada pessoa seja independente - um
    # descarte dela nao pode apagar a vaga dele.
    conexao.execute("""
        CREATE TABLE IF NOT EXISTS estado_item (
            id_canonico TEXT NOT NULL,
            quem        TEXT NOT NULL,
            estado      TEXT NOT NULL,
            motivo      TEXT,
            marcado_em  TEXT NOT NULL,
            PRIMARY KEY (id_canonico, quem)
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

    # Fase 4: preenche a chave canonica das vagas gravadas antes da S4. Sem isso, o
    # acervo existente ficaria fora de qualquer agrupamento - e o programa passaria a
    # funcionar so em banco novo, que e a falha silenciosa que a migracao evita.
    conexao.row_factory = sqlite3.Row
    pendentes = [dict(l) for l in conexao.execute(
        "SELECT * FROM vaga WHERE id_canonico IS NULL"
    )]
    for registro in pendentes:
        conexao.execute(
            "UPDATE vaga SET id_canonico = ? WHERE fonte = ? AND id_na_fonte = ?",
            (chave_canonica(registro), registro["fonte"], registro["id_na_fonte"]),
        )

    # Fase 5: migra a tabela de estados do formato antigo, que apontava para uma copia,
    # para o novo, que aponta para o grupo. O SQLite nao muda chave primaria, entao a
    # tabela e reconstruida - as marcacoes existentes sao mapeadas pela chave canonica
    # da vaga que apontavam.
    colunas_estado = {l[1] for l in conexao.execute("PRAGMA table_info(estado_item)")}
    if "id_na_fonte" in colunas_estado:
        conexao.execute("ALTER TABLE estado_item RENAME TO estado_item_antigo")
        conexao.execute("""
            CREATE TABLE estado_item (
                id_canonico TEXT NOT NULL, quem TEXT NOT NULL, estado TEXT NOT NULL,
                motivo TEXT, marcado_em TEXT NOT NULL,
                PRIMARY KEY (id_canonico, quem)
            )
        """)
        # A juncao com vaga e o que traduz a marcacao antiga para o grupo. Marcacao
        # orfa - de vaga que nao existe mais - e descartada de proposito.
        conexao.execute("""
            INSERT OR REPLACE INTO estado_item (id_canonico, quem, estado, motivo, marcado_em)
            SELECT v.id_canonico, a.quem, a.estado, a.motivo, a.marcado_em
            FROM estado_item_antigo a
            JOIN vaga v ON v.fonte = a.fonte AND v.id_na_fonte = a.id_na_fonte
        """)
        conexao.execute("DROP TABLE estado_item_antigo")

    # Saida: confirma tudo de uma vez.
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
    #
    # As colunas preservadas usam COALESCE: se a listagem trouxer nulo - e ela traz, no
    # caso do salario, em 100% das vagas do BNE - o valor que ja estava fica. Sem isso, a
    # recoleta de amanha desfaria o enriquecimento de hoje.
    atualizacoes = ", ".join(
        "{0} = COALESCE(excluded.{0}, vaga.{0})".format(coluna)
        if coluna in COLUNAS_PRESERVADAS
        else "{0} = excluded.{0}".format(coluna)
        for coluna in COLUNAS_VAGA[2:]
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

        # Fase 3: a chave canonica e calculada na gravacao, e nao na leitura - assim ela
        # pode ser indexada e a consulta nao recalcula o acervo inteiro.
        #
        # A chave e calculada sobre a linha JA GRAVADA, e nao sobre o dicionario que
        # chegou: a descricao vem do enriquecimento e nao aparece na listagem, entao usar
        # o dicionario da coleta faria a vaga enriquecida perder a chave boa a cada
        # recoleta e voltar a se agrupar pelo identificador.
        conexao.row_factory = sqlite3.Row
        gravada = dict(conexao.execute(
            "SELECT * FROM vaga WHERE fonte = ? AND id_na_fonte = ?",
            (vaga.get("fonte"), vaga.get("id_na_fonte")),
        ).fetchone())
        conexao.execute(
            "UPDATE vaga SET id_canonico = ? WHERE fonte = ? AND id_na_fonte = ?",
            (chave_canonica(gravada), vaga.get("fonte"), vaga.get("id_na_fonte")),
        )

    # Saida: uma transacao por rodada, e nao por vaga.
    conexao.commit()


def _melhor_copia(copias):
    """Escolhe qual copia do grupo representa o card.

    Por que esta funcao existe: o card mostra os dados de UMA das copias, e a escolha nao
    e indiferente. Pegar a copia nao enriquecida jogaria fora o subtitulo que a S3b
    trouxe - o unico campo que devolve informacao ao card, ja que o titulo do BNE e
    generico e igual em todas.

    Entrada -> as copias de um mesmo grupo.
    Fase 1  -> ordena por criterios de qualidade, do mais forte ao mais fraco.
    Saida   -> a copia escolhida.
    """
    def qualidade(copia):
        """Menor e melhor: a ordenacao crescente poe a copia escolhida na frente."""
        # Enriquecida vence, porque so ela tem o subtitulo que informa.
        enriquecida = 0 if copia.get("enriquecido_em") else 1
        # Data invertida faz a publicacao mais recente vir antes numa ordem crescente.
        data = copia.get("data_publicacao") or ""
        invertida = tuple(-int(p) for p in data.split("-")) if data else (0, 0, 0)
        # Identificador como desempate final: a escolha nunca varia entre execucoes.
        return (enriquecida, invertida, copia.get("id_na_fonte") or "")

    # Fase 1 e saida.
    return sorted(copias, key=qualidade)[0]


def listar_vagas(conexao, quem=None):
    """Devolve as vagas agrupadas por chave canonica, com o estado da pessoa indicada.

    Por que esta funcao agrupa em vez de devolver linha por linha: a decisao 3.7 pede um
    card com varios links, e nao varios cards. O agrupamento acontece na LEITURA, sem
    apagar copia nenhuma - apagar perderia a prova de origem que o D3 exige, e seria
    irreversivel se a chave se mostrasse errada depois.

    Entrada -> a conexao e, opcionalmente, de quem e o estado desejado.
    Fase 1  -> junta vaga com o estado do grupo para aquela pessoa.
    Fase 2  -> agrupa as copias pela chave canonica.
    Fase 3  -> escolhe a copia que representa o card e junta os links de todas.
    Saida   -> a lista de itens, em ordem estavel.
    """
    # LEFT JOIN porque a maioria das vagas nao tem marcacao nenhuma. A condicao de
    # `quem` entra no ON, e nao no WHERE, senao o LEFT JOIN viraria INNER JOIN.
    comando = """
        SELECT v.*, e.estado, e.motivo, e.marcado_em
        FROM vaga v
        LEFT JOIN estado_item e
               ON e.id_canonico = v.id_canonico
              AND e.quem = ?
        ORDER BY v.fonte, v.id_na_fonte
    """
    conexao.row_factory = sqlite3.Row
    linhas = [dict(l) for l in conexao.execute(comando, (quem or "",))]

    # Fase 2: dicionario comum preserva a ordem de insercao, que ja vem ordenada do SQL -
    # e o que mantem a saida estavel entre execucoes.
    grupos = {}
    for linha in linhas:
        # Vaga sem chave so existiria em banco corrompido; o identificador de origem
        # serve de grupo proprio, para ela nao sumir da listagem.
        chave = linha.get("id_canonico") or "{}/{}".format(
            linha["fonte"], linha["id_na_fonte"])
        grupos.setdefault(chave, []).append(linha)

    # Fase 3 e saida: um item por grupo.
    resultado = []
    for copias in grupos.values():
        item = dict(_melhor_copia(copias))
        # O estado ausente vira `nova`, e nao None.
        item["estado"] = item.get("estado") or "nova"
        # Agrupar nao pode significar perder: cada copia deixa seu link.
        item["origens"] = [
            {"fonte": c["fonte"], "id_na_fonte": c["id_na_fonte"], "url": c["url"]}
            for c in sorted(copias, key=lambda c: (c["fonte"], c["id_na_fonte"]))
        ]
        resultado.append(item)
    return resultado


def vagas_sem_detalhe(conexao, limite=None):
    """Devolve as vagas que ainda nao passaram pelo enriquecimento.

    Por que esta funcao existe: enriquecer custa uma requisicao por vaga. Buscar de novo
    o que ja foi buscado desperdicaria a rodada e pesaria sobre a fonte sem motivo - foi
    exatamente por isso que esta subfase veio depois da persistencia, e nao antes.

    Entrada -> a conexao e, opcionalmente, um teto de quantas devolver.
    Fase 1  -> seleciona as que nao tem carimbo de enriquecimento.
    Fase 2  -> aplica o teto, util para rodadas parciais em acervo grande.
    Saida   -> a lista de vagas pendentes, em ordem estavel.
    """
    # Fase 1: `enriquecido_em` nulo e o que significa "ainda nao buscada".
    comando = (
        "SELECT * FROM vaga WHERE enriquecido_em IS NULL"
        " ORDER BY fonte, id_na_fonte"
    )
    # Fase 2: o teto entra como LIMIT, para nao trazer o acervo inteiro a memoria.
    if limite:
        comando += " LIMIT {}".format(int(limite))

    conexao.row_factory = sqlite3.Row
    return [dict(linha) for linha in conexao.execute(comando)]


def salvar_detalhe(conexao, fonte, id_na_fonte, dados, agora):
    """Grava o que a pagina de detalhe trouxe e tira a vaga da fila.

    Por que esta funcao existe separada de `salvar_vagas`: sao duas origens diferentes
    com regras opostas. A listagem sobrescreve; o detalhe complementa. Junta-las faria a
    recoleta apagar o enriquecimento.

    Entrada -> a conexao, a origem da vaga, os campos extraidos e o horario.
    Fase 1  -> grava os campos que so o detalhe tem.
    Fase 2  -> grava o salario apenas quando o detalhe informou, para nao apagar um valor
               que ja estivesse la.
    Fase 3  -> carimba o enriquecimento, o que tira a vaga da fila.
    Fase 4  -> RECALCULA a chave canonica, porque ela depende da descricao que acabou de
               chegar. Sem isto, a vaga continuaria agrupada pelo identificador de origem
               e a deduplicacao nunca aconteceria - o enriquecimento seria requisicao
               gasta a toa.
    Fase 5  -> leva junto a marcacao que existisse na chave antiga, senao descartar uma
               vaga antes de ela ser enriquecida faria o descarte evaporar.
    Saida   -> nada; a funcao existe pelo efeito no banco.
    """
    # Fase 1, 2 e 3 num comando so: COALESCE no salario protege o que ja existia.
    conexao.execute("""
        UPDATE vaga SET
            subtitulo      = ?,
            descricao      = ?,
            tipo_vinculo   = ?,
            salario_texto  = COALESCE(?, salario_texto),
            enriquecido_em = ?
        WHERE fonte = ? AND id_na_fonte = ?
    """, (
        dados.get("subtitulo"),
        dados.get("descricao"),
        dados.get("tipo_vinculo"),
        dados.get("salario_texto"),
        agora,
        fonte, id_na_fonte,
    ))

    # Fase 4: le a linha ja atualizada e recalcula a chave sobre ela.
    conexao.row_factory = sqlite3.Row
    gravada = dict(conexao.execute(
        "SELECT * FROM vaga WHERE fonte = ? AND id_na_fonte = ?", (fonte, id_na_fonte)
    ).fetchone())
    anterior = gravada.get("id_canonico")
    nova = chave_canonica(gravada)

    if nova != anterior:
        conexao.execute(
            "UPDATE vaga SET id_canonico = ? WHERE fonte = ? AND id_na_fonte = ?",
            (nova, fonte, id_na_fonte),
        )

        # Fase 5: a marcacao pertence ao grupo, e o grupo acabou de mudar de nome.
        # INSERT OR IGNORE preserva a marcacao que ja existisse na chave nova - o caso de
        # a copia gemea ter sido marcada antes.
        conexao.execute("""
            INSERT OR IGNORE INTO estado_item (id_canonico, quem, estado, motivo, marcado_em)
            SELECT ?, quem, estado, motivo, marcado_em FROM estado_item WHERE id_canonico = ?
        """, (nova, anterior))

        # A marcacao antiga so e apagada se nenhuma outra vaga continuar naquele grupo -
        # a copia ainda nao enriquecida, por exemplo, segue apontando para ela.
        sobrou = conexao.execute(
            "SELECT 1 FROM vaga WHERE id_canonico = ?", (anterior,)
        ).fetchone()
        if sobrou is None:
            conexao.execute("DELETE FROM estado_item WHERE id_canonico = ?", (anterior,))

    conexao.commit()


def marcar(conexao, id_canonico, quem, estado, agora, motivo=None):
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
    # apontando para grupo que nunca existiu, e o erro so apareceria muito depois.
    existe = conexao.execute(
        "SELECT 1 FROM vaga WHERE id_canonico = ?", (id_canonico,)
    ).fetchone()
    if existe is None:
        raise EntradaInvalida(
            "Vaga {} nao esta no banco. Rode a coleta antes de marcar.".format(
                id_canonico)
        )

    # Fase 4: a chave inclui `quem`, entao a sobrescrita e por pessoa. E aponta para o
    # GRUPO, entao marcar uma vaga marca todas as republicacoes dela de uma vez.
    conexao.execute("""
        INSERT INTO estado_item (id_canonico, quem, estado, motivo, marcado_em)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (id_canonico, quem) DO UPDATE SET
            estado = excluded.estado,
            motivo = excluded.motivo,
            marcado_em = excluded.marcado_em
    """, (id_canonico, quem, estado, motivo, agora))

    # Fase 5: o agregado da 4.3 esta congelado, mas o dado precisa acumular desde ja -
    # depois e impossivel recuperar.
    registrar_evento(
        conexao, "marcacao", None, id_canonico,
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
