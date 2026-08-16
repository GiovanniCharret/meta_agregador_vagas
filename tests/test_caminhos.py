"""Testes de src/caminhos.py - a ancora de caminhos do projeto."""

# Path e usado para montar os caminhos esperados de forma independente do modulo testado.
from pathlib import Path


def test_raiz_aponta_para_o_diretorio_que_contem_src():
    """Por que este teste existe: se RAIZ apontar para o lugar errado, todo caminho
    derivado (config, dados, saida) aponta errado junto, e o programa passa a depender
    de onde o .bat foi chamado. Este e o teste que trava essa regressao."""
    # Importa dentro do teste para que a falha de import apareca como falha deste teste.
    from src.caminhos import RAIZ
    # A raiz do projeto e, por definicao, o diretorio que contem a pasta src.
    assert (RAIZ / "src").is_dir()
    # E tambem o diretorio que contem o proprio arquivo de configuracao do pytest.
    assert (RAIZ / "pytest.ini").is_file()


def test_raiz_independe_do_diretorio_de_trabalho(monkeypatch, tmp_path):
    """Por que este teste existe: o objetivo declarado de RAIZ e permitir que o
    executavel rode de qualquer diretorio. Mudar o diretorio de trabalho e a unica
    forma de provar que a ancora nao usa o cwd."""
    # Guarda o valor calculado quando o modulo foi importado a primeira vez.
    from src.caminhos import RAIZ
    esperado = RAIZ
    # Move o diretorio de trabalho para um lugar totalmente diferente.
    monkeypatch.chdir(tmp_path)
    # Reimporta o modulo do zero, para o calculo acontecer sob o novo cwd.
    import importlib
    import src.caminhos
    importlib.reload(src.caminhos)
    # O valor tem que ser o mesmo: a ancora vem do __file__, nao do cwd.
    assert src.caminhos.RAIZ == esperado


def test_raiz_pode_ser_redirecionada_por_variavel_de_ambiente(monkeypatch, tmp_path):
    """Por que este teste existe: o teste ponta a ponta roda o executavel como processo
    separado, e o processo usa os caminhos padrao - banco, feed e JSON de PRODUCAO.
    Sem um jeito de redirecionar, a suite passa a escrever no banco de verdade e, pior,
    a disparar centenas de requisicoes reais.

    Aconteceu em 16/08/2026, ao ligar o enriquecimento: a suite travou por minutos
    buscando paginas de detalhe de verdade, a partir do banco de producao."""
    import importlib
    import src.caminhos
    # A variavel aponta para outro lugar; RAIZ tem que obedecer.
    monkeypatch.setenv("MONITOR_VAGAS_RAIZ", str(tmp_path))
    importlib.reload(src.caminhos)
    assert src.caminhos.RAIZ == tmp_path
    # E os diretorios derivados acompanham, senao o redirecionamento seria parcial.
    assert src.caminhos.DIR_DADOS == tmp_path / "dados"
    # Desfaz, para nao contaminar os testes seguintes.
    monkeypatch.delenv("MONITOR_VAGAS_RAIZ")
    importlib.reload(src.caminhos)


def test_diretorios_derivam_da_raiz():
    """Por que este teste existe: os tres diretorios de dado sao irmaos de src/, nao
    filhos. Se alguem os mover para dentro de src/, a separacao entre codigo e dado
    quebra e este teste avisa."""
    from src.caminhos import RAIZ, DIR_CONFIG, DIR_DADOS, DIR_SAIDA
    # config/ guarda a entrada editada a mao.
    assert DIR_CONFIG == RAIZ / "config"
    # dados/ guarda o banco e os payloads crus.
    assert DIR_DADOS == RAIZ / "dados"
    # saida/ guarda a pagina gerada.
    assert DIR_SAIDA == RAIZ / "saida"
    # Nenhum deles pode estar dentro de src/.
    assert not str(DIR_CONFIG).startswith(str(RAIZ / "src"))


def test_arquivo_de_config_tem_caminho_padrao():
    """Por que este teste existe: o nome do arquivo de entrada e uma convencao do
    projeto. Deixar ele espalhado por varios modulos como string solta e como se
    perde a convencao."""
    from src.caminhos import DIR_CONFIG, ARQUIVO_CONFIG
    # O arquivo padrao vive dentro de config/ e se chama config.json.
    assert ARQUIVO_CONFIG == DIR_CONFIG / "config.json"


def test_caminhos_sao_objetos_path():
    """Por que este teste existe: o projeto roda em Windows com console cp1252 e nomes
    de insumo acentuados. Usar Path em vez de string e o que evita quebra de encoding
    e de separador de diretorio."""
    from src.caminhos import RAIZ, DIR_CONFIG, DIR_DADOS, DIR_SAIDA, ARQUIVO_CONFIG
    # Todos os caminhos publicos do modulo tem que ser Path, nunca str.
    for caminho in (RAIZ, DIR_CONFIG, DIR_DADOS, DIR_SAIDA, ARQUIVO_CONFIG):
        assert isinstance(caminho, Path)
