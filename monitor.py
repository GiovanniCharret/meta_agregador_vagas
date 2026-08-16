"""Lancador do monitor_vagas - o unico ponto de entrada do projeto.

Por que este arquivo existe na raiz e nao dentro de src/: quando o Python executa um
script, ele coloca o diretorio DO SCRIPT no caminho de import. Chamar `src/main.py`
direto colocaria `src/` no caminho, e o `import src.caminhos` de dentro dele falharia.
Com o lancador na raiz, o diretorio inserido e a propria raiz do projeto - e isso vale
mesmo quando a chamada vem de outro diretorio, que e o requisito de fazer um .bat
funcionar de qualquer lugar.

Uso:
    python monitor.py                      usa config/config.json
    python monitor.py caminho/outro.json   usa a configuracao indicada
"""

# sys da acesso aos argumentos da linha de comando e ao codigo de saida.
import sys

# Path converte o argumento de texto em caminho, que e o que o programa espera.
from pathlib import Path

# A logica toda vive em src/; este arquivo so resolve o argumento e delega.
from src.main import main

# Bloco de execucao direta: so roda quando o arquivo e chamado como script.
if __name__ == "__main__":
    # Sem argumento, main usa o caminho padrao do projeto; com argumento, usa o
    # indicado - o que permite testar contra uma configuracao temporaria.
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    # sys.exit converte o inteiro devolvido por main no codigo de saida do processo.
    sys.exit(main(caminho))
