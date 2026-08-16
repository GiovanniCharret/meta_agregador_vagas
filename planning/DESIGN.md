# DESIGN — hub de vagas filtradas

> Documento de design do MVP. Deriva de `planning/IDEIAS.md` (triagem de 15/08/2026) e
> `planning/FONTES_ODONTO.md` (triagem de 16/08/2026). Onde este documento contraria o
> `PLAN.md`, está sinalizado e **pende de decisão sua** — não mudei o `PLAN.md`.
>
> Escrito em 16/08/2026.

---

## D1 — O que o MVP é, e o que ele não é

### A pergunta que o produto responde

Nesta fase: *"quais vagas, dentro dos meus filtros, existem agora?"* — apresentadas num feed
simples, com um selo quando aquela cidade também tem oportunidade para a outra pessoa.

O eixo cidade, que eu tinha proposto como estrutura do produto, foi **rebaixado a atributo do
card** na triagem. O placar de cidades (`3.3`) está congelado.

### Escopo fechado — 10 itens

| # | Item | Alteração aprovada |
|---|---|---|
| `3.1` | Perfis de busca nomeados | — |
| `3.2` | Cidades e UFs bloqueadas / desejadas | — |
| `3.4` | Oportunidade para o companheiro | vira **selo no card**, não tela |
| `3.5` | Sinônimos por área, escritos à mão | — |
| `3.6` | Filtro de reprovação por palavra | — |
| `3.7` | Deduplicação: um card, vários links | — |
| `3.8` | Estado da vaga: nova / salva / descartada | descongelada |
| `4.1` | Descarte com motivo | motivo **obrigatório** |
| `4.2` | "Por que esta vaga apareceu" | — |
| `5.2` | Alertas por e-mail e Telegram | promovida do icebox |

### Princípios que regem as decisões

1. **Fácil de puxar primeiro.** Alto custo de desenvolvimento ou workaround vai para a fase
   seguinte. Critério declarado por você em 16/08/2026, vale mais que qualquer ranking meu.
2. **Sem teto de volume.** Mostrar todas as vagas; criar filtro depois, se o esforço compensar.
3. **Horizonte contínuo.** Não é uma busca de seis meses; é monitoramento permanente.
4. **Determinismo.** Mesma entrada, mesma saída. Nada de aleatoriedade não semeada.
5. **Limitação explícita, nunca silenciosa.** Erro de dado vira `EntradaInvalida` com mensagem
   pronta e saída com código 1, sem traceback. Descarte e fallback viram `AVISO: ...`.

### Fora do MVP

Placar de cidades · score de aderência · kanban de candidaturas · watchlist de empresas · mapa ·
RSS próprio · histórico por cidade · diário de números · custo de vida, competição e qualidade de
vida por cidade (`5.7`, rodada dois) · candidatura automática · multiusuário com autenticação.

---

## D2 — Modelo de dados

### Por que duas entidades e não uma

Concurso público **não é uma vaga**. Tem órgão em vez de empresa, prazo de inscrição em vez de
data de publicação, banca organizadora, e a distinção entre vaga imediata e cadastro reserva.
Forçar no esquema de vaga deixa metade dos campos vazios e a outra metade mentindo. Aprovado como
entidade separada, unificada só na apresentação.

### `vaga`

| Campo | Tipo | Observação |
|---|---|---|
| `id` | uuid | chave interna |
| `id_canonico` | texto | hash que agrupa duplicatas — ver D3 |
| `fonte` | texto | `catho`, `indeed`, `gupy`, … |
| `id_na_fonte` | texto | identificador externo, quando existir |
| `url` | texto | link original |
| `titulo_bruto` / `titulo_normalizado` | texto | no BNE é a função normalizada por eles, não o título do anúncio |
| `subtitulo` | texto | vem de `responsibilities` da página de detalhe; é onde mora a especialidade |
| `descricao` | texto | texto completo do anúncio, só disponível na página de detalhe |
| `empresa_bruta` / `empresa_normalizada` | texto | `Confidencial` aparece em 25% das vagas do BNE e **não é nome de empresa** |
| `cidade` / `uf` | texto | normalizados |
| `modalidade` | enum | `presencial`, `hibrido`, `remoto`, `desconhecido` |
| `perfil` | texto | qual perfil casou: `dados`, `dev`, `financeiro`, `odonto` |
| `termos_casados` | lista | alimenta a `4.2` |
| `salario_texto` | texto | **cru, sem parsing.** A listagem do BNE manda `0.0` sempre; o valor real só aparece na página de detalhe, em `baseSalary` |
| `data_publicacao` | data | quando a fonte informa |
| `capturado_em` | timestamp | quando entrou aqui |
| `ativa` | booleano | falsa quando some da fonte |

Salário fica como texto de propósito: nenhum item aprovado filtra por salário, e modelar
mínimo/máximo/moeda/período agora seria trabalho especulativo.

### `concurso`

`id` · `id_canonico` · `fonte` · `url` · `orgao` · `cidade` · `uf` · `cargo` · `n_vagas` ·
`tipo_vaga` (`imediata` | `cadastro_reserva`) · `salario_texto` · `prazo_inscricao` · `banca` ·
`capturado_em` · `ativa`

`cadastro_reserva` precisa ficar visível no card: é uma vaga que pode nunca existir.

### `estado_item`

| Campo | Observação |
|---|---|
| `id_canonico` | aponta para vaga ou concurso |
| `quem` | rótulo simples, sem autenticação — reusa o `lado` do perfil: `meu` ou `dela` |
| `estado` | `nova`, `salva`, `descartada` |
| `motivo` | **obrigatório** quando `descartada` |
| `marcado_em` | timestamp |

`quem` é um rótulo, não um sistema de contas. Multiusuário com autenticação está fora do escopo.

### `evento`

Log append-only: `tipo`, `id_canonico`, `payload`, `criado_em`. É a matéria-prima do dado de UX
que vai guiar as próximas fases. Coletar agora custa pouco; recuperar depois é impossível.

### Motivos de descarte (enum fechado)

`cidade` · `salario` · `requisito_que_nao_tenho` · `modalidade` · `empresa` · `nao_e_minha_area` ·
`vaga_velha_ou_fantasma`

---

## D3 — Pipeline de coleta

```
config (JSON/XLSX)
   ↓
[1] coleta por fonte     →  listagem: bruto + prova de origem
   ↓
[2] enriquecimento       →  pagina de detalhe de cada vaga INEDITA
   ↓                         descricao, subtitulo, salario real
[3] normalização         →  cidade, UF, modalidade, título, empresa
   ↓
[4] deduplicação         →  id_canonico
   ↓
[5] filtros              →  cidades bloqueadas, palavras de reprovação
   ↓
[6] persistência         →  vaga / concurso / estado_item / evento
   ↓
[7] feed HTML
```

**Por que o enriquecimento é um passo próprio.** A listagem não traz descrição nem salário
real; a página de detalhe traz os dois, em JSON-LD `JobPosting` (schema.org). Custa uma
requisição por vaga, e por isso só roda para vaga **inédita** — o que exige que o estado já
exista. Daí ele ser a subfase S3b, depois da persistência e antes da deduplicação, que
depende dele.

`JobPosting` em JSON-LD é padrão de indústria, publicado para o Google Empregos. Se as outras
fontes também publicarem, existe um caminho de extração único para todas — vale sondar antes
de escrever o segundo coletor.

### Entrada — o "JSON fechado" do PLAN.md

Esclarecido na triagem: é **arquivo de configuração**, não formato de dado de vaga. JSON ou XLSX,
editado à mão. Conteúdo:

- `perfis` — nome, lado (`meu` | `dela`), termos-semente, sinônimos (`3.1`, `3.5`)
- `ufs_liberadas` (`3.2`) — **lista branca, obrigatória e não vazia**. Começa com as 27
  unidades federativas e vai sendo podada. Ver `planning/ESTADOS.md`.
- `cidades_bloqueadas` (`3.2`) — lista **negra**
- `cidades_desejadas` — sobem no topo (`3.2`)

**Por que estado é lista branca e cidade é lista negra.** São 27 estados — conjunto pequeno e
fechado, onde podar uma lista pronta é mais fácil do que lembrar de proibir um a um, e o
resultado é visível de bater o olho. Cidades são milhares: enumerar as aceitas seria
impraticável. A assimetria é deliberada, não descuido.

`ufs_liberadas` ausente ou vazia é **recusada**, e não interpretada. Ausente poderia significar
"todos os estados" ou "nenhum", e qualquer das duas escolhida em silêncio produziria um feed
errado sem o usuário perceber.
- `termos_reprovacao` (`3.6`)
- `fontes_ativas`

Arquivo ausente ou malformado levanta `EntradaInvalida` com mensagem pronta para leitura humana.

### Chave canônica da deduplicação

```
empresa + cargo + cidade + UF + (hash da descricao normalizada
                                 ou id_na_fonte, quando nao houver descricao)
```

**Revisada duas vezes em 16/08/2026.** A segunda revisão veio de dado real, não de teoria.

#### Segunda revisão: a chave anterior estava fundindo vagas de verdade

Medido sobre as 178 vagas coletadas do BNE na S1:

| Medida | Valor |
|---|---|
| Chaves que juntavam mais de uma vaga | **26** |
| Pior caso — `Confidencial + desenvolvedor + São Paulo + SP` | **10 vagas num card só** |
| Vagas cuja empresa é `Confidencial` | **44 de 178 (25%)** |

`Confidencial` não é nome de empresa, é ausência de nome. E o problema não se limita a ela:
`pasqualisolution + desenvolvedor + São Paulo` juntava seis vagas distintas, porque o cargo
que o BNE expõe é genérico. Isso é **fusão falsa acontecendo em produção** — o pior erro
possível, porque é silencioso.

#### O que entra, e por quê

- **`empresa` fica.** Sem ela, duas clínicas diferentes da mesma cidade com descrições
  parecidas se fundem. Custo de manter é zero.
- **`descricao` entra, como hash da versão normalizada** — minúscula, sem acento, espaços
  colapsados, boilerplate removido. Não o texto cru: um espaço a mais faria a mesma vaga
  virar nova. É o campo onde mora a especialidade ("dentista especialista em ortodontia"),
  que é o que de fato discrimina duas vagas da mesma clínica.
- **`id_na_fonte` entra apenas como último recurso**, quando não houver descrição. É o caso
  das vagas anônimas sem texto: sem nada que as identifique, o identificador de origem é a
  única honestidade possível. **Nunca como componente fixo** — se entrasse sempre, cada fonte
  daria um identificador diferente para o mesmo anúncio e a deduplicação morreria inteira.

#### Uma correção de premissa que eu tinha errada

Eu havia argumentado que texto livre na chave mataria a deduplicação **entre fontes**. O
argumento não se sustenta: empresa e cidade também vêm escritas de forma diferente em cada
site. **Hash exato nunca vai cruzar fontes**, com ou sem descrição.

A consequência é de sequenciamento, não de desenho: o hash exato serve para juntar cópias
idênticas — recoleta, republicação, mesma fonte. **Cruzar fontes é problema da S4 e vai exigir
comparação por similaridade**, como a pesquisa original já recomendava (similaridade de título
após stemming, com janela de publicação).

#### Consequência: o enriquecimento vira pré-requisito

A descrição **só existe na página de detalhe**, não na listagem. Com isso, o passo de
enriquecimento deixa de ser um extra desejável e passa a ser **pré-requisito da deduplicação**.
Ver a subfase S3b.

---

### Primeira revisão: por que `modalidade` saiu da chave

Registro do raciocínio, porque a escolha não é óbvia:

Chave **mais estreita** funde mais, e o risco é **fusão falsa** — duas vagas diferentes viram uma,
e a que sumiu você nunca saberá que existiu. Chave **mais larga** funde menos, e o risco é
**separação falsa** — a mesma vaga aparece três vezes. **Fusão falsa é o erro pior**, porque é
silencioso; separação falsa é visível e recuperável.

- **`titulo` fica.** Sem ele, "Dentista Clínico Geral" e "Ortodontista" na mesma rede e na mesma
  cidade colapsam num card só. É fusão falsa, e frequente — redes de clínica anunciam várias
  funções na mesma unidade.
- **`modalidade` sai.** É o campo **menos confiável entre fontes**: a mesma vaga pode vir como
  `hibrido` na Catho, `presencial` no Indeed e `desconhecido` no Jooble. Na chave, isso gera três
  hashes e a deduplicação falha exatamente onde ela mais precisa funcionar. Fora da chave, a
  modalidade continua no card, resolvida por precedência de fonte quando houver conflito.

A normalização de `titulo` tem que ser **conservadora**: minúsculas, sem acento, sem pontuação e
sem ruído de anúncio (`URGENTE`, `[CONTRATA-SE]`). **Não remover senioridade** — "Analista Jr" e
"Analista Sr" são vagas diferentes.

Duplicatas não são apagadas: cada cópia guarda sua `fonte` e `url`, e o card mostra um item com
vários links. Isso importa mais do que eu estimei — o Jooble agrega dos outros e vai triplicar
ocorrências dos mesmos anúncios.

### Termos de reprovação — atenção especial ao perfil `odonto`

Além de `estagio`, `trainee`, `voluntario`, a lista precisa cobrir o ruído estrutural de
franquia em odontologia: `franquia`, `seja um franqueado`, `socio`, `comissionado`,
`percentual de producao`. Aprovado na triagem de fontes.

### Fontes da primeira rodada

`Catho` · `Vagas.com` · `Indeed` · `InfoJobs` · `BNE` · `Jooble` · `PCI Concursos` (condicional,
V1) · `OdontoPrev via Gupy` · `CROs regionais` **(subfase pendente — ver S-P)**

A ingestão por e-mail saiu da fase 1 (V2). **Consequência:** a fase 1 é 100% leitura de página
pública, sem canal de baixo atrito garantido.

---

## D4 — Documentação e companion HTML

Convenção do projeto, herdada e confirmada em uso:

- Toda função tem docstring explicando, nesta ordem: **por que a função existe** (o problema que
  resolve, o motivo de ser função separada) e depois a **lógica do input ao output em fases
  numeradas** (Entrada → Fase 1 → Fase 2 → … → Saída). Toda linha comentada, inclusive as óbvias.
- Código, docstrings e comentários em **português sem acento**. Documentação em `planning/` usa
  acento normalmente.
- Todo documento de planejamento novo ganha **companion HTML autocontido** em `planning/html/`,
  com triagem e resposta copiável. O prompt reutilizável está em `planning/PROMPT_COMPANION_HTML.md`.
- Caminhos relativos à raiz: `RAIZ = Path(__file__).resolve().parent.parent` a partir de `src/`.
- Formato BR em CSV/TXT: `sep=";"`, `decimal=","`, `encoding="latin-1"`.

---

## D5 — Feed de saída

HTML **o mais simples possível** — exigência sua. Um card por item canônico.

### O card mostra

Título · **subtítulo** · empresa (ou órgão) · cidade/UF · modalidade · salário como veio · data ·
links de todas as fontes onde apareceu · **por que apareceu** (`4.2`: qual perfil e quais termos
casaram) · botões de estado (`3.8`).

**O subtítulo** vem de `responsibilities` da página de detalhe e carrega a informação que o
título não carrega — a especialidade. Sem ele, todas as vagas de odonto do BNE aparecem como
"dentista". Precisa de limpeza para exibir: o texto real termina com boilerplate de template
(`"o link para \nSite da empresa: (Informação Confidencial)."`).

### Selo de companheiro (`3.4`)

Calculado na renderização, não armazenado: uma vaga em `cidade X` ganha o selo quando existe pelo
menos uma vaga ativa de um perfil do **outro lado** na mesma `cidade X`.

**Remoto não entra nessa conta.** Decidido na pergunta 2: remoto é categoria separada, não
coringa — senão o Brasil inteiro receberia o selo e ele perderia o sentido.

### Ordenação

Cidades desejadas primeiro, depois o resto, cada bloco por data decrescente. Determinística:
empate resolve pelo `id_canonico`, para a mesma entrada sempre gerar a mesma página.

### Concursos no feed

Mesmo feed, card visualmente distinto, com `prazo_inscricao` em destaque e etiqueta explícita
quando for `cadastro_reserva`.

---

## D6 — Instrumentação de UX

O MVP precisa **produzir o dado que vai guiar as próximas fases**. É barato agora e irrecuperável
depois.

- **`4.1` — descarte com motivo obrigatório.** O card não fecha sem motivo escolhido, e o sistema
  cobra enquanto houver descarte sem motivo. Justificativa sua: se vocês dois não responderem, a
  coleta vira esforço jogado fora.
- **`4.2` — por que apareceu.** Torna o filtro depurável sem abrir o código: dá para ver na hora se
  o problema é o sinônimo, a cidade ou a fonte.
- **`evento`** registra tudo. O agregado (`4.3`, diário de números) está congelado — o dado
  acumula sem visualização por enquanto, e isso é aceito.

---

## D7 — Arquitetura de módulos, e uma decisão de stack em aberto

### Layout

Achatado, padrão do canônico: módulos em `src/`, um executável de entrada.
**`src/` guarda só código. Dado não mora em `src/`, e `fontes/` não guarda dado nenhum.**

```
monitor_vagas/
  config/
    config.json      entrada editada a mao: perfis, cidades, sinonimos, reprovacao
  dados/
    vagas.sqlite     banco unico
    bruto/           payload cru por fonte e data (prova de origem)
  saida/
    feed.html        pagina gerada
  src/
    config.py        leitura e validacao do arquivo de entrada
    fontes/          CODIGO: um modulo por fonte, interface unica
    normaliza.py     cidade, UF, modalidade, titulo, empresa
    dedupe.py        chave canonica e agrupamento
    filtros.py       cidades bloqueadas, termos de reprovacao
    armazena.py      persistencia e estados
    feed.py          renderizacao do HTML
    main.py          orquestra o pipeline
```

`config/`, `dados/` e `saida/` são **irmãos de `src/`**, não filhos. É isso que faz a convenção
`RAIZ = Path(__file__).resolve().parent.parent` funcionar: a partir de qualquer módulo em `src/`,
`RAIZ` aponta para a raiz do projeto e todo caminho se resolve a partir dela, independente de onde
o `.bat` for chamado.

`dados/` **não entra no controle de versão** — banco e payload cru são reconstruíveis e pesados.
Vai para o `.gitignore` quando o repositório for criado.

### Comparação com Clean Architecture

O que vale a pena tomar emprestado: **regra de dependência** — `normaliza`, `dedupe` e `filtros`
não conhecem fonte nem banco, recebem e devolvem estruturas simples; e a **interface única por
fonte**, que deixa acrescentar coletor sem tocar no miolo.

O que fica de fora, deliberadamente: camadas de entidade/caso-de-uso/adaptador com abstração
formal, injeção de dependência e portas/adaptadores nomeados. Para um executável de dois usuários,
isso seria estrutura sem retorno — e contraria a diretriz de não criar abstração para código de
uso único.

### Stack — decidida em 16/08/2026

| Peça | Decisão | Motivo |
|---|---|---|
| Python | **entra** | — |
| FastAPI | **entra** | único jeito de gravar `salva`/`descartada`; sem ele a `3.8` e a `4.1` morrem |
| SQLite | **entra**, no lugar de PostgreSQL | dois usuários, uma máquina; um serviço a menos |
| Template no servidor | **entra** | atende "HTML o mais simples possível" |
| Alembic | **fora** por ora | entra quando o esquema doer e houver dado que não pode ser perdido |
| Next.js | **fora** | SPA é o oposto de "HTML o mais simples possível" |
| nginx | **fora** | sem internet nem TLS, é processo a mais sem contrapartida |

A linha de stack do `PLAN.md` foi atualizada para refletir esta decisão.

---

## D8 — Testes

> **Revisão adversarial: anulada** por decisão sua em 16/08/2026 — o projeto não tem complexidade
> que justifique o custo. `planning/ADVERSARIAL_REVIEW.md` não será escrito.

- **`planning/TESTES.md`** — mapa de testes por fase, para o teste poder ser repetido.
- **Testes e2e** cobrindo os caminhos importantes, além dos casos de borda. Cada subfase entrega
  algo verificável; subfase sem teste não conta como concluída.
- **Determinismo é testável e deve ser testado:** rodar duas vezes a mesma entrada tem que produzir
  HTML idêntico byte a byte.

---

## Subfases — desenvolvimento em partes pequenas

Cada uma entrega algo que você consegue abrir e conferir sozinho.

| # | Entrega | Cobre |
|---|---|---|
| **S0** | Esqueleto: `RAIZ`, leitura e validação da config, `EntradaInvalida` | D3, D7 |
| **S1** | **Uma fonte só**, a mais fácil, ponta a ponta até um JSON normalizado | D3 |
| **S2** | Feed HTML a partir do JSON, sem estado ainda | D5 |
| **S3** | Persistência + estados nova/salva/descartada + motivo obrigatório | `3.8`, `4.1` |
| **S3b** | **Enriquecimento pela página de detalhe** — descrição, subtítulo e salário real, só para vaga inédita | pré-requisito da `3.7` |
| **S4** | Deduplicação: um card, vários links | `3.7` |
| **S5** | Filtros: cidades bloqueadas/desejadas, palavras de reprovação, sinônimos | `3.2`, `3.5`, `3.6` |
| **S6** | Múltiplos perfis + "por que apareceu" | `3.1`, `4.2` |
| **S7** | Selo de companheiro | `3.4` |
| **S8** | Demais fontes da primeira rodada | D3 |
| **S9** | Concursos como entidade separada (PCI, condicional à V1) | D2 |
| **S10** | Alertas por e-mail e Telegram | `5.2` |
| **S-P** | **Coletor de CRO — PENDENTE** | ver abaixo |

### S-P — coletor de CRO (aguardando decisão, não mais insumo)

**Mudou de status em 16/08/2026.** O mecanismo e o dado já existem: `ufs_liberadas` está na
config com as 27 unidades federativas, e `planning/ESTADOS.md` traz a tabela por região para a
poda. São 27 conselhos com sites heterogêneos, feitos à mão, e o tamanho do trabalho é
exatamente o número de estados que sobrarem — 27 se nada for podado, 13 se cair pela metade.

O que falta é a **decisão** de quais estados saem, não o dado. Enquanto a poda não acontecer, a
subfase continua sem estimativa, mas por escolha em aberto e não por falta de insumo.

---

## Estado da aprovação — 16/08/2026

**Aprovadas:** D1, D2, D4, D5, D6, D8 e a ordem das subfases.
**Revisadas após pergunta sua:** D3 (chave canônica) e D7 (onde mora o dado). Aguardam seu aceite.
**Stack:** fechada.

### Pendências restantes

1. **Poda dos estados** — a lista completa já está na config e em `planning/ESTADOS.md`.
   Falta decidir quais saem. Dimensiona a S-P.
2. **Qual é a "fonte mais fácil"** de S1 — sem palpite; será decidida sondando duas ou três
   candidatas no início da própria S1, abordagem aprovada em 16/08/2026.

`V1` deixou de ser pendência: se puxar vaga do PCI se mostrar difícil, a S9 cai para a fase
seguinte, conforme acordado.
