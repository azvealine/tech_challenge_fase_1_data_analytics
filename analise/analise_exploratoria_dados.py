import pandas as pd
import os

# ==========================================
# 1. CARREGAMENTO E PREPARAÇÃO DOS DADOS
# ==========================================

def limpar_dados(df, nome_dataset, verbose=True):
    """
    Função para limpar e tratar dados:
    - Remove colunas completamente vazias
    - Remove duplicatas
    - Exibe relatório de valores nulos
    """
    if verbose:
        print(f"\n--- Limpeza: {nome_dataset} ---")
        print(f"Linhas originais: {len(df)}")
        print(f"Colunas originais: {len(df.columns)}")
    
    # Remover colunas completamente vazias (100% nulas)
    colunas_vazias = df.columns[df.isnull().all()].tolist()
    if colunas_vazias:
        if verbose:
            print(f"Colunas removidas (100% vazias): {colunas_vazias}")
        df = df.drop(columns=colunas_vazias)
    
    # Remover duplicatas
    duplicatas_antes = len(df)
    df = df.drop_duplicates()
    duplicatas_removidas = duplicatas_antes - len(df)
    if duplicatas_removidas > 0 and verbose:
        print(f"Linhas duplicadas removidas: {duplicatas_removidas}")
    
    # Limpar espaços em branco em colunas de texto
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip() if df[col].dtype == 'object' else df[col]
    
    # Relatório de valores nulos
    if verbose:
        nulos = df.isnull().sum()
        if nulos.sum() > 0:
            print("\nValores nulos por coluna:")
            for col, count in nulos[nulos > 0].items():
                pct = (count / len(df)) * 100
                print(f"  {col}: {count} ({pct:.2f}%)")
        else:
            print("Nenhum valor nulo encontrado")
        
        print(f"Linhas após limpeza: {len(df)}")
        print(f"Colunas após limpeza: {len(df.columns)}")
    
    return df


def carregar_dados_brutos(verbose=True):
    """Carrega todos os datasets CSV do diretório"""
    base_dir = os.path.dirname(__file__)
    
    if verbose:
        print("Carregando dados brutos...")
    
    orders = pd.read_csv(os.path.join(base_dir, 'data/orders_dataset.csv'))
    order_items = pd.read_csv(os.path.join(base_dir, 'data/order_items_dataset.csv'))
    customers = pd.read_csv(os.path.join(base_dir, 'data/customers_dataset.csv'))
    payments = pd.read_csv(os.path.join(base_dir, 'data/order_payments_dataset.csv'))
    products = pd.read_csv(os.path.join(base_dir, 'data/products_dataset.csv'))
    category_translation = pd.read_csv(os.path.join(base_dir, 'data/product_category_name_translation.csv'))
    reviews = pd.read_csv(os.path.join(base_dir, 'data/order_reviews_dataset.csv'))
    
    return orders, order_items, customers, payments, products, category_translation, reviews


def processar_dados_completos(verbose=True):
    """
    Carrega, limpa e processa todos os dados
    Retorna: (df_full, orders, order_items, customers, payments, products, category_translation, reviews)
    """
    # Carregar dados brutos
    orders, order_items, customers, payments, products, category_translation, reviews = carregar_dados_brutos(verbose)
    
    # Limpeza de cada dataset
    if verbose:
        print("\n========== LIMPEZA DOS DATASETS ==========")
    orders = limpar_dados(orders, 'orders', verbose)
    order_items = limpar_dados(order_items, 'order_items', verbose)
    customers = limpar_dados(customers, 'customers', verbose)
    payments = limpar_dados(payments, 'payments', verbose)
    products = limpar_dados(products, 'products', verbose)
    category_translation = limpar_dados(category_translation, 'category_translation', verbose)
    reviews = limpar_dados(reviews, 'reviews', verbose)

    # Converter colunas de data/hora para o formato datetime
    orders['order_purchase_timestamp'] = pd.to_datetime(orders['order_purchase_timestamp'])
    orders['order_delivered_customer_date'] = pd.to_datetime(orders['order_delivered_customer_date'])
    orders['order_estimated_delivery_date'] = pd.to_datetime(orders['order_estimated_delivery_date'])

    # Filtrar apenas os pedidos efetivamente entregues (GMV Real)
    delivered_orders = orders[orders['order_status'] == 'delivered'].copy()

    # ==========================================
    # 2. BASE DE DADOS UNIFICADA (MERGE)
    # ==========================================
    
    if verbose:
        print("\n========== CRIANDO BASE UNIFICADA ==========")

    # Unir Itens + Pedidos + Clientes + Produtos + Tradução de Categorias
    df_full = pd.merge(order_items, delivered_orders[['order_id', 'customer_id', 'order_purchase_timestamp']], on='order_id')
    df_full = pd.merge(df_full, customers[['customer_id', 'customer_unique_id', 'customer_state']], on='customer_id')
    df_full = pd.merge(df_full, products[['product_id', 'product_category_name']], on='product_id')
    df_full = pd.merge(df_full, category_translation, on='product_category_name', how='left')

    # Calcular a Receita Total por Item (Preço + Frete)
    df_full['total_value'] = df_full['price'] + df_full['freight_value']

    # ==========================================
    # 2.1 TRATAMENTO DE VALORES NULOS NA BASE UNIFICADA
    # ==========================================

    if verbose:
        print("\n--- Tratamento de Valores Nulos (Dados Unificados) ---")
        print(f"Total de linhas antes: {len(df_full)}")

    # Remover linhas com valores críticos nulos
    colunas_criticas = ['order_id', 'customer_id', 'product_id', 'price', 'freight_value']
    df_full = df_full.dropna(subset=colunas_criticas)

    if verbose:
        print(f"Total de linhas após remover valores nulos críticos: {len(df_full)}")

    # Preencher valores nulos em colunas não-críticas com valores padrão
    if 'product_category_name_english' in df_full.columns:
        nulos_cat = df_full['product_category_name_english'].isnull().sum()
        if nulos_cat > 0:
            df_full = df_full.assign(product_category_name_english=df_full['product_category_name_english'].fillna('Uncategorized'))
            if verbose:
                print(f"Preenchidos {nulos_cat} valores nulos em 'product_category_name_english' com 'Uncategorized'")

    if 'customer_state' in df_full.columns:
        nulos_state = df_full['customer_state'].isnull().sum()
        if nulos_state > 0:
            df_full = df_full.assign(customer_state=df_full['customer_state'].fillna('Unknown'))
            if verbose:
                print(f"Preenchidos {nulos_state} valores nulos em 'customer_state' com 'Unknown'")

    # Remover valores negativos (validação de dados)
    if verbose:
        print("\nValidação de valores negativos:")
    colunas_numericas = ['price', 'freight_value']
    for col in colunas_numericas:
        if col in df_full.columns:
            negativos = (df_full[col] < 0).sum()
            if negativos > 0:
                if verbose:
                    print(f"  {col}: {negativos} valores negativos encontrados e removidos")
                df_full = df_full[df_full[col] >= 0]

    if verbose:
        print(f"Total de linhas após validação: {len(df_full)}")

    # ==========================================
    # FILTRAR DADOS BASEADO NO MAX DATA
    # ==========================================

    # Encontrar a data máxima
    max_date = df_full['order_purchase_timestamp'].max()
    current_year = max_date.year
    previous_year = current_year - 1
    max_month = max_date.month

    # Filtrar para incluir o ano anterior inteiro e os meses até o mês da data máxima no ano atual
    df_full = df_full[
        (df_full['order_purchase_timestamp'].dt.year == previous_year) |
        ((df_full['order_purchase_timestamp'].dt.year == current_year) & (df_full['order_purchase_timestamp'].dt.month <= max_month))
    ]

    if verbose:
        print(f"Dados filtrados até {max_date.strftime('%Y-%m-%d')}: ano {previous_year} inteiro e meses 1-{max_month} de {current_year}")

    # ==========================================
    # FORMATAÇÃO ESTÉTICA DAS CATEGORIAS (CLEANING VISUAL)
    # ==========================================
    if verbose:
        print("Padronizando a nomenclatura das categorias...")
        
    if 'product_category_name_english' in df_full.columns:
        df_full['product_category_name_english'] = df_full['product_category_name_english'].astype(str).str.replace('_', ' ').str.title()

    if 'product_category_name' in df_full.columns:
        df_full['product_category_name'] = df_full['product_category_name'].astype(str).str.replace('_', ' ').str.title()

    return df_full, orders, order_items, customers, payments, products, category_translation, reviews


# ==========================================
# EXECUÇÃO QUANDO EXECUTADO DIRETAMENTE
# ==========================================

if __name__ == "__main__":
    print("="*50)
    print("PROCESSAMENTO E ANÁLISE DE DADOS OLIST")
    print("="*50)
    
    # Processar dados
    df_full, orders, order_items, customers, payments, products, category_translation, reviews = processar_dados_completos(verbose=True)

    # ==========================================
    # 3. ANÁLISE 1: CRESCIMENTO MENSAL E BLACK FRIDAY
    # ==========================================

    # Extrair Ano-Mês
    df_full['month_year'] = df_full['order_purchase_timestamp'].dt.to_period('M').astype(str)

    monthly_revenue = df_full.groupby('month_year')['total_value'].sum().reset_index()
    monthly_revenue['mom_growth_pct'] = monthly_revenue['total_value'].pct_change() * 100

    print("\n========== ANÁLISES ==========")
    print("\n--- Crescimento da Receita (Pico Black Friday 2017) ---")
    print(monthly_revenue[monthly_revenue['month_year'].str.contains('2017-10|2017-11|2017-12')])


    # ==========================================
    # 4. ANÁLISE 2: LEI DE PARETO (CONCENTRAÇÃO DE SELLERS)
    # ==========================================

    seller_revenue = df_full.groupby('seller_id')['total_value'].sum().sort_values(ascending=False)
    total_rev = seller_revenue.sum()
    cum_rev = seller_revenue.cumsum()

    # Identificar a receita gerada pelos 20% maiores vendedores
    top_20_percent_sellers = int(len(seller_revenue) * 0.20)
    rev_top_20 = cum_rev.iloc[top_20_percent_sellers] / total_rev * 100

    print(f"\n--- Concentração de Vendedores (Pareto) ---")
    print(f"Total de Sellers: {len(seller_revenue)}")
    print(f"Os top 20% geram {rev_top_20:.2f}% de toda a receita.")


    # ==========================================
    # 5. ANÁLISE 3: COMPORTAMENTO (RELÓGIO BIOLÓGICO)
    # ==========================================

    df_full['hour'] = df_full['order_purchase_timestamp'].dt.hour
    df_full['day_of_week'] = df_full['order_purchase_timestamp'].dt.day_name()

    hourly_purchases = df_full.groupby('hour')['order_id'].nunique().sort_values(ascending=False)
    dow_purchases = df_full.groupby('day_of_week')['order_id'].nunique().sort_values(ascending=False)

    print("\n--- Horários e Dias de Pico ---")
    print(dow_purchases.head(3))
    print(hourly_purchases.head(3))


    # ==========================================
    # 6. ANÁLISE 4: O "CUSTO BRASIL" (FRETE VS PREÇO POR ESTADO)
    # ==========================================

    state_metrics = df_full.groupby('customer_state').agg(
        total_freight=('freight_value', 'sum'),
        total_price=('price', 'sum')
    )
    state_metrics['freight_ratio_pct'] = (state_metrics['total_freight'] / state_metrics['total_price']) * 100
    state_metrics = state_metrics.sort_values('freight_ratio_pct', ascending=False)

    print("\n--- Estados com Maior Custo de Frete Proporcional ---")
    print(state_metrics['freight_ratio_pct'].head(5))


    # ==========================================
    # 7. ANÁLISE 5: PRODUTOS ISCA (VOLUME) VS MOTORES DE MARGEM (RECEITA)
    # ==========================================

    volume_vs_revenue = df_full.groupby('product_category_name_english').agg(
        unidades_vendidas=('order_id', 'count'),
        receita_total=('total_value', 'sum')
    ).reset_index()

    top_volume = volume_vs_revenue.sort_values('unidades_vendidas', ascending=False).head(3)
    top_receita = volume_vs_revenue.sort_values('receita_total', ascending=False).head(3)

    print("\n--- Top Categorias por Volume (Iscas) ---")
    print(top_volume[['product_category_name_english', 'unidades_vendidas']])
    print("\n--- Top Categorias por Receita (Motores) ---")
    print(top_receita[['product_category_name_english', 'receita_total']])


    # ==========================================
    # 8. ANÁLISE 6: RISCO DE CRÉDITO (PARCELAMENTO)
    # ==========================================

    df_payments_cat = pd.merge(df_full[['order_id', 'product_category_name_english']], 
                               payments[payments['payment_type'] == 'credit_card'][['order_id', 'payment_installments']], 
                               on='order_id')

    installments_cat = df_payments_cat.groupby('product_category_name_english')['payment_installments'].mean().sort_values(ascending=False)

    print("\n--- Categorias com Maior Prazo de Parcelamento ---")
    print(installments_cat.head(3))


    # ==========================================
    # 9. ANÁLISE 7: LOGÍSTICA VS SATISFAÇÃO DO CLIENTE (SLA VS NPS)
    # ==========================================

    # Calcular Tempo de Entrega (Lead Time)
    delivered_with_date = orders[orders['order_delivered_customer_date'].notnull()].copy()
    delivered_with_date['lead_time_days'] = (delivered_with_date['order_delivered_customer_date'] - delivered_with_date['order_purchase_timestamp']).dt.total_seconds() / (24 * 3600)

    # Deduplicar as notas (evitar que o mesmo pedido conte duas vezes)
    reviews_unique = reviews.drop_duplicates(subset=['order_id'], keep='first')

    # Cruzar SLA com as Notas (Review Scores)
    orders_reviews = pd.merge(delivered_with_date, reviews_unique[['order_id', 'review_score']], on='order_id', how='inner')

    lead_time_by_score = orders_reviews.groupby('review_score')['lead_time_days'].mean().reset_index().sort_values('review_score', ascending=False)

    print("\n--- Impacto do Prazo de Entrega na Satisfação (Estrelas) ---")
    print(lead_time_by_score)


    # ==========================================
    # 10. ANÁLISE 8: TAXA DE RETENÇÃO E RECOMPRA (LTV)
    # ==========================================

    repurchase_counts = df_full.groupby('customer_unique_id')['order_id'].nunique()
    repeat_customers_rate = (repurchase_counts > 1).mean() * 100

    print(f"\n--- Retenção de Clientes ---")
    print(f"Taxa de Recompra Global: {repeat_customers_rate:.2f}%")