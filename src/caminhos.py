"""Ancora unica de caminhos do projeto.

Por que este modulo existe: sem uma ancora, cada modulo montaria caminho do seu jeito
e o programa passaria a depender de qual diretorio o usuario estava quando chamou o
executavel. Concentrando tudo aqui, um arquivo .bat funciona de qualquer lugar e a
separacao entre codigo (src/) e dado (config/, dados/, saida/) fica explicita.

Logica da entrada a saida:
  Entrada -> o caminho do proprio arquivo, dado por __file__.
  Fase 1  -> resolve o caminho absoluto, eliminando ligacoes simbolicas e ".." .
  Fase 2  -> sobe dois niveis (arquivo -> src/ -> raiz do projeto).
  Fase 3  -> deriva os tres diretorios de dado e o arquivo de configuracao padrao.
  Saida   -> constantes Path prontas para uso pelos demais modulos.
"""

# Path e usado em vez de string para o codigo funcionar em Windows e Unix sem
# tratar separador de diretorio na mao, e para nao quebrar com nome acentuado.
from pathlib import Path

# Fase 1 e 2: __file__ aponta para este arquivo dentro de src/; o primeiro parent e
# src/ e o segundo e a raiz do projeto. resolve() garante caminho absoluto e real.
RAIZ = Path(__file__).resolve().parent.parent

# Fase 3: os tres diretorios de dado sao irmaos de src/, e nao filhos, para que
# nenhum dado gerado se misture com o codigo versionado.

# config/ guarda a entrada editada a mao pelo usuario (perfis, cidades, sinonimos).
DIR_CONFIG = RAIZ / "config"

# dados/ guarda o banco SQLite e os payloads crus de cada coleta (prova de origem).
DIR_DADOS = RAIZ / "dados"

# saida/ guarda a pagina HTML gerada ao fim do pipeline.
DIR_SAIDA = RAIZ / "saida"

# Nome do arquivo de entrada e convencao do projeto; fica aqui para nao se espalhar
# como string solta por varios modulos.
ARQUIVO_CONFIG = DIR_CONFIG / "config.json"
