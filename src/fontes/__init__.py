"""Coletores, um modulo por fonte.

Por que este pacote existe: cada site publica vaga de um jeito, e a diferenca entre
eles nao pode vazar para o resto do pipeline. Todo modulo daqui expoe a mesma dupla de
funcoes puras - `extrai_vagas(html)` devolve os registros crus da fonte, e
`para_vaga(registro)` traduz um registro para o formato unico do projeto.

Manter as duas funcoes puras, sem rede dentro, e o que permite testar coletor com
fixture em vez de internet ligada. Quem busca a pagina e o orquestrador, nao o coletor.

Nenhum dado vive aqui: este pacote guarda codigo. Payload cru vai para dados/bruto/.
"""
