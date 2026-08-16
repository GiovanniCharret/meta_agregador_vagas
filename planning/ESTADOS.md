# ESTADOS — a lista para podar

> Documento de apoio, **não é lido pelo programa**. Serve para vocês dois decidirem
> juntos quais estados ficam. A lista que vale é a `ufs_liberadas` do
> `config/config.json`; esta aqui existe só porque sigla sozinha não diz nada para quem
> vai escolher.
>
> Criado em 16/08/2026, a pedido: *"faça um json com todos os estados liberados, vamos
> filtrar isso só para frente"*.

## Por que lista branca e não lista negra

São 27 unidades federativas — um conjunto pequeno e fechado. Podar uma lista pronta é
mais fácil do que lembrar de proibir uma a uma, e o resultado é visível: dá para bater o
olho e ver onde vocês aceitariam morar. As **cidades** continuam em lista negra, porque
são milhares e enumerar as aceitas seria impraticável.

A lista é **obrigatória e não pode ficar vazia**. Se estivesse ausente, o programa teria
que adivinhar entre "todos os estados" e "nenhum", e qualquer das duas escolhida em
silêncio produziria um feed errado sem vocês perceberem.

## As 27, por região

Marque as que saem. A ordem abaixo é a mesma do `config.exemplo.json`.

### Norte — 7
| Sigla | Estado |
|---|---|
| AC | Acre |
| AP | Amapá |
| AM | Amazonas |
| PA | Pará |
| RO | Rondônia |
| RR | Roraima |
| TO | Tocantins |

### Nordeste — 9
| Sigla | Estado |
|---|---|
| AL | Alagoas |
| BA | Bahia |
| CE | Ceará |
| MA | Maranhão |
| PB | Paraíba |
| PE | Pernambuco |
| PI | Piauí |
| RN | Rio Grande do Norte |
| SE | Sergipe |

### Centro-Oeste — 4
| Sigla | Estado |
|---|---|
| DF | Distrito Federal |
| GO | Goiás |
| MT | Mato Grosso |
| MS | Mato Grosso do Sul |

### Sudeste — 4
| Sigla | Estado |
|---|---|
| ES | Espírito Santo |
| MG | Minas Gerais |
| RJ | Rio de Janeiro |
| SP | São Paulo |

### Sul — 3
| Sigla | Estado |
|---|---|
| PR | Paraná |
| RS | Rio Grande do Sul |
| SC | Santa Catarina |

## Como podar

Abra `config/config.json`, encontre `ufs_liberadas` e apague as siglas que saem. O
programa recusa sigla mal escrita — se alguém escrever `Parana` em vez de `PR`, a
mensagem cita o valor errado em vez de deixar o estado sumir do feed em silêncio.

## O que essa lista destrava

- **Filtro `3.2`** — vaga em estado fora da lista não chega ao feed.
- **Subfase `S-P`, coletor de CRO** — era a única subfase bloqueada por insumo. O número
  de conselhos a coletar é o número de estados que sobrarem aqui. Com as 27, são 27
  coletores; podando pela metade, são 13. **Enquanto a poda não acontecer, a S-P segue
  sem estimativa** — mas agora ela está bloqueada por uma decisão, não por falta de dado.
