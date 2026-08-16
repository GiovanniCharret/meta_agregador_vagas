"""Testes de erro de src/config.py.

Por que este arquivo existe separado do test_config.py: o caminho feliz e a recusa de
entrada torta sao responsabilidades diferentes. A regra do projeto e que limitacao
nunca seja silenciosa - entao a qualidade da recusa importa tanto quanto a da leitura,
e merece um arquivo que possa crescer sozinho.
"""

import json

import pytest

# Reaproveita o escritor de configuracao do arquivo de caminho feliz.
from tests.test_config import escreve_config, CONFIG_VALIDA


def config_sem(chave):
    """Devolve uma copia da configuracao valida sem uma das chaves.

    Por que esta funcao existe: varios testes precisam da mesma configuracao valida com
    exatamente um campo faltando. Montar isso na mao em cada teste esconderia qual e o
    campo em jogo.

    Entrada -> o nome da chave a remover.
    Fase 1  -> copia a configuracao valida em profundidade, para nao contaminar os
               outros testes que usam a mesma constante.
    Fase 2  -> remove a chave pedida.
    Saida   -> o dicionario resultante.
    """
    # json.loads(json.dumps(...)) e a copia profunda mais curta e sem import extra.
    copia = json.loads(json.dumps(CONFIG_VALIDA))
    # Remove a chave alvo do teste.
    copia.pop(chave, None)
    # Devolve para o teste escrever em disco.
    return copia


def config_com_perfil(perfil):
    """Devolve uma configuracao valida cujo unico perfil e o fornecido.

    Por que esta funcao existe: os testes de perfil invalido so diferem no perfil.
    Isolar isso deixa visivel, em cada teste, exatamente qual defeito esta sendo testado.

    Entrada -> um dicionario de perfil, possivelmente defeituoso.
    Fase 1  -> copia a configuracao valida.
    Fase 2  -> substitui a lista de perfis pelo perfil unico fornecido.
    Saida   -> o dicionario resultante.
    """
    copia = json.loads(json.dumps(CONFIG_VALIDA))
    # Substitui a lista inteira para o defeito ficar isolado.
    copia["perfis"] = [perfil]
    return copia


def test_arquivo_ausente_diz_qual_caminho_faltou(tmp_path):
    """Por que este teste existe: arquivo faltando e o erro mais comum de todos, e a
    mensagem tem que dizer onde o programa procurou - senao o usuario nao sabe onde
    criar o arquivo."""
    from src.config import carregar_config
    from src.erros import EntradaInvalida
    # Caminho que sabidamente nao existe.
    inexistente = tmp_path / "nao_existe.json"
    # A recusa tem que ser EntradaInvalida, nao FileNotFoundError cru.
    with pytest.raises(EntradaInvalida) as erro:
        carregar_config(inexistente)
    # A mensagem precisa conter o caminho procurado, para ser acionavel.
    assert "nao_existe.json" in str(erro.value)


def test_json_malformado_e_recusado_com_mensagem_legivel(tmp_path):
    """Por que este teste existe: virgula sobrando e o erro classico de quem edita JSON
    a mao. O traceback do json e ininteligivel para quem nao programa."""
    from src.config import carregar_config
    from src.erros import EntradaInvalida
    caminho = tmp_path / "config.json"
    # Chave sem valor: JSON invalido de proposito.
    caminho.write_text('{"perfis": [ }', encoding="utf-8")
    with pytest.raises(EntradaInvalida) as erro:
        carregar_config(caminho)
    # A mensagem tem que falar de arquivo mal formado, nao vazar jargao do parser.
    assert "JSON" in str(erro.value)


def test_sem_perfis_e_recusado(tmp_path):
    """Por que este teste existe: sem perfil nao ha o que buscar, e o programa rodaria
    inteiro para produzir um feed vazio - uma limitacao silenciosa."""
    from src.config import carregar_config
    from src.erros import EntradaInvalida
    caminho = escreve_config(tmp_path, config_sem("perfis"))
    with pytest.raises(EntradaInvalida) as erro:
        carregar_config(caminho)
    assert "perfis" in str(erro.value)


def test_lista_de_perfis_vazia_e_recusada(tmp_path):
    """Por que este teste existe: a chave presente mas vazia passaria por qualquer
    checagem de existencia, e cairia no mesmo feed vazio do teste anterior."""
    from src.config import carregar_config
    from src.erros import EntradaInvalida
    vazia = json.loads(json.dumps(CONFIG_VALIDA))
    vazia["perfis"] = []
    caminho = escreve_config(tmp_path, vazia)
    with pytest.raises(EntradaInvalida) as erro:
        carregar_config(caminho)
    assert "perfis" in str(erro.value)


def test_perfil_sem_nome_e_recusado(tmp_path):
    """Por que este teste existe: sem nome o perfil nao pode ser citado em mensagem
    nenhuma depois, nem no 'por que esta vaga apareceu' da decisao 4.2."""
    from src.config import carregar_config
    from src.erros import EntradaInvalida
    caminho = escreve_config(tmp_path, config_com_perfil({"lado": "meu", "termos": ["x"]}))
    with pytest.raises(EntradaInvalida) as erro:
        carregar_config(caminho)
    assert "nome" in str(erro.value)


def test_perfil_sem_termos_e_recusado(tmp_path):
    """Por que este teste existe: perfil sem termo nao casa com vaga nenhuma; seria um
    perfil que existe na configuracao e nunca produz resultado."""
    from src.config import carregar_config
    from src.erros import EntradaInvalida
    caminho = escreve_config(tmp_path, config_com_perfil({"nome": "dados", "lado": "meu"}))
    with pytest.raises(EntradaInvalida) as erro:
        carregar_config(caminho)
    # A mensagem tem que citar o perfil culpado, e nao so o campo.
    assert "dados" in str(erro.value)
    assert "termos" in str(erro.value)


def test_perfil_com_lista_de_termos_vazia_e_recusado(tmp_path):
    """Por que este teste existe: mesma falha do teste anterior, mas escapando por
    presenca da chave com lista vazia."""
    from src.config import carregar_config
    from src.erros import EntradaInvalida
    perfil = {"nome": "dados", "lado": "meu", "termos": []}
    caminho = escreve_config(tmp_path, config_com_perfil(perfil))
    with pytest.raises(EntradaInvalida) as erro:
        carregar_config(caminho)
    assert "termos" in str(erro.value)


def test_lado_invalido_lista_os_valores_aceitos(tmp_path):
    """Por que este teste existe: 'lado' e o campo que alimenta o selo de companheiro da
    3.4. Um valor errado ali quebraria o calculo em silencio, e a mensagem precisa
    ensinar quais valores existem - o usuario nao tem como adivinhar."""
    from src.config import carregar_config
    from src.erros import EntradaInvalida
    perfil = {"nome": "odonto", "lado": "dele", "termos": ["dentista"]}
    caminho = escreve_config(tmp_path, config_com_perfil(perfil))
    with pytest.raises(EntradaInvalida) as erro:
        carregar_config(caminho)
    mensagem = str(erro.value)
    # Cita o valor errado, o perfil culpado e os dois valores aceitos.
    assert "dele" in mensagem
    assert "odonto" in mensagem
    assert "meu" in mensagem and "dela" in mensagem


def test_uf_bloqueada_com_formato_errado_e_recusada(tmp_path):
    """Por que este teste existe: a lista de UFs vem da namorada por fora do sistema.
    Se ela escrever 'Acre' em vez de 'AC', o filtro nao casa com nada e a cidade
    bloqueada aparece no feed assim mesmo - limitacao silenciosa."""
    from src.config import carregar_config
    from src.erros import EntradaInvalida
    torta = json.loads(json.dumps(CONFIG_VALIDA))
    torta["ufs_bloqueadas"] = ["Acre"]
    caminho = escreve_config(tmp_path, torta)
    with pytest.raises(EntradaInvalida) as erro:
        carregar_config(caminho)
    # A mensagem cita o valor recusado e explica o formato esperado.
    assert "Acre" in str(erro.value)


def test_entrada_invalida_nao_e_confundida_com_bug_de_programa():
    """Por que este teste existe: a regra do projeto separa erro de dado (sai com
    codigo 1 e mensagem limpa) de bug de programa (levanta traceback normal). Se
    EntradaInvalida herdasse de algo generico demais, o executavel nao conseguiria
    distinguir os dois casos no except."""
    from src.erros import EntradaInvalida
    # Tem que ser uma excecao propria do projeto, capturavel de forma especifica.
    assert issubclass(EntradaInvalida, Exception)
    # E nao pode ser um alias de erros de programacao comuns, que precisam vazar.
    assert not issubclass(EntradaInvalida, (KeyError, TypeError, AttributeError))
