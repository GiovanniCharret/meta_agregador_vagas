"""Orquestracao da coleta: percorre paginas de uma fonte e devolve vagas do projeto.

Por que este modulo existe separado de `fontes/`: os coletores sao funcoes puras, que
recebem HTML e devolvem registro. Alguem precisa decidir quantas paginas pedir, quando
parar, e o que fazer com vaga repetida - e essa logica e a mesma para todas as fontes.
Deixa-la em cada coletor seria repetir a mesma paginacao N vezes.

Por que o buscador entra por parametro em vez de ser importado: e o que permite testar
paginacao, deduplicacao e parada sem nenhuma requisicao de rede, e sem bater no site de
terceiro a cada execucao da suite.
"""

# EntradaInvalida sinaliza nome de fonte errado no config, que o usuario corrige.
from src.erros import EntradaInvalida

# Um modulo por fonte; por ora so o BNE, escolhido na sondagem da subfase S1.
from src.fontes import bne

# Registro das fontes conhecidas. Cada valor precisa expor `extrai_vagas`, `para_vaga`
# e `url_de_busca`. Acrescentar fonte nova e acrescentar uma linha aqui.
FONTES = {
    bne.NOME: bne,
}

# Endereco base de cada fonte, montado a partir do termo buscado.
BASES = {
    "bne": "https://www.bne.com.br/vagas-de-emprego-para-{termo}",
}


def _url_da_pagina(nome, termo, pagina):
    """Monta o endereco de uma pagina de resultados.

    Por que esta funcao existe: a forma de paginar e detalhe de cada fonte, e a
    sondagem mostrou que errar isso e facil - no BNE, das tres formas testadas
    (`?pagina=2`, `/2` e `?page=2`), so a ultima trouxe vagas ineditas. As outras
    devolviam a primeira pagina de novo, e a coleta pararia achando que acabou.

    Entrada -> o nome da fonte, o termo buscado e o numero da pagina, base 1.
    Fase 1  -> monta o endereco base com o termo.
    Fase 2  -> acrescenta o parametro de pagina, exceto na primeira.
    Saida   -> a URL completa.
    """
    # Fase 1: o termo entra no proprio caminho da URL nesta fonte.
    base = BASES[nome].format(termo=termo)
    # Fase 2: a primeira pagina nao leva parametro; as demais usam page=N.
    if pagina <= 1:
        return base
    return "{}?page={}".format(base, pagina)


def coletar_fonte(nome, termo, paginas, buscador, perfil=None):
    """Percorre as paginas de uma fonte e devolve as vagas ja no formato do projeto.

    Por que esta funcao existe: e o ponto onde a coleta deixa de ser assunto de uma
    fonte especifica. Daqui para frente o pipeline so ve vagas no formato unico.

    Entrada -> o nome da fonte, o termo de busca, o teto de paginas e a funcao que
               busca uma URL e devolve HTML.
    Fase 1  -> confere que a fonte existe, para erro de digitacao no config nao virar
               fonte ignorada em silencio.
    Fase 2  -> percorre as paginas, traduzindo cada registro para o formato do projeto.
    Fase 3  -> descarta repetida pelo identificador de origem, porque pagina de busca
               costuma repetir item na virada.
    Fase 4  -> para assim que uma pagina nao trouxer nada inedito, para nao fazer
               requisicao inutil ao site de terceiro.
    Saida   -> a lista de vagas ordenada pelo identificador de origem, para que duas
               coletas da mesma entrada produzam exatamente a mesma lista.
    """
    # Fase 1: nome desconhecido e erro de dado do usuario, e a mensagem tem que dizer
    # quais existem - ele nao tem como adivinhar.
    if nome not in FONTES:
        raise EntradaInvalida(
            'A fonte "{}" nao existe. Fontes disponiveis: {}.'.format(
                nome, ", ".join(sorted(FONTES))
            )
        )

    # O modulo da fonte escolhida, com as duas funcoes puras de extracao e traducao.
    fonte = FONTES[nome]

    # Acumula por identificador de origem: e o que garante a deduplicacao da Fase 3.
    encontradas = {}

    # Fase 2: percorre da primeira pagina ate o teto pedido.
    for numero in range(1, paginas + 1):
        # O endereco e guardado porque entra na mensagem de erro do coletor, que
        # precisa dizer qual termo a fonte nao reconheceu.
        endereco = _url_da_pagina(nome, termo, numero)

        # Busca o HTML da pagina pela funcao injetada.
        html = buscador(endereco)

        # Quantas vagas ineditas esta pagina trouxe, usado na decisao de parar.
        ineditas = 0

        # Fase 3: traduz cada registro e guarda so o que ainda nao foi visto.
        for registro in fonte.extrai_vagas(html, endereco):
            vaga = fonte.para_vaga(registro)
            # De qual perfil veio a busca. Hoje ha um perfil so e o campo parece
            # constante, mas os perfis dele voltam - e descobrir depois que o acervo nao
            # sabe de onde veio custaria uma remigracao.
            vaga["perfil"] = perfil
            chave = vaga["id_na_fonte"]
            if chave in encontradas:
                continue
            encontradas[chave] = vaga
            ineditas += 1

        # Fase 4: pagina que nao acrescentou nada significa fim dos resultados.
        if ineditas == 0:
            break

    # Saida: ordem estavel pelo identificador de origem, exigencia de determinismo.
    return [encontradas[chave] for chave in sorted(encontradas)]
