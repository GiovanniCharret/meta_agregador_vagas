"""Lancador do monitor_vagas - o unico ponto de entrada do projeto.

Por que este arquivo existe na raiz e nao dentro de src/: quando o Python executa um
script, ele coloca o diretorio DO SCRIPT no caminho de import. Chamar `src/main.py`
direto colocaria `src/` no caminho, e o `import src.caminhos` de dentro dele falharia.
Com o lancador na raiz, o diretorio inserido e a propria raiz do projeto - e isso vale
mesmo quando a chamada vem de outro diretorio, que e o requisito de fazer um .bat
funcionar de qualquer lugar.

Uso:
    python monitor.py                      coleta e gera o feed estatico
    python monitor.py caminho/outro.json   coleta usando outra configuracao
    python monitor.py servir               sobe o servidor local para marcar as vagas
"""

# sys da acesso aos argumentos da linha de comando e ao codigo de saida.
import sys

# Path converte o argumento de texto em caminho, que e o que o programa espera.
from pathlib import Path

# Os caminhos padrao vivem na ancora, nao aqui.
from src.caminhos import ARQUIVO_CONFIG, DIR_DADOS

# A logica de coleta vive em src/; este arquivo so resolve o argumento e delega.
from src.main import main


def servir():
    """Sobe o servidor local que permite marcar as vagas.

    Por que existe um comando separado para isso: coletar e navegar sao duas atividades
    diferentes. A coleta roda uma vez e termina; o servidor fica de pe enquanto voces
    olham o feed. Juntar os dois obrigaria a recoletar toda vez que quisessem abrir a
    pagina.

    Entrada -> nada; usa os caminhos padrao do projeto.
    Fase 1  -> le a configuracao, so para saber as cidades desejadas.
    Fase 2  -> monta o aplicativo apontado para o banco do projeto.
    Fase 3  -> sobe o servidor no endereco local.
    Saida   -> zero quando o servidor for encerrado com Ctrl+C.
    """
    # Importados aqui dentro para que uma rodada de coleta nao pague o custo de carregar
    # o FastAPI e o uvicorn, que nao usa.
    import uvicorn

    from src.config import carregar_config
    from src.erros import EntradaInvalida
    from src.servidor import criar_app

    # Fase 1: a configuracao so e lida por causa das cidades desejadas, que mudam a
    # ordem do feed. Erro de dado aqui segue a mesma regra do resto do programa.
    try:
        configuracao = carregar_config(ARQUIVO_CONFIG)
    except EntradaInvalida as erro:
        print("ERRO: {}".format(erro), file=sys.stderr)
        return 1

    # Fase 2: o banco e o mesmo que a coleta alimenta.
    app = criar_app(
        DIR_DADOS / "vagas.sqlite",
        cidades_desejadas=configuracao.cidades_desejadas,
        ufs_liberadas=configuracao.ufs_liberadas,
        cidades_bloqueadas=configuracao.cidades_bloqueadas,
        termos_reprovacao=configuracao.termos_reprovacao,
    )

    # Fase 3: 127.0.0.1 de proposito, e nao 0.0.0.0 - o servidor nao deve ficar exposto
    # na rede local, porque nao tem autenticacao nenhuma.
    print("Feed em http://127.0.0.1:8000  (Ctrl+C para encerrar)")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

    # Saida: encerrar o servidor e uma acao normal, nao um erro.
    return 0


# Bloco de execucao direta: so roda quando o arquivo e chamado como script.
if __name__ == "__main__":
    # O primeiro argumento escolhe entre servir e coletar; sem argumento, coleta.
    primeiro = sys.argv[1] if len(sys.argv) > 1 else None

    if primeiro == "servir":
        sys.exit(servir())

    # Sem argumento, main usa o caminho padrao; com argumento, usa a configuracao
    # indicada - o que permite testar contra uma configuracao temporaria.
    sys.exit(main(Path(primeiro) if primeiro else None))
