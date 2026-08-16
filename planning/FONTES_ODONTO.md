# FONTES — onde vive a vaga de odontologia no Brasil

> **Por que este documento existe.** Na triagem de 15/08/2026 você definiu (resposta 3) que
> descobrir as fontes de odonto é a prioridade nº 1 do projeto: *"nada de UX que estamos pensando
> vive se não acharmos vagas para odonto"*. A pesquisa em `minhas_notas/` cobre job boards
> generalistas e ATSs com viés forte de tech, e não responde essa pergunta.
>
> **Método e limite.** Busca web em 15/08/2026, primeira passada. O índice de busca disponível é
> orientado a resultados dos EUA, o que pode subrepresentar sites regionais brasileiros pequenos.
> Trate a lista como **ponto de partida verificado, não como levantamento exaustivo**. Onde eu não
> confirmei algo abrindo a página, está escrito.

---

## 1. O achado principal

A vaga de dentista **não vive nos mesmos lugares** que a vaga de dados, dev ou financeiro. Além
dos generalistas, ela se concentra em quatro canais que a pesquisa original não mapeia:

| Canal | Por que importa | Existe nos generalistas? |
|---|---|---|
| **Concurso público municipal** | O SUS é um dos maiores empregadores de dentistas do país; salários altos (Florianópolis/SC: R$ 16.289,86) | Não |
| **Conselhos Regionais (CRO)** | Cada um dos 27 CROs mantém classificados próprios com vagas de clínicas locais | Não |
| **Redes e franquias de clínicas** | Sorridents tem 500+ unidades; OdontoCompany e OdontoPrev operam nacionalmente | Parcialmente |
| **Plataforma dedicada** | Existe pelo menos uma exclusiva de odontologia | Não |

**A consequência mais séria é estrutural:** concurso público **não é uma vaga** no formato do
resto do sistema. Tem órgão em vez de empresa, prazo de inscrição em vez de data de publicação,
banca organizadora, número de vagas, e a distinção entre *vaga imediata* e *cadastro reserva* —
que é uma vaga que talvez nunca exista. Isso precisa de decisão de modelagem antes do `DESIGN.md`.

---

## 2. Mapa de fontes

### 2.1 Generalistas com URL dedicada de odontologia

O caminho mais barato: mesma máquina dos outros perfis, só muda o termo-semente. Todos têm página
pública com recorte da área já pronto.

| Fonte | Caminho | Nota |
|---|---|---|
| Catho | `catho.com.br/vagas/area-odontologia/` | área própria de odontologia; ~358–398 vagas relatadas |
| Vagas.com | `vagas.com.br/vagas-de-dentista` e `/vagas-de-odontologia` | dois recortes distintos |
| Indeed | `br.indeed.com/q-dentista-vagas.html` | ~1.455 vagas relatadas, o maior volume visto |
| InfoJobs | busca por cirurgião-dentista | traz recorte por especialidade (odontologia do trabalho) |
| LinkedIn | `br.linkedin.com/jobs/dentista-vagas` | 836 "dentista" + 273–408 "cirurgião-dentista" |
| Glassdoor | busca por cirurgião-dentista | volume baixo (31 no Brasil) — confirma o PDF: usar como contexto |
| **BNE** | `bne.com.br/vagas-de-emprego-para-dentista` | **não está na pesquisa original**; anuncia canal exclusivo de odontologia |
| **Jooble** | `br.jooble.org` | **não está na pesquisa original**; meta-agregador, filtra por cidade/estado/contrato |

Jooble merece atenção: ele agrega de sites de empresas, agências e outras plataformas, e aceita
XML-feed do lado do anunciante. Como *fonte*, pode dar cobertura de anúncios que não aparecem em
nenhum dos seis grandes — ao custo de duplicação alta, o que reforça a `3.7`.

### 2.2 Concursos públicos — o canal que falta

Existe um ecossistema inteiro de agregadores especializados, separado do mundo de job board:

| Fonte | Caminho | Estrutura |
|---|---|---|
| **PCI Concursos** | `pciconcursos.com.br/vagas/cirurgiao-dentista` | **melhor achado desta pesquisa**: página dedicada ao cargo, listagem contínua com órgão, UF, nº de vagas, salário máximo, escolaridade e prazo; navegação por região e por cidade |
| OdontoConcursos | `odontoconcursos.com.br` | especializado em concursos de odontologia |
| OdonConcursos | `odonconcursos.com.br/noticia/editais-abertos-para-dentista` | agrega editais abertos para dentista |
| CD Concursos | `cdconcursos.com.br/blog/` | formato de blog, menos estruturado |
| APCD | `apcd.org.br/jornal-da-apcd/concursos/` | associação paulista, seção de concursos |

Verifiquei a página do PCI: os campos vêm organizados e há filtro geográfico. **Não encontrei
menção a RSS, feed ou alerta por e-mail** na parte visível — precisa ser confirmado abrindo o
site, porque muda o custo de coleta.

### 2.3 Conselhos Regionais de Odontologia

Confirmados com seção de classificados/vagas própria:

- CRO-RS — `crors.org.br/servicos-vagas-de-emprego/`
- CRO-PR — `cropr.org.br` (classificados por categoria)
- CRO-BA — `croba.org.br/classificados/`

São 27 conselhos. Volume individual baixo, mas sinal alto: são clínicas locais reais anunciando
diretamente, exatamente o tipo de vaga que não chega aos grandes portais. **Estratégia sugerida:**
não varrer os 27 — varrer só os das UFs que sobrevivem à sua lista de cidades bloqueadas (`3.2`).

### 2.4 Redes e franquias

| Rede | Canal | Observação |
|---|---|---|
| **OdontoPrev** | `vagasodontoprev.gupy.io` | **publica na Gupy** — confirma a aposta do achado 3 para o perfil odonto |
| Sorridents | `sorridents.com.br/trabalhe-conosco` + uma página em Google Sites | 500+ unidades franqueadas; canal improvisado |
| OdontoCompany | `odontocompany.com/trabalhe-conosco` | cadastro de currículo em PDF, sem listagem pública de vagas |

**Alerta importante para a `3.6`.** OdontoCompany e Sorridents são **redes de franquia**. Boa
parte do que aparece como "oportunidade" nesse universo é venda de franquia ou vaga comissionada,
não emprego. Seu filtro de reprovação por palavra precisa cobrir `franquia`, `seja um
franqueado`, `sócio`, `comissionado`, `percentual de produção` — senão o perfil odonto entope de
ruído. Isso vale mais para odontologia do que para qualquer outro perfil seu.

### 2.5 Plataforma dedicada e canais informais

- **Odonto.Job** — `odontojob.com.br` (antes `myodontojob.com`). Única plataforma exclusiva de
  odontologia encontrada. Ativa em 2026, anuncia "1.200+ profissionais ativos" e uma seção nova de
  vagas publicadas por clínicas. **Parece exigir cadastro para ver as vagas** e não expõe busca
  pública — o que a torna cara de coletar e pequena demais para valer a pena agora.
- **Grupos de Facebook** — citados por fonte do setor como tendo "centenas de vagas" anunciadas
  por donos de clínica. Alto sinal, coleta automatizada inviável (a pesquisa original já concluía
  isso para redes sociais).
- **APCD e associações estaduais** — mantêm classificados. Mesma lógica dos CROs.

---

## 3. Ordem de ataque sugerida

1. **Generalistas com URL de área pronta** (Catho, Vagas, Indeed, InfoJobs, BNE). Reaproveita tudo
   que já será construído para os outros perfis; só muda o dicionário de sinônimos da `3.5`.
2. **PCI Concursos**, página do cargo. Uma URL, campos estruturados, filtro por região, e cobre um
   canal que nenhum concorrente cobre. Melhor relação valor/esforço da lista inteira.
3. **Gupy**, já planejada — com OdontoPrev confirmando que há odonto lá.
4. **CROs das UFs que sobrarem** depois do filtro de cidades.
5. **Jooble**, para medir quanto ele acrescenta além dos itens 1–3.
6. **Odonto.Job, APCD, Facebook** — manual, ou rodada seguinte.

---

## 4. O que ainda precisa ser verificado

1. **PCI Concursos tem RSS ou alerta por e-mail?** Não apareceu na página. Muda o custo de coleta.
2. **Os alertas gratuitos por e-mail cobrem o Brasil inteiro?** Sua própria pergunta no achado 2, e
   ela vale dobrado aqui: se o plano grátis limitar a uma região, o alerta por e-mail deixa de ser
   a fonte barata que a pesquisa original promete.
3. **Odonto.Job exige login mesmo?** Se tiver listagem pública, sobe várias posições.
4. **Quais dos 27 CROs têm HTML aproveitável?** Provavelmente muito heterogêneo.
5. **Qual o volume real por cidade fora dos grandes centros?** Toda a lógica do selo da `3.4`
   depende de haver vaga de odonto em cidade média — isso ainda não foi medido.

---

## 5. Impacto no escopo já aprovado

- **`3.1` confirmada e reforçada.** O perfil `odonto` precisa de lista de fontes própria, não só de
  termos próprios. É a maior diferença entre ele e os outros três.
- **`3.6` fica mais importante do que eu estimei.** O ruído de franquia e comissionamento em
  odontologia é estrutural, não acidental.
- **`3.7` fica mais importante.** Jooble agrega dos outros; sem deduplicação, o mesmo anúncio
  aparece três vezes.
- **Decisão nova, ainda em aberto:** concurso público entra como o mesmo tipo de item da vaga, ou
  como entidade separada? Ele tem prazo de inscrição, banca, e o conceito de cadastro reserva —
  que é uma vaga que pode nunca existir. Isso precisa ser resolvido no `DESIGN.md`.

  **Minha recomendação:** entidade separada, unificada só na apresentação. Forçar concurso no
  esquema de vaga faz metade dos campos ficarem vazios e a outra metade mentir. Modelar à parte
  custa pouco agora e evita retrabalho quando entrarem prazo, banca e cadastro reserva.

---

## 6. Resultado da triagem — 16/08/2026

### O princípio que passa a reger a seleção

> *"Tudo que vai consumir alto custo de desenvolvimento ou workarounds pode ser colocado adiante.
> Vamos entregar as vagas fáceis de puxar nessa fase."*

Este critério vale mais que a minha ordem de ataque original e substitui o ranking do item 3.

### Primeira rodada — 9 fontes

`Catho` · `Vagas.com` · `Indeed` · `InfoJobs` · `BNE` · `Jooble` · `PCI Concursos` ·
`CROs regionais` · `OdontoPrev (Gupy)`

### Fase seguinte — 10 fontes

`LinkedIn` · `Glassdoor` · `OdontoConcursos` · `OdonConcursos` · `CD Concursos` · `APCD` ·
`Sorridents` · `OdontoCompany` · `Odonto.Job` · `Grupos de Facebook`

### Afirmações confirmadas

Achado principal, modelagem de concurso como entidade separada, alerta de franquia/comissionado,
impacto no escopo aprovado e ressalva de método — todas com concordância.

### Decisões vindas das verificações

| # | Decisão |
|---|---|
| V1 | PCI Concursos entra **condicionalmente**: se puxar a vaga se mostrar difícil, cai para a fase seguinte. |
| V2 | **Ingestão por e-mail sai da fase 1 inteira.** Exige tratamento caso a caso por plataforma. |
| V3 | Odonto.Job exige login, como suspeitado. Permanece na fase seguinte. |
| V4 | Os CROs são heterogêneos. Vai ser levantada uma **lista de UFs onde ela não trabalharia** (Acre, Roraima e afins). |
| V5 | Cidade média interessa **muito**, por competição fraca e qualidade de vida. |

### Consequência maior: a fase 1 vira 100% página pública

Com o e-mail adiado (V2), não sobra nenhum canal de baixo atrito garantido na primeira rodada.
Todo o volume da fase 1 depende de conseguir ler página pública — o que torna o critério
"fácil de puxar" a única coisa entre o plano e um trabalho grande de raspagem.

### Duas tensões com o princípio declarado

1. **`CROs regionais` é o item mais caro da primeira rodada.** São 27 sites feitos à mão, sem
   padrão — e a própria V4 reconhece isso ("provavelmente sim... precisaremos fazer um rebuild no
   plano"). É a definição de alto custo de desenvolvimento e workaround. **Encaminhamento:** a
   lista de UFs da V4 tem que vir *antes* de qualquer coletor de CRO, porque é ela que define se
   são 27 sites ou 12. Sem a lista, esse item não é estimável.

2. **`Indeed` ficou na primeira rodada e `LinkedIn` na seguinte, com perfil técnico parecido.**
   Ambos têm forte proteção anti-automação; a pesquisa original classifica o Indeed como "alta
   dificuldade fora de integrações oficiais". Não é questão de termos de uso (fora de escopo por
   decisão sua) — é custo de engenharia, exatamente o seu critério. **Ressalva honesta:** não
   testei nenhum dos dois, então isto é hipótese vinda da pesquisa, não medição.

### Item novo que apareceu

**Qualidade de vida por cidade** (V5) entra como dimensão futura, ao lado de custo de vida e
competição, que já estavam na `5.7`. Continua fora da rodada atual.

### Reaproveitamento: a V4 já tem dono

A lista de UFs excluídas **não é trabalho novo** — é exatamente o insumo da `3.2` (lista de
cidades bloqueadas), já aprovada. O que falta é o dado, não o mecanismo.

---

## Fontes consultadas

- [PCI Concursos — vagas de cirurgião-dentista](https://www.pciconcursos.com.br/vagas/cirurgiao-dentista)
- [Odonto.Job](https://www.myodontojob.com/)
- [Dental Office — 6 sites para procurar emprego](https://www.dentaloffice.com.br/vaga-para-dentista/)
- [CRO-RS — vagas de emprego](https://crors.org.br/servicos-vagas-de-emprego/)
- [CRO-PR — classificados](https://www.cropr.org.br/index.php/classificados/categoria/oferece/44)
- [CRO-BA — classificados](https://croba.org.br/classificados/)
- [OdontoPrev na Gupy](https://vagasodontoprev.gupy.io/)
- [Sorridents — trabalhe conosco](https://sorridents.com.br/trabalhe-conosco)
- [OdontoCompany — trabalhe conosco](https://odontocompany.com/trabalhe-conosco)
- [BNE — vagas para dentista](https://www.bne.com.br/vagas-de-emprego-para-dentista)
- [Catho — área de odontologia](https://www.catho.com.br/vagas/area-odontologia/)
- [Vagas.com — vagas de dentista](https://www.vagas.com.br/vagas-de-dentista)
- [Indeed — vagas de dentista](https://br.indeed.com/q-dentista-vagas.html)
- [LinkedIn — vagas de dentista](https://br.linkedin.com/jobs/dentista-vagas)
- [OdontoConcursos](https://www.odontoconcursos.com.br/)
- [OdonConcursos — editais abertos para dentista](https://odonconcursos.com.br/noticia/editais-abertos-para-dentista)
- [APCD — concursos](https://www.apcd.org.br/jornal-da-apcd/concursos/concurso-publico-da-prefeitura-de-jacarei-tem-vagas-para-cirurgiao-dentista)
- [Como o Jooble funciona](https://br.jooble.org/how-jooble-works/)
