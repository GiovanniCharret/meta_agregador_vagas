# PLAN — monitoramento de vagas de emprego

Construir uma página na web com um feed que reúnde oportunidades de emprego descritas através de jsons fechados. 
Desenvolver um modelo MVP de plataforma. Dispõe inicialmenete só do feed e alerta via whatsapp e e-mai. Novas ferramentas e recursos, podem ser planejados para serem desenvolvidos no futuro. 

> `PROJECT_BUILDING.md` não é alterado (checklist do humano). O controle do projeto do humano vive aqui.

## Glossário de status

`x` concluído · `f` revisão futura · `a` anulado · `n` não se aplica · `r` rollback (falhou) · `[ ]` pendente

## Macrofases

> Design aprovado: `planning/DESIGN.md` · Plano executável passo a passo: `planning/PLANO_IMPLEMENTACAO.md`
> Companions visuais: `planning/html/DESIGN.html` · `planning/html/PLANO_IMPLEMENTACAO.html`

— Infraestrutura: `src/`, venv uv 3.12, requirements, ritual , git, `definition of done.md`
— Stack — **decidida em 16/08/2026**: Python + FastAPI + SQLite, HTML renderizado no servidor por
  template. **Fora do MVP:** PostgreSQL (SQLite resolve para 2 usuários numa máquina), Alembic
  (entra quando o esquema doer), Next.JS e nginx. Justificativa em `DESIGN.md` D7.
  *(Substitui a declaração original: FastAPI, PostgreSQL, json, Alembic, Next.JS, nginx.)*

## Progresso

`x` Pesquisa de apoio lida (`minhas_notas/`, 23 páginas) e traduzida em `planning/IDEIAS.md`
`x` Triagem de ideias — 15/08/2026. Escopo do MVP fechado em 10 itens. Ver `IDEIAS.md` seção 8
`x` Pesquisa de fontes de odontologia — `planning/FONTES_ODONTO.md` (prioridade nº 1 definida por você)
`x` Triagem de fontes — 16/08/2026. 9 fontes na primeira rodada, 10 na seguinte. Ver seção 6
`x` `planning/DESIGN.md` escrito — D1 a D8 mais 11 subfases de implementação
`x` Companions HTML: `html/IDEIAS.html` e `html/FONTES_ODONTO.html`
`x` `planning/PROMPT_COMPANION_HTML.md` — semente da skill futura de companion
`a` `planning/ADVERSARIAL_REVIEW.md` — **anulado** em 16/08/2026: projeto sem complexidade que justifique
`x` `planning/TESTES.md` — mapa de testes por fase, com verificação manual do S0
`[ ]` `definition of done.md`
`x` Infraestrutura — venv uv 3.12.13, pytest 9.1.1, `requirements.txt`, `.gitignore`
`x` **S0 concluída** — `caminhos.py`, `erros.py`, `config.py`, `main.py`, lançador `monitor.py`.
  27 testes passando, executável verificado rodando de outro diretório.
`x` Lista de estados — `ufs_liberadas` com as 27 UFs na config; tabela por região em
  `planning/ESTADOS.md`. **Modelo invertido para lista branca**, a ser podada com o tempo.
`[ ]` Poda dos estados — decidir quais saem. Dimensiona a S-P (27 conselhos ou menos).
`x` **S1 concluída** — sondagem de 5 candidatas, coletor do **BNE**, orquestração com paginação
  e deduplicação, slug de termo, camada de rede isolada. **178 vagas reais coletadas**,
  59 testes passando. Detalhes em `planning/TESTES.md`.
`x` **S2 concluída** — `src/feed.py`, página autocontida com CSS embutido, ordenação por
  cidade desejada e data, escape de HTML. **178 cards em 89 KB**, 74 testes passando.
  Determinismo do D8 verificado sobre dado real: mesmo sha256, mesmos 91.310 bytes.
`x` **S3 concluída** — `src/armazena.py` (SQLite, estados por pessoa, motivo obrigatório,
  log de eventos) e `src/servidor.py` (FastAPI local, marcação por formulário sem JavaScript).
  `monitor.py servir` sobe o feed em `127.0.0.1:8000`. **100 testes**, banco com 186 vagas.
`x` **S3b concluída** — `src/enriquece.py` lê o JSON-LD `JobPosting` da página de detalhe.
  **165 de 269 vagas enriquecidas, 157 com subtítulo distinto** — a descrição discrimina, o
  que valida a chave canônica da S4. **124 testes.**
  - **Salário do detalhe é quase todo falso:** 163 de 165 traziam a mesma faixa
    R$ 1.000–15.000, que é preenchimento padrão do BNE. Descartado; sobraram 2 reais.
  - **Testes escreviam no banco de produção.** Corrigido com `banco` explícito em toda
    chamada e a variável `MONITOR_VAGAS_RAIZ`, que redireciona a raiz do projeto.
`[ ]` S3b — enriquecimento pela página de detalhe (novo, 16/08/2026). Vira **pré-requisito da
  deduplicação**, porque a descrição só existe lá. Chave canônica revisada no `DESIGN.md` D3
  depois de medir 26 colisões reais nas 178 vagas coletadas.

### Achados da S1 que mudam premissas

- **Catho e Jooble bloqueiam** (403; o Jooble com Cloudflare). Saem da primeira rodada — o
  projeto não contorna bloqueio. Isso reduz de 9 para 7 as fontes viáveis daquela lista.
- **Gupy rende pouco para odonto**: das 48 vagas da OdontoPrev, só 3 são de odontologia, todas
  "banco de talentos" e duas sem cidade. A pesquisa a apontava como confirmação para odonto;
  na prática, hoje, não é.
- **BNE tem soft 404**: slug de função inexistente devolve 200 com a página inicial. Três termos
  do config não existem lá (`analista-de-dados`, `administrador-financeiro`,
  `cirurgiao-dentista`). Não é erro — é vocabulário próprio da fonte, e o aviso já ensina isso.
- **BNE não expõe o título do anúncio**, só a função normalizada. Enfraquece a chave canônica
  para esta fonte. Registrado para a S4.
- **A página de detalhe da vaga resolve isso, e mais.** Ela publica `JobPosting` em JSON-LD
  (schema.org) com `responsibilities` e `description` — e é ali que aparece a especialidade
  ("dentista especialista em ortodontia"), que é justamente o que discrimina duas vagas da mesma
  clínica. Traz também `baseSalary` **que a listagem esconde** (a listagem manda `0.0`; o detalhe
  traz 1.000–15.000/mês), `employmentType`, `validThrough` e CEP.
  **Custo:** uma requisição por vaga. **Implicação maior:** `JobPosting` em JSON-LD é padrão de
  indústria — se as outras fontes também publicarem, existe um caminho de extração único para
  todas, em vez de um parser por site. Vale sondar antes de escrever o segundo coletor.

## Decisões tomadas

- **"JSONs fechados" = arquivo de configuração de entrada** (cidades excluídas, características da
  vaga), em JSON ou XLSX. **Não** é o formato do dado de vaga.
- Eixo do produto: **feed cronológico**; a lógica de cidade vira selo no card, não tela.
- Remoto é **categoria separada**, não coringa.
- Concurso público entra como **entidade separada**, unificada só na apresentação.
- Horizonte **contínuo**; **sem teto de volume**.
- Ingestão por e-mail sai da fase 1 — a fase 1 é 100% leitura de página pública.
- Critério de seleção de fonte: **fácil de puxar primeiro**, workaround fica para depois.

## Foco em odontologia — 16/08/2026

Decisão sua, urgente: **desligar `dados`, `dev` e `financeiro`. Só odontologia, inclusive
nesta fase de desenvolvimento.** Aplicado na configuração e no banco (126 vagas dos perfis
desligados removidas; nenhuma marcação foi perdida).

### Por que, e por quanto tempo

**A busca dela é prioridade; a dele pode esperar dias ou meses.** O foco é de urgência, não de
escopo — os outros perfis **voltam**.

**Consequência para o código, e é a que mais importa:** nada da máquina de múltiplos perfis
deve ser simplificado ou removido. O campo `lado`, a lista de perfis, o selo de companheiro da
`3.4` e a lógica de dois lados continuam de pé, dormentes. A tentação natural de "só existe um
perfil agora, dá para simplificar" produziria retrabalho garantido quando eles voltarem.

**Subfases afetadas enquanto durar o foco:**

- **`S7` selo de companheiro — suspensa.** Ela pergunta se a cidade fecha para os dois, e hoje
  só existe um lado. Volta sozinha quando os perfis dele voltarem, sem precisar ser reescrita.
- **`S6` múltiplos perfis — encolhe.** A parte de "por que esta vaga apareceu" continua valendo
  e é a que interessa agora; a de cruzar vários perfis fica dormente.

### O que a sondagem do vocabulário do BNE mostrou

| Slug | Vagas | Serve? |
|---|---|---|
| `dentista` | 275 | **sim** — é o único slug para cirurgiã-dentista |
| `auxiliar-de-saude-bucal` | 1.639 | **não** — é cargo auxiliar, não posição de dentista |
| `tecnico-em-saude-bucal` | 700 | **não** — idem |
| `protesista` | 62 | **não** — técnico de laboratório |
| `cirurgiao-dentista`, `odontologia`, `ortodontista`, `endodontista`, `implantodontista`, `odontopediatra`, `periodontista` | — | **não existem** no vocabulário do BNE |

**Decisão de julgamento:** não incluí os cargos auxiliares, apesar de somarem 2.339 vagas. Eles
inundariam o feed com posições que ela não ocuparia, e volume não é qualidade. Se algum dia
fizer sentido, é uma linha na configuração.

### Subcoleta encontrada e corrigida

O teto de páginas por termo estava em **3**, o que trazia 60 das 275 vagas — **dois terços do
acervo ficavam de fora sem ninguém perceber**. Subiu para 20. É teto e não meta: a coleta para
sozinha quando a página não traz nada inédito.

Resultado: **269 vagas de odontologia, cobrindo 23 UFs**. Só 1 é remota, o que reforça que o
eixo geográfico importa mais para este perfil do que para os outros.

## Pendências que travam a implementação

1. **Lista de UFs** onde ela não trabalharia. Bloqueia a subfase S-P (coletor de CRO) e alimenta a
   `3.2`. É o único item no caminho crítico que só vocês podem produzir. **Ainda não pronta.**
2. **Fonte mais fácil da S1** — sem palpite; será decidida testando, dentro da própria S1.

Resolvidas: stack (16/08), V1 (PCI vira fase seguinte se for difícil), revisão adversarial (anulada).
