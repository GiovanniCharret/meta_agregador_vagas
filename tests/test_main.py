"""Testes de src/main.py - o executavel unico do projeto."""

import json

# Reaproveita os utilitarios de escrita de configuracao dos outros testes.
from tests.test_config import escreve_config, CONFIG_VALIDA


def test_config_valida_devolve_codigo_zero(tmp_path):
    """Por que este teste existe: o codigo de saida e o unico jeito de um .bat ou um
    agendador saber se a rodada funcionou. Zero significa sucesso."""
    from src.main import main
    caminho = escreve_config(tmp_path, CONFIG_VALIDA)
    # main recebe o caminho explicito para o teste nao depender do arquivo real.
    assert main(caminho) == 0


def test_config_invalida_devolve_codigo_um(tmp_path):
    """Por que este teste existe: erro de dado precisa terminar o programa com codigo
    1, e nao com zero, senao um agendador trataria a falha como sucesso."""
    from src.main import main
    # Configuracao sem perfil nenhum: erro de dado, nao bug de programa.
    caminho = escreve_config(tmp_path, {"perfis": []})
    assert main(caminho) == 1


def test_erro_de_dado_escreve_mensagem_limpa_sem_traceback(tmp_path, capsys):
    """Por que este teste existe: esta e a regra central do projeto sobre falhas. O
    usuario final precisa ler uma frase que ele consiga agir, e nao um traceback. Se
    alguem trocar o `except` por um `raise`, este teste quebra."""
    from src.main import main
    caminho = escreve_config(tmp_path, {"perfis": []})
    # Executa e captura o que foi escrito nas duas saidas.
    main(caminho)
    capturado = capsys.readouterr()
    # A mensagem de erro vai para a saida de erro, nao para a saida padrao.
    assert "perfil" in capturado.err.lower()
    # E nao pode conter as marcas de um traceback vazado.
    assert "Traceback" not in capturado.err
    assert "File \"" not in capturado.err


def test_bug_de_programa_nao_e_engolido(tmp_path):
    """Por que este teste existe: o `except EntradaInvalida` nao pode virar um
    `except Exception` com o tempo. Se virar, um bug nosso passaria a ser mostrado ao
    usuario como se fosse erro de dado dele, e nos perderiamos o traceback."""
    import pytest
    from src.main import main
    # None nao tem o metodo exists(), entao a chamada levanta AttributeError - que e
    # um bug de programa e precisa vazar como traceback normal.
    with pytest.raises(AttributeError):
        main(None, usar_padrao=False)
