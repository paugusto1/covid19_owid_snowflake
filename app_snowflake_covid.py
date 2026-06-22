"""
APP STREAMLIT + SNOWFLAKE - DASHBOARD COVID-19 (TOP 10 POPULOUS COUNTRIES)
Visualização de dados OWID diretamente do Snowflake Cloud Data Warehouse
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import snowflake.connector
from datetime import datetime

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="COVID-19 Top 10 Populous Nations",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS para melhorar o visual
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        font-weight: bold;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .kpi-title {
        font-size: 0.9rem;
        color: #6B7280;
        font-weight: 500;
        text-transform: uppercase;
    }
    .kpi-value {
        font-size: 1.8rem;
        color: #1E3A8A;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNÇÕES DE CONEXÃO E LEITURA DO BANCO DE DADOS
# ============================================================================

@st.cache_resource
def get_snowflake_connection():
    """Retorna uma conexão bruta com o Snowflake usando secrets.toml"""
    return snowflake.connector.connect(
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        account=st.secrets["snowflake"]["account"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"]["role"],
        ocsp_fail_open=True  # Essencial para contornar problemas de firewall/validação OCSP
    )

@st.cache_data(ttl=300)
def load_all_data_from_snowflake():
    """Busca a série histórica completa de COVID19_OWID_SNOWFLAKE no Snowflake"""
    conn = get_snowflake_connection()
    cur = conn.cursor()
    try:
        cur.execute("USE DATABASE COVID19_DB")
        cur.execute("USE SCHEMA PUBLIC")
        cur.execute("SELECT * FROM COVID19_OWID_SNOWFLAKE ORDER BY DATE ASC")
        df = cur.fetch_pandas_all()
        
        # Converter coluna DATE para datetime e ordenar
        df['DATE'] = pd.to_datetime(df['DATE'])
        return df
    finally:
        cur.close()

# ============================================================================
# TÍTULO E SUBTÍTULO
# ============================================================================

st.markdown('<div class="main-header">🦠 Painel COVID-19: Top 10 Nações Mais Populosas</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Análise Analítica de Impacto e Vacinação (2020-2023) consumindo diretamente do Snowflake Data Warehouse</div>', unsafe_allow_html=True)

# ============================================================================
# CONEXÃO E CARGA DE DADOS
# ============================================================================

try:
    with st.spinner("Conectando ao Snowflake e carregando base de dados de alto desempenho..."):
        df_raw = load_all_data_from_snowflake()
except Exception as e:
    st.error(f"❌ Falha ao carregar dados do Snowflake: {str(e)}")
    st.info("Verifique se as tabelas foram criadas rodando `python main.py` primeiro ou clicando em Sincronizar.")
    st.stop()

# ============================================================================
# SIDEBAR - CONTROLE E FILTRO INTERATIVO (OBRIGATÓRIO)
# ============================================================================

with st.sidebar:
    st.header("⚙️ Filtros e Ajustes")
    
    # 1. FILTRO INTERATIVO OBRIGATÓRIO (Seleção de Países)
    all_countries = sorted(list(df_raw['LOCATION'].unique()))
    selected_countries = st.multiselect(
        "Selecione os Países para Análise:",
        options=all_countries,
        default=all_countries,
        help="Escolha um ou mais países. O painel e os gráficos serão recalculados automaticamente."
    )
    
    # Filtro adicional de período opcional
    st.subheader("🗓️ Filtro de Período")
    min_date = df_raw['DATE'].min().to_pydatetime()
    max_date = df_raw['DATE'].max().to_pydatetime()
    
    selected_period = st.slider(
        "Selecione o Período Temporal:",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )
    
    st.markdown("---")
    st.markdown("### ℹ️ Informações da Conexão")
    st.success("✅ Conectado ao Snowflake Cloud!")
    st.caption(f"Última consulta realizada às {datetime.now().strftime('%H:%M:%S')}")

# ============================================================================
# PROCESSAMENTO DOS DADOS FILTRADOS
# ============================================================================

if not selected_countries:
    st.warning("⚠️ Por favor, selecione pelo menos um país na barra lateral para carregar os gráficos.")
    st.stop()

# Aplicando os filtros do usuário
df_filtered = df_raw[
    (df_raw['LOCATION'].isin(selected_countries)) &
    (df_raw['DATE'] >= selected_period[0]) &
    (df_raw['DATE'] <= selected_period[1])
]

# ============================================================================
# SEÇÃO DE 3 KPIS OBRIGATÓRIOS (st.metric)
# ============================================================================

# Calculando os valores máximos cumulativos por país selecionado no período selecionado
df_kpis = df_filtered.groupby('LOCATION').agg({
    'TOTAL_CASES': 'max',
    'TOTAL_DEATHS': 'max',
    'PEOPLE_VACCINATED': 'max'
}).reset_index()

total_cases = df_kpis['TOTAL_CASES'].sum()
total_deaths = df_kpis['TOTAL_DEATHS'].sum()
total_vacc = df_kpis['PEOPLE_VACCINATED'].sum()

st.markdown("### 📌 Métricas Consolidadas do Período Selecionado")
col_kpi1, col_kpi2, col_kpi3 = st.columns(3)

with col_kpi1:
    st.metric(
        label="Total de Casos Confirmados", 
        value=f"{total_cases:,.0f}" if pd.notna(total_cases) else "0"
    )

with col_kpi2:
    st.metric(
        label="Total de Óbitos Confirmados", 
        value=f"{total_deaths:,.0f}" if pd.notna(total_deaths) else "0",
        delta=f"Mortalidade Média: {(total_deaths/total_cases)*100:.2f}%" if total_cases > 0 else "0.00%",
        delta_color="inverse"
    )

with col_kpi3:
    st.metric(
        label="Total de Vacinados (Mín. 1 dose)", 
        value=f"{total_vacc:,.0f}" if pd.notna(total_vacc) else "0"
    )

st.markdown("---")

# ============================================================================
# TABS PRINCIPAIS - DASHBOARD E DADOS BRUTOS
# ============================================================================

tab_dashboard, tab_raw_data = st.tabs([
    "📊 Dashboard Geral (Visualizações)",
    "📂 Dados Brutos & Exportação"
])

# ----------------------------------------------------------------------------
# TAB 1: DASHBOARD GERAL - 4 VISUALIZAÇÕES OBRIGATÓRIAS
# ----------------------------------------------------------------------------
with tab_dashboard:
    
    # Primeira linha de gráficos
    row1_col1, row1_col2 = st.columns(2)
    
    with row1_col1:
        st.subheader("📈 1. Evolução de Novos Casos por País (Linha)")
        # Linha — Evolução de casos novos por país
        fig_line = px.line(
            df_filtered,
            x='DATE',
            y='NEW_CASES',
            color='LOCATION',
            title="Evolução Temporal Diária de Novos Casos",
            labels={'DATE': 'Data', 'NEW_CASES': 'Novos Casos Diários', 'LOCATION': 'País'},
            template='plotly_white'
        )
        st.plotly_chart(fig_line, use_container_width=True)
        
    with row1_col2:
        st.subheader("💀 2. Total de Óbitos por País (Barras)")
        # Barras — Total de óbitos por país
        # Usamos df_kpis para pegar o máximo cumulativo do período por país
        fig_bar = px.bar(
            df_kpis,
            x='LOCATION',
            y='TOTAL_DEATHS',
            color='LOCATION',
            title="Total Acumulado de Óbitos no Período",
            labels={'LOCATION': 'País', 'TOTAL_DEATHS': 'Óbitos Confirmados'},
            text_auto='.3s',
            template='plotly_white'
        )
        fig_bar.update_layout(xaxis={'categoryorder':'total descending'})
        st.plotly_chart(fig_bar, use_container_width=True)
        
    # Segunda linha de gráficos
    row2_col1, row2_col2 = st.columns(2)
    
    with row2_col1:
        st.subheader("💉 3. Proporção de Vacinados - 1 dose (Pizza)")
        # Pizza — Proporção de vacinados (1 dose)
        fig_pie = px.pie(
            df_kpis,
            values='PEOPLE_VACCINATED',
            names='LOCATION',
            title="Distribuição Relativa de Pessoas Vacinadas",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with row2_col2:
        st.subheader("🎯 4. Relação População × Total de Casos (Dispersão)")
        # Dispersão — População × Total de casos
        # Adicionar população máxima no agrupamento para o dispersão
        df_scatter = df_filtered.groupby('LOCATION').agg({
            'POPULATION': 'max',
            'TOTAL_CASES': 'max'
        }).reset_index()
        
        fig_scatter = px.scatter(
            df_scatter,
            x='POPULATION',
            y='TOTAL_CASES',
            size='TOTAL_CASES',
            color='LOCATION',
            hover_name='LOCATION',
            title="Correlação: População Total vs Casos Totais",
            labels={'POPULATION': 'População Total', 'TOTAL_CASES': 'Casos Acumulados'},
            size_max=40,
            template='plotly_white'
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

# ----------------------------------------------------------------------------
# TAB 2: DADOS BRUTOS COM EXPORTAÇÃO CSV OBRIGATÓRIA
# ----------------------------------------------------------------------------
with tab_raw_data:
    st.header("📂 Dados Brutos da Tabela Snowflake")
    st.markdown("Exibição tabular e filtros detalhados dos registros consultados dinamicamente.")
    
    st.write(f"Exibindo dados filtrados: **{len(df_filtered):,} registros** encontrados.")
    st.dataframe(df_filtered, use_container_width=True)
    
    # Botão de exportação obrigatório
    csv_bytes = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="💾 Baixar Dados Filtrados (CSV)",
        data=csv_bytes,
        file_name="covid19_owid_filtered.csv",
        mime="text/csv",
        use_container_width=False
    )
