"""
APP STREAMLIT + SNOWFLAKE - DASHBOARD COVID-19 (TOP 10 POPULOUS COUNTRIES)
Visualização de dados OWID diretamente do Snowflake Cloud Data Warehouse
Desenvolvido por Pedro Augusto Vicente para a disciplina Aplicações em Data Science (Turma 3)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from datetime import datetime
import re

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
        margin-bottom: 0.5rem;
    }
    .academic-header {
        font-size: 0.95rem;
        color: #2563EB;
        font-weight: 500;
        margin-bottom: 1.5rem;
        background-color: #EFF6FF;
        padding: 0.4rem 1rem;
        border-radius: 4px;
        border-left: 4px solid #2563EB;
        display: inline-block;
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
    .footer {
        font-size: 0.85rem;
        color: #6B7280;
        text-align: center;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #E5E7EB;
    }
    .source-card {
        background-color: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 1rem;
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
        df['DATE'] = pd.to_datetime(df['DATE'])
        return df
    finally:
        cur.close()

def clean_column_names(df):
    """Limpa e formata os nomes das colunas para compatibilidade ideal com o Snowflake"""
    df_cleaned = df.copy()
    new_cols = []
    for col in df_cleaned.columns:
        cleaned = re.sub(r'[^a-zA-Z0-9]', '_', col.upper())
        cleaned = re.sub(r'_+', '_', cleaned).strip('_')
        new_cols.append(cleaned)
    df_cleaned.columns = new_cols
    return df_cleaned

def upload_custom_df_to_snowflake(df):
    """Faz o upload de um DataFrame customizado para o Snowflake"""
    conn = get_snowflake_connection()
    try:
        cur = conn.cursor()
        cur.execute("CREATE DATABASE IF NOT EXISTS COVID19_DB")
        cur.execute("USE DATABASE COVID19_DB")
        cur.execute("CREATE SCHEMA IF NOT EXISTS PUBLIC")
        cur.execute("USE SCHEMA PUBLIC")
        cur.close()
        
        df_clean = clean_column_names(df)
        success, nchunks, nrows, _ = write_pandas(
            conn=conn,
            df=df_clean,
            table_name="COVID19_OWID_SNOWFLAKE",
            database="COVID19_DB",
            schema="PUBLIC",
            auto_create_table=True,
            overwrite=True
        )
        return success, nrows
    except Exception as e:
        return False, str(e)

# ============================================================================
# TÍTULO, SUBTÍTULO E CRÉDITO ACADÊMICO
# ============================================================================

st.markdown('<div class="main-header">🦠 Painel COVID-19: Top 10 Nações Mais Populosas</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Análise Analítica de Impacto e Vacinação (2020-2023) consumindo diretamente do Snowflake Data Warehouse</div>', unsafe_allow_html=True)
st.markdown('<div class="academic-header">🎓 Desenvolvido por: <b>Pedro Augusto Vicente</b> | Disciplina: <i>Aplicações em Data Science (Turma 3)</i></div>', unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - CONTROLE E FILTROS
# ============================================================================

# Inicializar estados da sessão para controle do upload por CSV
if 'data_source' not in st.session_state:
    st.session_state['data_source'] = "❄️ Snowflake (Padrão)"
if 'uploaded_df' not in st.session_state:
    st.session_state['uploaded_df'] = None

with st.sidebar:
    st.header("⚙️ Configurações & Origem")
    
    # Seletor de Origem de Dados (O Default é Snowflake)
    st.markdown('<div class="source-card">', unsafe_allow_html=True)
    st.markdown("### 🗃️ Origem dos Dados")
    origem_selecionada = st.radio(
        "Selecione de onde obter os dados:",
        options=["❄️ Snowflake (Padrão)", "📂 CSV Carregado pelo Usuário"],
        index=0,
        help="O Snowflake é a base corporativa oficial. Caso faça upload de um CSV, você pode alternar para visualizá-lo."
    )
    st.session_state['data_source'] = origem_selecionada
    st.markdown('</div>', unsafe_allow_html=True)

    # 1. FILTRO INTERATIVO OBRIGATÓRIO (Será preenchido dinamicamente)
    st.subheader("🎯 Filtrar Dashboard")
    placeholder_filtro_paises = st.empty()
    placeholder_filtro_periodo = st.empty()
    
    # Informações Acadêmicas no Sidebar
    st.markdown("---")
    st.markdown("""
    **📚 Autoria & Acadêmico:**
    - **Autor:** Pedro Augusto Vicente
    - **Curso:** Aplicações em Data Science
    - **Turma:** Turma 3
    """)
    
    st.markdown("---")
    st.markdown("### ℹ️ Informações da Conexão")
    st.success("✅ Conectado ao Snowflake Cloud!")
    st.caption(f"Sessão ativa às {datetime.now().strftime('%H:%M:%S')}")

# ============================================================================
# CARGA DE DADOS COM BASE NA ORIGEM ESCOLHIDA (DEFAULT = SNOWFLAKE)
# ============================================================================

df_raw = None

if st.session_state['data_source'] == "❄️ Snowflake (Padrão)":
    try:
        df_raw = load_all_data_from_snowflake()
    except Exception as e:
        st.error(f"❌ Falha ao carregar dados do Snowflake: {str(e)}")
        st.info("Verifique se as tabelas foram criadas rodando `python main.py` primeiro ou utilize a aba de Upload.")
        st.stop()
else:
    # Se selecionado CSV mas nenhum arquivo foi carregado ainda
    if st.session_state['uploaded_df'] is None:
        st.warning("⚠️ Nenhum CSV foi carregado ainda! Por favor, vá na aba **📤 Upload de CSV** e faça o upload do seu arquivo.")
        st.info("Alternando temporariamente para a base padrão do Snowflake...")
        try:
            df_raw = load_all_data_from_snowflake()
            st.session_state['data_source'] = "❄️ Snowflake (Padrão)"
        except Exception:
            st.stop()
    else:
        df_raw = st.session_state['uploaded_df']

# ============================================================================
# POPULAR FILTROS DINÂMICOS NA SIDEBAR
# ============================================================================

all_countries = sorted(list(df_raw['LOCATION'].unique()))
selected_countries = placeholder_filtro_paises.multiselect(
    "Selecione os Países para Análise:",
    options=all_countries,
    default=all_countries,
    key="countries_multiselect"
)

min_date = df_raw['DATE'].min().to_pydatetime()
max_date = df_raw['DATE'].max().to_pydatetime()

selected_period = placeholder_filtro_periodo.slider(
    "Selecione o Período Temporal:",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),
    format="YYYY-MM-DD",
    key="period_slider"
)

# Aplicando os filtros do usuário
if not selected_countries:
    st.warning("⚠️ Por favor, selecione pelo menos um país na barra lateral para carregar os gráficos.")
    st.stop()

df_filtered = df_raw[
    (df_raw['LOCATION'].isin(selected_countries)) &
    (df_raw['DATE'] >= selected_period[0]) &
    (df_raw['DATE'] <= selected_period[1])
]

# ============================================================================
# SEÇÃO DE 3 KPIS OBRIGATÓRIOS (st.metric)
# ============================================================================

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
# TABS PRINCIPAIS - DASHBOARD, UPLOAD, DADOS BRUTOS
# ============================================================================

tab_dashboard, tab_upload, tab_raw_data = st.tabs([
    "📊 Dashboard Geral (Visualizações)",
    "📤 Upload de CSV & Sincronização",
    "📂 Dados Brutos & Exportação"
])

# ----------------------------------------------------------------------------
# TAB 1: DASHBOARD GERAL - 4 VISUALIZAÇÕES OBRIGATÓRIAS
# ----------------------------------------------------------------------------
with tab_dashboard:
    st.write(f"ℹ️ Mostrando dados de: **{st.session_state['data_source']}**")
    
    # Primeira linha de gráficos
    row1_col1, row1_col2 = st.columns(2)
    
    with row1_col1:
        st.subheader("📈 1. Evolução de Novos Casos por País (Linha)")
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
# TAB 2: UPLOAD DE CSV & SINCRONIZAÇÃO (NOVO REQUISITO)
# ----------------------------------------------------------------------------
with tab_upload:
    st.header("📤 Carregar Dados COVID-19 por CSV")
    st.markdown("""
    Aqui você pode carregar seu próprio arquivo CSV com dados estruturados.
    O CSV deve conter colunas equivalentes ao formato OWID (`location`, `date`, `new_cases`, `total_cases`, `total_deaths`, `people_vaccinated`, `population`).
    """)
    
    uploaded_file = st.file_uploader(
        "Selecione um arquivo CSV de dados COVID-19:",
        type=["csv"],
        help="Envie um arquivo CSV de até 200MB."
    )
    
    if uploaded_file is not None:
        try:
            # Ler o CSV do usuário
            df_uploaded_raw = pd.read_csv(uploaded_file)
            
            # Limpar nomes das colunas e garantir compatibilidade uppercase
            df_uploaded_clean = clean_column_names(df_uploaded_raw)
            
            # Garantir formato correto das colunas vitais
            if 'DATE' in df_uploaded_clean.columns:
                df_uploaded_clean['DATE'] = pd.to_datetime(df_uploaded_clean['DATE'])
            else:
                st.error("❌ O arquivo enviado precisa conter uma coluna 'date'.")
                st.stop()
                
            # Salvar no session_state para persistência
            st.session_state['uploaded_df'] = df_uploaded_clean
            st.success(f"✅ CSV carregado com sucesso! Contém **{df_uploaded_clean.shape[0]:,} linhas** e **{df_uploaded_clean.shape[1]:,} colunas**.")
            
            # Exibir prévia
            st.subheader("👀 Prévia dos Dados Enviados")
            st.dataframe(df_uploaded_clean.head(10), use_container_width=True)
            
            # Dar a opção de usar esses dados
            st.info("💡 Para visualizar este arquivo nos gráficos, selecione a opção **'📂 CSV Carregado pelo Usuário'** no menu lateral à esquerda.")
            
            st.markdown("---")
            st.subheader("❄️ Sincronizar este CSV enviado diretamente no Snowflake")
            st.markdown("Se desejar, você pode sobrescrever o banco de dados oficial no Snowflake com o seu novo CSV!")
            
            if st.button("🚀 Sobrescrever base do Snowflake com este CSV", use_container_width=True):
                with st.spinner("Conectando e enviando dados para o Snowflake..."):
                    success, message_or_rows = upload_custom_df_to_snowflake(df_uploaded_clean)
                    if success:
                        st.success(f"✅ Sucesso! Sobrescreveu a tabela com {message_or_rows} linhas do seu CSV!")
                        st.balloons()
                        # Atualizar cache
                        st.cache_data.clear()
                    else:
                        st.error(f"❌ Falha no upload para o Snowflake: {message_or_rows}")
                        
        except Exception as e:
            st.error(f"❌ Erro ao processar o CSV enviado: {str(e)}")
    else:
        st.info("Nenhum arquivo enviado no momento. Arraste e solte o CSV acima.")

# ----------------------------------------------------------------------------
# TAB 3: DADOS BRUTOS COM EXPORTAÇÃO CSV OBRIGATÓRIA
# ----------------------------------------------------------------------------
with tab_raw_data:
    st.header("📂 Dados Brutos & Visualizador Tabular")
    st.write(f"Exibindo dados de: **{st.session_state['data_source']}**")
    st.write(f"Contém **{len(df_filtered):,} registros** após a filtragem atual.")
    
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

# ============================================================================
# FOOTER ACADÊMICO
# ============================================================================

st.markdown("""
<div class="footer">
    Desenvolvido por <b>Pedro Augusto Vicente</b> para a disciplina <b>Aplicações em Data Science (Turma 3)</b><br>
    Projeto de Data Pipeline & Business Intelligence integrado com Snowflake e Streamlit Cloud.
</div>
""", unsafe_allow_html=True)
