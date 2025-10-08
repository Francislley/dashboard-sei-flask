from flask import Flask, render_template, jsonify, request
import gspread
import pandas as pd
import json
import os
from datetime import datetime

app = Flask(__name__)

# --- Configurações da Planilha ---
# SUBSTITUA PELO ID DA SUA PLANILHA
SPREADSHEET_ID = '171LrxIb7IhCnYTP3rV7WaUGp0_mBaO2pX9cS0va6JJs'
# SUBSTITUA PELO NOME DA SUA ABA
WORKSHEET_NAME = 'SEI'
# Caminho para o arquivo de credenciais
CREDENTIALS_FILE = '/home/francislley/dashboard-sei-flask/dashboard-sei-flask/dashboard-sei-8f0c2c70b56c.json'

# --- Função para Carregar Dados Brutos da Planilha ---
# Esta função será chamada sempre que precisarmos dos dados brutos.
# Para grandes planilhas, considere implementar um cache para evitar re-leitura constante.
def load_raw_data_from_sheet():
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # Limpeza básica: substituir vazios por NA e remover linhas totalmente vazias
        df.replace('', pd.NA, inplace=True)
        # df.dropna(how='all', inplace=True) # Opcional: remover linhas onde TODAS as colunas são NA

        # Converter coluna 'Data' para datetime, se existir
        if 'Data' in df.columns:
            # Tenta converter para datetime, erros resultam em NaT (Not a Time)
            # Assumindo formato YYYY-MM-DD ou MM-DD-YYYY, ajuste dayfirst=True se for DD-MM-YYYY
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=False)
            # Formata de volta para string YYYY-MM-DD para consistência com JS
            df['Data'] = df['Data'].dt.strftime('%Y-%m-%d').replace({pd.NA: None})

        return df
    except Exception as e:
        print(f"Erro ao carregar dados da planilha: {e}")
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

# --- Função para Derivar Sigla (deve ser consistente com o frontend) ---
def derive_sigla(unidade):
    u = str(unidade or '').strip()
    if not u:
        return ''

    hyphen_index = u.find('-')
    if hyphen_index != -1:
        return u[hyphen_index + 1:].strip()

    # Divide por espaços, barras ou hífens e filtra vazios
    parts = [w for w in u.split(' ') if w] # Ajustado para split por espaço, depois filtra
    initials = ''.join([w[0].upper() for w in parts if len(w) >= 3 and w[0].isalpha()])
    if initials:
        return initials
    return u[:3].upper() # Fallback para as 3 primeiras letras se não houver palavras adequadas

# --- Função para Processar e Filtrar Dados ---
def process_dashboard_data(df_raw, filters=None):
    if filters is None:
        filters = {}

    df = df_raw.copy()

    # 1. Aplicar Filtro de Busca Rápida (quickSearch)
    quick_search_term = filters.get('quickSearch', '').lower()
    if quick_search_term:
        # Cria uma máscara booleana para cada linha
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(quick_search_term, na=False).any(), axis=1)
        df = df[mask]

    # 2. Aplicar Filtros de Combo Multi (unidade, sigla, usuario)
    for field in ['unidade', 'sigla', 'usuario']:
        selected_values = filters.get(field, [])
        if selected_values:
            # As colunas na planilha são 'Unidade', 'Sigla', 'Usuario' (com maiúscula)
            df = df[df[field.capitalize()].isin(selected_values)]

    # 3. Aplicar Filtro de Data (selectedDateString)
    selected_date_str = filters.get('selectedDateString')
    if selected_date_str and 'Data' in df.columns:
        # Garante que a coluna 'Data' no DataFrame é string no formato YYYY-MM-DD para comparação
        df_date_str = df['Data'].astype(str)
        df = df[df_date_str == selected_date_str]

    # --- Calcular KPIs ---
    total_processos = df['Processo'].nunique() if 'Processo' in df.columns else 0
    total_documentos = len(df) # Contagem de linhas após filtros
    total_unidades = df['Unidade'].nunique() if 'Unidade' in df.columns else 0
    total_usuarios = df['Usuario'].nunique() if 'Usuario' in df.columns else 0

    # --- Dados para Gráfico de Donut (Distribuição por Unidade/Sigla) ---
    donut_chart_data = []
    if 'Unidade' in df.columns:
        unidade_counts = df['Unidade'].value_counts().reset_index()
        unidade_counts.columns = ['Unidade', 'Count']
        donut_chart_data = [
            {
                'name': derive_sigla(row['Unidade']), # Sigla para o gráfico
                'value': row['Count'],
                'unidadeCompleta': row['Unidade'],
                'siglaOriginal': row['Sigla'] if 'Sigla' in df.columns else derive_sigla(row['Unidade']) # Mantém a sigla original da planilha ou deriva
            }
            for index, row in unidade_counts.iterrows()
        ]
        # Ordena por valor (Count) decrescente
        donut_chart_data = sorted(donut_chart_data, key=lambda x: x['value'], reverse=True)

    # --- Dados para Gráfico de Barras (Documentos por Usuário) ---
    bar_chart_data = []
    if 'Usuario' in df.columns:
        usuario_counts = df['Usuario'].value_counts().reset_index()
        usuario_counts.columns = ['Usuario', 'Count']
        bar_chart_data = [
            {'name': row['Usuario'], 'value': row['Count']}
            for index, row in usuario_counts.iterrows()
        ]
        # Ordena por valor (Count) decrescente
        bar_chart_data = sorted(bar_chart_data, key=lambda x: x['value'], reverse=True)

    # --- Dados para Tabela ---
    # Seleciona as colunas na ordem desejada e converte para lista de dicionários
    table_columns = ['Processo', 'Documento', 'Descricao', 'Unidade', 'Sigla', 'Usuario', 'CPF', 'Data']
    table_data = df[[col for col in table_columns if col in df.columns]].to_dict(orient='records')

    return {
        'totalProcessos': total_processos,
        'totalDocumentos': total_documentos,
        'totalUnidades': total_unidades,
        'totalUsuarios': total_usuarios,
        'donutChartData': donut_chart_data,
        'barChartData': bar_chart_data,
        'tableData': table_data
    }

# --- Rotas Flask ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/initial_data')
def get_initial_data():
    df_raw = load_raw_data_from_sheet()

    # Obter opções únicas para os filtros (deve ser dos dados BRUTOS)
    filter_options = {
        'unidades': sorted(df_raw['Unidade'].dropna().unique().tolist()) if 'Unidade' in df_raw.columns else [],
        'siglas': sorted(df_raw['Sigla'].dropna().unique().tolist()) if 'Sigla' in df_raw.columns else [],
        'usuarios': sorted(df_raw['Usuario'].dropna().unique().tolist()) if 'Usuario' in df_raw.columns else []
    }

    # Processar dados iniciais (sem filtros)
    initial_dashboard_data = process_dashboard_data(df_raw)

    return jsonify({
        # rawData não é mais enviado para o frontend, o backend sempre recarrega/processa
        'filterOptions': filter_options,
        'initialDashboardData': initial_dashboard_data
    })

@app.route('/api/filter_data', methods=['POST'])
def get_filtered_data():
    filters = request.json # Recebe os filtros do frontend
    df_raw = load_raw_data_from_sheet() # Recarrega os dados brutos
    filtered_dashboard_data = process_dashboard_data(df_raw, filters)
    return jsonify(filtered_dashboard_data)

# --- Execução Local (para testes) ---
if __name__ == '__main__':
    # Para rodar localmente, certifique-se de ter o credentials.json na mesma pasta
    # e as libs instaladas (pip install Flask gspread pandas)
    app.run(debug=True, host='0.0.0.0')
