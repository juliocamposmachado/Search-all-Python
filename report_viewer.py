import json
from datetime import datetime
from pathlib import Path

# Caminho para o relatório gerado pelo script anterior
json_file = Path("ferrana_report.json")

if not json_file.exists():
    print("❌ Arquivo ferrana_report.json não encontrado. Execute o script anterior primeiro.")
    exit(1)

# Carregar dados do relatório
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

wayback = data.get("wayback", {})
crtsh = data.get("crtsh", {})
whois_data = data.get("whois", {})

# Função para verificar se há capturas válidas
def validar_wayback(entries):
    return len(entries) > 0

# Função para validar certificados SSL encontrados
def validar_crt(entries):
    return len(entries) > 0

# Função para verificar se o WHOIS retornou dados significativos
def validar_whois(texto):
    if not texto or "No match" in texto or "NOT FOUND" in texto:
        return False
    return True

# Preparar dados para HTML
linhas_html = []
dominios_encontrados = 0

for dominio, entradas in wayback.items():
    tem_wayback = validar_wayback(entradas)
    tem_whois = validar_whois(whois_data.get(dominio, ""))
    tem_crt = False

    # Verificar se o domínio ou termo aparece em crt.sh
    for termo, certs in crtsh.items():
        if any(dominio in c.get("name_value", "") for c in certs):
            tem_crt = True
            break

    if tem_wayback or tem_crt or tem_whois:
        dominios_encontrados += 1

    # Links de verificação
    wayback_link = f"https://web.archive.org/web/*/{dominio}"
    crt_link = f"https://crt.sh/?q={dominio}"

    linhas_html.append(f"""
    <tr>
        <td>{dominio}</td>
        <td style="text-align:center;">{"✅" if tem_wayback else "❌"}</td>
        <td style="text-align:center;">{"✅" if tem_crt else "❌"}</td>
        <td style="text-align:center;">{"✅" if tem_whois else "❌"}</td>
        <td><a href="{wayback_link}" target="_blank">Archive.org</a> | 
            <a href="{crt_link}" target="_blank">crt.sh</a></td>
    </tr>
    """)

# Estatísticas gerais
total_dominios = len(wayback)
pct_encontrados = (dominios_encontrados / total_dominios * 100) if total_dominios else 0

# Montar HTML final
html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório de Rastros - Ferrana Acessórios</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background: #0b0c10;
    color: #f0f0f0;
    padding: 20px;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin-top: 20px;
}}
th, td {{
    border: 1px solid #444;
    padding: 10px;
}}
th {{
    background: #1f2833;
}}
tr:nth-child(even) {{
    background: #222;
}}
.summary {{
    margin-top: 20px;
    padding: 10px;
    background: #1f2833;
    border-radius: 8px;
}}
</style>
</head>
<body>
<h1>📜 Relatório de Rastros - Ferrana Acessórios do Vestuário Ltda</h1>
<p>Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>

<div class="summary">
    <p><strong>Total de domínios analisados:</strong> {total_dominios}</p>
    <p><strong>Domínios com algum vestígio (Wayback / CRT / WHOIS):</strong> {dominios_encontrados}</p>
    <p><strong>Percentual encontrado:</strong> {pct_encontrados:.1f}%</p>
</div>

<table>
<thead>
<tr>
    <th>Domínio</th>
    <th>Wayback</th>
    <th>Certificados SSL</th>
    <th>WHOIS</th>
    <th>Verificação</th>
</tr>
</thead>
<tbody>
{''.join(linhas_html)}
</tbody>
</table>

</body>
</html>
"""

# Salvar HTML
output_file = Path("relatorio_ferrana.html")
output_file.write_text(html, encoding="utf-8")
print(f"✅ Relatório gerado com sucesso: {output_file.resolve()}")
