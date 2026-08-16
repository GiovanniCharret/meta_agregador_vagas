"""Executavel unico do monitor_vagas.

Por que este modulo existe: o projeto tem layout achatado e um so ponto de entrada.
E aqui que a regra central sobre falhas se materializa - erro de dado do usuario vira
mensagem limpa e codigo de saida 1, enquanto bug de programa continua levantando
traceback normal. Deixar essa distincao em qualquer outro lugar faria cada modulo ter
que decidir sozinho o que mostrar ao usuario.

No estado atual (subfase S0) ele so le e valida a configuracao. As fases seguintes
penduram coleta, normalizacao, deduplicacao, filtros e feed neste mesmo lugar.
"""

# json grava o resultado normalizado da coleta.
import json

# sys da acesso a saida de erro e ao codigo de saida do processo.
import sys

# Os caminhos padrao vivem na ancora de caminhos, nao aqui.
from src.caminhos import ARQUIVO_CONFIG, DIR_DADOS

# coletar_fonte percorre as paginas de uma fonte e devolve vagas ja traduzidas.
from src.coleta import coletar_fonte

# carregar_config e a unica porta de entrada de dado do usuario no programa.
from src.config import carregar_config

# As tres excecoes que a rodada trata de formas diferentes.
from src.erros import EntradaInvalida, EstruturaInesperada, FonteIndisponivel

# para_slug transforma o termo escrito a mao no pedaco de URL da fonte.
from src.normaliza import para_slug

# rede e o buscador de verdade; nos testes ele e substituido por uma funcao falsa.
from src import rede

# Teto de paginas por termo. Baixo de proposito nesta fase: a coleta para sozinha
# quando a pagina nao traz nada inedito, e pedir muito seria abusar da fonte.
PAGINAS_POR_TERMO = 3


def _coleta_tudo(configuracao, buscador):
    """Percorre fontes ativas e termos de cada perfil, juntando as vagas encontradas.

    Por que esta funcao existe: separa a politica de rodada - o que fazer quando uma
    fonte nao tem coletor ou mudou de formato - da mecanica de paginar, que vive em
    `coletar_fonte`. A funcao de baixo e estrita e levanta excecao; e aqui que se
    decide que uma fonte com problema vira aviso e nao derruba as outras.

    Entrada -> a configuracao lida e a funcao que busca uma URL.
    Fase 1  -> percorre cada fonte ativa e cada termo de cada perfil.
    Fase 2  -> converte o termo em slug, porque ele entra dentro da URL.
    Fase 3  -> coleta, transformando problema de fonte em aviso visivel.
    Fase 4  -> junta tudo numa chave unica de fonte mais identificador de origem, para
               o mesmo anuncio encontrado por dois termos nao entrar duas vezes.
    Saida   -> a lista de vagas, ordenada de forma estavel.
    """
    # Acumula por chave de origem: e o que impede o mesmo anuncio, achado por dois
    # termos diferentes do mesmo perfil, de aparecer duplicado.
    encontradas = {}

    # Fase 1: fonte por fonte, na ordem em que o usuario escreveu.
    for nome_da_fonte in configuracao.fontes_ativas:
        # Conta quantas vagas esta fonte trouxe, para o resumo do fim.
        antes = len(encontradas)

        for perfil in configuracao.perfis:
            for termo in perfil.termos:
                # Fase 2: o termo entra no caminho da URL, entao precisa virar slug.
                alvo = para_slug(termo)

                # Fase 3: os dois problemas possiveis de fonte viram aviso, nunca
                # interrupcao - uma fonte quebrada nao pode impedir a coleta das outras.
                try:
                    vagas = coletar_fonte(
                        nome_da_fonte, alvo, PAGINAS_POR_TERMO, buscador
                    )
                except EntradaInvalida as erro:
                    # Fonte sem coletor: avisa uma vez e passa para a proxima fonte.
                    print("AVISO: {}".format(erro))
                    break
                except EstruturaInesperada as erro:
                    # Site mudou de formato: avisa e segue com as demais.
                    print("AVISO: {}".format(erro))
                    continue
                except FonteIndisponivel as erro:
                    # Termo inexistente naquela fonte (404), bloqueio (403) ou site
                    # fora do ar: nada rendeu agora, mas os outros termos seguem.
                    print("AVISO: {}".format(erro))
                    continue

                # Fase 4: a chave junta fonte e identificador de origem.
                for vaga in vagas:
                    encontradas[(vaga["fonte"], vaga["id_na_fonte"])] = vaga
            else:
                # O for interno terminou sem break; segue para o proximo perfil.
                continue
            # Houve break la dentro: a fonte nao tem coletor, entao abandona o perfil.
            break

        # Resumo por fonte, para o usuario ver de onde veio o que.
        print("  {}: {} vaga(s).".format(nome_da_fonte, len(encontradas) - antes))

    # Saida: ordem estavel pela chave, exigencia de determinismo.
    return [encontradas[chave] for chave in sorted(encontradas)]


def main(caminho=None, usar_padrao=True, buscador=None, destino=None):
    """Le a configuracao e devolve o codigo de saida do processo.

    Por que esta funcao existe: concentra o tratamento de falha num unico lugar, para
    que nenhum modulo do pipeline precise decidir se um problema deve virar mensagem
    para o usuario ou traceback para nos.

    Entrada -> opcionalmente o caminho da configuracao; sem ele, usa o caminho padrao
               do projeto. O parametro existe para os testes rodarem sobre arquivos
               temporarios sem depender do config real da maquina.
    Fase 1  -> resolve qual arquivo sera lido.
    Fase 2  -> tenta carregar e validar a configuracao.
    Fase 3  -> se o dado estiver torto, escreve a mensagem pronta na saida de erro e
               devolve 1, sem deixar traceback vazar para o usuario final.
    Fase 4  -> se estiver tudo certo, informa o que foi carregado.
    Saida   -> 0 em caso de sucesso, 1 em caso de erro de dado.
    """
    # Fase 1: usar_padrao=False permite ao teste passar None de proposito e provar que
    # um bug de programa nao e engolido pelo except abaixo.
    if caminho is None and usar_padrao:
        caminho = ARQUIVO_CONFIG

    # Fase 2 e 3: apenas EntradaInvalida e capturada. Qualquer outra excecao sobe como
    # traceback, porque significa defeito no programa e nao no dado do usuario.
    try:
        configuracao = carregar_config(caminho)
    except EntradaInvalida as erro:
        # A mensagem ja vem pronta para o usuario final de quem a levantou.
        print("ERRO: {}".format(erro), file=sys.stderr)
        # Codigo 1 permite que um .bat ou agendador detecte a falha.
        return 1

    # Fase 4: confirmacao curta do que foi lido, para o usuario ver que a configuracao
    # esta sendo enxergada como ele espera.
    print(
        "Configuracao lida: {} perfil(is), {} estado(s) liberado(s).".format(
            len(configuracao.perfis), len(configuracao.ufs_liberadas)
        )
    )

    # Fase 5: em producao o buscador e o de rede; nos testes, uma funcao falsa.
    if buscador is None:
        buscador = rede.busca

    # Fase 6: o destino padrao fica em dados/, que e irmao de src/ e nao entra no
    # controle de versao.
    if destino is None:
        destino = DIR_DADOS / "vagas_normalizadas.json"

    # Fase 7: a coleta em si. Problema de fonte vira aviso la dentro, nao excecao.
    print("Coletando...")
    vagas = _coleta_tudo(configuracao, buscador)

    # Fase 8: o diretorio pode nao existir na primeira execucao.
    destino.parent.mkdir(parents=True, exist_ok=True)

    # Fase 9: indent fixo e sort_keys deixam o arquivo estavel entre execucoes, o que a
    # subfase S2 vai exigir para gerar HTML identico byte a byte. ensure_ascii=False
    # mantem os acentos legiveis para quem abrir o arquivo.
    destino.write_text(
        json.dumps(vagas, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Confirmacao final com o que foi produzido e onde.
    print("{} vaga(s) gravada(s) em {}".format(len(vagas), destino))

    # Saida: zero significa rodada bem sucedida.
    return 0


# Este modulo nao tem bloco de execucao direta de proposito. Chamar `python src/main.py`
# colocaria src/ no caminho de import em vez da raiz, e os imports acima falhariam. O
# unico ponto de entrada e o monitor.py da raiz.
