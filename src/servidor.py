"""Servidor local que serve o feed e recebe as marcacoes.

Por que este modulo existe, e por que ele foi o unico motivo de haver FastAPI no
projeto: marcar uma vaga como salva ou descartada precisa GRAVAR, e HTML estatico nao
grava. Sem ele, a decisao 3.8 e a 4.1 nao existiriam - o feed seria so leitura e toda a
instrumentacao de UX morreria junto.

Postura: servidor local, para duas pessoas, sem autenticacao. `quem` e um rotulo que
separa os estados de cada um, e nao uma conta - multiusuario com login esta fora do
escopo por decisao da triagem.

A marcacao acontece por formulario HTML puro, sem JavaScript, respondendo com um
redirecionamento. Isso evita o reenvio do formulario quando o navegador atualiza a
pagina, que e o defeito classico de responder POST com HTML.
"""

# sqlite3 abre uma conexao por requisicao; o custo e irrisorio nesta escala e evita ter
# que lidar com conexao compartilhada entre threads.
import sqlite3

# datetime carimba o horario da marcacao e o rodape do feed.
from datetime import datetime

# As pecas do FastAPI usadas: o app, o corpo de formulario e as duas respostas.
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse

# As funcoes de persistencia e o vocabulario fechado de estados e motivos.
from src.armazena import MOTIVOS, listar_vagas, marcar

# EntradaInvalida e o que separa erro do usuario de defeito nosso.
from src.erros import EntradaInvalida

# montar_feed transforma a lista de vagas na pagina.
from src.feed import montar_feed

# aplicar roda os filtros; anotar_casamentos explica por que a vaga apareceu.
from src.filtros import anotar_casamentos, aplicar


def criar_app(caminho_banco, cidades_desejadas=(), ufs_liberadas=(),
              cidades_bloqueadas=(), termos_reprovacao=(), termos_por_perfil=None):
    """Monta o aplicativo apontado para um banco.

    Por que o caminho do banco entra por parametro em vez de vir da ancora de caminhos:
    e o que permite aos testes rodarem sobre um banco temporario. Sem isso, a suite
    passaria a marcar vagas no banco de verdade do projeto.

    Entrada -> o caminho do arquivo SQLite e as cidades desejadas da configuracao.
    Fase 1  -> cria o aplicativo e a funcao que abre conexao.
    Fase 2  -> registra a rota do feed.
    Fase 3  -> registra a rota que recebe a marcacao.
    Saida   -> o aplicativo pronto para ser servido.
    """
    # Fase 1: um aplicativo por chamada, sem estado global.
    app = FastAPI(title="monitor_vagas")

    def conectar():
        """Abre uma conexao nova para a requisicao atual."""
        # Uma conexao por requisicao evita compartilhar conexao entre threads, que o
        # sqlite3 nao permite por padrao.
        return sqlite3.connect(caminho_banco)

    def pagina_de_erro(mensagem):
        """Monta a resposta de erro que o usuario le na tela.

        Por que ela existe: sem isto, uma EntradaInvalida viraria erro 500 com traceback
        na tela - exatamente o que a regra do projeto proibe para erro de dado.
        """
        # Pagina minima, com o caminho de volta explicito.
        corpo = (
            "<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
            "<title>Nao deu</title></head><body style=\"font-family:system-ui;"
            "max-width:640px;margin:64px auto;padding:0 24px;line-height:1.6\">"
            "<h1 style=\"font-size:20px\">Nao deu para marcar</h1>"
            "<p>{}</p><p><a href=\"/\">voltar ao feed</a></p></body></html>"
        ).format(mensagem)
        # 400 e o codigo certo: o pedido chegou torto, o servidor esta bem.
        return HTMLResponse(corpo, status_code=400)

    @app.get("/", response_class=HTMLResponse)
    def feed(quem: str = "meu"):
        """Serve o feed da pessoa indicada.

        Entrada -> de quem sao os estados a mostrar, vindo da barra de endereco.
        Fase 1  -> le as vagas do banco, ja com o estado daquela pessoa.
        Fase 2  -> tira da lista as descartadas, que e a razao de existir da 3.8.
        Fase 3  -> monta a pagina, informando quantas foram escondidas.
        Saida   -> o HTML do feed.
        """
        # Fase 1: uma consulta so devolve vaga e estado juntos.
        conexao = conectar()
        try:
            todas = listar_vagas(conexao, quem=quem)
        finally:
            conexao.close()

        # Fase 2: descartar tem que TIRAR a vaga da frente - senao o horizonte continuo
        # deixaria o feed impraticavel em poucos dias.
        visiveis = [v for v in todas if v["estado"] != "descartada"]
        escondidas = len(todas) - len(visiveis)

        # Fase 3: os filtros da configuracao rodam na LEITURA, e nao na coleta. Assim,
        # mudar a lista de cidades tem efeito imediato sem recoletar, e nenhuma vaga se
        # perde por causa de uma lista mal escrita - o dado continua no banco.
        visiveis, filtradas = aplicar(
            visiveis, ufs_liberadas, cidades_bloqueadas, termos_reprovacao
        )

        # A anotacao do "por que apareceu" tambem roda na leitura, pela mesma razao dos
        # filtros: mudar a lista de sinonimos passa a ter efeito imediato.
        visiveis = anotar_casamentos(visiveis, termos_por_perfil or {})

        # Fase 4 e saida: os contadores evitam a limitacao silenciosa de o feed encolher
        # sem explicacao.
        return montar_feed(
            visiveis,
            cidades_desejadas=cidades_desejadas,
            gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"),
            quem=quem,
            motivos=MOTIVOS,
            descartadas=escondidas,
            filtradas=filtradas,
        )

    @app.post("/marcar")
    def registrar_marcacao(
        id_canonico: str = Form(...),
        quem: str = Form(...),
        estado: str = Form(...),
        motivo: str = Form(default=""),
    ):
        """Recebe a marcacao de uma vaga e volta para o feed.

        Entrada -> os campos do formulario do card.
        Fase 1  -> grava, deixando a validacao inteira para a camada de armazenamento -
                   e ela quem conhece as regras da 3.8 e da 4.1.
        Fase 2  -> erro de dado vira pagina legivel, e nao traceback.
        Saida   -> redirecionamento de volta para o feed da mesma pessoa.
        """
        conexao = conectar()
        try:
            # Fase 1: a regra do motivo obrigatorio mora em `marcar`, e nao aqui. Se
            # fosse duplicada, um dia as duas discordariam.
            marcar(
                conexao, id_canonico, quem=quem, estado=estado,
                motivo=motivo or None,
                agora=datetime.now().isoformat(timespec="seconds"),
            )
        except EntradaInvalida as erro:
            # Fase 2: mensagem pronta para o usuario, como toda EntradaInvalida.
            return pagina_de_erro(str(erro))
        finally:
            conexao.close()

        # Saida: 303 faz o navegador trocar o POST por um GET, o que evita o reenvio do
        # formulario quando a pagina e atualizada.
        return RedirectResponse("/?quem={}".format(quem), status_code=303)

    return app
