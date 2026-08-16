"""Filtros: o que nao chega ao feed, e por que.

Por que este modulo existe: o horizonte e continuo e sem teto de volume, entao o feed so
e utilizavel se o que nao interessa nao chegar nele. Os dois filtros vem de decisoes
diferentes da triagem:

  3.2 - geografico. Lista BRANCA de estados, porque sao 27 e podar uma lista pronta e
        mais facil que proibir um a um. Lista NEGRA de cidades, porque sao milhares.
  3.6 - palavras que reprovam a vaga na hora, contra o ruido de franquia e comissionamento
        que a pesquisa apontou como estrutural em odontologia.

Este modulo nao conhece fonte nem banco: recebe dicionario e devolve resposta. E a parte
do miolo que a regra de dependencia manda manter isolada (D7).

Os filtros rodam na LEITURA, e nao na coleta. Assim, mudar a lista de cidades tem efeito
imediato, sem precisar recoletar - e nenhuma vaga se perde por causa de uma lista mal
escrita, porque o dado continua no banco.
"""

# Counter conta quantas vagas cada termo reprovou, para o filtro poder ser calibrado.
from collections import Counter

# re monta a busca por palavra inteira.
import re

# unicodedata separa o acento da letra, para poder descarta-lo.
import unicodedata


def normalizar(texto):
    """Reduz um texto a sua forma comparavel: minusculo, sem acento, espaco unico.

    Por que esta funcao existe: as listas sao escritas a mao, sem acento por convencao do
    projeto, e a fonte escreve com acento. Sem reduzir os dois lados a mesma forma, o
    bloqueio de "Anastácio" nao pegaria a cidade escrita "anastacio" - e a vaga apareceria
    assim mesmo, que e exatamente a limitacao silenciosa que o projeto proibe.

    Entrada -> um texto qualquer, possivelmente nulo.
    Fase 1  -> decompoe os acentuados e descarta as marcas de acento.
    Fase 2  -> passa a minusculo e colapsa espaco.
    Saida   -> o texto reduzido, ou string vazia.
    """
    # Campo ausente e campo vazio recebem o mesmo tratamento.
    if not texto:
        return ""
    # Fase 1: NFKD separa a letra do acento; a categoria Mn marca o acento.
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
    # Fase 2 e saida.
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def passa_no_geografico(vaga, ufs_liberadas, cidades_bloqueadas):
    """Diz se a vaga sobrevive ao filtro de lugar.

    Por que esta funcao existe: e o filtro que mais importa para este perfil. Vaga em
    estado onde ela nao moraria vale zero, por melhor que seja - e sao 269 vagas
    espalhadas por 23 estados.

    Entrada -> a vaga, a lista branca de UFs e a lista negra de cidades.
    Fase 1  -> exige que a UF esteja na lista branca. Vaga sem UF nao passa: se passasse,
               bastaria a fonte omitir o estado para furar o filtro.
    Fase 2  -> recusa cidade que esteja na lista negra, mesmo com o estado liberado.
    Saida   -> verdadeiro quando a vaga pode aparecer.
    """
    # Lista vazia desliga o filtro de estado, e a escolha e deliberada. A leitura da
    # configuracao JA RECUSA lista vazia, com mensagem propria - entao o unico jeito de
    # chegar aqui sem lista e defeito no nosso codigo. Nesse caso e melhor o feed aparecer
    # inteiro, que se percebe na hora, do que aparecer vazio, que parece "nao tem vaga".
    if ufs_liberadas:
        # Fase 1: comparacao em maiuscula dos dois lados, porque a configuracao normaliza
        # na leitura mas a fonte pode mandar de qualquer jeito.
        uf = (vaga.get("uf") or "").upper()
        # Vaga sem UF nao passa quando ha lista: se passasse, bastaria a fonte omitir o
        # estado para furar o filtro.
        if not uf or uf not in {u.upper() for u in ufs_liberadas}:
            return False

    # Fase 2: acento e caixa nao podem separar a mesma cidade em duas.
    cidade = normalizar(vaga.get("cidade"))
    if cidade and cidade in {normalizar(c) for c in cidades_bloqueadas}:
        return False

    # Saida: sobreviveu aos dois.
    return True


def _texto_da_vaga(vaga):
    """Junta os campos onde um termo de reprovacao pode aparecer.

    Por que esta funcao existe: olhar so a descricao deixaria passar a vaga cujo TITULO ja
    diz "estagio". Juntar os tres num texto so evita repetir a busca tres vezes.
    """
    # Campos nulos sao descartados antes de juntar.
    pedacos = [vaga.get("titulo_bruto"), vaga.get("subtitulo"), vaga.get("descricao")]
    return normalizar(" ".join(p for p in pedacos if p))


def termo_que_reprova(vaga, termos):
    """Devolve o primeiro termo que reprova a vaga, ou nada.

    Por que devolve o TERMO e nao apenas verdadeiro ou falso: esconder vaga sem dizer por
    que seria limitacao silenciosa. Com o termo em maos, a tela consegue explicar - e voce
    consegue descobrir que um termo esta reprovando demais.

    Por que casa PALAVRA INTEIRA e nao pedaco: medido no acervo real em 16/08/2026, o
    termo "mei" casava dentro de "meio dia" e reprovava 4 vagas boas por acidente. Busca
    por pedaco e armadilha classica - quanto mais curto o termo, mais dano causa. E filtro
    que reprova errado e pior que filtro nenhum, porque some com a vaga sem deixar rastro.

    Entrada -> a vaga e a lista de termos.
    Fase 1  -> monta o texto onde procurar.
    Fase 2  -> procura cada termo, exigindo fronteira de palavra dos dois lados.
    Saida   -> o termo encontrado, ou None.
    """
    # Fase 1: sem texto nao ha o que reprovar - o caso da vaga ainda nao enriquecida.
    texto = _texto_da_vaga(vaga)
    if not texto:
        return None

    # Fase 2: a ordem da lista decide qual termo e citado quando mais de um casa, e por
    # isso a lista do usuario e percorrida como ele a escreveu.
    for termo in termos:
        alvo = normalizar(termo)
        if not alvo:
            continue
        # \b nas duas pontas exige fronteira de palavra; re.escape protege termos com
        # caractere especial. Expressao de varias palavras funciona igual, porque a
        # fronteira vale para o conjunto.
        if re.search(r"\b{}\b".format(re.escape(alvo)), texto):
            return alvo

    # Saida: nenhum termo reprovou.
    return None


def termos_que_casam(vaga, termos):
    """Devolve quais termos do perfil aparecem no texto da vaga.

    Por que esta funcao existe: e a decisao 4.2, "por que esta vaga apareceu". Sem ela,
    quando o feed trouxer lixo voce nao consegue distinguir se o problema e o sinonimo, a
    cidade ou a fonte - teria que abrir o codigo para descobrir.

    E a contrapartida de `termo_que_reprova`: uma funcao tira vaga do feed, esta explica
    por que a vaga esta la. Ambas usam a mesma busca por palavra inteira, pela mesma razao
    - casar pedaco de palavra aqui nao esconderia vaga, mas mentiria na explicacao, e
    explicacao errada e pior que explicacao nenhuma, porque voce confiaria nela.

    Efeito colateral util: e aqui que os SINONIMOS finalmente servem. Eles nao funcionam
    como expansao de busca no BNE, porque o vocabulario da fonte nao os conhece - mas
    funcionam como leitura rapida da especialidade. Medido no acervo: `clinico geral`
    aparece em 50 vagas e `odontologia` em 47.

    Entrada -> a vaga e a lista de termos do perfil, sementes mais sinonimos.
    Fase 1  -> monta o texto onde procurar.
    Fase 2  -> guarda cada termo presente, uma vez so, na ordem da configuracao.
    Saida   -> a lista de termos que casaram.
    """
    # Fase 1: sem texto a explicacao fica pobre, mas nao pode estourar.
    texto = _texto_da_vaga(vaga)
    if not texto:
        return []

    # Fase 2: a ordem e a da configuracao, e nao a de aparicao no texto - ordem instavel
    # faria a etiqueta do card mudar entre execucoes sem o dado mudar.
    casados = []
    for termo in termos:
        alvo = normalizar(termo)
        # Termo vazio ou ja registrado nao entra de novo: a etiqueta diz QUAIS casaram,
        # e nao quantas vezes cada um apareceu.
        if not alvo or alvo in casados:
            continue
        if re.search(r"\b{}\b".format(re.escape(alvo)), texto):
            casados.append(alvo)

    # Saida.
    return casados


def anotar_casamentos(vagas, termos_por_perfil):
    """Acrescenta a cada vaga a lista de termos do seu perfil que aparecem no texto.

    Por que a anotacao acontece na LEITURA e nao fica gravada: ela depende da lista de
    sinonimos, que muda no arquivo de configuracao. Gravada, mudar a lista exigiria
    recoletar o acervo inteiro para ver o efeito.

    Por que aqui e nao dentro da montagem da pagina: mantem `feed.py` apenas
    apresentacional - ele recebe dado pronto e desenha. Casar texto e trabalho deste
    modulo, que ja tem a normalizacao e a busca por palavra inteira.

    Entrada -> as vagas e um dicionario de perfil para a lista de termos dele.
    Fase 1  -> descobre os termos do perfil de cada vaga.
    Fase 2  -> anota, sem alterar o dicionario original.
    Saida   -> a lista de vagas anotadas.
    """
    anotadas = []
    for vaga in vagas:
        # Fase 1: vaga de perfil desconhecido - ou sem perfil, do acervo antigo - fica
        # sem termos, e o card simplesmente nao mostra a etiqueta.
        termos = termos_por_perfil.get(vaga.get("perfil")) or []
        # Fase 2: copia rasa para nao alterar o que veio do banco.
        copia = dict(vaga)
        copia["termos_casados"] = termos_que_casam(vaga, termos)
        anotadas.append(copia)
    # Saida.
    return anotadas


def aplicar(vagas, ufs_liberadas, cidades_bloqueadas, termos_reprovacao):
    """Aplica os dois filtros e devolve o que passou junto com a contagem do que sumiu.

    Por que devolve a contagem, e nao so a lista: esconder vaga sem dizer quantas foram
    escondidas seria limitacao silenciosa - voce nao saberia se o feed encolheu porque o
    filtro trabalhou bem ou porque a coleta falhou.

    Por que conta POR TERMO: sem isso nao da para perceber que um termo esta reprovando
    demais. Foi contando que descobrimos, no acervo real, que "mei" casava dentro de
    "meio dia" e derrubava 4 vagas boas.

    Entrada -> as vagas e as tres listas da configuracao.
    Fase 1  -> percorre na ordem de entrada, para nao embaralhar o que a montagem do feed
               vai ordenar depois.
    Fase 2  -> reprova por lugar primeiro, que e o filtro mais barato e mais decisivo.
    Fase 3  -> reprova por termo, guardando qual termo foi.
    Saida   -> a lista filtrada e um resumo com as contagens.
    """
    # O resumo comeca zerado para o feed poder exibi-lo mesmo sem nenhuma reprovacao.
    resumo = {"fora_do_mapa": 0, "reprovadas": Counter()}
    visiveis = []

    # Fase 1: ordem preservada; a ordenacao do feed acontece depois.
    for vaga in vagas:
        # Fase 2: lugar antes de texto - e mais barato e decide mais.
        if not passa_no_geografico(vaga, ufs_liberadas, cidades_bloqueadas):
            resumo["fora_do_mapa"] += 1
            continue

        # Fase 3: o termo encontrado vai para a contagem, e nao so o fato da reprovacao.
        termo = termo_que_reprova(vaga, termos_reprovacao)
        if termo:
            resumo["reprovadas"][termo] += 1
            continue

        visiveis.append(vaga)

    # Saida: as duas coisas juntas, calculadas numa passada so.
    return visiveis, resumo
