import streamlit as st
import pandas as pd
import plotly.express as px
from app_tratamento_dados import (
    processar_dados_completos,
    preparar_kpis_ytd,
    preparar_pedidos_logistica,
    preparar_pedidos_com_reviews,
    preparar_regiao_logistica,
    preparar_stats_rota,
)

# ============================================================
# CONFIGURAÇÃO DA PÁGINA E CARREGAMENTO
# ============================================================
st.set_page_config(
    page_title="Dashboard - Eficiência Logística", 
    page_icon="📦", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

#@st.cache_data(show_spinner="Analisando malha logística da Olist...")
def load_data():
    return processar_dados_completos(verbose=False)

df_full, orders, order_items, customers, payments, products, category_translation, reviews, sellers = load_data()

REGIOES_MAP = {
    'AM': 'Norte', 'RR': 'Norte', 'AP': 'Norte', 'PA': 'Norte', 'TO': 'Norte', 'RO': 'Norte', 'AC': 'Norte',
    'MA': 'Nordeste', 'PI': 'Nordeste', 'CE': 'Nordeste', 'RN': 'Nordeste', 'PE': 'Nordeste', 'PB': 'Nordeste', 'SE': 'Nordeste', 'AL': 'Nordeste', 'BA': 'Nordeste',
    'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste', 'GO': 'Centro-Oeste', 'DF': 'Centro-Oeste',
    'SP': 'Sudeste', 'RJ': 'Sudeste', 'ES': 'Sudeste', 'MG': 'Sudeste',
    'PR': 'Sul', 'RS': 'Sul', 'SC': 'Sul'
}

# ============================================================
# BARRA LATERAL (FILTROS ESTRATÉGICOS)
# ============================================================
st.sidebar.image("https://logopng.com.br/logos/olist-125.png", width=150)
st.sidebar.header("🎯 Filtros Estratégicos")

# 1. Período com 2018 como Padrão (AGORA COMO RANGE SLIDER)
periodos_disponiveis = sorted(df_full['ano_mes'].dropna().unique())

# Identificar o primeiro e último mês de 2018 para o intervalo padrão
meses_2018 = [mes for mes in periodos_disponiveis if str(mes).startswith('2018')]
padrao_inicio = meses_2018[0] if meses_2018 else periodos_disponiveis[0]
padrao_fim = meses_2018[-1] if meses_2018 else periodos_disponiveis[-1]

periodo_selecionado = st.sidebar.select_slider(
    "📅 Período (Ano-Mês):", 
    options=periodos_disponiveis,
    value=(padrao_inicio, padrao_fim), # Passar uma tupla cria um slider de duas pontas (Range)
    help="Arraste as pontas para selecionar o intervalo de tempo desejado."
)

estado_selecionado = st.sidebar.multiselect(
    "📍 Estado de Destino (UF):", 
    options=sorted(df_full['customer_state'].dropna().unique())
)

col_categoria = 'product_category_name_english' if 'product_category_name_english' in df_full.columns else 'product_category_name'
categoria_selecionada = st.sidebar.multiselect(
    "📦 Categoria do Produto:", 
    options=sorted(df_full[col_categoria].dropna().unique())
)

# Motor de Filtros (Aplica-se apenas ao corpo do Dash, não ao Cabeçalho)
df_view = df_full.copy()

if periodo_selecionado: 
    mes_inicio, mes_fim = periodo_selecionado
    # Filtra tudo que for maior/igual ao início E menor/igual ao fim
    df_view = df_view[(df_view['ano_mes'] >= mes_inicio) & (df_view['ano_mes'] <= mes_fim)]
    
if estado_selecionado: 
    df_view = df_view[df_view['customer_state'].isin(estado_selecionado)]
if categoria_selecionada: 
    df_view = df_view[df_view[col_categoria].isin(categoria_selecionada)]

st.sidebar.markdown("---")
st.sidebar.markdown("💡 *Os filtros acima modificam apenas os gráficos operacionais de Logística e OKRs, não o Cabeçalho Global.*")

# ============================================================
# CABEÇALHO GLOBAL ESTÁTICO (2018 vs 2017 YTD)
# ============================================================
st.title("📊 Dashboard Executivo - Olist E-commerce")

# NOVO INFORMATIVO CLARO PARA O USUÁRIO
st.info("📌 **Visão YTD (Year-to-Date):** Os indicadores estratégicos abaixo refletem a "
        "operação de **2018** em comparação ao mesmo período de 2017. "
        "Esta é uma fotografia executiva fixa e **não** é alterada pelos filtros laterais.")

st.markdown("---")

# 1. Isolar 2018 e achar o limite de meses (YTD) EXCLUSIVAMENTE na BASE TRATADA (df_full)
df_full_18 = df_full[df_full['order_purchase_timestamp'].dt.year == 2018].copy()
mes_maximo = df_full_18['order_purchase_timestamp'].dt.month.max()

# Isolar 2017 YTD na base tratada
df_full_17_ytd = df_full[(df_full['order_purchase_timestamp'].dt.year == 2017) & 
                         (df_full['order_purchase_timestamp'].dt.month <= mes_maximo)].copy()

# GARANTIA DE DADOS TRATADOS: Extrair as chaves (order_id) válidas
valid_orders_18 = df_full_18['order_id'].unique()
valid_orders_17 = df_full_17_ytd['order_id'].unique()

kpis = preparar_kpis_ytd(df_full, orders, reviews)

rev_18 = kpis['rev_18']
rev_17 = kpis['rev_17']
yoy_rev = kpis['yoy_rev']
dist_rev = kpis['dist_rev']

ped_18 = kpis['ped_18']
ped_17 = kpis['ped_17']
yoy_ped = kpis['yoy_ped']
dist_ped = kpis['dist_ped']

prazo_18 = kpis['prazo_18']
prazo_17 = kpis['prazo_17']
yoy_prazo = kpis['yoy_prazo']
dist_prazo = kpis['dist_prazo']

nps_18 = kpis['nps_18']
nps_17 = kpis['nps_17']
yoy_nps = kpis['yoy_nps']
dist_nps = kpis['dist_nps']

tx_18 = kpis['tx_18']
tx_17 = kpis['tx_17']
yoy_tx = kpis['yoy_tx']
dist_tx = kpis['dist_tx']

# 3. Nova Função de UI Executiva: Criar Cards Consistentes (Agora aceita formatação customizada)
def kpi_card(title, value, yoy_val, yoy_text, dist_val, dist_text, meta_label, is_inverse=False):
    # Regra de cor para o YoY (Crescimento)
    if yoy_val > 0:
        yoy_color = "#ff4b4b" if is_inverse else "#09ab3b"
        yoy_arrow = "▲"
    elif yoy_val < 0:
        yoy_color = "#09ab3b" if is_inverse else "#ff4b4b"
        yoy_arrow = "▼"
    else:
        yoy_color = "#888888"
        yoy_arrow = "➖"

    # Regra de cor para a Distância da Meta
    if dist_val > 0:
        dist_color = "#ff4b4b" if is_inverse else "#09ab3b"
        dist_sinal = "+"
    elif dist_val < 0:
        dist_color = "#09ab3b" if is_inverse else "#ff4b4b"
        dist_sinal = ""
    else:
        dist_color = "#888888"
        dist_sinal = ""

    html = f"""
    <div style="background-color: #ffffff; border: 1px solid #e6e6e6; border-radius: 10px; padding: 18px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <div style="font-size: 13px; font-weight: 700; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">{title}</div>
        <div style="font-size: 28px; font-weight: 900; color: #111; margin: 8px 0;">{value}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; margin-top: 15px; border-top: 1px solid #f0f0f0; padding-top: 12px;">
            <div style="color: {yoy_color}; font-weight: 700; background-color: {yoy_color}1A; padding: 3px 6px; border-radius: 4px;">{yoy_arrow} {yoy_text} (vs 2017)</div>
            <div style="color: {dist_color}; font-weight: 600;">🎯 {dist_sinal}{dist_text} ({meta_label})</div>
        </div>
    </div>
    """
    return html

# 4. Exibição dos KPIs Refatorada com Arredondamento nos Dias
col1, col2, col3, col4, col5 = st.columns(5)
with col1: 
    st.markdown(kpi_card("💰 Receita (YTD)", f"R$ {rev_18:.1f}M", yoy_rev, f"{abs(yoy_rev):.1f}%", dist_rev, f"{dist_rev:.1f}M", "Alvo: 8M"), unsafe_allow_html=True)
with col2: 
    st.markdown(kpi_card("📦 Pedidos (YTD)", f"{ped_18:,}", yoy_ped, f"{abs(yoy_ped):.1f}%", dist_ped, f"{int(dist_ped):,}", "Alvo: 60k"), unsafe_allow_html=True)
with col3: 
    # AQUI ESTÁ A MÁGICA: Transformamos o prazo médio em um número inteiro (round)
    st.markdown(kpi_card("🚚 Prazo Médio", f"{int(round(prazo_18))}d", yoy_prazo, f"{abs(yoy_prazo):.0f}d", dist_prazo, f"{dist_prazo:.0f}d", "Meta: 10d", is_inverse=True), unsafe_allow_html=True)
with col4: 
    st.markdown(kpi_card("⭐ Satisfação", f"{nps_18:.2f}", yoy_nps, f"{abs(yoy_nps):.2f}", dist_nps, f"{dist_nps:.2f}", "Meta: 4.50"), unsafe_allow_html=True)
with col5: 
    st.markdown(kpi_card("🔄 Taxa Recompra", f"{tx_18:.1f}%", yoy_tx, f"{abs(yoy_tx):.1f}pp", dist_tx, f"{dist_tx:.1f}%", "Meta: 5%"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ============================================================
# OKR 1: LOGÍSTICA E SLA (DINÂMICO PELOS FILTROS)
# ============================================================
st.header("🎯 OKR Dinâmico: Eficiência Logística e SLA")
st.markdown("Diagnóstico profundo dos gargalos operacionais e seu impacto direto na retenção. *Os dados abaixo respondem aos filtros da barra lateral.*")

# Preparação de Dados Logísticos Centralizada usando df_view (Filtros ativos)
pedidos_logistica, pct_falha, falha_rastreio, jornada_perfeita_inicial = preparar_pedidos_logistica(df_view, orders)

# --- VISÃO 1: JORNADA EMPILHADA E QUALIDADE DE DADOS ---
st.subheader("⏱️ 1. Jornada do Pedido e Auditoria de Telemetria")

# Calcular tempos apenas com dados válidos
avg_aprovacao = pedidos_logistica['tempo_aprovacao'].mean()
avg_postagem = pedidos_logistica['tempo_postagem'].mean()
avg_transporte = pedidos_logistica['tempo_transporte'].mean()
lead_time_perfeito = avg_aprovacao + avg_postagem + avg_transporte

# TRAVA DE SEGURANÇA CONTRA NaN: Protege o título se os filtros zerarem os dados
tempo_titulo = f"{int(round(lead_time_perfeito))} dias" if pd.notnull(lead_time_perfeito) else "0 dias (Sem dados)"

df_jornada = pd.DataFrame({
    'Etapa': ['1. Aprovação', '2. Separação', '3. Transporte'],
    'Dias': [avg_aprovacao, avg_postagem, avg_transporte],
    'Jornada': 'Tempo Médio' 
})

# 3. Renderizar o Gráfico
fig_jornada = px.bar(
    df_jornada, x='Dias', y='Jornada', color='Etapa', orientation='h', 
    text=df_jornada['Dias'].apply(lambda x: f"{int(round(x))}d" if pd.notnull(x) else "0d"), 
    title=f"Lead Time Auditado (Rastreio Completo): {tempo_titulo}", # <-- Variável protegida aplicada aqui
    color_discrete_map={'1. Aprovação': '#00CC96', '2. Separação': '#FDB328', '3. Transporte': '#EF553B'}
)
fig_jornada.update_traces(textposition='inside', textfont=dict(size=14, color='white', family='Arial Black'), insidetextanchor='middle')
fig_jornada.update_layout(
    barmode='stack', 
    xaxis_title="Dias Decorridos", 
    yaxis_title="", 
    showlegend=True, 
    height=280, 
    margin=dict(t=40, b=0, l=0, r=0),
    template='plotly_white',
    font=dict(family="Arial, sans-serif", size=11)
)
fig_jornada.update_yaxes(showticklabels=False)

st.plotly_chart(fig_jornada, use_container_width=True)

# 4. O Alerta Executivo (O seu insight de Engenharia de Dados)
if pct_falha > 0.5:
    st.warning(f"⚠️ **Auditoria de Telemetria:** {pct_falha:.2f}% dos pedidos ({int(falha_rastreio):,}) apresentam sequência temporal invertida - possível falha na atualização de status de rastreio. Estes registros foram excluídos desta análise de SLA.")
else:
    st.success(f"✅ **Qualidade de Dados:** {pct_falha:.2f}% de falhas de telemetria detectadas. Base limpa e confiável para análise de SLA.")

# --- VISÃO 2: ATRASO vs AVALIAÇÃO (SCATTER + DISTRIBUIÇÃO) ---
st.subheader("⭐ 2. Correlação: Atrasos Logísticos vs Satisfação (Churn)")
st.markdown("Como a quebra da promessa de entrega destrói a experiência do cliente e dispara o risco de evasão.")

# Preparar dados para análise de atraso
pedidos_com_reviews, sla_metrics = preparar_pedidos_com_reviews(pedidos_logistica, reviews)

# ==========================================
# TRAVA DE SEGURANÇA CONTRA DATAFRAME VAZIO
# ==========================================
if sla_metrics.empty:
    st.warning("⚠️ Não há avaliações suficientes com os filtros selecionados para cruzar os dados de Churn e Satisfação.")
else:
    # Criar dois gráficos complementares e diretos se houver dados
    col1, col2 = st.columns(2)

    cores_map = {
        '1. No Prazo/Adiantado': '#00CC96',
        '2. Atraso Leve (1-3d)': '#FDB328',
        '3. Atraso Moderado (4-7d)': '#FF6B6B',
        '4. Atraso Crítico (>7d)': '#8B0000'
    }

    with col1:
        fig_nps = px.bar(
            sla_metrics, x='Status SLA', y='nota_media', color='Status SLA',
            title="📉 Queda da Satisfação por Atraso",
            text=sla_metrics['nota_media'].apply(lambda x: f"{x:.2f} ⭐"),
            color_discrete_map=cores_map
        )
        fig_nps.update_traces(textposition='outside', textfont=dict(size=14, family='Arial Black'))
        fig_nps.update_layout(
            yaxis=dict(range=[0, 5.5], title='Nota Média (1 a 5)'), 
            xaxis_title="", showlegend=False, height=350, margin=dict(t=50, b=0, l=0, r=0),
            template='plotly_white'
        )
        st.plotly_chart(fig_nps, use_container_width=True)

    with col2:
        # Cálculo seguro do limite do eixo Y (usando função do Pandas)
        max_churn = sla_metrics['Taxa de Churn (%)'].max()
        limite_eixo_y = max_churn * 1.3 if pd.notnull(max_churn) and max_churn > 0 else 100

        fig_churn = px.bar(
            sla_metrics, x='Status SLA', y='Taxa de Churn (%)',
            title="🚨 Explosão do Risco de Churn (Notas 1)",
            text=sla_metrics['Taxa de Churn (%)'].apply(lambda x: f"{x:.1f}%")
        )
        # Pintar o gráfico de Churn com um vermelho alerta unificado
        fig_churn.update_traces(marker_color='#8B0000', textposition='outside', textfont=dict(size=14, family='Arial Black'))
        fig_churn.update_layout(
            yaxis=dict(title='% de Clientes Detratores', range=[0, limite_eixo_y]), 
            xaxis_title="", showlegend=False, height=350, margin=dict(t=50, b=0, l=0, r=0),
            template='plotly_white'
        )
        st.plotly_chart(fig_churn, use_container_width=True)

st.info("💡 **Insight Estratégico:** O gráfico direito escancara o verdadeiro custo do atraso logístico. Quando o pedido entra na zona de 'Atraso Crítico', a taxa de clientes que avaliam a loja com a nota mínima dispara vertiginosamente, sinalizando a perda definitiva do LTV (Lifetime Value) daquele consumidor.")

# --- VISÃO 3: MATRIZ ESTRATÉGICA DE LOGÍSTICA ---
st.subheader("🗺️ 3. Matriz Estratégica: Custo vs Prazo")
st.markdown("Classificação direta das macro-regiões em quadrantes de eficiência operacional baseada na média nacional.")

# TRAVA DE SEGURANÇA: Se o filtro zerar os dados, esconde o gráfico elegantemente
if pedidos_logistica.empty:
    st.warning("⚠️ Não há dados suficientes com os filtros selecionados para gerar o mapa de desempenho por região.")
else:
    regiao_logistica, media_prazo_global, media_frete_global = preparar_regiao_logistica(pedidos_com_reviews, order_items, sellers, REGIOES_MAP)
    
    # Criar uma "folga" no gráfico para as bolhas não encostarem na borda
    max_prazo = max(regiao_logistica['Prazo_Medio'].max(), media_prazo_global) * 1.15
    max_frete = max(regiao_logistica['Frete_Medio'].max(), media_frete_global) * 1.15

    # === GRÁFICO DE DISPERSÃO (COM FUNDOS COLORIDOS OBJETIVOS) ===
    fig_frete = px.scatter(
        regiao_logistica, 
        x='Prazo_Medio', 
        y='Frete_Medio', 
        size='Volume_Pedidos',
        color='Regiao',
        text='Regiao',
        labels={'Prazo_Medio': 'Prazo de Entrega (Dias)', 'Frete_Medio': 'Custo de Frete (R$)'},
        size_max=45,
        color_discrete_sequence=px.colors.qualitative.Dark24
    )

    # Desenhar os Quadrantes Coloridos (Estratégia Visual Objetiva)
    # 1. Verde (Ideal: Abaixo da média de prazo e frete)
    fig_frete.add_shape(type="rect", x0=0, y0=0, x1=media_prazo_global, y1=media_frete_global, fillcolor="#d4edda", opacity=0.5, layer="below", line_width=0)
    # 2. Vermelho (Crítico: Acima da média de prazo e frete)
    fig_frete.add_shape(type="rect", x0=media_prazo_global, y0=media_frete_global, x1=max_prazo, y1=max_frete, fillcolor="#f8d7da", opacity=0.5, layer="below", line_width=0)
    # 3. Amarelos (Atenção: Premium ou Econômico)
    fig_frete.add_shape(type="rect", x0=0, y0=media_frete_global, x1=media_prazo_global, y1=max_frete, fillcolor="#fff3cd", opacity=0.5, layer="below", line_width=0)
    fig_frete.add_shape(type="rect", x0=media_prazo_global, y0=0, x1=max_prazo, y1=media_frete_global, fillcolor="#fff3cd", opacity=0.5, layer="below", line_width=0)

    # Injetar os Nomes de Cada Quadrante direto no fundo
    fig_frete.add_annotation(x=media_prazo_global/2, y=media_frete_global/2, text="IDEAL<br>Rápido e Barato", showarrow=False, font=dict(color="#155724", size=16, family="Arial Black"), opacity=0.3)
    fig_frete.add_annotation(x=media_prazo_global + (max_prazo-media_prazo_global)/2, y=media_frete_global + (max_frete-media_frete_global)/2, text="CRÍTICO<br>Lento e Caro", showarrow=False, font=dict(color="#721c24", size=16, family="Arial Black"), opacity=0.3)
    fig_frete.add_annotation(x=media_prazo_global/2, y=media_frete_global + (max_frete-media_frete_global)/2, text="PREMIUM<br>Rápido e Caro", showarrow=False, font=dict(color="#856404", size=16, family="Arial Black"), opacity=0.3)
    fig_frete.add_annotation(x=media_prazo_global + (max_prazo-media_prazo_global)/2, y=media_frete_global/2, text="ECONÔMICO<br>Lento e Barato", showarrow=False, font=dict(color="#856404", size=16, family="Arial Black"), opacity=0.3)

    # Ajustes finais dos rótulos
    fig_frete.update_traces(
        textposition='top center', 
        textfont=dict(size=13, family='Arial Black', color='#111'),
        hovertemplate='<b>%{text}</b><br>Frete Médio: R$ %{y:.2f}<br>Prazo Médio: %{x:.1f} dias<br>Satisfação: %{customdata:.2f} ⭐<extra></extra>',
        customdata=regiao_logistica['Review_Score']
    )

    # Remover linhas de grade para não poluir os quadrantes
    fig_frete.update_layout(
        template='plotly_white', height=550, showlegend=False,
        xaxis=dict(range=[0, max_prazo], showgrid=False, zeroline=False),
        yaxis=dict(range=[0, max_frete], showgrid=False, zeroline=False),
        margin=dict(t=30, b=20, l=20, r=20), font=dict(family="Arial, sans-serif")
    )
    
    st.plotly_chart(fig_frete, use_container_width=True)

    # === CARDS COLORIDOS DE AVALIAÇÃO E LOGÍSTICA ===
    st.markdown("**Termômetro de Satisfação e Custos por Região:**")
    
    regiao_cards = regiao_logistica.sort_values('Review_Score', ascending=False)
    regiao_cols = st.columns(len(regiao_cards))

    for idx, (index, row) in enumerate(regiao_cards.iterrows()):
        with regiao_cols[idx]:
            if row['Review_Score'] >= 4.15:
                emoji_status = "🟢 Excelente"
                bg_color = "#d4edda"      
                text_color = "#155724"    
            elif row['Review_Score'] >= 4.0:
                emoji_status = "🟡 Bom"
                bg_color = "#fff3cd"      
                text_color = "#856404"    
            else:
                emoji_status = "🔴 Crítico"
                bg_color = "#f8d7da"      
                text_color = "#721c24"    
            
            st.markdown(f"""
            <div style='background-color: {bg_color}; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid {text_color}40; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                <h4 style='margin: 0 0 10px 0; color: {text_color};'>{row['Regiao']}</h4>
                <p style='margin: 5px 0; font-size: 20px; font-weight: 900; color: {text_color};'>{row['Review_Score']:.2f} ⭐</p>
                <small style='color: {text_color}; font-weight: 700;'>{emoji_status}</small>
                <hr style='margin: 12px 0; border: 0; border-top: 1px solid {text_color}40;'>
                <div style='font-size: 13px; color: {text_color}; text-align: left; padding-left: 10px;'>
                    <p style='margin: 3px 0;'><b>🚚 Frete:</b> R$ {row['Frete_Medio']:,.2f}</p>
                    <p style='margin: 3px 0;'><b>⏱️ Prazo:</b> {int(round(row['Prazo_Medio']))} dias</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# VISÃO: IMPACTO E PERCENTUAL DE ATRASO POR ROTA
# ============================================================
st.header("📊 Diagnóstico Detalhado de riscos")

# Cálculo para o Alerta de Risco
vendedor_lento_entrega_ok = pedidos_logistica[
    (pedidos_logistica['tempo_postagem'] > 3.0) & 
    (pedidos_logistica['order_delivered_customer_date'] <= pedidos_logistica['order_estimated_delivery_date'])
]

st.markdown("---")
st.subheader("⚠️ Alerta de Eficiência: O Risco Invisível")
col_risco1, col_risco2 = st.columns(2)

with col_risco1:
    st.metric("Vendedor Lento (Entrega no Prazo)", f"{len(vendedor_lento_entrega_ok):,} ped.")
    st.caption("Pedidos onde a transportadora salvou o prazo do lojista.")

with col_risco2:
    pct_risco = (len(vendedor_lento_entrega_ok) / len(pedidos_logistica)) * 100
    st.metric("Exposição ao Risco", f"{pct_risco:.1f}%", help="Percentual de pedidos que quase atrasaram por culpa do vendedor.")

st.warning("💡 **Insight de Risco:** 27.4% da nossa operação depende da transportadora compensar a lentidão do lojista. Se houver qualquer greve ou problema na malha, todos esses pedidos se tornam atrasos críticos imediatamente.")

# 3. Top 5 Rotas com Maior % de Atraso
st.markdown("---")
st.subheader("🚨 Top 5 Rotas Críticas (% de Atraso)")

stats_rota = preparar_stats_rota(pedidos_logistica, order_items, sellers)

# Filtrar rotas com volume mínimo (>50 pedidos) para relevância estatística
top_5_percentual = stats_rota[stats_rota['total'] > 50].nlargest(5, '% Atraso')

fig_pct = px.bar(
    top_5_percentual, x='Rota', y='% Atraso',
    title="Rotas com Maior Probabilidade de Atraso",
    text=top_5_percentual['% Atraso'].apply(lambda x: f"{x:.1f}%"),
    color_discrete_sequence=['#8B0000']
)
fig_pct.update_layout(yaxis_title="% de Pedidos Fora do SLA", template='plotly_white')
st.plotly_chart(fig_pct, use_container_width=True)

# ============================================================
# VISÃO 6: ROADMAP ESTRATÉGICO (BENCHMARK MALI/SHOPEE)
# ============================================================
st.markdown("---")
st.header("🚀 Roadmap Estratégico: O Caminho para a Logística 2.0")
st.markdown("Baseado nos diagnósticos anteriores e nos modelos de sucesso do **Mercado Livre** e **Shopee**, "
            "listamos as ações prioritárias para ganho de escala e redução de Churn.")

rec_col1, rec_col2 = st.columns(2)

with rec_col1:
    st.subheader("📦 Operação & Infraestrutura")
    st.info("""
    **1. Implementação de Hubs Regionalizados (Fulfillment):**
    * **Ação:** Criar Centros de Distribuição nas rotas identificadas como 'Críticas' (Norte/Nordeste).
    * **Impacto:** Redução imediata de 40% no Lead Time ao assumir a custódia do estoque.
    
    **2. Pontos de Coleta Colaborativos (Last-Mile):**
    * **Ação:** Estabelecer comércios locais como pontos de drop-off para vendedores.
    * **Impacto:** Agilidade na coleta (First-Mile) e redução de custos logísticos para pequenos lojistas.
    """)

with rec_col2:
    st.subheader("⚙️ Tecnologia & Governança")
    st.success("""
    **3. Gamificação e Ranking de Sellers:**
    * **Ação:** Criar selos de 'Envio Rápido' (<24h). Lojistas lentos perdem relevância na busca.
    * **Impacto:** Estímulo à eficiência na origem e proteção do NPS da plataforma.
    
    **4. SLA Dinâmico e Proatividade no CRM:**
    * **Ação:** Integrar o Simulador de Risco ao checkout para ajustar prazos em tempo real.
    * **Impacto:** Gestão honesta de expectativa e redução de avaliações Nota 1 (Detratores).
    """)

# Tabela de Priorização Executiva
st.markdown("### 📊 Matriz de Priorização das Recomendações")
data_rec = {
    "Recomendação": ["Fulfillment (CD Nordeste)", "Simulador de Risco", "Gamificação de Sellers", "SLA de Telemetria"],
    "Esforço": ["Alto", "Médio", "Baixo", "Médio"],
    "Impacto no LTV": ["Altíssimo", "Alto", "Alto", "Médio"],
    "Referência": ["Mercado Livre", "Inovação Interna", "Shopee", "Padrão de Mercado"]
}
st.table(pd.DataFrame(data_rec))