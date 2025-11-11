from flask import Flask, render_template_string, request, jsonify
import whois

app = Flask(__name__)

# HTML com frontend interativo
HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>🔎 Localizador de Registros</title>
    <style>
        body {
            background: #101010;
            color: #e0e0e0;
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
        }
        input, button {
            padding: 10px;
            margin: 8px;
            border-radius: 8px;
            border: none;
        }
        input { width: 300px; }
        button { background: #007bff; color: white; cursor: pointer; }
        button:hover { background: #0056b3; }
        #results {
            margin-top: 30px;
            text-align: left;
            background: #202020;
            padding: 20px;
            border-radius: 10px;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }
        pre { white-space: pre-wrap; }
    </style>
</head>
<body>
    <h1>🔍 Localizador de Registros Antigos</h1>
    <p>Pesquise por domínio, nome ou e-mail para tentar localizar registros históricos.</p>
    <input id="query" placeholder="ex: lojaantiga.com.br ou nome@email.com">
    <button onclick="search()">Buscar</button>
    <div id="results"></div>

<script>
async function search() {
    const query = document.getElementById('query').value.trim();
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = "<p>⏳ Buscando...</p>";
    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await response.json();
        if (data.error) {
            resultsDiv.innerHTML = "<p style='color:red'>Erro: " + data.error + "</p>";
        } else {
            resultsDiv.innerHTML = "<h3>Resultados encontrados:</h3><pre>" + data.result + "</pre>";
        }
    } catch (err) {
        resultsDiv.innerHTML = "<p style='color:red'>Erro na requisição.</p>";
        console.error(err);
    }
}
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()

        if not query:
            return jsonify({"error": "Consulta vazia."})

        # 🔧 WHOIS seguro sem cache
        try:
            result = whois.whois(query)
            if not result:
                return jsonify({"error": "Nenhum resultado encontrado."})
            return jsonify({"result": str(result)})
        except Exception as e:
            return jsonify({"error": f"Erro na consulta WHOIS: {e}"})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
