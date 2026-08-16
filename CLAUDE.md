# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é este repositório (leia primeiro)

Projeto de screening de vagas de emprego na internet: vagas filtradas são compiladas e apresentadas
em um feed em página HTML, com alertas via WhatsApp e e-mail no MVP. Pensar o site como uma
**plataforma** é importante — o projeto ganhará recursos e ferramentas no futuro (marketplaces,
automação via Telegram/redes sociais, hub que normaliza dados de múltiplas fontes).

**Estado atual: fase de planejamento.** Ainda não existe código (`src/` não foi criado), não há
venv nem `requirements.txt`, e o diretório **ainda não é um repositório git** — `git init` faz
parte da fase de infraestrutura. Todo o conteúdo hoje vive em `planning/`.

### Stack decidida (ver `planning/PLAN.md`)

- Backend: Python 3.12 (venv via **uv**), FastAPI, PostgreSQL, Alembic, JSON como formato de vaga.
- Frontend: Next.js servido por nginx.

### Ambiente Python (Windows, uv)

```powershell
uv venv                                  # criar venv 3.12
.venv\Scripts\activate                   # ativar
uv pip install <pacotes>                 # instalar dependencias
uv pip freeze > requirements.txt         # congelar
```

> **NUNCA fazer `git push`** — o repositório permanece local; publicar no GitHub é decisão do
> humano. Commits locais frequentes, mensagens `feat:`/`fix:`/`test:`/`docs:`/`chore:` em português.

## Arquitetura

Layout achatado (padrão do canônico): módulos em `src/`, um único executável.
Compare sua arquitetura com a doutrina do Clean Architecture.

## Governança e documentação

> `PROJECT_BUILDING.md` não é alterado (checklist do humano). O controle do projeto do humano
> vive em `planning/PLAN.md`. Toda a documentação está no diretório `planning/` e o documento-chave
> é `PLAN.md`.

Existem hoje em `planning/`:

- `PLAN.md` — **documento-chave**: macrofases, decisões e pendências. Registre progresso aqui.
- `PROJECT_BUILDING.md` — checklist do humano, **somente leitura**. Não são atividades para a IA.
- `Behavioral guidelines.md` — diretrizes de disciplina de código (pensar antes de codar,
  simplicidade, mudanças cirúrgicas, critérios de sucesso verificáveis). O plugin `craft/`
  empacota as mesmas diretrizes como skill.
- `notas_humano_pesquisa_chatGPT.md` — roadmap de fontes (job boards generalistas primeiro:
  vagas.com.br, InfoJobs, Catho, Indeed, Glassdoor, empregos.com.br).
- `html-effectiveness/` — clone de modelos HTML de referência; inspira os companions visuais.
- `IDEIAS.md` — ideias do MVP e o **resultado da triagem** (seção 8): escopo fechado em 10 itens.
- `FONTES_ODONTO.md` — pesquisa de fontes de vaga de odontologia e a triagem das 19 fontes (seção 6).
- `DESIGN.md` — **design do MVP**, D1 a D8, mais 11 subfases de implementação.
- `PROMPT_COMPANION_HTML.md` — prompt reutilizável para gerar companion HTML; semente de skill futura.
- `html/IDEIAS.html`, `html/FONTES_ODONTO.html`, `html/DESIGN.html` — companions com triagem
  interativa e resposta copiável de volta para o chat.

Ainda **não escritos** (planejados, não os cite como existentes): `TESTES.md`,
`definition of done.md`, `MODELO_CUSTO.md`, `PLANO_IMPLEMENTACAO.md`.

`ADVERSARIAL_REVIEW.md` foi **anulado** em 16/08/2026 — projeto sem complexidade que o justifique.

- Cada documento de planejamento novo ganha companion HTML autocontido em `planning/html/`
  (inspirado em `planning/html-effectiveness/`).
- Glossário de status: `x` concluído · `f` revisão futura · `a` anulado · `n` não se aplica ·
  `r` rollback (falhou) · `[ ]` pendente.
- `suporte_contexto/` — contexto de apoio/bugfix; **hoje vazio**.
- `minhas_notas/` é material de **pesquisa**, nunca entrada de execução.

## Code development pace

- O desenvolvimento dos módulos deve ser feito em pequenas partes para facilitar o acompanhamento
  e entendimento humano.
- Explique critérios de sucesso de cada fase em `definition of done.md` para humanos acompanharem.

## Documentation

- Toda função com docstring explicando, nesta ordem: por que a função existe (o problema que ela
  resolve / o motivo de ser função separada); a lógica do input ao output, em fases numeradas
  (Entrada → Fase 1 → Fase 2 → … → Saída), descrevendo o que cada bloco transforma. Além disso,
  toda linha de código comentada — inclusive as que parecem óbvias.

## Convenções herdadas do sistema canônico

- Código, docstrings e comentários em **português sem acento** (evita quebra de encoding).
  Nomes de arquivo de insumo têm acento — use `Path`/raw strings e cuidado com o console cp1252.
- **Formato BR** em CSV/TXT: `sep=";"`, `decimal=","`, `encoding="latin-1"`.
- **Determinismo**: mesma entrada → mesma saída (rota gulosa desempata pelo menor índice,
  `groupby(sort=False)` preserva ordem). Nada de aleatoriedade não semeada.
- **Limitações são explícitas, nunca silenciosas**: `EntradaInvalida` com mensagem pronta para o
  usuário final (erro de dados → exit 1 sem traceback); `print("AVISO: ...")` para descartes e
  fallbacks. Bug de programa continua levantando traceback normal.
- Caminhos relativos à raiz (`RAIZ = Path(__file__).resolve().parent.parent` a partir de `src/`),
  para um arquivo `.bat` funcionar de qualquer diretório. Guarde essa orientação mesmo que esse
  projeto não tenha essa necessidade.

## Testes

- Faça Mapa de testes (o que testa e como testar) escrito em um arquivo `TESTES.md` que explica o
  teste de cada fase caso queira repetir.
- Always include e2e tests to cover important paths. You should always make sure that the plans
  include a test suite that covers the happy paths and edge cases. Your tests should be high
  quality and give confidence while covering most of the implementation.
