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
CREDENTIALS_FILE = '/home/francislley/dashboard-sei-flask/dashboard-sei-flask/dashboard-sei-8f0c2c70b56c.json' # Caminho ABSOLUTO

# --- Função para Carregar Dados Brutos da Planilha ---
def load_raw_data_from_sheet():
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # Limpeza básica: substituir vazios por NA
        df.replace('', pd.NA, inplace=True)

        # Tentar padronizar nomes de colunas comuns (com e sem acento)
        if 'Usuário' in df.columns and 'Usuario' not in df.columns:
            df.rename(columns={'Usuário': 'Usuario'}, inplace=True)
        if 'Descrição' in df.columns and 'Descricao' not in df.columns:
            df.rename(columns={'Descrição': 'Descricao'}, inplace=True)

        # Converter coluna 'Data' para datetime, se existir
        if 'Data' in df.columns:
            # dayfirst=True é crucial se suas datas estão em DD/MM/AAAA
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce', dayfirst=True)
            # Formata de volta para string YYYY-MM-DD para consistência com JS
            df['Data'] = df['Data'].dt.strftime('%Y-%m-%d').replace({pd.NA: None})

        return df
    except Exception as e:
        print(f"Erro ao carregar dados da planilha: {e}")
        # Para depuração, você pode querer levantar o erro ou retornar um DataFrame vazio
        # raise e # Descomente para ver o erro completo no log do PythonAnywhere
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

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
            # Verifica se a coluna existe antes de filtrar
            col_name = field.capitalize()
            if col_name in df.columns:
                df = df[df[col_name].isin(selected_values)]
            else:
                print(f"Aviso: Coluna '{col_name}' não encontrada no DataFrame para filtro.")


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
    if 'Unidade' in df.columns and 'Sigla' in df.columns: # Garante que ambas as colunas existam
        # Agrega por Sigla para obter a contagem
        sigla_counts = df.groupby('Sigla')['Unidade'].count().reset_index()
        sigla_counts.columns = ['Sigla', 'Count']

        # Prepara os dados para o gráfico
        for index, row in sigla_counts.iterrows():
            sigla_exibicao = row['Sigla']
            count = row['Count']
            
            # Pega o nome completo da unidade para o tooltip, associado a esta sigla
            # Isso pode pegar a primeira unidade encontrada para a sigla, ou você pode ajustar
            # para pegar todas as unidades ou uma representativa.
            unidade_completa = df[df['Sigla'] == sigla_exibicao]['Unidade'].iloc[0] if not df[df['Sigla'] == sigla_exibicao]['Unidade'].empty else sigla_exibicao

            donut_chart_data.append({
                'name': sigla_exibicao, # Usa a sigla diretamente da coluna
                'value': count,
                'unidadeCompleta': unidade_completa, # Nome completo para o tooltip
                'siglaOriginal': sigla_exibicao # A sigla para o filtro (já é a desejada)
            })
        
        # Ordena por valor (Count) decrescente
        donut_chart_data = sorted(donut_chart_data, key=lambda x: x['value'], reverse=True)

    # --- Dados para Gráfico de Barras (Documentos por Usuário) ---
    bar_chart_data = []
    # Verifica se as colunas 'Usuario' e 'Setor' existem no DataFrame
    if 'Usuario' in df.columns and 'Sigla' in df.columns:
        # Cria um mapa de usuário para setor.
        # Se um usuário tiver múltiplas entradas com setores diferentes,
        # ele pegará o último setor encontrado para aquele usuário.
        user_to_sector_map = df[['Usuario', 'Sigla']].drop_duplicates(subset=['Usuario'], keep='last').set_index('Usuario')['Sigla'].to_dict()

        usuario_counts = df['Usuario'].value_counts().reset_index()
        usuario_counts.columns = ['Usuario', 'Count']
        bar_chart_data = [
            {
                'name': row['Usuario'],
                'value': row['Count'],
                'sector': user_to_sector_map.get(row['Usuario'], 'Setor Desconhecido') # Adiciona a informação do setor aqui
            }
            for index, row in usuario_counts.iterrows()
        ]
        # Ordena por valor (Count) decrescente
        bar_chart_data = sorted(bar_chart_data, key=lambda x: x['value'], reverse=True)
    elif 'Usuario' in df.columns: # Caso a coluna 'Setor' não exista, mantém o comportamento anterior
        usuario_counts = df['Usuario'].value_counts().reset_index()
        usuario_counts.columns = ['Usuario', 'Count']
        bar_chart_data = [
            {'name': row['Usuario'], 'value': row['Count']}
            for index, row in usuario_counts.iterrows()
        ]
        bar_chart_data = sorted(bar_chart_data, key=lambda x: x['value'], reverse=True)
    # Se nem 'Usuario' nem 'Setor' existirem, bar_chart_data permanece vazio, o que é o comportamento esperado.

    # --- Dados para Tabela ---
    # Seleciona as colunas na ordem desejada e converte para lista de dicionários
    # Garante que as colunas existam antes de tentar selecioná-las
    table_columns = ['Processo', 'Documento', 'Descricao', 'Unidade', 'Sigla', 'Usuario', 'CPF', 'Data']
    existing_table_columns = [col for col in table_columns if col in df.columns]
    table_data = df[existing_table_columns].to_dict(orient='records')

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
        'siglas': sorted(df_raw['Sigla'].dropna().unique().tolist()) if 'Sigla' in df_raw.columns else [], # Usa a coluna Sigla diretamente
        'usuarios': sorted(df_raw['Usuario'].dropna().unique().tolist()) if 'Usuario' in df_raw.columns else []
    }

    # Processar dados iniciais (sem filtros)
    initial_dashboard_data = process_dashboard_data(df_raw)

    return jsonify({
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
    app.run(debug=True, host='0.0.0.0')
