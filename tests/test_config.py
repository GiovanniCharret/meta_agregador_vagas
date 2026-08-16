"""Testes de src/config.py - leitura e validacao do arquivo de entrada."""

# json serve para escrever os arquivos de configuracao usados como insumo dos testes.
import json

# pytest fornece o tmp_path e o pytest.raises usado nos testes de erro.
import pytest


def escreve_config(destino, conteudo):
    """Por que esta funcao existe: quase todo teste deste arquivo precisa de um
    config.json em disco, e repetir a escrita em cada teste esconderia o que cada um
    esta de fato verificando.

    Entrada -> um diretorio temporario e um dicionario Python.
    Fase 1  -> monta o caminho do arquivo dentro do diretorio.
    Fase 2  -> serializa o dicionario em JSON com acento preservado.
    Saida   -> o caminho do arquivo escrito, pronto para ser passado ao carregador.
    """
    # O nome do arquivo nao importa para o carregador, que recebe o caminho explicito.
    caminho = destino / "config.json"
    # ensure_ascii=False mantem acento legivel no arquivo, como o usuario escreveria.
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    # Devolve o caminho para o teste passar ao codigo sob teste.
    return caminho


# Configuracao minima valida, reaproveitada como base pelos testes que alteram um campo.
CONFIG_VALIDA = {
    "perfis": [
        {
            "nome": "dados",
            "lado": "meu",
            "termos": ["cientista de dados"],
            "sinonimos": ["data scientist"],
        },
        {"nome": "odonto", "lado": "dela", "termos": ["dentista"]},
    ],
    "ufs_liberadas": ["sc", "PR"],
    "cidades_bloqueadas": ["Rio Branco/AC"],
    "cidades_desejadas": ["Florianopolis/SC"],
    "termos_reprovacao": ["estagio"],
    "fontes_ativas": ["catho"],
}


def test_carrega_os_perfis_na_ordem_do_arquivo(tmp_path):
    """Por que este teste existe: a ordem dos perfis define a ordem de tudo o que vem
    depois. Determinismo e regra do projeto, e dicionario/set embaralhariam a ordem."""
    from src.config import carregar_config
    # Escreve a configuracao valida em disco.
    caminho = escreve_config(tmp_path, CONFIG_VALIDA)
    # Carrega pelo caminho explicito, sem depender do arquivo padrao do projeto.
    cfg = carregar_config(caminho)
    # Os dois perfis tem que voltar na mesma ordem em que foram escritos.
    assert [p.nome for p in cfg.perfis] == ["dados", "odonto"]


def test_perfil_expoe_lado_termos_e_sinonimos(tmp_path):
    """Por que este teste existe: o lado (meu/dela) e o que permite calcular o selo de
    companheiro; termos e sinonimos sao o que alimenta a busca."""
    from src.config import carregar_config
    caminho = escreve_config(tmp_path, CONFIG_VALIDA)
    cfg = carregar_config(caminho)
    # O primeiro perfil traz todos os campos preenchidos.
    primeiro = cfg.perfis[0]
    assert primeiro.lado == "meu"
    assert primeiro.termos == ["cientista de dados"]
    assert primeiro.sinonimos == ["data scientist"]


def test_sinonimos_ausentes_viram_lista_vazia(tmp_path):
    """Por que este teste existe: sinonimo e opcional, e obrigar o usuario a escrever
    uma lista vazia so para satisfazer o programa seria atrito sem motivo."""
    from src.config import carregar_config
    caminho = escreve_config(tmp_path, CONFIG_VALIDA)
    cfg = carregar_config(caminho)
    # O segundo perfil foi escrito sem a chave "sinonimos".
    assert cfg.perfis[1].sinonimos == []


def test_ufs_liberadas_viram_maiusculas(tmp_path):
    """Por que este teste existe: o usuario edita o arquivo a mao e vai escrever 'sc'
    e 'SC' de forma inconsistente. Normalizar na entrada evita que o filtro de estado
    falhe em silencio - que seria uma limitacao silenciosa, proibida pelo projeto."""
    from src.config import carregar_config
    caminho = escreve_config(tmp_path, CONFIG_VALIDA)
    cfg = carregar_config(caminho)
    # 'sc' foi escrito em minuscula no arquivo e tem que voltar normalizado.
    assert cfg.ufs_liberadas == ["SC", "PR"]


def test_carrega_as_listas_simples(tmp_path):
    """Por que este teste existe: cidades e termos de reprovacao alimentam os filtros
    da 3.2 e da 3.6; se nao chegarem inteiros, o feed filtra errado."""
    from src.config import carregar_config
    caminho = escreve_config(tmp_path, CONFIG_VALIDA)
    cfg = carregar_config(caminho)
    assert cfg.cidades_bloqueadas == ["Rio Branco/AC"]
    assert cfg.cidades_desejadas == ["Florianopolis/SC"]
    assert cfg.termos_reprovacao == ["estagio"]
    assert cfg.fontes_ativas == ["catho"]


def test_listas_opcionais_ausentes_viram_vazias(tmp_path):
    """Por que este teste existe: no comeco do projeto so os perfis existem de fato.
    Exigir todas as listas desde o primeiro dia travaria a S1 sem necessidade."""
    from src.config import carregar_config
    # Configuracao com o minimo indispensavel: perfis e a lista branca de estados.
    minima = {
        "perfis": [{"nome": "dados", "lado": "meu", "termos": ["python"]}],
        "ufs_liberadas": ["SC"],
    }
    caminho = escreve_config(tmp_path, minima)
    cfg = carregar_config(caminho)
    # Todas as listas opcionais tem que existir vazias, nunca None.
    assert cfg.cidades_bloqueadas == []
    assert cfg.cidades_desejadas == []
    assert cfg.termos_reprovacao == []
    assert cfg.fontes_ativas == []
