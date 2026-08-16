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
    python monitor.py publicar             monta o pacote para subir por FTP
"""

# sys da acesso aos argumentos da linha de comando e ao codigo de saida.
import sys

# Path converte o argumento de texto em caminho, que e o que o programa espera.
from pathlib import Path

# Os caminhos padrao vivem na ancora, nao aqui.
from src.caminhos import ARQUIVO_CONFIG, DIR_DADOS, DIR_SAIDA, RAIZ

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
        termos_por_perfil={
            p.nome: list(p.termos) + list(p.sinonimos) for p in configuracao.perfis
        },
    )

    # Fase 3: 127.0.0.1 de proposito, e nao 0.0.0.0 - o servidor nao deve ficar exposto
    # na rede local, porque nao tem autenticacao nenhuma.
    print("Feed em http://127.0.0.1:8000  (Ctrl+C para encerrar)")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

    # Saida: encerrar o servidor e uma acao normal, nao um erro.
    return 0


def publicar():
    """Monta o pacote de arquivos que sobe para o presenterosa.com.br.

    Por que existe um comando separado: o deploy desta fase e estatico e manual - voce
    atualiza quando quiser e sobe por FTP. Um comando que junta tudo numa pasta so evita
    voce ter que lembrar quais arquivos mudaram a cada vez.

    Por que ele NAO coleta: coletar e publicar sao decisoes diferentes. Voce pode querer
    republicar sem recoletar, ou coletar varias vezes antes de publicar. Junta-los tiraria
    essa escolha de voce.

    Entrada -> nada; usa o banco e os arquivos do site ja no projeto.
    Fase 1  -> le a configuracao e o acervo do banco.
    Fase 2  -> aplica os mesmos filtros e anotacoes do feed local.
    Fase 3  -> monta a pagina no visual do site, linkando a folha dele.
    Fase 4  -> edita o index e o app.js do site para apontarem para a pagina nova.
    Fase 5  -> grava tudo numa pasta so e diz o que subir.
    Saida   -> zero quando o pacote for montado.
    """
    # Importados aqui dentro para uma rodada de coleta nao pagar o custo de carregar o
    # que ela nao usa.
    import sqlite3
    from datetime import datetime

    from src.armazena import listar_vagas
    from src.config import carregar_config
    from src.erros import EntradaInvalida
    from src.feed import montar_feed
    from src.filtros import anotar_casamentos, aplicar
    from src.publica import ARQUIVO_DA_PAGINA, app_js_atualizado, index_atualizado

    # A pasta com os arquivos originais do site, e o destino do pacote.
    origem_do_site = RAIZ / "suporte_contexto" / "site"
    destino = DIR_SAIDA / "publicar"

    # Fase 1: erro de dado segue a mesma regra do resto do programa.
    try:
        configuracao = carregar_config(ARQUIVO_CONFIG)
    except EntradaInvalida as erro:
        print("ERRO: {}".format(erro), file=sys.stderr)
        return 1

    banco = DIR_DADOS / "vagas.sqlite"
    if not banco.exists():
        print("ERRO: banco nao encontrado em {}. Rode a coleta antes de publicar."
              .format(banco), file=sys.stderr)
        return 1

    conexao = sqlite3.connect(banco)
    try:
        itens = listar_vagas(conexao)
    finally:
        conexao.close()

    # Fase 2: os mesmos filtros do feed local, para a pagina publicada nao divergir do
    # que voce ve na sua maquina.
    itens, _ = aplicar(
        itens, configuracao.ufs_liberadas, configuracao.cidades_bloqueadas,
        configuracao.termos_reprovacao,
    )
    itens = anotar_casamentos(itens, {
        p.nome: list(p.termos) + list(p.sinonimos) for p in configuracao.perfis
    })

    # Fase 3: `filtradas` fica de fora de proposito - "reprovadas por termo" e diagnostico
    # para quem construiu, e nao informacao para quem usa.
    pagina = montar_feed(
        itens,
        cidades_desejadas=configuracao.cidades_desejadas,
        gerado_em=datetime.now().strftime("%d/%m/%Y"),
        folha_do_site="style.css",
    )

    # Fase 4: as edicoes falham alto se o site tiver mudado.
    try:
        indice = index_atualizado(
            (origem_do_site / "index.html").read_text(encoding="utf-8"))
        script = app_js_atualizado(
            (origem_do_site / "app.js").read_text(encoding="utf-8"))
    except FileNotFoundError as erro:
        print("ERRO: arquivo do site nao encontrado: {}".format(erro), file=sys.stderr)
        return 1
    except EntradaInvalida as erro:
        print("ERRO: {}".format(erro), file=sys.stderr)
        return 1

    # Fase 5: newline="" evita o Windows trocar \n por \r\n e inflar o diff a cada
    # geracao, o que atrapalharia comparar dois pacotes.
    destino.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in ((ARQUIVO_DA_PAGINA, pagina),
                           ("index.html", indice),
                           ("app.js", script)):
        with open(destino / nome, "w", encoding="utf-8", newline="") as arquivo:
            arquivo.write(conteudo)

    # Saida: instrucao explicita, porque o upload e manual.
    print("Pacote pronto em {}".format(destino))
    print("{} vaga(s) na pagina.".format(len(itens)))
    print()
    print("Suba estes tres arquivos para a raiz do site (public_html), por FTP:")
    for nome in (ARQUIVO_DA_PAGINA, "index.html", "app.js"):
        print("   {}".format(nome))
    print()
    print("O style.css nao mudou e nao precisa subir.")
    return 0


# Bloco de execucao direta: so roda quando o arquivo e chamado como script.
if __name__ == "__main__":
    # O primeiro argumento escolhe o comando; sem argumento, coleta.
    primeiro = sys.argv[1] if len(sys.argv) > 1 else None

    if primeiro == "servir":
        sys.exit(servir())

    if primeiro == "publicar":
        sys.exit(publicar())

    # Sem argumento, main usa o caminho padrao; com argumento, usa a configuracao
    # indicada - o que permite testar contra uma configuracao temporaria.
    sys.exit(main(Path(primeiro) if primeiro else None))
