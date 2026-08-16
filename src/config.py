"""Leitura do arquivo de entrada do projeto.

Por que este modulo existe: o `PLAN.md` chama a entrada de "JSON fechado", e a triagem
esclareceu que ela e um arquivo de configuracao editado a mao - perfis, cidades
bloqueadas, sinonimos, termos de reprovacao. Concentrar a leitura num modulo so evita
que cada coletor invente seu proprio jeito de ler o mesmo arquivo, e da um unico lugar
onde a validacao pode acontecer antes de qualquer coleta comecar.
"""

# json faz a leitura do formato de entrada escolhido.
import json

# dataclass da estruturas imutaveis e legiveis sem escrever __init__ na mao.
from dataclasses import dataclass

# EntradaInvalida e o contrato de "erro que o usuario corrige sozinho".
from src.erros import EntradaInvalida

# Os dois unicos valores aceitos no campo `lado` de um perfil. Ficam numa constante
# para que a validacao e a mensagem de erro nunca discordem entre si.
LADOS_ACEITOS = ("meu", "dela")


@dataclass(frozen=True)
class Perfil:
    """Uma busca nomeada, com lado e vocabulario proprios.

    Por que esta classe existe: a decisao 3.1 diz que nao sao dois perfis (um por
    pessoa), e sim varias buscas independentes - porque area, geografia e vocabulario
    mudam radicalmente entre elas. O campo `lado` e o que permite calcular depois o
    selo de companheiro da 3.4, que pergunta se a cidade fecha para as duas pessoas.
    """

    # Identificador curto da busca: dados, dev, financeiro, odonto.
    nome: str
    # A quem a busca pertence: "meu" ou "dela". Alimenta o selo de companheiro.
    lado: str
    # Termos-semente escritos a mao pelo usuario.
    termos: list
    # Sinonimos da area, tambem escritos a mao (decisao 3.5).
    sinonimos: list


@dataclass(frozen=True)
class Config:
    """A entrada inteira do programa, ja normalizada.

    Por que esta classe existe: passar um dicionario cru adiante espalharia
    `cfg["ufs_bloqueadas"]` por todo o codigo e deixaria erro de digitacao virar
    KeyError no meio do pipeline. Com uma estrutura declarada, o erro aparece na
    leitura, que e onde o usuario ainda consegue corrigir.
    """

    # Buscas nomeadas, na ordem em que o usuario escreveu.
    perfis: list
    # Lista BRANCA de estados: so vaga em UF desta lista sobrevive ao filtro.
    # Comeca com as 27 unidades federativas e vai sendo podada com o tempo. E lista
    # branca, e nao negra, porque o conjunto de estados e pequeno e fechado - podar
    # uma lista pronta e mais facil do que lembrar de proibir um a um (decisao 3.2).
    ufs_liberadas: list
    # Cidades especificas que descartam a vaga direto. Aqui a lista e NEGRA, porque
    # sao milhares de cidades e enumerar as aceitas seria impraticavel.
    cidades_bloqueadas: list
    # Cidades que sobem ao topo do feed.
    cidades_desejadas: list
    # Palavras que reprovam a vaga na hora (decisao 3.6).
    termos_reprovacao: list
    # Fontes ligadas nesta rodada de coleta.
    fontes_ativas: list


def _lista(bruto, chave):
    """Le uma lista opcional do dicionario cru.

    Por que esta funcao existe: cinco campos da configuracao sao listas opcionais com
    exatamente o mesmo tratamento. Sem ela, o mesmo `bruto.get(chave, [])` apareceria
    cinco vezes e o dia em que o tratamento mudar, mudaria em cinco lugares.

    Entrada -> o dicionario lido do JSON e o nome da chave.
    Fase 1  -> busca a chave, usando lista vazia quando ela nao existir.
    Saida   -> uma lista, nunca None, para o codigo seguinte nao precisar checar.
    """
    # get com default evita KeyError e garante que campo ausente vire lista vazia.
    return list(bruto.get(chave, []))


def _monta_perfil(bruto, posicao):
    """Valida e converte um perfil cru do JSON na estrutura Perfil.

    Por que esta funcao existe: o perfil e a unica parte da configuracao com regras
    proprias (lado restrito, termos obrigatorios), e a mensagem de erro precisa citar
    qual perfil esta errado. Sem isolar isso, o carregador principal viraria uma
    parede de validacao e a mensagem perderia o contexto de qual perfil falhou.

    Entrada -> um dicionario de perfil e a posicao dele na lista, base para a mensagem
               quando o proprio nome estiver faltando.
    Fase 1  -> exige o campo `nome`, sem o qual nenhuma mensagem seguinte teria como
               identificar o perfil culpado.
    Fase 2  -> exige `lado` dentro dos valores aceitos, porque ele alimenta o selo de
               companheiro da 3.4 e um valor errado quebraria o calculo em silencio.
    Fase 3  -> exige `termos` nao vazio, porque perfil sem termo nunca casa com vaga.
    Fase 4  -> le sinonimos como lista opcional.
    Saida   -> um Perfil imutavel e ja validado.
    """
    # Fase 1: sem nome nao ha como citar o perfil nas mensagens seguintes, entao esta
    # checagem vem antes de todas as outras.
    if not bruto.get("nome"):
        # A posicao e informada em base 1 porque a mensagem e para quem le o arquivo,
        # nao para quem programa.
        raise EntradaInvalida(
            'Perfil na posicao {} esta sem o campo "nome". '
            "Todo perfil precisa de um nome curto, como: dados, dev, odonto.".format(
                posicao + 1
            )
        )

    # A partir daqui o nome existe e pode ser usado para localizar o erro.
    nome = bruto["nome"]

    # Fase 2: lado fora dos valores aceitos quebraria o selo de companheiro sem avisar.
    lado = bruto.get("lado")
    if lado not in LADOS_ACEITOS:
        raise EntradaInvalida(
            'Perfil "{}" tem lado "{}", que nao existe. '
            "Os valores aceitos sao: {}.".format(
                nome, lado, " ou ".join(LADOS_ACEITOS)
            )
        )

    # Fase 3: termos ausente e termos vazio sao o mesmo defeito - um perfil que nunca
    # produziria resultado - e por isso recebem a mesma mensagem.
    termos = _lista(bruto, "termos")
    if not termos:
        raise EntradaInvalida(
            'Perfil "{}" esta sem o campo "termos". '
            "Escreva ao menos um termo de busca, como: cientista de dados.".format(nome)
        )

    # Fase 4 e saida: sinonimo e opcional - ausencia vira lista vazia, nao None.
    return Perfil(
        nome=nome,
        lado=lado,
        termos=termos,
        sinonimos=_lista(bruto, "sinonimos"),
    )


def _valida_ufs(siglas):
    """Confere se cada UF liberada e uma sigla de duas letras.

    Por que esta funcao existe: a lista de estados e podada a mao, por fora do sistema.
    Se alguem escrever "Parana" em vez de "PR", a sigla nao casa com o que vem da fonte
    e o estado inteiro some do feed sem aviso - exatamente o tipo de limitacao
    silenciosa que o projeto proibe.

    Entrada -> a lista de siglas exatamente como escrita no arquivo, ainda sem
               normalizar, para a mensagem poder cita-la do jeito que o usuario a ve.
    Fase 1  -> percorre cada sigla procurando a que nao tem duas letras.
    Saida   -> nada; a funcao existe pelo efeito de recusar entrada torta.
    """
    # Fase 1: percorre em ordem para que a primeira sigla errada seja a citada.
    for sigla in siglas:
        # isalpha() recusa numero e pontuacao; len() recusa nome de estado por extenso.
        if len(sigla) != 2 or not sigla.isalpha():
            raise EntradaInvalida(
                'A UF liberada "{}" nao e uma sigla valida. '
                "Use a sigla de duas letras do estado, como: SC, PR, SP.".format(sigla)
            )


def carregar_config(caminho):
    """Le o arquivo de configuracao e devolve a entrada ja normalizada.

    Por que esta funcao existe: e o unico ponto de entrada de dado do usuario no
    programa. Tudo o que vier torto tem que ser recusado aqui, antes de qualquer
    coleta, porque depois disso o erro apareceria no meio do pipeline sem contexto.

    Entrada -> o caminho de um arquivo JSON.
    Fase 1  -> confere que o arquivo existe, dizendo onde procurou quando nao existir.
    Fase 2  -> le o arquivo em UTF-8, que e como o usuario o escreve.
    Fase 3  -> converte o texto em dicionario, traduzindo erro de sintaxe do parser
               numa mensagem que quem edita o arquivo a mao consiga entender.
    Fase 4  -> exige ao menos um perfil, sem o qual o programa rodaria inteiro para
               produzir um feed vazio.
    Fase 5  -> monta os perfis, preservando a ordem do arquivo (determinismo).
    Fase 6  -> normaliza as UFs para maiuscula e recusa sigla mal escrita.
    Fase 7  -> le as listas opcionais, transformando ausencia em lista vazia.
    Saida   -> um Config imutavel, pronto para o pipeline.
    """
    # Fase 1: sem esta checagem, o usuario receberia um FileNotFoundError cru sem
    # saber em que diretorio o programa procurou.
    if not caminho.exists():
        raise EntradaInvalida(
            "Arquivo de configuracao nao encontrado: {}. "
            "Crie o arquivo a partir do modelo config/config.exemplo.json.".format(
                caminho
            )
        )

    # Fase 2: utf-8-sig, e nao utf-8. O "sig" descarta o BOM quando ele existe e nao
    # atrapalha quando nao existe. Isso importa porque no Windows o Bloco de Notas e o
    # PowerShell gravam UTF-8 com BOM por padrao, e o BOM e um caractere invisivel que
    # faz o leitor de JSON falhar na linha 1, coluna 1 - o usuario receberia um erro de
    # sintaxe apontando para um arquivo que, na tela dele, esta perfeito.
    texto = caminho.read_text(encoding="utf-8-sig")

    # Fase 3: o traceback do json cita coluna e byte, o que nao ajuda quem esqueceu uma
    # virgula. A traducao aponta o arquivo e a linha.
    try:
        bruto = json.loads(texto)
    except json.JSONDecodeError as falha:
        raise EntradaInvalida(
            "O arquivo {} nao e um JSON valido (linha {}, coluna {}). "
            "Confira virgula sobrando, aspas faltando ou chave nao fechada.".format(
                caminho, falha.lineno, falha.colno
            )
        ) from falha

    # Fase 4: chave ausente e lista vazia sao o mesmo defeito para o usuario - nao ha
    # o que buscar - e por isso recebem a mesma mensagem.
    if not bruto.get("perfis"):
        raise EntradaInvalida(
            'O arquivo {} nao tem nenhum perfil de busca. '
            'Preencha a lista "perfis" com ao menos uma busca.'.format(caminho)
        )

    # Fase 5: enumerate da a posicao usada na mensagem quando o perfil nao tiver nome;
    # a list comprehension preserva a ordem, exigencia de determinismo.
    perfis = [_monta_perfil(p, i) for i, p in enumerate(bruto["perfis"])]

    # Fase 6: a lista branca de estados e obrigatoria. Ausente ou vazia seria ambigua -
    # poderia significar "todos os estados" ou "nenhum" - e qualquer das duas escolhida
    # em silencio produziria um feed errado sem o usuario perceber.
    if not bruto.get("ufs_liberadas"):
        raise EntradaInvalida(
            'O arquivo {} nao tem a lista "ufs_liberadas". '
            "Liste as siglas dos estados onde voces aceitariam trabalhar; "
            "o modelo config/config.exemplo.json ja vem com as 27 para voce podar."
            .format(caminho)
        )

    # A validacao vem ANTES da normalizacao de proposito. A mensagem de erro precisa
    # citar o valor exatamente como esta escrito no arquivo, senao o usuario procura
    # por "Parana" no editor e nao encontra o "PARANA" que a mensagem mostrou.
    ufs_escritas = _lista(bruto, "ufs_liberadas")
    _valida_ufs(ufs_escritas)
    # So depois de aceitas, as siglas viram maiusculas: assim "sc" escrito a mao ainda
    # casa com o "SC" que vem da fonte, e o filtro nao falha em silencio.
    ufs = [uf.upper() for uf in ufs_escritas]

    # Fase 7 e saida: monta a estrutura final com as listas opcionais ja resolvidas.
    return Config(
        perfis=perfis,
        ufs_liberadas=ufs,
        cidades_bloqueadas=_lista(bruto, "cidades_bloqueadas"),
        cidades_desejadas=_lista(bruto, "cidades_desejadas"),
        termos_reprovacao=_lista(bruto, "termos_reprovacao"),
        fontes_ativas=_lista(bruto, "fontes_ativas"),
    )
