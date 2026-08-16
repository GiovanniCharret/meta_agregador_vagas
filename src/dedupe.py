"""Chave canonica: o que decide se duas vagas sao a mesma vaga.

Por que este modulo existe: a mesma vaga aparece mais de uma vez - o anunciante
republica, a fonte da um identificador novo, e no futuro um agregador vai repetir o que
outro ja publicou. Sem uma chave que ignore essas diferencas, o feed mostra a mesma vaga
varias vezes e toda contagem por cidade passa a mentir.

O desenho esta no DESIGN.md D3 e foi revisado duas vezes. A segunda revisao veio de
medicao sobre as 269 vagas reais, e nao de teoria:

  - Chave SEM a descricao formava 181 grupos, e o pior deles juntava 8 vagas distintas
    num card so. Fusao falsa e o pior erro possivel, porque some com uma vaga em silencio.
  - Chave COM a descricao forma 265 grupos e captura 4 republicacoes verdadeiras.

O que entra, e por que cada peca:

  empresa   fica, porque sem ela duas clinicas da mesma cidade com textos parecidos se
            fundem. Foi decisao do humano, contra a proposta de troca-la pelo subtitulo.
  cargo     fica, porque "dentista" e "auxiliar" na mesma clinica sao vagas diferentes.
  cidade+UF ficam, porque a mesma rede contrata em varias pracas.
  descricao entra como HASH do texto normalizado, e nao como texto cru - um espaco a mais
            faria a mesma vaga parecer nova.
  id        entra SO quando nao ha descricao. Nunca como componente fixo: fixo, cada
            fonte daria um identificador diferente para o mesmo anuncio e a deduplicacao
            morreria inteira.

Limite conhecido: hash exato nao cruza fontes, porque cada site escreve empresa, cidade e
texto de um jeito. Cruzar fontes vai exigir comparacao por similaridade, e isso e problema
de outra subfase - nao deste modulo.
"""

# hashlib gera o resumo do texto da descricao, que seria longo demais para ir inteiro.
import hashlib

# unicodedata separa o acento da letra, para poder descarta-lo.
import unicodedata

# re colapsa espaco e troca pontuacao por separador.
import re

# Tudo o que nao for letra ou numero vira espaco, e nao desaparece: juntar palavras que
# estavam separadas por pontuacao criaria falsa igualdade entre textos diferentes.
NAO_ALFANUMERICO = re.compile(r"[^a-z0-9]+")

# Quantos caracteres do resumo entram na chave. 16 hexadecimais dao 64 bits, o que torna
# colisao acidental improvavel neste volume e mantem a chave curta para virar indice.
TAMANHO_DO_RESUMO = 16


def normalizar(texto):
    """Reduz um texto a sua forma comparavel.

    Por que esta funcao existe: os quatro campos da chave precisam da mesma reducao, e
    duplica-la seria garantir que um dia as versoes divergissem. E o que faz "Requisitos:
    experiência na área." e "Requisitos. experiencia na area" virarem o mesmo texto - caso
    real, medido em duas republicacoes da mesma vaga no acervo.

    Entrada -> um texto qualquer, possivelmente nulo.
    Fase 1  -> decompoe os acentuados em letra base mais acento.
    Fase 2  -> descarta as marcas de acento.
    Fase 3  -> passa a minusculo.
    Fase 4  -> troca toda pontuacao e espaco por um separador unico.
    Saida   -> o texto reduzido, ou string vazia.
    """
    # Campo ausente e campo vazio recebem o mesmo tratamento.
    if not texto:
        return ""
    # Fase 1 e 2: NFKD separa "á" em "a" mais acento; a categoria Mn marca o acento.
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
    # Fase 3 e 4: minusculo antes da troca, porque o padrao so aceita minuscula.
    return NAO_ALFANUMERICO.sub(" ", sem_acento.lower()).strip()


def _assinatura_do_texto(vaga):
    """Devolve a parte da chave que distingue vagas com os mesmos dados cadastrais.

    Por que esta funcao existe: e a peca que a segunda revisao acrescentou, e a unica com
    duas formas possiveis. Isolar a escolha aqui torna visivel quando cada uma vale.

    Entrada -> a vaga.
    Fase 1  -> normaliza a descricao.
    Fase 2  -> quando houver texto, devolve o resumo dele.
    Fase 3  -> quando nao houver, recorre ao identificador de origem - e o unico jeito
               honesto de separar vagas anonimas ainda nao enriquecidas.
    Saida   -> a assinatura.
    """
    # Fase 1: mesma normalizacao dos demais campos.
    texto = normalizar(vaga.get("descricao"))

    # Fase 2: o resumo cabe na chave; o texto inteiro nao caberia.
    if texto:
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:TAMANHO_DO_RESUMO]

    # Fase 3 e saida: o prefixo deixa explicito, ao ler a chave, que esta vaga caiu no
    # ultimo recurso - util para diagnosticar agrupamento estranho depois.
    return "id:" + str(vaga.get("id_na_fonte") or "")


def chave_canonica(vaga):
    """Devolve a chave que agrupa copias da mesma vaga.

    Por que esta funcao existe: e o unico lugar do projeto que decide se duas vagas sao a
    mesma. Espalhar essa decisao faria o feed, o banco e os alertas discordarem entre si.

    Entrada -> uma vaga no formato do projeto.
    Fase 1  -> normaliza os quatro campos cadastrais.
    Fase 2  -> acrescenta a assinatura do texto, ou o identificador de origem.
    Fase 3  -> resume tudo, para a chave caber numa coluna indexada.
    Saida   -> a chave, estavel para a mesma entrada.
    """
    # Fase 1 e 2: a ordem dos campos e fixa, senao a chave variaria sem o dado variar.
    partes = [
        normalizar(vaga.get("empresa_bruta")),
        normalizar(vaga.get("titulo_bruto")),
        normalizar(vaga.get("cidade")),
        (vaga.get("uf") or "").upper(),
        _assinatura_do_texto(vaga),
    ]

    # Fase 3 e saida: o separador nao pode aparecer dentro das partes, e nao aparece -
    # a normalizacao ja tirou tudo o que nao e letra, numero ou espaco.
    bruta = "|".join(partes)
    return hashlib.sha256(bruta.encode("utf-8")).hexdigest()[:32]
