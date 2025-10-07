from flask import Flask, render_template
import gspread
import pandas as pd
import json
import os

app = Flask(__name__)

# --- Configurações da Planilha ---
# SUBSTITUA PELO ID DA SUA PLANILHA
SPREADSHEET_ID = '171LrxIb7IhCnYTP3rV7WaUGp0_mBaO2pX9cS0va6JJs'
# SUBSTITUA PELO NOME DA SUA ABA
WORKSHEET_NAME = 'SEI'

# --- Função para Carregar Dados da Planilha ---
def load_data():
    try:
        # Tenta ler as credenciais do arquivo local 'credentials.json'
        # Este arquivo DEVE estar na raiz do seu projeto no PythonAnywhere
        gc = gspread.service_account(filename='credentials.json')

        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # --- Tratamento de Dados: Desconsiderar células em branco ---
        df.replace('', pd.NA, inplace=True)
        df.dropna(how='any', inplace=True)

        return df.to_dict(orient='records') # Retorna como lista de dicionários para o template
    except Exception as e:
        print(f"Erro ao carregar dados da planilha: {e}")
        # Em produção, você pode querer logar isso e mostrar uma mensagem de erro amigável
        return [] # Retorna lista vazia em caso de erro

@app.route('/')
def index():
    data = load_data()
    return render_template('index.html', data=data)

if __name__ == '__main__':
    # Esta parte não é executada no PythonAnywhere, mas é útil para testes locais
    # Se você estivesse testando localmente, precisaria do credentials.json na raiz do seu projeto
    app.run(debug=True, host='0.0.0.0')