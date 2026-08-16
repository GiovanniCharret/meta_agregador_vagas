"""Teste ponta a ponta do executavel real, rodado como processo separado.

Por que este arquivo existe: os testes de unidade importam `src.main` com a raiz do
projeto ja no caminho de import, porque o pytest.ini coloca ela la. Isso esconde uma
falha inteira - a de o executavel nao conseguir importar os proprios modulos quando
chamado direto pela linha de comando. So chamando o processo de verdade, de outro
diretorio, esse tipo de defeito aparece.
"""

# os copia o ambiente atual para acrescentar o redirecionamento da raiz.
import os

# subprocess roda o executavel como o usuario rodaria, num processo separado.
import subprocess

# sys da o interpretador atual, que dentro do pytest e o do proprio venv.
import sys

# Path monta o caminho do lancador sem depender do diretorio de trabalho.
from pathlib import Path

# Reaproveita os utilitarios de escrita de configuracao dos outros testes.
from tests.test_config import escreve_config, CONFIG_VALIDA

# A raiz do projeto e o diretorio acima de tests/.
RAIZ = Path(__file__).resolve().parent.parent

# O lancador e o unico ponto de entrada do projeto.
LANCADOR = RAIZ / "monitor.py"


def roda(caminho_config, diretorio_de_trabalho):
    """Executa o lancador num processo separado e devolve o resultado.

    Por que esta funcao existe: os dois testes deste arquivo so diferem na configuracao
    passada. Concentrar a chamada aqui deixa visivel, em cada teste, apenas o que ele
    esta de fato verificando.

    Entrada -> o caminho de um config.json e o diretorio de onde chamar o processo.
    Fase 1  -> monta a linha de comando com o interpretador do venv.
    Fase 2  -> executa capturando as duas saidas como texto.
    Saida   -> o objeto de resultado do subprocess, com codigo, stdout e stderr.
    """
    # O ambiente redireciona a raiz do projeto para o diretorio temporario. Sem isso o
    # processo filho escreveria no banco e no feed de PRODUCAO, e o enriquecimento sairia
    # buscando paginas de detalhe de verdade a partir do acervo real - foi o que travou a
    # suite em 16/08/2026.
    ambiente = dict(os.environ)
    ambiente["MONITOR_VAGAS_RAIZ"] = str(diretorio_de_trabalho)

    # Fase 1 e 2: cwd diferente da raiz e o que prova que o programa nao depende dele.
    return subprocess.run(
        [sys.executable, str(LANCADOR), str(caminho_config)],
        cwd=str(diretorio_de_trabalho),
        capture_output=True,
        text=True,
        env=ambiente,
    )


def test_executavel_roda_de_outro_diretorio(tmp_path):
    """Por que este teste existe: a razao de existir da ancora RAIZ e permitir que um
    .bat funcione de qualquer diretorio. Rodar a partir de um diretorio temporario e a
    unica forma de provar isso de verdade."""
    # Escreve uma configuracao valida no diretorio temporario.
    caminho = escreve_config(tmp_path, CONFIG_VALIDA)
    # Chama o executavel a partir do proprio diretorio temporario, longe da raiz.
    resultado = roda(caminho, tmp_path)
    # Codigo zero significa rodada bem sucedida; o stderr entra na mensagem para o
    # diagnostico aparecer quando falhar.
    assert resultado.returncode == 0, resultado.stderr
    # A confirmacao do que foi lido tem que chegar na saida padrao.
    assert "Configuracao lida" in resultado.stdout


def test_executavel_recusa_dado_torto_sem_vazar_traceback(tmp_path):
    """Por que este teste existe: a regra do projeto sobre falhas so vale se valer no
    processo real. Um traceback capturado dentro do pytest nao prova que o usuario
    final nao veria um."""
    # Configuracao sem perfil nenhum: erro de dado, nao bug de programa.
    caminho = escreve_config(tmp_path, {"perfis": []})
    resultado = roda(caminho, tmp_path)
    # Erro de dado termina com codigo 1.
    assert resultado.returncode == 1
    # A mensagem tem que ser legivel e citar o problema.
    assert "perfil" in resultado.stderr.lower()
    # E nenhum traceback pode vazar para o usuario final.
    assert "Traceback" not in resultado.stderr
