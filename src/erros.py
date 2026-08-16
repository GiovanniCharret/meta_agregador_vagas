"""Excecoes proprias do projeto.

Por que este modulo existe: o projeto distingue dois tipos de falha que precisam de
tratamento oposto. Erro de dado do usuario deve sair com codigo 1 e uma mensagem que
ele consiga ler e corrigir, sem traceback. Bug de programa deve levantar traceback
normal, porque quem precisa ler aquilo somos nos. Ter uma excecao propria e o que
permite ao executavel capturar so o primeiro caso e deixar o segundo passar.
"""


class EntradaInvalida(Exception):
    """Dado de entrada que o usuario pode corrigir sozinho.

    Por que esta classe existe: e o contrato entre a validacao e o executavel. Quem
    levanta esta excecao esta afirmando que a mensagem ja esta pronta para o usuario
    final - sem jargao de biblioteca, citando o valor errado e o que se esperava.

    Herda direto de Exception, e nao de KeyError ou ValueError, justamente para que o
    `except EntradaInvalida` do executavel nao capture, por acidente, um bug de
    programa que deveria vazar como traceback.
    """


class EstruturaInesperada(Exception):
    """A pagina de uma fonte nao tem mais o formato que o coletor espera.

    Por que esta classe existe e por que ela nao e EntradaInvalida: aqui nao ha nada
    que o usuario possa corrigir no arquivo dele, e tambem nao e bug nosso - e o site
    de terceiro que mudou. Precisa de tratamento proprio: numa coleta com varias
    fontes, uma fonte que mudou deve virar aviso e ser pulada, sem derrubar as outras.

    O caso que ela evita e o pior de todos: extracao devolvendo zero vaga em silencio.
    Zero vaga e indistinguivel de "nao ha vaga hoje", e o feed ficaria vazio sem
    ninguem entender por que.
    """


class FonteIndisponivel(Exception):
    """A fonte nao entregou a pagina pedida nesta tentativa.

    Por que esta classe existe: engloba os casos em que o site respondeu, mas nao com o
    conteudo - 404 quando o termo nao existe naquela fonte, 403 quando ela bloqueia
    acesso automatizado, 5xx quando esta fora do ar.

    Por que os tres casos ficam juntos: para o pipeline a consequencia e a mesma - esse
    termo, nesta fonte, nao rendeu nada agora. Nenhum deles pode derrubar a rodada,
    porque um termo mal escolhido apagaria a coleta inteira das outras fontes.

    Nao e EntradaInvalida porque nao ha nada no arquivo do usuario a corrigir, e nao e
    EstruturaInesperada porque o formato da pagina nem chegou a ser avaliado.
    """
