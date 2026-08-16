"""Normalizacoes de texto compartilhadas pelo pipeline.

Por que este modulo existe: cidade, titulo, empresa e termo de busca vem escritos de
jeitos diferentes em cada fonte e na mao do usuario. Concentrar a normalizacao aqui e o
que faz "Cirurgiao Dentista" e "cirurgião-dentista" virarem a mesma coisa - e o que
impede cada modulo de inventar a sua propria versao da mesma regra.

Este modulo nao conhece fonte nem banco: recebe texto e devolve texto. E a parte do
miolo que a regra de dependencia da Clean Architecture manda manter isolada (D7).
"""

# re faz a troca de tudo o que nao e letra ou numero por separador.
import re

# unicodedata decompoe o acento para que ele possa ser descartado.
import unicodedata

# Tudo o que nao for letra ou numero vira separador; assim pontuacao, espaco duplo e
# hifen ja existente recebem o mesmo tratamento.
NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")


def para_slug(texto):
    """Converte um texto livre no pedaco de URL correspondente.

    Por que esta funcao existe: o termo de busca escrito pelo usuario entra dentro do
    caminho da URL da fonte. Espaco cru, acento ou maiuscula quebram o endereco, e o
    sintoma seria a coleta voltar vazia - uma falha dificil de enxergar, porque parece
    apenas que nao ha vaga.

    Entrada -> um texto qualquer, como o usuario escreveu no config.
    Fase 1  -> decompoe os caracteres acentuados em letra base mais acento.
    Fase 2  -> descarta as marcas de acento, sobrando so a letra base.
    Fase 3  -> passa tudo para minusculo.
    Fase 4  -> troca qualquer sequencia de caractere nao alfanumerico por um hifen.
    Fase 5  -> remove hifen sobrando nas pontas, que costuma virar 404.
    Saida   -> o slug, estavel para a mesma entrada.
    """
    # Fase 1: NFKD separa "ã" em "a" + til combinante.
    decomposto = unicodedata.normalize("NFKD", texto)

    # Fase 2: categoria "Mn" e marca combinante - descartar sobra so a letra base.
    sem_acento = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")

    # Fase 3: minusculo antes da troca, porque o padrao so aceita letra minuscula.
    minusculo = sem_acento.lower()

    # Fase 4: qualquer pontuacao, espaco ou hifen vira um unico hifen.
    com_hifen = NAO_ALFANUMERICO.sub("-", minusculo)

    # Fase 5 e saida: pontas limpas.
    return com_hifen.strip("-")
