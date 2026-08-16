# TESTES — mapa de testes por fase

> Para você poder repetir qualquer verificação sozinho, sem depender de mim.
> Atualizado em 16/08/2026, ao fim da subfase **S0**.

## Como rodar

```powershell
# a suite inteira
.venv\Scripts\python.exe -m pytest

# um arquivo so
.venv\Scripts\python.exe -m pytest tests/test_config.py

# um teste so, pelo nome
.venv\Scripts\python.exe -m pytest -k lado_invalido

# vendo o nome de cada teste que passou
.venv\Scripts\python.exe -m pytest -v
```

O `pytest.ini` coloca a raiz do projeto no caminho de import e aponta `testpaths` para
`tests/`, então não é preciso instalar o projeto nem mexer em variável de ambiente.

**Estado atual: 27 testes, todos passando.**

---

## S0 — esqueleto

### `tests/test_caminhos.py` — 5 testes

Testa a âncora de caminhos, que é o que faz um `.bat` funcionar de qualquer diretório.

| Teste | O que trava |
|---|---|
| `raiz_aponta_para_o_diretorio_que_contem_src` | `RAIZ` apontando para o lugar errado |
| `raiz_independe_do_diretorio_de_trabalho` | alguém trocar `__file__` por `cwd` |
| `diretorios_derivam_da_raiz` | mover `config/`, `dados/` ou `saida/` para dentro de `src/` |
| `arquivo_de_config_tem_caminho_padrao` | o nome do arquivo virar string solta espalhada |
| `caminhos_sao_objetos_path` | alguém trocar `Path` por `str` e quebrar em Windows |

O teste do diretório de trabalho recarrega o módulo com o `cwd` trocado — é a única
forma de provar que a âncora não usa o diretório atual.

### `tests/test_config.py` — 6 testes

Caminho feliz da leitura da configuração.

Cobrem: ordem dos perfis preservada (determinismo), campos do perfil, `sinonimos`
ausente virando lista vazia, UF normalizada para maiúscula, listas simples carregadas,
e listas opcionais ausentes virando vazias em vez de `None`.

### `tests/test_config_erros.py` — 10 testes

A recusa de entrada torta. **É o arquivo mais importante do S0**, porque a regra do
projeto é que limitação nunca seja silenciosa.

Cobrem: arquivo ausente (mensagem cita o caminho procurado), JSON malformado
(mensagem cita linha e coluna, sem jargão do parser), `perfis` ausente ou vazio, perfil
sem `nome`, sem `termos` ou com `termos` vazio, `lado` inválido (mensagem cita o valor
errado, o perfil culpado e os valores aceitos), UF mal escrita, e a hierarquia de
`EntradaInvalida`.

**Detalhe que um teste pegou e que vale lembrar:** a validação de UF acontece *antes* da
normalização para maiúscula. Se fosse depois, a mensagem diria `ACRE` enquanto o arquivo
do usuário diz `Acre`, e um Ctrl+F no editor não acharia nada.

### `tests/test_main.py` — 4 testes

O executável: código de saída 0 no sucesso e 1 no erro de dado, mensagem limpa na saída
de erro sem `Traceback`, e — o mais importante — **bug de programa não é engolido**.
Esse último trava a degeneração do `except EntradaInvalida` em `except Exception`, que
faria um defeito nosso aparecer para o usuário como se fosse erro de dado dele.

### `tests/test_e2e_executavel.py` — 2 testes

Ponta a ponta, rodando `monitor.py` como **processo separado** a partir de um diretório
temporário.

**Este arquivo existe por causa de um bug real.** A suíte de unidade passava enquanto o
executável não rodava: o `pytest.ini` coloca a raiz no caminho de import, escondendo o
fato de que `python src/main.py` colocaria `src/` no caminho e o import falharia. Só
chamando o processo de verdade o defeito apareceu. Daí o lançador `monitor.py` na raiz.

**Lição a manter:** toda subfase precisa de ao menos um teste que rode o programa como o
usuário roda. Teste de unidade que importa o módulo não prova que o programa executa.

---

## Verificação manual do S0

```powershell
# 1. sucesso, rodando de qualquer diretorio
cd $env:TEMP
& "C:\Users\gioch\Documents\Python_Projects\monitor_vagas\.venv\Scripts\python.exe" `
  "C:\Users\gioch\Documents\Python_Projects\monitor_vagas\monitor.py"
# esperado: "Configuracao lida: 4 perfil(is), 2 UF(s) bloqueada(s)." e codigo 0

# 2. erro de dado, com mensagem limpa
cd C:\Users\gioch\Documents\Python_Projects\monitor_vagas
.venv\Scripts\python.exe monitor.py config\nao_existe.json
# esperado: linha comecando com "ERRO:" e codigo 1, sem traceback
```

---

## Subfases seguintes — o que cada uma precisa provar

Registro antecipado para o teste não virar reflexão tardia. **Subfase sem teste não conta
como concluída** (D8).

| Subfase | O teste tem que provar |
|---|---|
| S1 | uma fonte real vira JSON normalizado; erro de rede não derruba a rodada inteira |
| S2 | o mesmo JSON gera o mesmo HTML **byte a byte** (determinismo, D8) |
| S3 | estado sobrevive a reinício; descarte sem motivo é recusado |
| S4 | duas cópias da mesma vaga viram um card com dois links; duas vagas diferentes da mesma empresa e cidade **não** se fundem |
| S5 | cidade bloqueada não aparece; termo de reprovação descarta; sinônimo encontra o que o termo-semente sozinho não acharia |
| S6 | vaga casada por dois perfis aparece uma vez, citando os dois; "por que apareceu" mostra os termos certos |
| S7 | o selo aparece só quando há vaga viva do outro lado na mesma cidade; **remoto não gera selo** |
| S8 | cada fonte nova não quebra as anteriores |
| S9 | concurso não é forçado no esquema de vaga; `cadastro_reserva` fica visível |
| S10 | alerta não dispara duas vezes para a mesma vaga |
