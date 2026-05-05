# 📖 Documentação Técnica e Governança de Dados

## 1. Objetivo
Este documento estabelece as diretrizes de governança e arquitetura de dados aplicadas ao pipeline do dashboard executivo (`analise/app_streamlit.py`) e ao motor de processamento (`analise/app_tratamento_dados.py`). 

O foco desta documentação é garantir:
*   **Transparência:** Documentação clara de fontes e dicionário de dados.
*   **Qualidade (Data Observability):** Regras rigorosas de validação e limpeza.
*   **Source of Truth (SOT):** Centralização das regras de negócio em uma base única.
*   **Reprodutibilidade:** Garantia de execução determinística do processo analítico.

---

## 2. Fontes de Dados (Ingestão)
Os dados brutos são extraídos de arquivos locais em formato CSV, garantindo que o pipeline seja independente do diretório de execução atual. Os datasets estão divididos em dois domínios:

**Domínio Transacional:**
*   `orders_dataset.csv`: Cabeçalho de pedidos e *timestamps* logísticos.
*   `order_items_dataset.csv`: Relação de itens, preços e fretes.
*   `order_payments_dataset.csv`: Transações financeiras.
*   `order_reviews_dataset.csv`: Avaliações e *scores* de satisfação.

**Domínio Cadastral (Dimensões):**
*   `customers_dataset.csv`: Dados geográficos e IDs de clientes.
*   `sellers_dataset.csv`: Dados geográficos dos lojistas parceiros.
*   `products_dataset.csv`: Metadados do catálogo.
*   `product_category_name_translation.csv`: Padronização de idioma das categorias.

---

## 3. Data Lineage e Fluxo de Processamento

### 3.1. Tratamento da Camada Raw (Bruta)
A função `limpar_dados` atua como o primeiro filtro de qualidade, executando:
1.  **Drop de Colunas Vazias:** Remoção de features com 100% de nulidade.
2.  **Desduplicação:** Eliminação de registros duplicados (`drop_duplicates`).
3.  **Higienização de Strings:** Aplicação de `strip()` em variáveis do tipo `object` para remover espaços invisíveis.

### 3.2. Transformações e Regras de Negócio (Camada Silver/Gold)
O pipeline constrói a *Single Source of Truth* (`df_full`) aplicando as seguintes lógicas:
*   **Tipagem Dinâmica:** Conversão massiva de colunas de data em `orders` para formato `datetime` via `pd.to_datetime(..., errors='coerce')`.
*   **Filtro de Status:** Seleção estrita de pedidos finalizados (`order_status == 'delivered'`).
*   **Feature Engineering:** Criação da feature financeira macro: `total_value = price + freight_value`.
*   **Tratamento de Missing Values:**
    *   `product_category_name_english` preenchido como `Uncategorized`.
    *   `customer_state` preenchido como `Unknown`.

### 3.3. Corte Temporal Determinístico (Safra YTD)
Para garantir comparações justas (Year-over-Year), a base `df_full` sofre um recorte dinâmico baseado na variável `max_date`:
*   Mantém o ano anterior completo.
*   Recorta o ano vigente exatamente até o mês correspondente ao último dado disponível, evitando falsas quedas de performance causadas por anos incompletos.

---

## 4. Dicionário de Dados (Data Schema)

A base consolidada `df_full` é a fonte oficial do dashboard. Abaixo, as colunas críticas modeladas:

| Nome da Coluna | Tipo de Dado | Descrição / Regra de Negócio |
| :--- | :--- | :--- |
| `order_id` | String (PK) | Identificador único do pedido. |
| `customer_unique_id` | String | Identificador único do cliente (usado para cálculo de recompra). |
| `customer_state` | String | UF de destino do comprador (Ex: SP, RJ). |
| `seller_state` | String | UF de origem do lojista parceiro. |
| `order_purchase_timestamp`| Datetime | Data e hora exata da aprovação da compra. |
| `product_category_name` | String | Categoria do produto padronizada em *Title Case*. |
| `price` | Float | Valor do produto (Regra: deve ser >= 0). |
| `freight_value` | Float | Custo logístico repassado (Regra: deve ser >= 0). |
| `total_value` | Float | Receita bruta da transação (`price` + `freight_value`). |
| `ano_mes` | String | Feature temporal derivada no formato 'YYYY-MM' para filtros. |

---

## 5. Controles de Qualidade (Data Observability)

Para proteger a integridade da análise executiva, o pipeline impõe três travas críticas:

### 5.1. Validação de Telemetria Logística
O sistema detecta e isola anomalias de *timestamp* (sequência temporal invertida) geradas pelas transportadoras:
*   Aprovação registrada antes da Compra.
*   Entrega à transportadora registrada antes da Aprovação.
*   Entrega ao cliente registrada antes da coleta.
*   **Ação:** Estes dados são excluídos do cálculo de SLA e o percentual de falha (`pct_falha`) é gerado como um indicador técnico de qualidade do fornecedor.

### 5.2. Expurgos de Integridade Relacional
Registros são removidos sumariamente se apresentarem nulidade nas chaves primárias ou valores financeiros:
*   Drop `NaN` em: `order_id`, `customer_id`, `product_id`, `price`, `freight_value`.

### 5.3. Trava de Valores Negativos
Garantia de consistência contábil aplicando a restrição `df_full[col] >= 0` para todas as features monetárias.

---

## 6. Padronização das Métricas de Negócio

Para garantir que não haja divergência de relatórios na companhia, as fórmulas abaixo são o padrão-ouro matemático do sistema:

*   **Receita Total:** `sum(total_value) / 1e6` (Exibido em Milhões).
*   **Prazo Médio (Lead Time):** Média da diferença entre `order_delivered_customer_date` e `order_purchase_timestamp` em dias.
*   **Taxa de Recompra:** Percentual de `customer_unique_id` com contagem distinta de `order_id` > 1.
*   **Satisfação (NPS Analógico):** Média simples de `review_score` (escala 1 a 5).
*   **Taxa de Churn por Atraso:** Soma de `review_score == 1` dividida pelo volume total da faixa de SLA.

---

## 7. Diretrizes de Privacidade e LGPD

Como parte fundamental da governança de dados:
*   **Anonimização:** Este projeto não expõe Dados Pessoais Identificáveis (PII - *Personally Identifiable Information*). Nomes, e-mails, CPFs ou endereços residenciais exatos não são trafegados no pipeline.
*   **Agregação Geográfica:** Análises espaciais são restritas a níveis macro (Região e UF), impossibilitando a identificação pontual de usuários.

---

## 8. Reprodutibilidade e Deploy

O pipeline é 100% determinístico. A mesma base CSV original sempre produzirá o mesmo Dashboard, pois:
1.  Não há amostragem aleatória ativa.
2.  A regra de *cut-off* temporal (`max_date`) calcula a referência a partir do próprio conjunto de dados.

**Execução do Ambiente:**
*   **Requisito:** Recomenda-se rodar na raiz do projeto.
*   **Comando:** `streamlit run analise/app_streamlit.py`
*   **Caching:** A ingestão de dados (`load_data`) utiliza o decorador `@st.cache_data` do Streamlit para otimizar o uso de memória em recargas de UI.