## Prompt para colar

> Crie um HTML autocontido para eu ler **[DOCUMENTO]** e responder sobre ele. Requisitos:
>
> **1. Autocontido.** CSS e JS inline, sem CDN, sem build, sem dependência externa. Tem que abrir
> com duplo clique, via `file://`.
>
> **2. Numeração espelhada.** Use exatamente os mesmos números e títulos do documento de origem.
> Se lá é `3.4`, aqui é `3.4`. Assim eu debato por número e você sabe do que estou falando.
>
> **3. Canal de volta — o ponto principal.** Você não vê o que eu clico. Cada item precisa de
> controles, e uma barra fixa no rodapé deve montar um **texto puro** com as minhas escolhas e
> comentários, com um botão "copiar resposta". Eu colo esse texto no chat. O texto tem que citar
> o documento de origem e ser legível sozinho, sem a página.
>
> **4. Controles por item.** Botões mutuamente exclusivos para os estados **[LISTAR ESTADOS]**,
> mais uma caixa de texto livre em cada item. O conteúdo da caixa entra na resposta copiada,
> junto do número do item. Defina e me diga as regras de precedência entre botão e texto.
>
> **5. Persistência.** Salve marcações e textos em `localStorage`, com chave versionada. Se o
> formato mudar depois, suba a versão em vez de restaurar estado antigo torto.
>
> **6. Estética.** [REFERÊNCIA VISUAL]. Títulos em serifada, rótulos em monoespaçada, cartões com
> borda fina, uma cor por estado. Sem degradê genérico, sem emoji decorativo.
>
> **7. Não invente conteúdo.** O HTML é uma vista do documento, não uma reescrita. Se resumir
> algo, deixe claro que é resumo.
>
> **Antes de dizer que está pronto, valide:** confira que todo item tem controle, `id` e caixa
> correspondentes; e teste a lógica de montagem da resposta com um DOM de verdade (jsdom serve).
> Me diga quantas asserções rodaram e quais cenários cobriu.

---

## O que trocar em cada uso

| Campo | Exemplo |
|---|---|
| `[DOCUMENTO]` | `planning/IDEIAS.md` |
| `[LISTAR ESTADOS]` | `Aprovado` / `Icebox` — e texto livre significando "aprovado com mudanças" |
| `[REFERÊNCIA VISUAL]` | `inspirado nos modelos de planning/html-everything/` |

---

## As quatro decisões que fizeram diferença

1. **Estado derivado, não estado declarado.** Em vez de um botão "quero comentar", o simples ato
   de escrever no campo já define o estado. Menos cliques, menos ambiguidade.

2. **Precedência explícita entre controles.** "Icebox vence o comentário; comentário vence o
   Aprovado." Sem essa regra escrita, o LLM inventa uma e você descobre tarde.

3. **Contar o que ficou em branco.** A resposta copiada termina com `(15 ideias sem marcar)`.
   Isso separa "eu rejeitei" de "eu não cheguei lá" — distinção que muda o que o LLM faz depois.

4. **Exigir teste com DOM real.** Inspeção visual do código não pega erro de lógica de estado.
   Um teste que clica, digita, copia e compara o texto final pega. Peça o número de asserções: é
   a diferença entre "achei que funciona" e "verifiquei".