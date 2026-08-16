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

# Folha de estilo embutida. Inline de proposito: a pagina tem que abrir com duplo clique,
# sem servidor e sem arquivo ao lado.
ESTILO = """
:root {
  --ivory:#FAF9F5; --paper:#FFF; --slate:#141413;
  --clay:#D97757; --clay-d:#B85C3E; --oat:#E3DACC;
  --olive:#788C5D; --ice:#5F7A8A;
  --g100:#F0EEE6; --g300:#D1CFC5; --g500:#87867F; --g700:#3D3D3A;
  --serif: ui-serif, Georgia, "Times New Roman", serif;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
body { margin:0; background:var(--ivory); color:var(--slate);
       font-family:var(--sans); line-height:1.55; }
.wrap { max-width:900px; margin:0 auto; padding:0 24px 80px; }
header { padding:48px 0 8px; }
.eyebrow { font-family:var(--mono); font-size:12px; letter-spacing:.12em;
           text-transform:uppercase; color:var(--g500); margin-bottom:16px;
           display:flex; align-items:center; gap:12px; }
.eyebrow::before { content:""; width:24px; height:1.5px; background:var(--clay); }
h1 { font-family:var(--serif); font-weight:500; font-size:clamp(30px,4vw,42px);
     line-height:1.1; letter-spacing:-.018em; margin:0 0 8px; }
.resumo { font-size:15px; color:var(--g700); margin:0 0 32px; }
.resumo b { color:var(--clay-d); font-weight:600; }
.vazio { border:1.5px dashed var(--g300); border-radius:12px; padding:32px;
         text-align:center; color:var(--g700); font-size:15px; }
.cards { display:flex; flex-direction:column; gap:12px; }
.vaga { border:1.5px solid var(--g300); border-radius:12px; background:var(--paper);
        padding:16px 18px; }
.vaga.desejada { border-color:var(--clay); background:#FDF6F2; }
.topo { display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; }
.vaga h2 { font-family:var(--serif); font-weight:500; font-size:19px;
           margin:0; flex:1 1 auto; min-width:180px; letter-spacing:-.01em; }
.empresa { font-size:14px; color:var(--g700); margin:6px 0 0; }
.meta { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.selo { font-family:var(--mono); font-size:10.5px; font-weight:700;
        letter-spacing:.05em; border-radius:999px; padding:3px 10px;
        border:1.5px solid var(--g300); background:var(--g100); color:var(--g700); }
.selo.local { background:var(--oat); border-color:var(--g300); color:#7A6A4F; }
.selo.remoto { background:#EDF2F5; border-color:#C7D6DE; color:var(--ice); }
.selo.salario { background:#EEF2E6; border-color:#C9D4B6; color:var(--olive); }
.selo.desejada { background:var(--clay); border-color:var(--clay-d); color:#fff; }
.rodape-card { margin-top:12px; padding-top:10px; border-top:1px dashed var(--g300);
               display:flex; justify-content:space-between; gap:12px;
               font-size:12.5px; color:var(--g500); flex-wrap:wrap; }
.rodape-card a { color:var(--clay-d); text-decoration-color:var(--oat);
                 text-underline-offset:3px; }
footer { margin-top:40px; font-size:12.5px; color:var(--g500); }
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


def _card(vaga, desejadas):
    """Monta o HTML de uma vaga.

    Por que esta funcao existe: isolar o card deixa a montagem da pagina legivel e da um
    unico lugar para acrescentar campo novo - o subtitulo da S3b, por exemplo.

    Entrada -> uma vaga e a lista de cidades desejadas.
    Fase 1  -> descobre se a cidade e desejada, o que muda a moldura e acrescenta selo.
    Fase 2  -> monta os selos de local, modalidade e salario.
    Fase 3  -> monta o rodape com data e link de origem.
    Saida   -> o HTML do card, sem quebra de linha final.
    """
    # Fase 1: cidade desejada ganha destaque visual e selo proprio.
    e_desejada = vaga.get("cidade") in desejadas
    classe_vaga = "vaga desejada" if e_desejada else "vaga"

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

    # Fase 3: data e link vivem no rodape do card, separados do conteudo.
    data = vaga.get("data_publicacao") or "data nao informada"
    origem = "{} &middot; {}".format(escape(vaga.get("fonte") or "?"), escape(data))
    link = '<a href="{}" target="_blank" rel="noopener">ver na origem</a>'.format(
        escape(vaga.get("url") or "", quote=True)
    )

    # Saida: as linhas sao juntadas com quebra fixa, sem depender de formatacao externa.
    return "\n".join([
        '      <article class="{}">'.format(classe_vaga),
        '        <div class="topo"><h2>{}</h2></div>'.format(
            escape(vaga.get("titulo_bruto") or "sem titulo")),
        '        <p class="empresa">{}</p>'.format(
            escape(vaga.get("empresa_bruta") or "empresa nao informada")),
        '        <div class="meta">{}</div>'.format("".join(selos)),
        '        <div class="rodape-card"><span>{}</span>{}</div>'.format(origem, link),
        "      </article>",
    ])


def montar_feed(vagas, cidades_desejadas=(), gerado_em=None):
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
    if ordenadas:
        resumo = "<b>{}</b> vaga(s) no feed.".format(len(ordenadas))
    else:
        resumo = "Nenhuma vaga no feed."

    # Fase 3: pagina em branco seria indistinguivel de programa quebrado.
    if ordenadas:
        corpo = '    <div class="cards">\n{}\n    </div>'.format(
            "\n".join(_card(vaga, desejadas) for vaga in ordenadas)
        )
    else:
        corpo = (
            '    <div class="vazio">Nenhuma vaga encontrada nesta rodada. '
            "Confira os avisos da coleta no terminal.</div>"
        )

    # Fase 4: o horario so aparece quando informado de fora.
    rodape = "Gerado por monitor_vagas."
    if gerado_em:
        rodape += " Atualizado em {}.".format(escape(gerado_em))

    # Saida: a estrutura e montada como lista de linhas para o controle de quebra ser
    # explicito - e o que garante bytes identicos entre duas execucoes.
    return "\n".join([
        "<!doctype html>",
        '<html lang="pt-BR">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Feed de vagas</title>",
        "<style>{}</style>".format(ESTILO),
        "</head>",
        "<body>",
        '  <div class="wrap">',
        "    <header>",
        '      <div class="eyebrow">monitor_vagas</div>',
        "      <h1>Feed de vagas</h1>",
        '      <p class="resumo">{}</p>'.format(resumo),
        "    </header>",
        corpo,
        "    <footer>{}</footer>".format(rodape),
        "  </div>",
        "</body>",
        "</html>",
        "",
    ])
