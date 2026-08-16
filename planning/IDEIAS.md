# IDEIAS — hub simples de vagas filtradas no Brasil

> **O que este documento é:** uma lista de ideias numerada, para debate. Não é decisão, não é
> design, não é plano. Debatemos por número e o que sobreviver vai para o `DESIGN.md`.
>
> **Escopo desta rodada:** só o hub que coleta e filtra vagas do Brasil. Arquitetura, stack,
> legislação/LGPD e candidatura automática ficam explicitamente de fora — entram depois.
>
> **Base:** `minhas_notas/Pesquisa profunda sobre monitoramento de vagas e candidaturas no
> Brasil.pdf` (23 páginas, corte em 26/05/2026) + `planning/notas_humano_pesquisa_chatGPT.md`.

---

## 1. A releitura que a pesquisa provoca

A pesquisa foi escrita para um produto de mercado, multiusuário, com CRM de candidaturas,
scoring, extensão de navegador e compliance desde o MVP. **Nosso caso é outro:** dois usuários
conhecidos, sem cliente externo, sem prazo comercial. Isso libera simplificações grandes — não
precisamos de multi-tenancy, papéis, consentimento granular nem SLA.

Mas há três conclusões da pesquisa que valem para nós e que **contradizem ou refinam o que está
hoje no `PLAN.md`**:

- **Não existe RSS nem API pública de candidato em nenhuma das plataformas revisadas.** O
  `PLAN.md` fala em "vagas descritas através de jsons fechados" — esse JSON vai ser *nosso*,
  produzido pela normalização. Não é um formato que os sites entregam.
- **A fonte mais barata e mais atualizada não é o site, é o e-mail.** Todas as plataformas
  (LinkedIn, Indeed, Catho, Vagas, InfoJobs, Empregos) oferecem alerta nativo por e-mail, de
  graça, com frescor de 15–30 min. Ler a caixa de entrada dá cobertura que raspagem não dá.
- **Gupy é a melhor fonte estruturada do Brasil** (portal público agregado, com salário,
  benefícios e senioridade em muitas vagas) e a de menor atrito.

Nenhum desses pontos é decisão de arquitetura — são fatos sobre **de onde vem o dado**, que
determinam **o que dá para filtrar**. Por isso estão aqui.

---

## 2. A ideia central: o eixo não é a vaga, é a cidade

Somos duas pessoas com carreiras que não se movem juntas. Uma vaga excelente em uma cidade onde
a outra pessoa não trabalha **vale zero**. Isso reposiciona o produto inteiro:

> O hub não responde *"quais vagas boas existem?"*.
> Responde ***"em quais cidades nós dois temos vaga boa ao mesmo tempo?"***

Essa é a diferença entre construir mais um agregador de vagas (existem dezenas, todos melhores
que o nosso jamais será) e construir a única ferramenta que resolve o nosso problema real.

Tudo abaixo deriva daí.

---

## 3. Ideias do núcleo — o que eu defenderia no MVP

### 3.1 — Perfis de busca nomeados, não um perfil por pessoa

Não são 2 perfis, são pelo menos 4 buscas independentes, porque um de nós tem três carreiras
plausíveis:

| Perfil | Termos-semente | Observação |
|---|---|---|
| `dados` | cientista de dados, data scientist, analista de dados, engenheiro de dados, BI | maior oferta remota |
| `dev` | desenvolvedor, backend, python, fullstack | maior oferta remota |
| `financeiro` | administrador financeiro, controladoria, analista financeiro, FP&A, tesouraria | oferta muito presencial |
| `odonto` | dentista, cirurgião-dentista, odontologia, clínico geral, odontopediatra | oferta local, fontes diferentes |

**Por que é legal:** cada perfil tem oferta, geografia e vocabulário radicalmente diferentes.
Tratar tudo como uma busca só produz um feed inútil.

### 3.2 — Lista de cidades bloqueadas (e uma lista de desejadas)

Duas listas explícitas, editáveis à mão:

- **Bloqueadas** — cidades/UFs que descartam a vaga direto, sem aparecer no feed.
- **Desejadas** — cidades que sobem no topo, mesmo com vaga mediana.
- **O resto do Brasil** — aparece, mas embaixo.

**Por que é legal:** é o filtro que você pediu, e é o mais barato de implementar de todos. Uma
lista em arquivo já resolve na v0.

### 3.3 — Painel de cidades: a tela principal, não o feed

Em vez de abrir numa lista cronológica de vagas, abrir num **placar de cidades**:

```
Florianópolis/SC     dados 12 · dev 8 · financeiro 3 · odonto 5     ← os 2 fecham
Curitiba/PR          dados  9 · dev 6 · financeiro 7 · odonto 4     ← os 2 fecham
Uberlândia/MG        dados  1 · dev 0 · financeiro 2 · odonto 6     ← só odonto
Recife/PE            dados  7 · dev 5 · financeiro 1 · odonto 0     ← só tech
```

Clicar na cidade abre as vagas dela.

**Por que é legal:** é a resposta direta à pergunta que realmente importa, e nenhum job board do
mercado faz isso. É a tela que justifica o projeto existir.

### 3.4 — Marcador de "cidade que fecha para os dois"

Uma cidade "fecha" quando tem pelo menos uma vaga viva em `odonto` **e** pelo menos uma em
qualquer um de `dados`/`dev`/`financeiro`. Fica destacada.

**Ponto de debate:** remoto quebra a regra. Se a vaga de dados for remota, só a cidade dela
importa e o Brasil inteiro "fecha". Precisamos decidir se remoto entra como coringa ou como
categoria separada. **Minha sugestão:** categoria separada, porque misturar polui o placar.

### 3.5 — Sinônimos por área, escritos à mão

Um dicionário simples por perfil. `dentista → cirurgião-dentista, odontologia, CD, clínico geral`.

**Por que é legal:** é o que separa um filtro que acha 3 vagas de um que acha 40. E é trabalho
de 20 minutos, não de engenharia.

### 3.6 — Filtro de reprovação por palavra

Lista de termos que descartam a vaga na hora: `estágio`, `trainee`, `voluntário`, `comissionado`,
`sem salário fixo`, `franquia`, `MEI obrigatório`.

**Por que é legal:** em odontologia e financeiro, o ruído de vaga comissionada/franquia é enorme.
Sem isso o feed fica impraticável.

### 3.7 — Deduplicação: um card, vários links

A mesma vaga aparece em Catho, Indeed e Vagas. Vira **um** card com três links de origem.

**Por que é legal:** sem isso o feed triplica e a contagem do placar de cidades mente.
A pesquisa dá a receita pronta: chave canônica por `empresa + título + cidade + modalidade`.

### 3.8 — Estado da vaga em um clique

`nova` → `salva` / `descartada`. Só isso. Sem kanban, sem pipeline.

**Por que é legal:** é o mínimo para o feed não repetir o que já vimos — e é a origem do dado de
UX (ver 4).

---

## 4. Ideias para gerar o dado de UX que vai guiar o futuro

Você pediu para pensar o projeto como algo que ganha funcionalidade **à medida que tivermos dados
sobre UX**. Então o MVP precisa produzir esse dado desde o primeiro dia. É barato agora e
impossível de recuperar depois.

### 4.1 — Descarte com motivo em um clique

Ao descartar, escolher o porquê: `cidade` · `salário` · `requisito que não tenho` ·
`modalidade` · `empresa` · `não é minha área` · `vaga velha/fantasma`.

**Por que é legal:** depois de 200 descartes, a distribuição dos motivos diz exatamente qual é o
próximo filtro a construir. É a diferença entre adivinhar o roadmap e derivá-lo.

### 4.2 — "Por que esta vaga apareceu"

Cada card mostra qual perfil e quais termos casaram.

**Por que é legal:** quando o feed traz lixo, você vê na hora se o problema é o sinônimo, a
cidade ou a fonte. Debuga o filtro sem abrir o código.

### 4.3 — Diário de números por semana

Quantas vagas entraram, por fonte, por perfil, por cidade; quantas foram descartadas e por quê.

**Por que é legal:** mede se a fonte nova valeu o esforço. Também revela sazonalidade.

---

## 5. Ideias legais que eu deixaria para depois (mas quero registrar)

| # | Ideia | Por que adiar |
|---|---|---|
| 5.1 | Score de aderência explicável (0–100, cobre 4/5 obrigatórios) | precisa de perfil estruturado e de dado de UX que ainda não temos |
| 5.2 | Alertas por e-mail/Telegram | enquanto formos 2 pessoas, abrir a página resolve |
| 5.3 | Kanban de candidaturas | só faz sentido quando estivermos de fato aplicando em volume |
| 5.4 | Watchlist de empresas | depende de saber quais empresas importam — que é dado de UX |
| 5.5 | Mapa do Brasil com as cidades | bonito, mas o placar em tabela resolve melhor |
| 5.6 | RSS próprio de saída | zero valor para 2 usuários na mesma casa |
| 5.7 | Custo de vida / salário relativo por cidade | muito legal para decidir mudança, mas é outro projeto |
| 5.8 | Histórico: "esta cidade fechava em março, não fecha mais" | precisa de meses de dado acumulado |

---

## 6. Perguntas em aberto para o debate

1. **"Cidades não bloqueadas"** — confirmo o entendimento? Varre o Brasil inteiro e exclui uma
   lista de cidades/UFs, em vez de escolher um punhado de cidades-alvo.
2. **Remoto entra como coringa ou como categoria separada?** (ver 3.4)
3. **O perfil `odonto` tem fontes próprias?** A pesquisa mapeia job boards generalistas e ATSs de
   tech. Vaga de dentista vive muito em Catho, Indeed, redes de clínicas e canais regionais. Pode
   ser que `odonto` precise de fontes que os outros três perfis não usam — e isso é a maior
   incerteza de cobertura do projeto.
4. **Os três perfis dele são realmente três, ou é para focar em um?** Três perfis triplicam o
   trabalho de sinônimos e o ruído do feed.
5. **Qual o horizonte?** Procurar mudança para os próximos 6 meses é um produto; monitorar o
   mercado de forma contínua por anos é outro.
6. **Quantas vagas por dia você tolera ver?** Se a resposta for "10", o produto é agressivo em
   filtro. Se for "100", é permissivo e o placar de cidades importa mais.

---

## 7. Fora de escopo nesta rodada

Registrado só para não voltar como surpresa: arquitetura e stack; banco de dados; legislação e
LGPD; termos de uso das plataformas; candidatura automática ou assistida; geração de currículo e
carta; multiusuário e autenticação; qualquer coisa de recrutador.

---

## 8. Resultado da triagem — 15/08/2026

### Aprovado sem alteração

`3.1` perfis nomeados · `3.2` cidades bloqueadas/desejadas · `3.5` sinônimos ·
`3.6` filtro de reprovação · `3.7` deduplicação · `4.2` "por que esta vaga apareceu" ·
`5.2` alertas por e-mail e Telegram **(promovida do icebox)** ·
`3.8` estado da vaga **(descongelada — ver nota abaixo)**

> **Por que `3.8` voltou.** Ela dependia de si mesma para a `4.1` existir: não há "descarte com
> motivo obrigatório" sem a ação de descartar. E as respostas 5 e 6 (horizonte contínuo, sem teto
> de volume) a transformaram de conveniência em peça estrutural — sem memória de "já vi esta", o
> feed reapresenta o acervo inteiro a cada abertura. Aprovado em 15/08/2026.

### Aprovado com alteração

- **3.4 — vira uma tag, não uma tela.** Basta um selo no card dizendo que aquela cidade também
  tem oportunidade para o companheiro. Esforço reclassificado de médio para **pequeno**.
- **4.1 — o motivo do descarte passa a ser obrigatório.** Sem responder, o card não fecha, e o
  sistema cobra. Justificativa: se nós dois não respondermos, a coleta vira esforço jogado fora.
- **5.7 — aprovada e ampliada.** Além de custo de vida, medir a **competição pelo profissional na
  cidade**. Competição fraca é o segredo (lei de Buffett): cidade com demanda baixa e competição
  alta não vale o mesmo esforço que o inverso.

### Icebox

`3.3` painel de cidades · `4.3` diário de números · `5.1` score de aderência · `5.3` kanban ·
`5.4` watchlist · `5.5` mapa · `5.6` RSS · `5.8` histórico de cidades

### Decisões vindas das perguntas em aberto

| # | Decisão |
|---|---|
| 1 | Varre o Brasil inteiro e exclui uma lista de cidades/UFs. Confirmado. |
| 2 | Remoto é **categoria separada**, não coringa. |
| 3 | **Descobrir as fontes de odonto é a prioridade nº 1 do projeto.** "Nada de UX que estamos pensando vive se não acharmos vagas para odonto." |
| 4 | O número de perfis não é decisão de agora; mudar depois custa pouco. |
| 5 | Horizonte **contínuo**, não uma busca de 6 meses. |
| 6 | Sem teto de volume: mostrar todas as vagas, criar filtros depois se o esforço não compensar. |

### Esclarecimento que resolve a ambiguidade do PLAN.md

"JSONs fechados" significa **arquivo de configuração de entrada** — JSON ou XLSX — com as cidades
excluídas e as características da vaga que alimentam o script. **Não** é o formato do dado de
vaga. O HTML de saída deve ser o mais simples possível.

### Sobre as fontes

Gupy primeiro, por ser a mais fácil, mas o objetivo declarado é **consultar tudo que existe, de
forma ordenada** — um hub personalizado de todas as fontes. Sobre os alertas por e-mail, é preciso
descobrir antes qual a capacidade real do plano gratuito (dá para monitorar todas as cidades do
país, ou exige plano pago?).

### Escopo fechado do MVP

Oito itens no núcleo: `3.1` `3.2` `3.5` `3.6` `3.7` `3.8` `4.2` mais `5.2`, somados às alterações
de `3.4` (selo no card) e `4.1` (motivo obrigatório).

### Premissas de trabalho, ainda não confirmadas explicitamente

Sigo com estas duas até você dizer o contrário — nenhuma bloqueia o próximo passo:

1. **O feed cronológico volta a ser a tela principal.** Com `3.3` congelada e `3.4` reduzida a
   selo, o eixo cidade deixa de ser a estrutura do produto e passa a ser um atributo do card.
2. **`5.7` fica para a rodada dois.** É análise por cidade sem tela de cidade, e é de longe o item
   mais caro aprovado — exige fonte de custo de vida e alguma proxy de oferta/demanda por praça,
   maior que todo o núcleo somado.

### Próximo passo definido pela resposta 3

Pesquisa de fontes de vagas de odontologia, **antes** do `DESIGN.md`. Sem vagas de odonto, nenhuma
das telas planejadas se sustenta. A pesquisa do PDF cobre job boards generalistas e ATSs com viés
de tech, e não responde onde vive a vaga de dentista no Brasil.
