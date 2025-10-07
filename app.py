import streamlit as st
#import gspread
#import pandas as pd
#import json

# --- Configurações da Planilha ---
SPREADSHEET_ID = '171LrxIb7IhCnYTP3rV7WaUGp0_mBaO2pX9cS0va6JJs'
WORKSHEET_NAME = 'SEI'

#teste de gcp_service
st.set_page_config(page_title="Teste Simples Secrets", layout="wide")
st.title("Teste de Acesso a Secret Simples")

try:
    secret_value = st.secrets["teste_simples"]
    st.success(f"Secret 'teste_simples' acessado com sucesso! Valor: {secret_value}")
except KeyError:
    st.error("Erro: Secret 'teste_simples' NÃO encontrado.")
    st.info("Verifique a configuração na seção 'Secrets' do Streamlit Cloud.")
except Exception as e:
    st.error(f"Ocorreu um erro inesperado ao acessar o secret: {e}")

"""
# --- Função para Carregar Dados (com cache para performance) ---
@st.cache_data(ttl=600) # Cache por 10 minutos (600 segundos)
def load_data():
    try:
        # --- Autenticação Segura para Streamlit Cloud ---
        # As credenciais serão lidas de st.secrets, que é a forma segura no Streamlit Cloud
        # No ambiente local, você precisaria de um arquivo de credenciais ou variáveis de ambiente
        # Para testar localmente, você pode temporariamente descomentar a linha abaixo e
        # garantir que seu arquivo JSON esteja na mesma pasta do app.py, mas REMOVA ISSO ANTES DE SUBIR PARA O GITHUB!
        # with open('nome-do-seu-arquivo-de-credenciais.json') as f:
        #     creds_json = json.load(f)
        # gc = gspread.service_account_from_dict(creds_json)

        # Para Streamlit Cloud, st.secrets é o caminho
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])

        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # --- Tratamento de Dados: Desconsiderar células em branco ---
        df.replace('', pd.NA, inplace=True)
        df.dropna(how='any', inplace=True)

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        st.info("Verifique se as credenciais estão configuradas corretamente no Streamlit Secrets e se a planilha está compartilhada.")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro

# --- Configuração da Página do Dashboard ---
st.set_page_config(
    page_title="Dashboard SEI - França Carvalho",
    layout="wide", # Usa a largura total da tela
    initial_sidebar_state="expanded"
)

# --- Título e Descrição do Dashboard ---
st.title("📊 Dashboard de Análise SEI")
st.markdown(f"Bem-vindo, França Carvalho! Este dashboard exibe dados da sua planilha Google na aba '{WORKSHEET_NAME}'.")
st.markdown("---")

# --- Carrega os dados ---
df_sei = load_data()

if not df_sei.empty:
    # --- Sidebar para Filtros ou Informações Adicionais ---
    st.sidebar.header("Filtros e Opções")
    st.sidebar.write(f"Total de registros: **{len(df_sei)}**")

    # Exemplo de filtro na sidebar (se você tiver uma coluna categórica)
    # if 'NomeDaColunaCategorica' in df_sei.columns:
    #     selected_category = st.sidebar.selectbox(
    #         "Selecione uma Categoria",
    #         ['Todos'] + list(df_sei['NomeDaColunaCategorica'].unique())
    #     )
    #     if selected_category != 'Todos':
    #         df_sei = df_sei[df_sei['NomeDaColunaCategorica'] == selected_category]

    # --- Exibição dos Dados Brutos ---
    st.subheader("Dados Brutos da Planilha (Primeiras 100 Linhas)")
    st.dataframe(df_sei.head(100), use_container_width=True) # Exibe as primeiras 100 linhas

    st.markdown("---")

    # --- Seção de Visualizações (Exemplos) ---
    st.header("Visualizações Chave")

    # Exemplo 1: Gráfico de Barras para Contagem de Valores em uma Coluna
    # SUBSTITUA 'NomeDaColunaParaContagem' por uma coluna real da sua planilha
    # Ex: 'Tipo de Documento', 'Status', 'Departamento'
    if 'NomeDaColunaParaContagem' in df_sei.columns:
        st.subheader("Contagem por Categoria")
        contagem_coluna = df_sei['NomeDaColunaParaContagem'].value_counts().reset_index()
        contagem_coluna.columns = ['Categoria', 'Contagem']
        st.bar_chart(contagem_coluna.set_index('Categoria'))
    else:
        st.info("Para um gráfico de contagem, substitua 'NomeDaColunaParaContagem' por uma coluna existente na sua planilha.")

    # Exemplo 2: Gráfico de Linhas para Dados Temporais (se houver coluna de data)
    # Se você tiver uma coluna de data, converta-a para datetime antes de usar
    # Ex: df_sei['Data'] = pd.to_datetime(df_sei['Data'])
    # if 'Data' in df_sei.columns and 'ValorNumerico' in df_sei.columns: # Substitua 'ValorNumerico'
    #     st.subheader("Tendência ao Longo do Tempo")
    #     df_sei_sorted = df_sei.sort_values('Data')
    #     st.line_chart(df_sei_sorted.set_index('Data')['ValorNumerico'])
    # else:
    #     st.info("Para um gráfico de tendência, certifique-se de ter colunas 'Data' e 'ValorNumerico' válidas.")

    st.markdown("---")
    st.write("Este é um ponto de partida! Explore suas colunas e adicione mais gráficos e interatividade.")

else:
    st.warning("Não foi possível exibir o dashboard pois os dados não foram carregados.")
"""

