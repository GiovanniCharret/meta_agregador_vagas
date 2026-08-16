"""Montagem da pagina de saida.

Por que este modulo existe: e a unica parte do projeto que sabe como a vaga vira tela.
Todo o resto do pipeline trabalha com dicionarios; aqui eles viram HTML.

Por que HTML montado a mao, sem biblioteca de template: a pagina desta fase e uma so, o
requisito declarado foi "HTML o mais simples possivel", e o determinismo exigido pelo D8
- mesma entrada, bytes identicos - e mais facil de garantir controlando cada quebra de
linha. Quando o FastAPI chegar e houver mais de uma tela, vale reavaliar; ate la, uma
dependencia a menos.

Por que o horario de geracao entra por parametro em vez de ser lido do relogio: se fosse
lido aqui, duas execucoes da mesma entrada produziriam paginas diferentes e o teste de
determinismo passaria por acaso, quando as duas caissem no mesmo segundo, falhando de
forma intermitente depois. Com o horario vindo de fora, a funcao continua pura.
"""

# escape protege contra nome de empresa com & ou < vindo de terceiro.
from html import escape

# Data usada para ordenar; ISO em texto ja ordena certo, mas a conversao deixa o
# tratamento de data ausente explicito.
from datetime import date

# Rotulo legivel de cada modalidade, para a tela nao mostrar o termo interno.
ROTULO_MODALIDADE = {
    "presencial": "Presencial",
    "hibrido": "Hibrido",
    "remoto": "Remoto",
    "desconhecido": "Modalidade nao informada",
}

# Folha de estilo da pagina.
#
# A paleta e as fontes sao as do presenterosa.com.br, onde a pagina vai viver. As
# variaveis tem os mesmos nomes do style.css do site de proposito: quando o site linkar a
# folha dele, os valores dele vencem e a pagina acompanha a mudanca sozinha. Rodando
# local, sem a folha do site, os valores daqui servem de reserva e o visual continua o
# mesmo.
#
# O cartao repete o desenho do `.card` do site - fundo branco, borda rosa clara, canto de
# 20px e a mesma elevacao no hover - para a pagina parecer parte do site e nao um corpo
# estranho colado nele.
ESTILO = """
:root {
  --rosa-principal:#ff85a1; --rosa-claro:#fbb1bd; --rosa-escuro:#f25c7d;
  --fundo:#fff5f7; --texto:#4a4a4a;
  --branco:#fff; --suave:#8b7f83; --linha:#f0dde2;
  --titulo:'Dancing Script', cursive;
  --corpo:'Montserrat', sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--fundo); color:var(--texto);
       font-family:var(--corpo); line-height:1.6; }
.wrap { max-width:900px; margin:0 auto; padding:0 1rem 3rem; }

/* Cabecalho no mesmo desenho da navbar do site. */
.topo-site { background:var(--branco); padding:1rem; box-shadow:0 2px 10px rgba(0,0,0,.05);
             display:flex; flex-direction:column; align-items:center; gap:.5rem; }
.topo-site .logo { font-family:var(--titulo); font-size:1.8rem; color:var(--rosa-escuro); }
.topo-site a { text-decoration:none; color:var(--texto); font-weight:500; font-size:.9rem; }
.topo-site a:hover { color:var(--rosa-escuro); }

.cabecalho { text-align:center; padding:2rem 0 1rem; }
h1 { font-family:var(--titulo); font-size:2.5rem; color:var(--rosa-escuro);
     margin:0 0 .5rem; font-weight:600; }
.resumo { font-size:1rem; margin:0 auto; max-width:520px; }
.resumo b { color:var(--rosa-escuro); font-weight:500; }
.vazio { background:var(--branco); border:1px solid var(--rosa-claro); border-radius:20px;
         padding:2rem; text-align:center; }

.cards { display:flex; flex-direction:column; gap:1rem; }
.vaga { background:var(--branco); border:1px solid var(--rosa-claro); border-radius:20px;
        padding:1.25rem 1.5rem; transition:transform .3s; }
.vaga:hover { transform:translateY(-5px); }
.vaga.desejada { border-color:var(--rosa-escuro); box-shadow:0 4px 14px rgba(242,92,125,.12); }
.vaga.salva { border-color:var(--rosa-principal); background:#fff9fa; }
.topo { display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; }
.vaga h2 { font-size:1.1rem; font-weight:500; margin:0; color:var(--rosa-escuro);
           flex:1 1 auto; min-width:180px; }
.empresa { font-size:.9rem; margin:.25rem 0 0; }
.subtitulo { font-size:.88rem; margin:.6rem 0 0; padding-left:.75rem;
             border-left:3px solid var(--rosa-claro); color:var(--texto); }
.casamento { margin:.6rem 0 0; display:flex; flex-wrap:wrap; gap:6px; align-items:baseline; }
.casamento span { font-size:.7rem; letter-spacing:.08em; text-transform:uppercase;
                  color:var(--suave); }
.casamento em { font-style:normal; font-size:.75rem; background:var(--fundo);
                border:1px solid var(--rosa-claro); border-radius:25px;
                padding:2px 10px; color:var(--rosa-escuro); }
.meta { display:flex; flex-wrap:wrap; gap:8px; margin-top:.7rem; }
.selo { font-size:.72rem; font-weight:500; letter-spacing:.03em; border-radius:25px;
        padding:3px 12px; border:1px solid var(--linha); background:var(--fundo);
        color:var(--texto); }
.selo.local { background:var(--rosa-claro); border-color:var(--rosa-claro); color:#7a3346; }
.selo.remoto { background:#eaf4f4; border-color:#cfe6e6; color:#2b6b6b; }
.selo.salario { background:#f0f7ec; border-color:#d3e7c9; color:#4a7038; }
.selo.desejada { background:var(--rosa-principal); border-color:var(--rosa-escuro); color:#fff; }
.rodape-card { margin-top:.8rem; padding-top:.6rem; border-top:1px solid var(--linha);
               display:flex; justify-content:space-between; gap:12px;
               font-size:.78rem; color:var(--suave); flex-wrap:wrap; }
.rodape-card a { color:var(--rosa-escuro); text-underline-offset:3px; }
/* Os links vivem num agrupador proprio: soltos, o space-between do rodape jogaria
   cada um numa ponta da tela em janela larga. */
.rodape-card .links { display:flex; gap:14px; flex-wrap:wrap; flex:none; }
footer { background:var(--branco); text-align:center; padding:2rem; margin-top:2rem; }
footer p { font-weight:500; }
.heart { display:inline-block; animation:pulse 1.5s infinite; }
@keyframes pulse { 0%{transform:scale(1);} 50%{transform:scale(1.2);} 100%{transform:scale(1);} }
@media (min-width:768px) {
  .topo-site { flex-direction:row; justify-content:space-around; padding:1rem 5%; }
  .wrap { padding:0 2rem 3rem; }
}
.acoes { margin-top:12px; padding-top:10px; border-top:1px dashed var(--g300);
         display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
.acoes form { display:flex; gap:6px; align-items:center; margin:0; }
.acoes button, .acoes select {
  font-family:var(--mono); font-size:11px; font-weight:700; letter-spacing:.04em;
  padding:6px 12px; border-radius:999px; border:1.5px solid var(--g300);
  background:var(--paper); color:var(--g700); cursor:pointer; }
.acoes button.salvar:hover { border-color:var(--olive); color:var(--olive); }
.acoes button.descartar:hover { border-color:var(--clay-d); color:var(--clay-d); }
.acoes select { border-radius:8px; font-weight:400; }
.quem { display:flex; gap:8px; margin:0 0 24px; font-family:var(--mono); font-size:12px; }
.quem a { padding:6px 14px; border-radius:999px; border:1.5px solid var(--g300);
          background:var(--paper); color:var(--g700); text-decoration:none; }
.quem a.ativo { background:var(--slate); border-color:var(--slate); color:var(--ivory); }
"""


def _chave_de_ordem(vaga, desejadas):
    """Devolve a chave que ordena uma vaga no feed.

    Por que esta funcao existe: a ordem do feed tem tres regras que precisam conviver -
    cidade desejada primeiro, depois data decrescente, e desempate estavel. Espalhar
    isso pela montagem do HTML tornaria impossivel testar a ordem sozinha.

    Entrada -> uma vaga e a lista de cidades desejadas.
    Fase 1  -> prioridade 0 para cidade desejada, 1 para o resto.
    Fase 2  -> data invertida, para o mais recente vir antes numa ordenacao crescente.
    Fase 3  -> fonte e identificador como desempate, para a ordem nunca variar entre
               duas execucoes com a mesma entrada.
    Saida   -> a tupla de ordenacao.
    """
    # Fase 1: pertencer a lista de desejadas vence qualquer data.
    prioridade = 0 if vaga.get("cidade") in desejadas else 1

    # Fase 2: a data vem como texto ISO. Convertida em numeros e negada, o mais recente
    # passa a vir primeiro numa ordenacao crescente comum. Vaga sem data recebe a data
    # minima, o que a joga para o fim - e correto, porque e a menos confiavel.
    texto = vaga.get("data_publicacao")
    if texto:
        publicacao = date.fromisoformat(texto)
        ordem_data = (-publicacao.year, -publicacao.month, -publicacao.day)
    else:
        ordem_data = (0, 0, 0)

    # Fase 3 e saida: desempate estavel, exigencia de determinismo.
    return (prioridade, ordem_data, vaga.get("fonte") or "", vaga.get("id_na_fonte") or "")


def _selo(texto, classe=""):
    """Monta um selo da barra de metadados do card."""
    # A classe extra e opcional; o espaco so entra quando ela existe.
    sufixo = " " + classe if classe else ""
    return '<span class="selo{}">{}</span>'.format(sufixo, escape(texto))


def _seletor_de_pessoa(quem):
    """Monta os links que trocam de quem e a sessao.

    Por que esta funcao existe: sao duas pessoas com perfis e estados independentes
    olhando o mesmo feed, e precisa haver como alternar. Nao e autenticacao - e um
    rotulo, porque multiusuario com login esta fora do escopo.

    Entrada -> o lado ativo, ou None na pagina estatica.
    Fase 1  -> na pagina sem servidor nao ha o que alternar, entao devolve linha vazia.
    Saida   -> o HTML dos dois links, com o ativo destacado.
    """
    # Fase 1: sem servidor, trocar de pessoa nao faz sentido.
    if not quem:
        return ""
    # Saida: ordem fixa, para a pagina nao variar entre execucoes.
    links = "".join(
        '<a class="{}" href="/?quem={}">{}</a>'.format(
            "ativo" if lado == quem else "", lado, rotulo)
        for lado, rotulo in (("meu", "as minhas"), ("dela", "as dela"))
    )
    return '      <div class="quem">{}</div>'.format(links)


def _acoes(vaga, quem, motivos):
    """Monta os botoes de marcacao de um card.

    Por que esta funcao existe: a marcacao acontece por formulario HTML puro, sem
    JavaScript. Sao dois formularios - um para salvar, outro para descartar com motivo -
    e mante-los fora da montagem do card deixa os dois legiveis.

    Por que sem JavaScript: o requisito declarado foi HTML o mais simples possivel, e
    formulario com POST resolve inteiro. Menos codigo, nada para carregar, funciona
    mesmo se algo quebrar.

    Entrada -> a vaga, de quem e a sessao e a lista fechada de motivos.
    Fase 1  -> monta os campos escondidos que identificam a vaga.
    Fase 2  -> monta o botao de salvar.
    Fase 3  -> monta o seletor de motivo mais o botao de descartar. O motivo e
               obrigatorio na 4.1, entao o campo entra com `required`.
    Saida   -> o HTML do bloco de acoes.
    """
    # Fase 1: os mesmos campos escondidos servem aos dois formularios. A marcacao aponta
    # para a chave do GRUPO, e nao para uma copia - senao descartar a vaga faria a
    # republicacao dela reaparecer amanha como se fosse nova.
    escondidos = "".join(
        '<input type="hidden" name="{}" value="{}">'.format(
            nome, escape(str(valor or ""), quote=True))
        for nome, valor in (
            ("id_canonico", vaga.get("id_canonico")),
            ("quem", quem),
        )
    )

    # Fase 2: salvar nao pede nada alem do clique.
    salvar = (
        '<form action="/marcar" method="post">{}'
        '<button class="salvar" name="estado" value="salva">salvar</button>'
        "</form>"
    ).format(escondidos)

    # Fase 3: `required` no seletor faz o proprio navegador cobrar o motivo antes de
    # enviar. A validacao de verdade continua no servidor - isto e so conveniencia.
    opcoes = '<option value="">motivo do descarte...</option>' + "".join(
        '<option value="{0}">{0}</option>'.format(escape(m)) for m in motivos
    )
    descartar = (
        '<form action="/marcar" method="post">{}'
        '<select name="motivo" required>{}</select>'
        '<button class="descartar" name="estado" value="descartada">descartar</button>'
        "</form>"
    ).format(escondidos, opcoes)

    # Saida: os dois formularios lado a lado.
    return '        <div class="acoes">{}{}</div>'.format(salvar, descartar)


def _card(vaga, desejadas, quem=None, motivos=()):
    """Monta o HTML de uma vaga.

    Por que esta funcao existe: isolar o card deixa a montagem da pagina legivel e da um
    unico lugar para acrescentar campo novo - o subtitulo da S3b, por exemplo.

    Entrada -> uma vaga e a lista de cidades desejadas.
    Fase 1  -> descobre se a cidade e desejada, o que muda a moldura e acrescenta selo.
    Fase 2  -> monta os selos de local, modalidade e salario.
    Fase 3  -> monta o rodape com data e link de origem.
    Saida   -> o HTML do card, sem quebra de linha final.
    """
    # Fase 1: cidade desejada ganha destaque visual e selo proprio. Vaga ja salva ganha
    # destaque proprio tambem, para nao se perder no meio das novas.
    e_desejada = vaga.get("cidade") in desejadas
    if vaga.get("estado") == "salva":
        classe_vaga = "vaga salva"
    elif e_desejada:
        classe_vaga = "vaga desejada"
    else:
        classe_vaga = "vaga"

    # Fase 2: os selos sao montados em ordem fixa, para a saida ser deterministica.
    selos = []
    if e_desejada:
        selos.append(_selo("cidade desejada", "desejada"))
    local = "{}/{}".format(vaga.get("cidade") or "?", vaga.get("uf") or "?")
    selos.append(_selo(local, "local"))
    modalidade = vaga.get("modalidade") or "desconhecido"
    selos.append(_selo(
        ROTULO_MODALIDADE.get(modalidade, modalidade),
        "remoto" if modalidade == "remoto" else "",
    ))
    if vaga.get("salario_texto"):
        selos.append(_selo(vaga["salario_texto"], "salario"))

    # Fase 3: data e links vivem no rodape do card, separados do conteudo.
    data = vaga.get("data_publicacao") or "data nao informada"
    origem = "{} &middot; {}".format(escape(vaga.get("fonte") or "?"), escape(data))

    # A decisao 3.7 pede um card com VARIOS links: a mesma vaga republicada tem mais de
    # um endereco, e a republicacao as vezes esta mais atualizada que a original.
    copias = vaga.get("origens") or [
        {"fonte": vaga.get("fonte"), "url": vaga.get("url")}
    ]
    if len(copias) > 1:
        # O aviso explica por que ha mais de um link; sem ele, o segundo pareceria erro.
        origem += " &middot; {} anuncios".format(len(copias))
        # O agrupador nao e decoracao: o rodape usa `justify-content: space-between`, e
        # links soltos como filhos diretos seriam espalhados um em cada ponta da tela.
        link = '<span class="links">{}</span>'.format("".join(
            '<a href="{}" target="_blank" rel="noopener">anuncio {}</a>'.format(
                escape(c.get("url") or "", quote=True), numero)
            for numero, c in enumerate(copias, 1)
        ))
    else:
        # O mesmo agrupador vale para o link unico, para os dois casos terem a mesma
        # estrutura e o CSS nao precisar tratar excecao.
        link = (
            '<span class="links">'
            '<a href="{}" target="_blank" rel="noopener">ver na origem</a>'
            "</span>"
        ).format(escape(copias[0].get("url") or "", quote=True))

    # As linhas do card sao montadas em lista para o controle de quebra ser explicito.
    linhas = [
        '      <article class="{}">'.format(classe_vaga),
        '        <div class="topo"><h2>{}</h2></div>'.format(
            escape(vaga.get("titulo_bruto") or "sem titulo")),
        '        <p class="empresa">{}</p>'.format(
            escape(vaga.get("empresa_bruta") or "empresa nao informada")),
    ]

    # O subtitulo so existe depois do enriquecimento (S3b). Vaga ainda nao enriquecida
    # nao ganha elemento vazio, que abriria um buraco no card sem motivo.
    if vaga.get("subtitulo"):
        linhas.append(
            '        <p class="subtitulo">{}</p>'.format(escape(vaga["subtitulo"]))
        )

    # "Por que esta vaga apareceu" (decisao 4.2). Com um perfil so, a etiqueta virou
    # tambem uma leitura rapida da especialidade, porque os sinonimos sao termos de area.
    casados = vaga.get("termos_casados") or []
    if casados:
        linhas.append(
            '        <p class="casamento"><span>casou por</span> {}</p>'.format(
                "".join('<em>{}</em>'.format(escape(t)) for t in casados)
            )
        )

    linhas += [
        '        <div class="meta">{}</div>'.format("".join(selos)),
        '        <div class="rodape-card"><span>{}</span>{}</div>'.format(origem, link),
    ]

    # Os botoes so existem quando ha servidor para recebe-los. Na pagina estatica
    # gravada em saida/, formulario seria botao que nao faz nada.
    if quem:
        linhas.append(_acoes(vaga, quem, motivos))

    # Saida: o card fechado.
    linhas.append("      </article>")
    return "\n".join(linhas)


def montar_feed(vagas, cidades_desejadas=(), gerado_em=None,
                quem=None, motivos=(), descartadas=0, filtradas=None,
                folha_do_site=None):
    """Monta a pagina inteira do feed.

    Por que esta funcao existe: e a fronteira entre dado e tela. Recebe dicionarios e
    devolve texto, sem tocar em disco nem em relogio - o que a torna testavel sozinha e
    deterministica por construcao.

    Entrada -> a lista de vagas, as cidades desejadas e, opcionalmente, o horario de
               geracao ja formatado.
    Fase 1  -> ordena pelas tres regras do feed.
    Fase 2  -> monta o resumo do topo, que e o primeiro sinal de que a coleta funcionou.
    Fase 3  -> monta um card por vaga, ou o aviso de pagina vazia.
    Fase 4  -> monta o rodape, com o horario apenas se ele tiver sido informado.
    Saida   -> o HTML completo, terminando em quebra de linha.
    """
    # Conjunto para a checagem de cidade desejada ser barata dentro do laco.
    desejadas = set(cidades_desejadas)

    # Fase 1: a ordem inteira vem de uma funcao so, testavel em separado.
    ordenadas = sorted(vagas, key=lambda v: _chave_de_ordem(v, desejadas))

    # Fase 2: o numero e a primeira coisa que diz se a coleta funcionou.
    #
    # A frase muda conforme quem le. Na versao do site ela conta vagas e estados em
    # portugues normal, porque e o que responde "vale a pena olhar isso hoje?". Na versao
    # local o texto e mais seco, porque quem le e quem construiu.
    if not ordenadas:
        resumo = "Nenhuma vaga no feed."
    elif folha_do_site:
        estados = {v.get("uf") for v in ordenadas if v.get("uf")}
        resumo = "<b>{}</b> {} em {} {}.".format(
            len(ordenadas),
            "vaga" if len(ordenadas) == 1 else "vagas",
            len(estados),
            "estado" if len(estados) == 1 else "estados",
        )
    else:
        resumo = "<b>{}</b> vaga(s) no feed.".format(len(ordenadas))

    # Esconder vaga sem dizer quantas foram escondidas seria limitacao silenciosa: nao
    # daria para saber se o feed encolheu porque filtrou bem ou porque a coleta falhou.
    if descartadas:
        resumo += " {} descartada(s), fora da lista.".format(descartadas)

    # O mesmo vale para os filtros: dizer quantas sumiram e por qual termo e o que permite
    # perceber que um termo esta reprovando demais. Contagem zerada NAO e exibida - com as
    # 27 UFs liberadas o filtro geografico nao remove nada, e anunciar "0" toda rodada
    # ensinaria a ignorar o aviso justamente quando ele passasse a importar.
    if filtradas:
        if filtradas.get("fora_do_mapa"):
            resumo += " {} fora dos estados liberados.".format(filtradas["fora_do_mapa"])
        reprovadas = filtradas.get("reprovadas") or {}
        if reprovadas:
            detalhe = ", ".join(
                "{} por {}".format(quantas, escape(termo))
                # Ordem fixa pela contagem e depois pelo nome, para a saida nao variar
                # entre execucoes com o mesmo acervo.
                for termo, quantas in sorted(
                    reprovadas.items(), key=lambda p: (-p[1], p[0]))
            )
            resumo += " Reprovadas por termo: {}.".format(detalhe)

    # Fase 3: pagina em branco seria indistinguivel de programa quebrado.
    if ordenadas:
        corpo = '    <div class="cards">\n{}\n    </div>'.format(
            "\n".join(_card(vaga, desejadas, quem, motivos) for vaga in ordenadas)
        )
    else:
        corpo = (
            '    <div class="vazio">Nenhuma vaga encontrada nesta rodada. '
            "Confira os avisos da coleta no terminal.</div>"
        )

    # Fase 4: o horario so aparece quando informado de fora.
    #
    # Na versao do site ele sobe para o resumo, e nao fica no rodape. Num feed de vagas a
    # pergunta "isso esta atualizado?" e das primeiras que a leitora faz, e a resposta nao
    # pode estar no fim da pagina depois de 262 cards.
    rodape = "Gerado por monitor_vagas."
    if gerado_em:
        if folha_do_site:
            resumo += " Atualizado em {}.".format(escape(gerado_em))
        else:
            rodape += " Atualizado em {}.".format(escape(gerado_em))

    # A folha do site so e linkada quando a pagina vai viver dentro dele. Rodando local
    # ela nao esta ao lado do arquivo, e um link quebrado polui o console de quem depura.
    cabecalho_extra = []
    if folha_do_site:
        cabecalho_extra.append(
            '<link rel="stylesheet" href="{}">'.format(escape(folha_do_site, quote=True))
        )
        # As mesmas fontes do site, para a pagina nao destoar.
        cabecalho_extra.append(
            '<link href="https://fonts.googleapis.com/css2?'
            "family=Dancing+Script:wght@600&family=Montserrat:wght@300;500&display=swap"
            '" rel="stylesheet">'
        )

    # O cabecalho de navegacao so aparece na versao do site: e o caminho de volta para a
    # home, sem o qual a unica saida seria o botao do navegador.
    if folha_do_site:
        topo = (
            '  <div class="topo-site">'
            '<div class="logo">Presente Rosa</div>'
            '<a href="index.html">&larr; voltar para a home</a>'
            "</div>"
        )
        assinatura = 'Feito para voce <span class="heart">&#128151;</span>'
    else:
        topo = ""
        assinatura = rodape

    # Saida: a estrutura e montada como lista de linhas para o controle de quebra ser
    # explicito - e o que garante bytes identicos entre duas execucoes.
    linhas_da_pagina = [
        "<!doctype html>",
        '<html lang="pt-BR">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Meta_Agregador de Vagas</title>",
    ]
    linhas_da_pagina += cabecalho_extra
    linhas_da_pagina += [
        "<style>{}</style>".format(ESTILO),
        "</head>",
        "<body>",
        topo,
        '  <div class="wrap">',
        '    <header class="cabecalho">',
        "      <h1>Meta_Agregador de Vagas</h1>",
        '      <p class="resumo">{}</p>'.format(resumo),
        _seletor_de_pessoa(quem),
        "    </header>",
        corpo,
        "  </div>",
        "  <footer><p>{}</p></footer>".format(assinatura),
        "</body>",
        "</html>",
        "",
    ]
    # Linhas vazias so existem quando um bloco opcional nao entrou; tira-las mantem a
    # saida limpa sem precisar de condicional no meio da lista.
    return "\n".join(l for l in linhas_da_pagina if l != "")
