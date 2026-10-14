# Legado — score de viabilidade comercial (descartado)

Código do Random Forest que estimava risco comercial (Baixo/Médio/Alto) a partir de
`vendas_estimadas`. **Não está mais conectado ao ml-service nem à API.**

Por que foi descartado: as vendas da Steam não são públicas; o rótulo dependia de uma
estimativa (multiplicador sobre o número de reviews), sem ground truth. Mesmo após corrigir
o data leakage, a acurácia honesta ficou em ~55% — insuficiente para sustentar um score
exibido ao desenvolvedor.

O Random Forest foi reaproveitado em `ml-service/ml/train_drivers.py`, agora com rótulo
real (`voted_up` de cada review) para identificar quais temas mais pesam na recomendação.

Os imports deste diretório refletem a estrutura antiga (`domain.risk`, `ml.features`…) e
não resolvem a partir da raiz atual. Mantido apenas como registro metodológico do TCC.
Ver vault: `decisoes/Descarte do Score de Vendas`.
