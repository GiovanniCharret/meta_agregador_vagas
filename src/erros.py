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
