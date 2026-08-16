"""Coletor da fonte BNE - Banco Nacional de Empregos.

Por que esta fonte foi a escolhida para a primeira subfase: das cinco candidatas
sondadas em 16/08/2026, Catho e Jooble responderam 403 (o Jooble com desafio
Cloudflare) e nao entram sem contornar bloqueio, coisa que o projeto nao faz. Das tres
que responderam, o BNE foi a de extracao mais barata e dado mais completo:

  - a pagina de resultados guarda a lista INTEIRA de vagas como JSON escapado dentro de
    um input escondido, entao nao e preciso interpretar HTML nem instalar parser;
  - cobertura de 100% nos campos que o modelo precisa: cidade, UF, empresa, URL e data;
  - vinte vagas por pagina, espalhadas por dez estados diferentes.

Armadilha da fonte, encontrada na sondagem e travada por teste: existem DOIS campos de
UF. O que fica dentro de `City` vem nulo em 100% das vagas medidas; o que vale e o
`StateAbbreviation` do topo do registro.

Limitacao conhecida: o BNE nao devolve o titulo original do anuncio - `Titulo` vem nulo
em 100% dos casos e o que sobra e `Function.Name`, que e a funcao normalizada por eles
("dentista"). Isso enfraquece a chave canonica de deduplicacao para esta fonte, porque
o titulo deixa de discriminar. Fica registrado para a subfase S4.
"""

# html.unescape desfaz o escape do JSON que vem dentro do atributo do input.
import html as libhtml

# json interpreta o conteudo do input, que e uma lista de vagas.
import json

# re localiza o input escondido dentro da pagina.
import re

# As duas excecoes que a ausencia do bloco pode significar.
from src.erros import EstruturaInesperada, FonteIndisponivel

# Nome curto da fonte, usado no campo `fonte` de cada vaga e nas mensagens de erro.
NOME = "bne"

# O bloco onde o BNE guarda a lista de vagas. O padrao aceita tanto `>` quanto `/>` no
# fim porque a pagina real e a fixture diferem nesse detalhe irrelevante.
PADRAO_BLOCO = re.compile(r'id="jobInfoLocal"\s+value="(.*?)"\s*/?>', re.DOTALL)

# O canonical da pagina. Quando o slug de funcao nao existe na taxonomia do BNE, o site
# responde 200 servindo a pagina inicial, e o unico sinal confiavel dessa troca e o
# canonical apontar para a raiz em vez de apontar para a URL pedida.
PADRAO_CANONICAL = re.compile(
    r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', re.IGNORECASE
)

# Enderecos que identificam a raiz do site.
RAIZES = ("https://www.bne.com.br/", "https://www.bne.com.br")


def extrai_vagas(html, url=""):
    """Devolve os registros crus de vaga contidos numa pagina de resultados do BNE.

    Por que esta funcao existe separada da busca pela rede: coletor que so pode ser
    testado com internet ligada nao e testado. Recebendo o HTML pronto, ela vira uma
    funcao pura, exercitavel com fixture.

    Entrada -> o HTML de uma pagina de resultados e, opcionalmente, a URL pedida, usada
               so para deixar a mensagem de erro acionavel.
    Fase 1  -> localiza o input escondido que carrega a lista de vagas.
    Fase 2  -> quando o bloco falta, distingue termo inexistente de mudanca de formato.
    Fase 3  -> desfaz o escape de atributo HTML, recuperando o JSON original.
    Fase 4  -> interpreta o JSON.
    Saida   -> a lista de registros crus, no formato do proprio BNE.
    """
    # Fase 1: sem o bloco, a extracao devolveria zero vaga, que e indistinguivel de
    # "nao ha vaga hoje". Melhor falhar alto do que esvaziar o feed em silencio.
    achado = PADRAO_BLOCO.search(html)
    if achado is None:
        # Fase 2: sao dois motivos possiveis, com consequencias opostas. O BNE responde
        # 200 servindo a pagina inicial quando o slug de funcao nao existe na taxonomia
        # dele - e ai o canonical aponta para a raiz. Isso e problema do termo escrito
        # no config, nao do coletor, e nao pode virar alarme de mudanca de formato.
        canonical = PADRAO_CANONICAL.search(html)
        if canonical and canonical.group(1).strip() in RAIZES:
            raise FonteIndisponivel(
                'A fonte {} nao conhece esse termo de busca ({}): ela respondeu com a '
                "pagina inicial. Troque o termo no config por um que exista la - por "
                "exemplo, ela conhece 'dentista' mas nao 'cirurgiao-dentista'.".format(
                    NOME, url or "sem URL"
                )
            )
        # Sem o sinal do canonical, a ausencia do bloco e mesmo inesperada.
        raise EstruturaInesperada(
            "A fonte {} mudou de formato: o bloco jobInfoLocal nao foi encontrado "
            "na pagina. O coletor precisa ser revisto.".format(NOME)
        )

    # Fase 2: o JSON vem dentro de um atributo, entao aspas e acentos estao escapados.
    texto = libhtml.unescape(achado.group(1))

    # Fase 3: o conteudo e uma lista de objetos, um por vaga.
    try:
        registros = json.loads(texto)
    except json.JSONDecodeError as falha:
        # JSON quebrado aqui tambem significa mudanca de formato, nao erro do usuario.
        raise EstruturaInesperada(
            "A fonte {} devolveu um bloco jobInfoLocal ilegivel: {}.".format(NOME, falha)
        ) from falha

    # Saida: os registros seguem crus; a traducao acontece em para_vaga.
    return registros


def _texto_de_salario(minimo, maximo):
    """Traduz o par de salarios do BNE em texto, ou em nada quando nao informado.

    Por que esta funcao existe: o BNE manda 0.0 nos dois campos quando a empresa nao
    informou salario. Deixar o zero passar faria o feed anunciar vaga de R$ 0,00, que e
    pior do que nao mostrar valor nenhum.

    Entrada -> os dois numeros como vieram da fonte.
    Fase 1  -> trata ausencia e zero como o mesmo caso: nao informado.
    Fase 2  -> monta o texto quando ha valor.
    Saida   -> uma string legivel, ou None quando nao ha informacao.
    """
    # Fase 1: `or 0` cobre None; a soma cobre o caso dos dois zerados de uma vez.
    if not (minimo or 0) and not (maximo or 0):
        return None
    # Fase 2: mantido como texto cru de proposito - nenhum item aprovado filtra por
    # salario, e modelar moeda e periodo agora seria trabalho especulativo (D2).
    if minimo and maximo and minimo != maximo:
        return "R$ {:.2f} a R$ {:.2f}".format(minimo, maximo)
    return "R$ {:.2f}".format(minimo or maximo)


def para_vaga(registro):
    """Traduz um registro cru do BNE para o formato unico do projeto.

    Por que esta funcao existe: e o contrato entre a fonte e o resto do pipeline. Toda
    diferenca de nome e de formato do BNE morre aqui; normalizacao, deduplicacao e feed
    so conhecem o formato de saida.

    Entrada -> um registro cru, como veio de extrai_vagas.
    Fase 1  -> le os campos de identificacao e origem.
    Fase 2  -> le localizacao, pegando a UF do topo do registro e nao de dentro de
               City, que vem nula em 100% das vagas medidas.
    Fase 3  -> traduz a modalidade a partir do sinalizador de home office.
    Fase 4  -> resolve salario e data, descartando o que a fonte nao informou.
    Saida   -> um dicionario no formato do projeto, sem nenhum carimbo de horario -
               determinismo e regra, e a hora de coleta pertence a camada de gravacao.
    """
    # Sub-objetos podem vir nulos; `or {}` evita ter que checar cada acesso.
    cidade = registro.get("City") or {}
    funcao = registro.get("Function") or {}

    # Fase 1: o Id vira texto porque identificador nao e numero para fazer conta.
    identificador = str(registro.get("Id"))

    # Fase 4: a data vem como timestamp com fuso e milissegundo; guardar so a data
    # evita diferenca falsa entre duas coletas da mesma vaga.
    publicacao = registro.get("PostDate") or ""

    return {
        # Fase 1: origem do dado, para o card poder mostrar de onde veio.
        "fonte": NOME,
        "id_na_fonte": identificador,
        "url": registro.get("Url"),
        # O titulo possivel: o BNE nao expoe o titulo original do anuncio.
        "titulo_bruto": funcao.get("Name"),
        "empresa_bruta": registro.get("CompanyName"),
        # Fase 2: a UF que presta e a do topo, nao a de dentro de City.
        "cidade": cidade.get("Name"),
        "uf": registro.get("StateAbbreviation"),
        # Fase 3: remoto e categoria separada, e nao coringa (decisao da pergunta 2).
        "modalidade": "remoto" if registro.get("Home_Office") else "presencial",
        # Fase 4: zero na fonte significa nao informado, e vira ausencia aqui.
        "salario_texto": _texto_de_salario(
            registro.get("MinSalary"), registro.get("MaxSalary")
        ),
        "data_publicacao": publicacao[:10] or None,
    }
