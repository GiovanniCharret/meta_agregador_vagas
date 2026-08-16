"""Leitura da pagina de detalhe de uma vaga.

Por que esta subfase existe: a listagem do BNE nao traz descricao nem salario real - ela
manda 0.0 em 100% das vagas medidas. A pagina de detalhe traz os dois, num bloco JSON-LD
do tipo JobPosting. E ali que mora a especialidade ("dentista especialista em
ortodontia"), que e o que discrimina duas vagas da mesma clinica - exatamente o que
faltava para a chave canonica revisada no D3.

Por que ela vem depois da persistencia, e nao antes: custa uma requisicao por vaga. Sem
estado no banco, a rodada refaria centenas de buscas de detalhe toda vez. Com estado, so
busca o que e inedito, e o custo decai sozinho.

Por que JSON-LD e nao raspagem de HTML: `JobPosting` e padrao schema.org, publicado pelos
sites para aparecerem no Google Empregos. Isso o torna mais estavel que qualquer seletor
de HTML - e, se outras fontes tambem publicarem, o mesmo codigo serve para todas.
"""

# json interpreta o bloco de dado estruturado.
import json

# re localiza os blocos e limpa marcacao e boilerplate.
import re

# Localiza cada bloco de dado estruturado da pagina.
PADRAO_JSONLD = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL
)

# Remove qualquer marcacao HTML de dentro do texto.
PADRAO_TAG = re.compile(r"<[^>]+>")

# Qualquer sequencia de espaco, tabulacao ou quebra vira um espaco so.
PADRAO_ESPACO = re.compile(r"\s+")

# Rabo de template que o BNE acrescenta a toda vaga. Nao informa nada: no subtitulo
# ocuparia o espaco util do card, e na chave canonica seria ruido igual em todas.
PADRAO_BOILERPLATE = re.compile(
    r"\s*o link para\s*Site da empresa:.*$", re.IGNORECASE | re.DOTALL
)

# Teto do subtitulo. Descricao inteira num card transformaria o feed em paragrafo.
LIMITE_SUBTITULO = 200

# Como cada unidade de periodo do schema.org se le em portugues.
PERIODO = {"HOUR": "hora", "DAY": "dia", "WEEK": "semana", "MONTH": "mes", "YEAR": "ano"}

# Faixas que a fonte grava quando o anunciante NAO informa salario. Medido em 16/08/2026:
# de 165 vagas enriquecidas do BNE, 163 traziam exatamente (1000, 15000) - 99% do acervo.
# Isso nao e salario, e preenchimento padrao de formulario.
#
# Deixar passar seria pior do que nao ter salario nenhum: o card anunciaria uma faixa que
# parece informacao e nao e, e ela entraria na comparacao entre vagas como se
# distinguisse algo, quando e igual em quase todas.
#
# Este conhecimento e especifico do BNE. Quando houver uma segunda fonte enriquecida, ele
# deve mudar para o modulo da fonte, em fontes/, junto com o resto do que so vale para ela.
FAIXAS_DE_PREENCHIMENTO_PADRAO = {(1000.0, 15000.0)}


def _limpo(texto):
    """Tira marcacao, boilerplate e espaco sobrando de um texto da fonte.

    Por que esta funcao existe: os dois campos de texto - descricao e responsabilidades -
    chegam com os mesmos tres problemas. Sem ela, a limpeza apareceria duplicada e um dia
    as duas versoes divergiriam.

    Entrada -> o texto como veio do dado estruturado, possivelmente nulo.
    Fase 1  -> remove as marcacoes HTML embutidas.
    Fase 2  -> corta o rabo de template do BNE.
    Fase 3  -> colapsa todo espaco em branco num espaco so, o que e o que torna o texto
               estavel o bastante para virar hash na S4.
    Saida   -> o texto limpo, ou string vazia quando nao havia nada.
    """
    # Campo ausente e campo vazio recebem o mesmo tratamento.
    if not texto:
        return ""
    # Fase 1: a descricao vem embrulhada em <p>.
    sem_tag = PADRAO_TAG.sub(" ", texto)
    # Fase 2: o corte vem antes do colapso de espaco porque o padrao tolera a quebra de
    # linha que a fonte insere no meio da frase.
    sem_rabo = PADRAO_BOILERPLATE.sub("", sem_tag)
    # Fase 3 e saida: espacamento estavel.
    return PADRAO_ESPACO.sub(" ", sem_rabo).strip()


def _texto_de_salario(base):
    """Traduz o salario do schema.org em texto no formato brasileiro.

    Por que esta funcao existe: o dado vem em tres pedacos - minimo, maximo e unidade de
    periodo - e cada um pode faltar. Montar isso no meio da extracao esconderia os casos.

    Entrada -> o objeto `baseSalary` do JobPosting, possivelmente nulo.
    Fase 1  -> le os tres pedacos, tolerando ausencia.
    Fase 2  -> desiste quando nao ha valor nenhum, para o feed nao anunciar R$ 0,00.
    Fase 3  -> formata no padrao BR: ponto no milhar, virgula no decimal.
    Saida   -> o texto, ou None quando a fonte nao informou.
    """
    # Fase 1: os sub-objetos podem vir nulos.
    valor = (base or {}).get("value") or {}
    minimo = valor.get("minValue") or 0
    maximo = valor.get("maxValue") or 0
    periodo = PERIODO.get(valor.get("unitText") or "", "")

    # Fase 2: zero nos dois lados significa nao informado.
    if not minimo and not maximo:
        return None

    # A faixa de preenchimento padrao tambem significa nao informado - a fonte grava um
    # intervalo fixo quando o anunciante deixa o campo em branco. Ver a constante.
    if (float(minimo), float(maximo)) in FAIXAS_DE_PREENCHIMENTO_PADRAO:
        return None

    def bra(numero):
        """Formata um numero no padrao brasileiro."""
        # O formato do Python usa virgula no milhar e ponto no decimal; a troca dupla
        # via marcador temporario inverte os dois sem embaralhar.
        return "{:,.2f}".format(numero).replace(",", "|").replace(".", ",").replace("|", ".")

    # Fase 3 e saida: faixa quando os dois lados diferem, valor unico quando iguais.
    if minimo and maximo and minimo != maximo:
        texto = "R$ {} a R$ {}".format(bra(minimo), bra(maximo))
    else:
        texto = "R$ {}".format(bra(minimo or maximo))
    return "{} por {}".format(texto, periodo) if periodo else texto


def _subtitulo(responsabilidades, descricao):
    """Escolhe o texto curto que vai aparecer sob o titulo do card.

    Por que esta funcao existe: o titulo do BNE e generico - "dentista" para todas as
    vagas - e o subtitulo e o que devolve informacao ao card. A escolha tem duas regras
    que precisam conviver, e deixa-las soltas na extracao esconderia a segunda.

    Entrada -> as responsabilidades e a descricao, ambas ja limpas.
    Fase 1  -> prefere as responsabilidades, que sao o campo mais especifico da fonte.
    Fase 2  -> cai para a descricao quando elas vierem nulas, o que acontece em parte das
               vagas - foi medido na sondagem.
    Fase 3  -> corta no limite do card, preferindo cortar no fim de uma frase.
    Saida   -> o subtitulo.
    """
    # Fase 1 e 2: a primeira que tiver conteudo vence.
    texto = responsabilidades or descricao
    if not texto:
        return ""

    # Fase 3: cabe inteiro, nao ha o que cortar.
    if len(texto) <= LIMITE_SUBTITULO:
        return texto

    # Corta no limite e recua ate o ultimo ponto final, para nao terminar no meio de uma
    # palavra. Se nao houver ponto, corta na palavra mesmo e sinaliza com reticencias.
    pedaco = texto[:LIMITE_SUBTITULO]
    ponto = pedaco.rfind(". ")
    if ponto > 60:
        return pedaco[: ponto + 1]
    return pedaco.rsplit(" ", 1)[0] + "..."


def extrai_detalhe(html):
    """Le os campos uteis da pagina de detalhe de uma vaga.

    Por que esta funcao existe separada da busca pela rede: mesma razao dos coletores -
    funcao pura, testavel com fixture, sem internet ligada.

    Entrada -> o HTML da pagina de detalhe.
    Fase 1  -> percorre os blocos de dado estruturado procurando o do tipo JobPosting.
    Fase 2  -> desiste devolvendo nada quando nao houver, porque pagina fora do padrao
               deve virar aviso e nao derrubar a rodada.
    Fase 3  -> limpa os textos e monta salario e subtitulo.
    Saida   -> o dicionario com os campos, ou None.
    """
    # Fase 1: alguns sites embrulham varios objetos numa lista so.
    vaga = None
    for bruto in PADRAO_JSONLD.findall(html):
        try:
            dado = json.loads(bruto.strip())
        except json.JSONDecodeError:
            # Bloco quebrado nao invalida os outros da mesma pagina.
            continue
        for item in (dado if isinstance(dado, list) else [dado]):
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                vaga = item
                break
        if vaga:
            break

    # Fase 2: sem dado estruturado nao ha o que enriquecer; quem chamou emite o aviso.
    if vaga is None:
        return None

    # Fase 3: os dois textos passam pela mesma limpeza.
    descricao = _limpo(vaga.get("description"))
    responsabilidades = _limpo(vaga.get("responsibilities"))

    # Saida: so os campos que o feed e a chave canonica usam.
    return {
        "descricao": descricao,
        "subtitulo": _subtitulo(responsabilidades, descricao),
        "salario_texto": _texto_de_salario(vaga.get("baseSalary")),
        "tipo_vinculo": vaga.get("employmentType"),
    }
