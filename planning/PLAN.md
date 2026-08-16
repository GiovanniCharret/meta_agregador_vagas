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
`[ ]` S1 — uma fonte só, ponta a ponta até JSON normalizado

## Decisões tomadas

- **"JSONs fechados" = arquivo de configuração de entrada** (cidades excluídas, características da
  vaga), em JSON ou XLSX. **Não** é o formato do dado de vaga.
- Eixo do produto: **feed cronológico**; a lógica de cidade vira selo no card, não tela.
- Remoto é **categoria separada**, não coringa.
- Concurso público entra como **entidade separada**, unificada só na apresentação.
- Horizonte **contínuo**; **sem teto de volume**.
- Ingestão por e-mail sai da fase 1 — a fase 1 é 100% leitura de página pública.
- Critério de seleção de fonte: **fácil de puxar primeiro**, workaround fica para depois.

## Pendências que travam a implementação

1. **Lista de UFs** onde ela não trabalharia. Bloqueia a subfase S-P (coletor de CRO) e alimenta a
   `3.2`. É o único item no caminho crítico que só vocês podem produzir. **Ainda não pronta.**
2. **Fonte mais fácil da S1** — sem palpite; será decidida testando, dentro da própria S1.

Resolvidas: stack (16/08), V1 (PCI vira fase seguinte se for difícil), revisão adversarial (anulada).
