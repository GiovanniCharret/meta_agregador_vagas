"""Acesso a rede - a unica parte do projeto que fala com a internet.

Por que este modulo existe isolado: manter os coletores puros. Eles recebem HTML e
devolvem registro, sem saber de onde o HTML veio, e e isso que permite testa-los com
fixture em vez de internet ligada. Toda a rede mora aqui.

Postura de coleta, herdada da leitura da pesquisa em `minhas_notas/`: uma requisicao
por pagina, sem paralelismo, com pausa entre elas, tempo limite curto e User-Agent
honesto que identifica o projeto em vez de fingir ser um navegador. Fonte que responde
403 e tratada como fonte indisponivel - o projeto nao contorna bloqueio.
"""

# time da a pausa entre requisicoes.
import time

# requests faz a requisicao HTTP.
import requests

# FonteIndisponivel traduz status HTTP em vocabulario do projeto.
from src.erros import FonteIndisponivel

# Identificacao honesta: diz o que o programa e, sem se passar por navegador.
CABECALHOS = {
    "User-Agent": "monitor_vagas/0.1 (projeto pessoal de busca de emprego)",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# Tempo limite por requisicao, em segundos. Curto de proposito: fonte lenta nao pode
# travar a rodada inteira.
LIMITE_SEGUNDOS = 25

# Pausa entre requisicoes, em segundos. Existe para nao pesar sobre o site de terceiro.
PAUSA_SEGUNDOS = 2


def busca(url):
    """Busca uma URL e devolve o HTML como texto.

    Por que esta funcao existe: e o buscador injetado em `coletar_fonte`. Nos testes ele
    e substituido por uma funcao falsa; em producao, e este.

    Entrada -> o endereco a buscar.
    Fase 1  -> pausa antes de pedir, para espacar as requisicoes.
    Fase 2  -> faz a requisicao com identificacao honesta e tempo limite.
    Fase 3  -> devolve o corpo como texto quando a resposta for 200.
    Saida   -> o HTML da pagina.
    """
    # Fase 1: a pausa vem antes para valer tambem entre paginas consecutivas.
    time.sleep(PAUSA_SEGUNDOS)

    # Fase 2: sem retentativa nem paralelismo - simples de proposito nesta fase.
    resposta = requests.get(url, headers=CABECALHOS, timeout=LIMITE_SEGUNDOS)

    # Fase 3: qualquer status diferente de 200 vira FonteIndisponivel com o codigo
    # visivel, para o operador distinguir bloqueio (403) de pagina inexistente (404).
    # A excecao e do projeto, e nao a do requests, para o resto do codigo nao precisar
    # conhecer a biblioteca de rede que usamos.
    if resposta.status_code != 200:
        raise FonteIndisponivel(
            "{} respondeu {} em {}".format(
                resposta.status_code, resposta.reason or "", url
            ).replace("  ", " ")
        )

    # Saida: o texto ja decodificado pelo requests.
    return resposta.text
