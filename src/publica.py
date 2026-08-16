"""Preparacao dos arquivos que sobem para o presenterosa.com.br por FTP.

Por que este modulo existe: o feed vai viver dentro de um site que ja existe, e a
integracao mexe em arquivos que sao DO SITE - o `index.html` e o `app.js`. Fazer isso a
mao a cada atualizacao seria repetir a mesma edicao para sempre e errar uma hora.

Por que cada substituicao FALHA ALTO quando nao encontra o alvo: e o defeito mais
perigoso daqui. Uma troca que nao acha o texto devolveria o arquivo igual, e o pacote de
deploy pareceria pronto sem mudar nada - o erro so apareceria depois do upload, olhando
o site no ar. Melhor recusar de cara, com mensagem dizendo o que nao foi encontrado.

Escopo desta fase: deploy estatico e provisorio. A pagina congela no momento em que e
gerada, e a atualizacao e manual - decisao consciente para medir a reacao da usuaria
antes de investir em hospedagem de servico. Marcar vaga como salva ou descartada nao
existe aqui, porque exige servidor; o proprio `montar_feed` ja nasce sem os botoes
quando nao ha ninguem logado, entao nao ha botao que nao faz nada.
"""

# EntradaInvalida sinaliza o que o humano pode corrigir - aqui, um arquivo do site que
# mudou de forma inesperada.
from src.erros import EntradaInvalida

# Nome do arquivo da pagina nova dentro do site, escolhido junto com voce.
ARQUIVO_DA_PAGINA = "vagas.html"

# Nome que o card passa a exibir na home.
NOME_DA_APLICACAO = "Meta_Agregador de Vagas"

# Trechos do site que precisam existir para a integracao funcionar. Cada par diz o que
# procurar e por que ele importa, para a mensagem de erro poder explicar.
ALVO_TITULO = "<h3>Lista de Bairros</h3>"
ALVO_DESCRICAO = "Quase completo<br>Falta você julgar"
ALVO_DESTINO = "resultado2.html"


def _troca_exigindo(texto, alvo, novo, onde):
    """Substitui um trecho, recusando quando ele nao existe.

    Por que esta funcao existe: as tres substituicoes tem a mesma armadilha - o metodo
    `replace` do Python nao reclama quando nao encontra nada, ele simplesmente devolve o
    texto igual. Concentrar a exigencia aqui garante que nenhuma delas passe batida.

    Entrada -> o texto original, o trecho procurado, o substituto e o nome do arquivo.
    Fase 1  -> confere que o alvo existe.
    Fase 2  -> substitui todas as ocorrencias.
    Saida   -> o texto alterado.
    """
    # Fase 1: sem o alvo, a substituicao seria silenciosa - e um pacote de deploy que
    # parece pronto e nao muda nada e pior do que um erro na hora de gerar.
    if alvo not in texto:
        raise EntradaInvalida(
            "Nao encontrei {!r} em {}. O arquivo do site mudou desde a ultima vez; "
            "confira o trecho e ajuste src/publica.py antes de publicar.".format(
                alvo, onde)
        )
    # Fase 2 e saida.
    return texto.replace(alvo, novo)


def index_atualizado(html):
    """Devolve o index.html do site com o card apontando para a pagina nova.

    Por que a edicao e cirurgica e nao uma reescrita: o index e do site, nao nosso. Ele
    tem foto, texto e um segundo card que nao estamos olhando - reescrever arriscaria
    quebrar o que funciona por descuido.

    Entrada -> o conteudo do index.html original.
    Fase 1  -> troca o titulo do card.
    Fase 2  -> troca a descricao, que falava da lista de bairros.
    Saida   -> o HTML alterado.
    """
    # Fase 1: o titulo e o que ela le no card.
    novo = _troca_exigindo(
        html, ALVO_TITULO, "<h3>{}</h3>".format(NOME_DA_APLICACAO), "index.html")

    # Fase 2: deixar a descricao antiga sob o titulo novo confundiria quem abre.
    return _troca_exigindo(
        novo, ALVO_DESCRICAO,
        "Vagas de odontologia<br>no Brasil inteiro", "index.html")


def app_js_atualizado(js):
    """Devolve o app.js do site com o botao abrindo a pagina nova.

    Por que isto e separado da troca de nome: trocar o titulo sem trocar o destino levaria
    ela para a lista de bairros - o pior resultado possivel, porque PARECE que funcionou.

    Entrada -> o conteudo do app.js original.
    Fase 1  -> troca o destino nas duas ocorrencias, a da aba nova e a do redirecionamento.
    Saida   -> o JavaScript alterado.
    """
    # Fase 1 e saida: o `replace` troca as duas de uma vez.
    return _troca_exigindo(js, ALVO_DESTINO, ARQUIVO_DA_PAGINA, "app.js")
