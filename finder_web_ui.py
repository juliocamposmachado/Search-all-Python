# finder_web_ui.py
# Small Flask app to run searches by domain / name / email across several public archival sources
# Usage:
# 1) python -m venv venv
# 2) venv\Scripts\Activate.ps1  (PowerShell) or venv\Scripts\activate.bat (cmd)
# 3) pip install flask requests python-whois beautifulsoup4
# 4) python finder_web_ui.py
# Then open http://127.0.0.1:5000

from flask import Flask, request, jsonify, render_template_string, send_file
import requests
import whois
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import quote

app = Flask(__name__)

# Simple HTML UI (single-file) served by Flask
INDEX_HTML = '''
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Finder - Rastros Ferrana / Dama</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body{font-family:Arial,Helvetica,sans-serif;background:#0b0c10;color:#eaeaea;padding:20px}
    input,select,button,textarea{padding:8px;margin:6px 0;width:100%}
    .row{display:flex;gap:12px}
    .col{flex:1}
    table{width:100%;border-collapse:collapse;margin-top:12px}
    th,td{border:1px solid #333;padding:8px}
    th{background:#14171a}
    .stats{margin-top:12px;padding:12px;background:#14171a;border-radius:8px}
    a{color:#7bd389}
  </style>
</head>
<body>
  <h1>Finder — Busca por nomes / e-mails / domínios</h1>
  <p>Digite nomes, e-mails ou domínios para procurar vestígios em Archive.org, Geocities mirrors, crt.sh e WHOIS.</p>

  <div>
    <label>Consulta (separe múltiplos por vírgula):</label>
    <textarea id="queries" rows="2">ferrana, damabolsas, damaacessorios, fernanda marsiglia, regina marsiglia, radiotatuapefm@gmail.com</textarea>

    <label>Opções:</label>
    <div class="row">
      <div class="col">
        <select id="sources" multiple>
          <option value="wayback">Wayback (Archive.org)</option>
          <option value="crtsh">crt.sh (certificados)</option>
          <option value="oocities">Oocities / Geocities mirrors</option>
          <option value="whois">WHOIS (domínios)</option>
        </select>
      </div>
      <div class="col">
        <button id="run">Executar busca</button>
        <button id="download">Baixar JSON</button>
      </div>
    </div>

    <div class="stats" id="stats" style="display:none"></div>
    <table id="results_table" style="display:none">
      <thead><tr><th>Consulta</th><th>Fonte</th><th>Resumo</th><th>Links</th></tr></thead>
      <tbody id="results_body"></tbody>
    </table>
  </div>

<script>
async function postJSON(url,data){
  const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  return r.json();
}

function addRow(q,source,summary,links){
  const tb = document.getElementById('results_body');
  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${q}</td><td>${source}</td><td>${summary}</td><td>${links}</td>`;
  tb.appendChild(tr);
}

document.getElementById('run').onclick = async ()=>{
  document.getElementById('results_body').innerHTML = '';
  document.getElementById('results_table').style.display='none';
  document.getElementById('stats').style.display='none';
  const raw = document.getElementById('queries').value.split(',').map(s=>s.trim()).filter(Boolean);
  const sources = Array.from(document.getElementById('sources').selectedOptions).map(o=>o.value);
  if(sources.length==0) alert('Selecione ao menos uma fonte.');
  const payload = {queries: raw, sources: sources};
  const res = await postJSON('/api/search',payload);
  // populate
  let found=0; let total=0; let rows=0;
  for(const p of res.hits){
    total++;
    const q = p.query;
    for(const s of p.sources){
      rows++;
      const summary = s.summary.replace(/\n/g,'<br>');
      const links = (s.links||[]).map(l=>`<a href="${l}" target="_blank">${l}</a>`).join('<br>');
      addRow(q,s.source,summary,links);
      if(s.found) found++;
    }
  }
  document.getElementById('stats').style.display='block';
  document.getElementById('stats').innerHTML = `<strong>Consultas:</strong> ${raw.length} &nbsp; <strong>Linhas de resultado:</strong> ${rows} &nbsp; <strong>Hits:</strong> ${found}`;
  document.getElementById('results_table').style.display='table';
};

document.getElementById('download').onclick = ()=>{ window.location='/api/download' };
</script>
</body>
</html>
'''

# Helper functions

def search_wayback_for_term(term, max_results=50):
    """Try to find Archive.org captures for likely URL patterns containing the term.
    We will query CDX for common hostnames and for wildcard attempts.
    """
    results = []
    # common host patterns used in 90s
    hosts = [
        f"www.uol.com.br/~{term}",
        f"www.geocities.com/{term}",
        f"br.geocities.com/{term}",
        f"oocities.org/*{term}*",
        f"usuarios.terra.com.br/{term}",
        f"members.aol.com/{term}",
        f"www.tripod.com/{term}",
        f"www.ibiblio.org/{term}",
    ]
    seen = set()
    for h in hosts:
        # transform to a search URL
        query = quote(h, safe='')
        url = f"http://web.archive.org/cdx/search/cdx?url={h}/*&output=json&limit={max_results}"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code==200:
                data = r.json()
                if len(data)>1:
                    for row in data[1:]:
                        key = (row[1], row[2]) if len(row)>2 else tuple(row)
                        if key not in seen:
                            seen.add(key)
                            results.append({'raw': row, 'capture_url': f"https://web.archive.org/web/{row[1]}/{row[2]}" if len(row)>2 else None})
        except Exception as e:
            # ignore transient errors
            continue
    return results


def search_crtsh(term):
    url = f"https://crt.sh/?q=%25{quote(term)}%25&output=json"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code==200 and r.text.strip():
            try:
                return r.json()
            except:
                # sometimes crt.sh returns non-json when too large
                return []
    except Exception:
        return []
    return []


def whois_lookup(domain):
    try:
        w = whois.whois(domain)
        return w
    except Exception as e:
        return None


def search_oocities(term):
    """Simple scraper of oocities search pages (best-effort)."""
    hits = []
    try:
        q = quote(term)
        url = f"https://oocities.org/search?q={q}"
        r = requests.get(url, timeout=15)
        if r.status_code==200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.select('a'):
                href = a.get('href','')
                text = a.get_text(strip=True)
                if term.lower() in text.lower() or term.lower() in href.lower():
                    full = href if href.startswith('http') else 'https://oocities.org'+href
                    hits.append({'title':text,'url':full})
    except Exception:
        pass
    return hits

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/api/search', methods=['POST'])
def api_search():
    payload = request.json or {}
    queries = payload.get('queries', [])
    sources = payload.get('sources', ['wayback','crtsh','oocities','whois'])
    hits = []
    for q in queries:
        q_lower = q.lower()
        entry = {'query': q, 'sources': []}
        # Wayback
        if 'wayback' in sources:
            wb = search_wayback_for_term(re.sub(r'[^a-z0-9\-]','',q_lower))
            entry['sources'].append({'source':'wayback','found': len(wb)>0, 'count': len(wb), 'summary': f'Capturas encontradas: {len(wb)}', 'links': [r.get('capture_url') for r in wb if r.get('capture_url')]})
        # crt.sh
        if 'crtsh' in sources:
            crt = search_crtsh(q_lower)
            # reduce to unique names
            domains = set()
            for c in crt:
                nv = c.get('name_value')
                if nv:
                    for d in nv.split('\n'):
                        domains.add(d.strip())
            entry['sources'].append({'source':'crt.sh','found': len(domains)>0, 'count': len(domains), 'summary': f'Domínios certificados encontrados: {len(domains)}', 'links': [f'https://crt.sh/?q={quote(d)}' for d in list(domains)[:20]]})
        # oocities
        if 'oocities' in sources:
            oc = search_oocities(q_lower)
            entry['sources'].append({'source':'oocities','found': len(oc)>0, 'count': len(oc), 'summary': f'Páginas mirror encontradas: {len(oc)}', 'links': [h.get('url') for h in oc[:30]]})
        # whois (only if the query looks like domain)
        if 'whois' in sources:
            # extract domain-like tokens
            tokens = re.findall(r'[a-z0-9\-]+\.(com|com.br|net|org|br)', q_lower)
            whois_res = None
            # if raw query looks like email, try domain part
            if '@' in q_lower:
                dom = q_lower.split('@')[-1]
                whois_res = whois_lookup(dom)
                entry['sources'].append({'source':'whois','found': bool(whois_res), 'count': 1 if whois_res else 0, 'summary': str(whois_res)[:500] if whois_res else 'nenhum whois', 'links': []})
            else:
                # try direct
                if re.search(r'\.', q_lower):
                    # treat as domain
                    try:
                        whois_res = whois_lookup(q_lower)
                        entry['sources'].append({'source':'whois','found': bool(whois_res), 'count':1 if whois_res else 0, 'summary': str(whois_res)[:500] if whois_res else 'nenhum whois', 'links': []})
                    except:
                        entry['sources'].append({'source':'whois','found':False,'count':0,'summary':'whois falhou','links':[]})
        hits.append(entry)
    return jsonify({'ok':True,'hits':hits})

@app.route('/api/download')
def api_download():
    # if ferrana_report.json exists, return it, otherwise create minimal
    try:
        return send_file('ferrana_report.json', as_attachment=True)
    except Exception:
        return jsonify({'error':'arquivo não encontrado'}),404

if __name__=='__main__':
    app.run(debug=True)
