"""Executavel unico do monitor_vagas.

Por que este modulo existe: o projeto tem layout achatado e um so ponto de entrada.
E aqui que a regra central sobre falhas se materializa - erro de dado do usuario vira
mensagem limpa e codigo de saida 1, enquanto bug de programa continua levantando
traceback normal. Deixar essa distincao em qualquer outro lugar faria cada modulo ter
que decidir sozinho o que mostrar ao usuario.

No estado atual (subfase S0) ele so le e valida a configuracao. As fases seguintes
penduram coleta, normalizacao, deduplicacao, filtros e feed neste mesmo lugar.
"""

# sys da acesso a saida de erro e ao codigo de saida do processo.
import sys

# O caminho padrao da configuracao vive na ancora de caminhos, nao aqui.
from src.caminhos import ARQUIVO_CONFIG

# carregar_config e a unica porta de entrada de dado do usuario no programa.
from src.config import carregar_config

# EntradaInvalida e o contrato que separa erro do usuario de bug nosso.
from src.erros import EntradaInvalida


def main(caminho=None, usar_padrao=True):
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
        "Configuracao lida: {} perfil(is), {} UF(s) bloqueada(s).".format(
            len(configuracao.perfis), len(configuracao.ufs_bloqueadas)
        )
    )
    # Saida: zero significa rodada bem sucedida.
    return 0


# Este modulo nao tem bloco de execucao direta de proposito. Chamar `python src/main.py`
# colocaria src/ no caminho de import em vez da raiz, e os imports acima falhariam. O
# unico ponto de entrada e o monitor.py da raiz.
