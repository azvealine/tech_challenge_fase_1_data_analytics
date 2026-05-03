import pandas as pd
import os

def limpar_dados(df, nome_dataset, verbose=True):
    """Limpa e trata dados: remove colunas vazias, duplicatas e limpa strings."""
    if verbose:
        print(f"\n--- Limpeza: {nome_dataset} ---")
    
    colunas_vazias = df.columns[df.isnull().all()].tolist()
    if colunas_vazias:
        df = df.drop(columns=colunas_vazias)
    
    df = df.drop_duplicates()
    
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].str.strip()
    
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
    sellers = pd.read_csv(os.path.join(base_dir, 'data/sellers_dataset.csv'))
    return orders, order_items, customers, payments, products, category_translation, reviews, sellers

def preparar_orders(orders):
    """Normaliza e valida os campos de data no dataset de pedidos."""
    colunas_data = [
        'order_purchase_timestamp',
        'order_approved_at',
        'order_delivered_carrier_date',
        'order_delivered_customer_date',
        'order_estimated_delivery_date'
    ]
    for col in colunas_data:
        if col in orders.columns:
            orders[col] = pd.to_datetime(orders[col], errors='coerce')
    return orders


def processar_dados_completos(verbose=True):
    """Carrega, limpa, unifica e formata os dados principais."""
    orders, order_items, customers, payments, products, category_translation, reviews, sellers = carregar_dados_brutos(verbose)
    
    orders = limpar_dados(orders, 'orders', verbose)
    order_items = limpar_dados(order_items, 'order_items', verbose)
    customers = limpar_dados(customers, 'customers', verbose)
    payments = limpar_dados(payments, 'payments', verbose)
    products = limpar_dados(products, 'products', verbose)
    category_translation = limpar_dados(category_translation, 'category_translation', verbose)
    reviews = limpar_dados(reviews, 'reviews', verbose)
    sellers = limpar_dados(sellers, 'sellers', verbose)

    orders = preparar_orders(orders)
    delivered_orders = orders[orders['order_status'] == 'delivered'].copy()

    df_full = pd.merge(order_items, delivered_orders[['order_id', 'customer_id', 'order_purchase_timestamp']], on='order_id')
    df_full = pd.merge(df_full, customers[['customer_id', 'customer_unique_id', 'customer_state']], on='customer_id')
    df_full = pd.merge(df_full, products[['product_id', 'product_category_name']], on='product_id')
    df_full = pd.merge(df_full, category_translation, on='product_category_name', how='left')
    df_full = pd.merge(df_full, sellers[['seller_id', 'seller_state']], on='seller_id', how='left')
    df_full['total_value'] = df_full['price'] + df_full['freight_value']

    colunas_criticas = ['order_id', 'customer_id', 'product_id', 'price', 'freight_value']
    df_full = df_full.dropna(subset=colunas_criticas)

    if 'product_category_name_english' in df_full.columns:
        df_full['product_category_name_english'] = df_full['product_category_name_english'].fillna('Uncategorized')
    if 'customer_state' in df_full.columns:
        df_full['customer_state'] = df_full['customer_state'].fillna('Unknown')

    for col in ['price', 'freight_value']:
        if col in df_full.columns:
            df_full = df_full[df_full[col] >= 0]

    max_date = df_full['order_purchase_timestamp'].max()
    df_full = df_full[
        (df_full['order_purchase_timestamp'].dt.year == max_date.year - 1) |
        ((df_full['order_purchase_timestamp'].dt.year == max_date.year) & (df_full['order_purchase_timestamp'].dt.month <= max_date.month))
    ]

    if 'product_category_name_english' in df_full.columns:
        df_full['product_category_name_english'] = df_full['product_category_name_english'].astype(str).str.replace('_', ' ').str.title()
    if 'product_category_name' in df_full.columns:
        df_full['product_category_name'] = df_full['product_category_name'].astype(str).str.replace('_', ' ').str.title()

    df_full['ano_mes'] = df_full['order_purchase_timestamp'].dt.strftime('%Y-%m')

    return df_full, orders, order_items, customers, payments, products, category_translation, reviews, sellers


def preparar_pedidos_logistica(df_view, orders):
    """Prepara o conjunto de pedidos logísticos com métricas de tempo e auditoria."""
    pedidos_logistica = df_view[['order_id', 'customer_state']].drop_duplicates().merge(
        orders[['order_id', 'order_purchase_timestamp', 'order_approved_at',
                'order_delivered_carrier_date', 'order_delivered_customer_date',
                'order_estimated_delivery_date']],
        on='order_id', how='inner'
    ).dropna(subset=['order_delivered_customer_date']).copy()

    date_cols = ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date',
                 'order_delivered_customer_date', 'order_estimated_delivery_date']
    for col in date_cols:
        if col in pedidos_logistica.columns:
            pedidos_logistica[col] = pd.to_datetime(pedidos_logistica[col], errors='coerce')

    pedidos_logistica['tempo_aprovacao'] = (pedidos_logistica['order_approved_at'] - pedidos_logistica['order_purchase_timestamp']).dt.total_seconds() / 86400
    pedidos_logistica['tempo_postagem'] = (pedidos_logistica['order_delivered_carrier_date'] - pedidos_logistica['order_approved_at']).dt.total_seconds() / 86400
    pedidos_logistica['tempo_transporte'] = (pedidos_logistica['order_delivered_customer_date'] - pedidos_logistica['order_delivered_carrier_date']).dt.total_seconds() / 86400
    pedidos_logistica['dias_atraso'] = (pedidos_logistica['order_delivered_customer_date'] - pedidos_logistica['order_estimated_delivery_date']).dt.total_seconds() / 86400
    pedidos_logistica['tempo_total_exato'] = (pedidos_logistica['order_delivered_customer_date'] - pedidos_logistica['order_purchase_timestamp']).dt.total_seconds() / 86400

    sequencia_errada = (
        (pedidos_logistica['tempo_aprovacao'] < 0) |
        (pedidos_logistica['tempo_postagem'] < 0) |
        (pedidos_logistica['tempo_transporte'] < 0)
    )
    jornada_perfeita_inicial = len(pedidos_logistica)
    pedidos_logistica = pedidos_logistica[~sequencia_errada].copy()

    falha_rastreio = sequencia_errada.sum()
    pct_falha = (falha_rastreio / jornada_perfeita_inicial) * 100 if jornada_perfeita_inicial > 0 else 0

    return pedidos_logistica, pct_falha, falha_rastreio, jornada_perfeita_inicial


def categorizar_sla(dias):
    if pd.isna(dias):
        return "Desconhecido"
    if dias <= 0:
        return "1. No Prazo/Adiantado"
    elif dias <= 3:
        return "2. Atraso Leve (1-3d)"
    elif dias <= 7:
        return "3. Atraso Moderado (4-7d)"
    else:
        return "4. Atraso Crítico (>7d)"


def preparar_pedidos_com_reviews(pedidos_logistica, reviews):
    """Cria conjunto de pedidos com avaliações e categorias SLA para análise de churn."""
    pedidos_com_reviews = pedidos_logistica.merge(
        reviews[['order_id', 'review_score']],
        on='order_id', how='inner'
    ).drop_duplicates(subset=['order_id'])

    pedidos_com_reviews['Status SLA'] = pedidos_com_reviews['dias_atraso'].apply(categorizar_sla)
    pedidos_com_reviews['Detrator (Nota 1)'] = pedidos_com_reviews['review_score'] == 1

    sla_metrics = pedidos_com_reviews.groupby('Status SLA').agg(
        volume=('order_id', 'count'),
        nota_media=('review_score', 'mean'),
        churn_vol=('Detrator (Nota 1)', 'sum')
    ).reset_index()
    sla_metrics['Taxa de Churn (%)'] = (sla_metrics['churn_vol'] / sla_metrics['volume']) * 100
    sla_metrics = sla_metrics[sla_metrics['Status SLA'] != 'Desconhecido'].sort_values('Status SLA')

    return pedidos_com_reviews, sla_metrics


def preparar_regiao_logistica(pedidos_com_reviews, order_items, sellers, regioes_map):
    """Agrupa e calcula métricas de custo, prazo e satisfação por região."""
    frete_por_pedido = order_items.groupby('order_id')['freight_value'].sum().reset_index()
    pedidos_regiao = pedidos_com_reviews.merge(frete_por_pedido, on='order_id', how='inner')
    pedidos_regiao['Regiao'] = pedidos_regiao['customer_state'].map(regioes_map)

    regiao_logistica = pedidos_regiao.groupby('Regiao').agg(
        Volume_Pedidos=('order_id', 'count'),
        Frete_Medio=('freight_value', 'mean'),
        Prazo_Medio=('tempo_total_exato', 'mean'),
        Review_Score=('review_score', 'mean')
    ).reset_index()

    media_frete_global = pedidos_regiao['freight_value'].mean()
    media_prazo_global = pedidos_regiao['tempo_total_exato'].mean()

    return regiao_logistica, media_prazo_global, media_frete_global


def preparar_stats_rota(pedidos_logistica, order_items, sellers):
    """Gera métricas de atraso por rota para análise de risco."""
    df_rotas_all = pedidos_logistica.merge(order_items[['order_id', 'seller_id']], on='order_id', how='left')
    df_rotas_all = df_rotas_all.merge(sellers[['seller_id', 'seller_state']], on='seller_id', how='left')
    df_rotas_all['Rota'] = df_rotas_all['seller_state'] + " ➔ " + df_rotas_all['customer_state']
    df_rotas_all['Atrasou'] = df_rotas_all['dias_atraso'] > 0

    stats_rota = df_rotas_all.groupby('Rota').agg(
        total=('order_id', 'count'),
        atrasos=('Atrasou', 'sum')
    ).reset_index()
    stats_rota['% Atraso'] = (stats_rota['atrasos'] / stats_rota['total']) * 100

    return stats_rota


def preparar_kpis_ytd(df_full, orders, reviews, ano_base=2018):
    """Calcula as métricas YTD com base em df_full como fonte de verdade."""
    df_full_18 = df_full[df_full['order_purchase_timestamp'].dt.year == ano_base].copy()
    mes_maximo = df_full_18['order_purchase_timestamp'].dt.month.max()

    df_full_17_ytd = df_full[(df_full['order_purchase_timestamp'].dt.year == ano_base - 1) &
                             (df_full['order_purchase_timestamp'].dt.month <= mes_maximo)].copy()

    valid_orders_18 = df_full_18['order_id'].unique()
    valid_orders_17 = df_full_17_ytd['order_id'].unique()

    orders_18_limpo = orders[orders['order_id'].isin(valid_orders_18)].copy()
    orders_17_limpo = orders[orders['order_id'].isin(valid_orders_17)].copy()

    reviews_18_limpo = reviews[reviews['order_id'].isin(valid_orders_18)]
    reviews_17_limpo = reviews[reviews['order_id'].isin(valid_orders_17)]

    rev_18 = df_full_18['total_value'].sum() / 1e6
    rev_17 = df_full_17_ytd['total_value'].sum() / 1e6
    yoy_rev = ((rev_18 / rev_17) - 1) * 100 if rev_17 > 0 else 0
    dist_rev = rev_18 - 8.0

    ped_18 = df_full_18['order_id'].nunique()
    ped_17 = df_full_17_ytd['order_id'].nunique()
    yoy_ped = ((ped_18 / ped_17) - 1) * 100 if ped_17 > 0 else 0
    dist_ped = ped_18 - 60000

    deliv_18 = orders_18_limpo[orders_18_limpo['order_status'] == 'delivered'].copy()
    deliv_17 = orders_17_limpo[orders_17_limpo['order_status'] == 'delivered'].copy()

    prazo_18 = (deliv_18['order_delivered_customer_date'] - deliv_18['order_purchase_timestamp']).dt.total_seconds().mean() / 86400
    prazo_17 = (deliv_17['order_delivered_customer_date'] - deliv_17['order_purchase_timestamp']).dt.total_seconds().mean() / 86400
    yoy_prazo = prazo_18 - prazo_17
    dist_prazo = prazo_18 - 10.0

    nps_18 = reviews_18_limpo['review_score'].mean()
    nps_17 = reviews_17_limpo['review_score'].mean()
    yoy_nps = nps_18 - nps_17
    dist_nps = nps_18 - 4.50

    tx_18 = (df_full_18.groupby('customer_unique_id')['order_id'].nunique() > 1).mean() * 100
    tx_17 = (df_full_17_ytd.groupby('customer_unique_id')['order_id'].nunique() > 1).mean() * 100
    yoy_tx = tx_18 - tx_17
    dist_tx = tx_18 - 5.0

    return {
        'rev_18': rev_18,
        'rev_17': rev_17,
        'yoy_rev': yoy_rev,
        'dist_rev': dist_rev,
        'ped_18': ped_18,
        'ped_17': ped_17,
        'yoy_ped': yoy_ped,
        'dist_ped': dist_ped,
        'prazo_18': prazo_18,
        'prazo_17': prazo_17,
        'yoy_prazo': yoy_prazo,
        'dist_prazo': dist_prazo,
        'nps_18': nps_18,
        'nps_17': nps_17,
        'yoy_nps': yoy_nps,
        'dist_nps': dist_nps,
        'tx_18': tx_18,
        'tx_17': tx_17,
        'yoy_tx': yoy_tx,
        'dist_tx': dist_tx,
    }

