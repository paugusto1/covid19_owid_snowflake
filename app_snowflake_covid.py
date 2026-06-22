"""
APP STREAMLIT + SNOWFLAKE - DASHBOARD COVID-19 (OWID EXCLUSIVE)
Integração de dados OWID e carga no Snowflake
Desenvolvido para Demonstração de Pipelines de Dados
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
    page_title="COVID-19 OWID Snowflake",
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
    .kpi-card {
        background-color: #F3F4F6;
        border-radius: 8px;
        padding: 1rem;
        border-left: 5px solid #3B82F6;
    }
    .sync-card {
        background-color: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNÇÕES DE CONEXÃO E BANCO DE DADOS
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
        role=st.secrets["snowflake"]["role"]
    )

def setup_writable_db():
    """Garante a existência do banco de dados COVID19_DB e esquema PUBLIC para escrita"""
    conn = get_snowflake_connection()
    cur = conn.cursor()
    try:
        cur.execute("CREATE DATABASE IF NOT EXISTS COVID19_DB")
        cur.execute("USE DATABASE COVID19_DB")
        cur.execute("CREATE SCHEMA IF NOT EXISTS PUBLIC")
        cur.execute("USE SCHEMA PUBLIC")
        conn.commit()
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

def upload_data_to_snowflake():
    """Lê o arquivo CSV local do OWID do main.py e faz o upload para o Snowflake"""
    setup_writable_db() # Cria COVID19_DB e PUBLIC
    
    conn = get_snowflake_connection()
    status_messages = []
    
    # Arquivo: covid19_owid_snowflake.csv
    try:
        owid_csv = "covid19_owid_snowflake.csv"
        df_owid = pd.read_csv(owid_csv)
        
        df_owid_clean = clean_column_names(df_owid)
        
        # Enviar ao Snowflake (COVID19_DB.PUBLIC.COVID19_OWID_SNOWFLAKE)
        success, nchunks, nrows, _ = write_pandas(
            conn=conn,
            df=df_owid_clean,
            table_name="COVID19_OWID_SNOWFLAKE",
            database="COVID19_DB",
            schema="PUBLIC",
            auto_create_table=True,
            overwrite=True
        )
        if success:
            status_messages.append(f"✅ Tabela COVID19_OWID_SNOWFLAKE carregada com {nrows} linhas!")
        else:
            status_messages.append("❌ Erro no upload da tabela histórica OWID.")
            
    except Exception as e:
        status_messages.append(f"❌ Erro ao processar dados históricos OWID: {str(e)}")
        
    return status_messages

@st.cache_data(ttl=300)
def run_query_from_db(query, database="COVID19_DB", schema="PUBLIC"):
    """Executa queries de consulta no banco de dados especificado"""
    conn = get_snowflake_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"USE DATABASE {database}")
        cur.execute(f"USE SCHEMA {schema}")
        cur.execute(query)
        df = cur.fetch_pandas_all()
        return df
    finally:
        cur.close()

# ============================================================================
# INTERFACE PRINCIPAL
# ============================================================================

st.markdown('<div class="main-header">🦠 COVID-19 Snowflake Analytics</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Carga de Dados, Armazenamento Seguro e Business Intelligence com Snowflake Cloud Data Warehouse (Dataset OWID)</div>', unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - CONTROLE E CONEXÃO
# ============================================================================

with st.sidebar:
    st.header("⚙️ Controle e Conexão")
    
    # Exibir credenciais (segura)
    try:
        conn_test = get_snowflake_connection()
        cur_test = conn_test.cursor()
        cur_test.execute("SELECT CURRENT_VERSION()")
        version = cur_test.fetchone()[0]
        cur_test.close()
        conn_test.close()
        
        st.success("✅ Conectado ao Snowflake!")
        with st.expander("ℹ️ Detalhes da Sessão"):
            st.code(f"""
Conta: {st.secrets["snowflake"]["account"]}
User: {st.secrets["snowflake"]["user"]}
Role: {st.secrets["snowflake"]["role"]}
Versão: {version}
            """)
    except Exception as e:
        st.error(f"❌ Erro de Conexão: {str(e)}")
        st.info("Verifique se as credenciais no secrets.toml estão corretas.")
        st.stop()
        
    st.markdown("---")
    
    # Card de Sincronização de Dados
    st.markdown('<div class="sync-card">', unsafe_allow_html=True)
    st.markdown("### 🔄 Sincronização Snowflake")
    st.markdown("Envia os resultados do dataset OWID do `main.py` diretamente para o Snowflake.")
    
    if st.button("🚀 Enviar Resultados para o Snowflake", use_container_width=True):
        with st.spinner("Conectando, criando tabela e inserindo dados de COVID-19..."):
            status_logs = upload_data_to_snowflake()
            for log in status_logs:
                if "✅" in log:
                    st.toast(log, icon="✅")
                else:
                    st.toast(log, icon="❌")
            st.success("Carga concluída!")
            st.write(status_logs)
            st.cache_data.clear()
            
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.info("""
    **Sobre o Pipeline:**
    1. `main.py` coleta, filtra e gera o dataset OWID no CSV `covid19_owid_snowflake.csv` localmente.
    2. Este app lê o CSV, limpa suas colunas e o envia ao Snowflake usando `write_pandas`.
    3. Os dashboards consomem os dados diretamente do Snowflake.
    """)

# ============================================================================
# VERIFICAR SE A TABELA EXISTE ANTES DE CARREGAR OS TABS
# ============================================================================

tables_ready = False
try:
    test_owid = run_query_from_db("SELECT COUNT(*) FROM COVID19_OWID_SNOWFLAKE")
    tables_ready = True
except Exception:
    pass

if not tables_ready:
    st.warning("⚠️ Os dados do COVID-19 OWID ainda não foram enviados ao Snowflake.")
    st.info("Por favor, clique no botão **🚀 Enviar Resultados para o Snowflake** na barra lateral esquerda para iniciar a carga de dados.")
    
    try:
        st.subheader("Prévia local: Dados Históricos OWID")
        df_preview_owid = pd.read_csv("covid19_owid_snowflake.csv").head(10)
        st.dataframe(df_preview_owid, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao carregar prévia local: {e}. Certifique-se de rodar `python main.py` primeiro.")
    st.stop()

# ============================================================================
# TABS PRINCIPAIS DE NAVEGAÇÃO
# ============================================================================

tab_dashboard, tab_explorer, tab_playground = st.tabs([
    "📊 Dashboard Histórico (OWID)",
    "❄️ Visualizador Snowflake",
    "💻 SQL Playground"
])

# ----------------------------------------------------------------------------
# TAB 1: DASHBOARD HISTÓRICO (OWID)
# ----------------------------------------------------------------------------
with tab_dashboard:
    st.header("📈 Evolução Histórica Temporal (Our World in Data)")
    st.markdown("Análise comparativa temporal de COVID-19 (2020-2023) obtida diretamente do Snowflake.")
    
    # Buscar série temporal
    df_owid = run_query_from_db("SELECT * FROM COVID19_OWID_SNOWFLAKE ORDER BY DATE ASC")
    df_owid['DATE'] = pd.to_datetime(df_owid['DATE'])
    
    # Seleção de Países
    available_locations = list(df_owid['LOCATION'].unique())
    selected_locations = st.multiselect(
        "Selecione os Países para Comparação:",
        options=available_locations,
        default=available_locations
    )
    
    # Seleção de Métrica
    metrics_map = {
        "NEW_CASES": "Novos Casos Diários",
        "TOTAL_DEATHS": "Óbitos Acumulados",
        "PEOPLE_VACCINATED": "Pessoas Vacinadas",
        "POPULATION": "População Total"
    }
    selected_metric = st.selectbox(
        "Selecione a Métrica para o Eixo Y:",
        options=list(metrics_map.keys()),
        format_func=lambda x: metrics_map[x]
    )
    
    df_owid_filtered = df_owid[df_owid['LOCATION'].isin(selected_locations)]
    
    if not df_owid_filtered.empty:
        # Gráfico temporal
        fig_line = px.line(
            df_owid_filtered,
            x='DATE',
            y=selected_metric,
            color='LOCATION',
            title=f"Evolução Temporal: {metrics_map[selected_metric]}",
            labels={'DATE': 'Data', selected_metric: metrics_map[selected_metric], 'LOCATION': 'País'},
            template='plotly_white'
        )
        st.plotly_chart(fig_line, use_container_width=True)
        
        # Seção de KPIs Comparativos de Acordo com a Seleção de Países
        st.markdown("---")
        st.subheader("🎯 Resumo de Estatísticas Máximas no Período (2020-2023)")
        
        kpi_cols = st.columns(len(selected_locations) if len(selected_locations) > 0 else 1)
        for i, loc in enumerate(selected_locations):
            loc_data = df_owid_filtered[df_owid_filtered['LOCATION'] == loc]
            max_cases_day = loc_data['NEW_CASES'].max()
            max_deaths = loc_data['TOTAL_DEATHS'].max()
            max_vacc = loc_data['PEOPLE_VACCINATED'].max()
            
            with kpi_cols[i]:
                st.markdown(f"#### 📍 {loc}")
                st.metric("Pico de Casos Diários", f"{max_cases_day:,.0f}" if pd.notna(max_cases_day) else "N/A")
                st.metric("Total de Óbitos", f"{max_deaths:,.0f}" if pd.notna(max_deaths) else "N/A")
                st.metric("Máx. Vacinados", f"{max_vacc:,.0f}" if pd.notna(max_vacc) else "N/A")
    else:
        st.warning("Selecione pelo menos um país para visualizar as métricas e o gráfico histórico.")

# ----------------------------------------------------------------------------
# TAB 2: VISUALIZADOR SNOWFLAKE
# ----------------------------------------------------------------------------
with tab_explorer:
    st.header("❄️ Visualizador de Registros Físicos do Snowflake")
    st.markdown("Exibição direta e paginação rápida dos registros reais armazenados na tabela `COVID19_OWID_SNOWFLAKE` no Snowflake.")
    
    rows_limit = st.slider("Limite de Linhas a Buscar:", min_value=5, max_value=500, value=50, step=5)
    
    with st.spinner("Buscando registros no Snowflake..."):
        df_preview = run_query_from_db(f"SELECT * FROM COVID19_OWID_SNOWFLAKE LIMIT {rows_limit}")
        
    st.success(f"✅ {len(df_preview)} linhas carregadas diretamente da tabela `COVID19_OWID_SNOWFLAKE`.")
    st.dataframe(df_preview, use_container_width=True)
    
    # Download Button
    csv_data = df_preview.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="💾 Baixar registros exibidos em CSV",
        data=csv_data,
        file_name="snowflake_owid_preview.csv",
        mime="text/csv"
    )

# ----------------------------------------------------------------------------
# TAB 3: SQL PLAYGROUND
# ----------------------------------------------------------------------------
with tab_playground:
    st.header("💻 SQL Playground")
    st.markdown("Escreva queries SQL ANSI personalizadas e execute-as diretamente na tabela `COVID19_OWID_SNOWFLAKE` no Snowflake!")
    
    exemplo_query = """-- Query exemplo: Total de obitos acumulados e taxa de obitos por 100 mil habitantes
SELECT 
    LOCATION,
    MAX(TOTAL_DEATHS) as TOTAL_OBITOS,
    MAX(POPULATION) as POPULACAO_TOTAL,
    ROUND((MAX(TOTAL_DEATHS)/MAX(POPULATION))*100000, 2) as OBITOS_POR_100K_HAB
FROM COVID19_OWID_SNOWFLAKE
GROUP BY LOCATION
ORDER BY OBITOS_POR_100K_HAB DESC;"""

    user_query = st.text_area(
        "Sua Query SQL:",
        value=exemplo_query,
        height=200
    )
    
    if st.button("⚡ Executar Query no Snowflake", use_container_width=True):
        if user_query.strip() != "":
            with st.spinner("Enviando query ao Snowflake..."):
                try:
                    df_custom = run_query_from_db(user_query)
                    st.success("✅ Query executada com sucesso!")
                    st.dataframe(df_custom, use_container_width=True)
                except Exception as e:
                    st.error(f"❌ Erro de Sintaxe ou Execução SQL: {str(e)}")
        else:
            st.warning("Por favor, digite uma query SQL válida antes de executar.")
