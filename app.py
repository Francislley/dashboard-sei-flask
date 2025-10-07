# app.py
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    # Para desenvolvimento local, você usaria app.run(debug=True)
    # No PythonAnywhere, o servidor web deles gerencia a execução.
    # Esta parte só é relevante se você rodar localmente (o que não é o caso aqui).
    # No PythonAnywhere, o WSGI file vai importar 'app' diretamente.
    pass # Deixamos vazio ou removemos o if __name__ para o deploy no PA