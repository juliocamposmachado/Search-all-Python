import requests
import time
import json
import subprocess
import sys
from urllib.parse import quote
import warnings
from datetime import datetime

warnings.filterwarnings("ignore", category=DeprecationWarning)

DOMAINS = [
    "ferrana.com.br", "ferranaacessorios.com.br", "ferranaacessorios.com", "ferrana-acessorios.com.br",
    "damabolsas.com.br", "damabolsas.com", "damaacessorios.com.br", "damaacessorio.com.br"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HistoricalScanner/1.0; +https://github.com/JulioCamposMachado)"
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    sys.stdout.flush()

def retry_request(url, retries=3, delay=3):
    """Executa requisição com tentativas e backoff exponencial."""
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return r
            log(f"⚠️ Status {r.status_code} em {url}")
        except requests.exceptions.RequestException as e:
            log(f"⚠️ Erro em {url}: {e}")
        time.sleep(delay * (i + 1))
    return None

def wayback_checks(domain):
    """Busca capturas no Internet Archive (Wayback Machine)."""
    url = f"http://web.archive.org/cdx/search/cdx?url={domain}/*&output=json"
    r = retry_request(url)
    if not r:
        return []
    try:
        data = r.json()
        if isinstance(data, list) and len(data) > 1:
            return data[1:]
    except Exception as e:
        log(f"Erro ao processar Wayback JSON para {domain}: {e}")
    return []

def crt_sh_search(term, retries=3):
    """Busca certificados SSL relacionados ao domínio ou nome comercial."""
    url = f"https://crt.sh/?q=%25{quote(term)}%25&output=json"
    r = retry_request(url, retries=retries)
    if not r:
        return []
    try:
        data = r.json()
        if isinstance(data, list):
            return data
    except Exception as e:
        log(f"Erro ao processar crt.sh JSON para {term}: {e}")
    return []

def whois_lookup(domain):
    """Executa consulta WHOIS (compatível com Windows e Linux)."""
    try:
        out = subprocess.check_output(["whois", domain], stderr=subprocess.DEVNULL, timeout=60)
        return out.decode(errors="ignore")
    except FileNotFoundError:
        return "❌ WHOIS não disponível neste sistema."
    except subprocess.TimeoutExpired:
        return "❌ Timeout na consulta WHOIS."
    except Exception as e:
        return f"❌ Erro no WHOIS: {e}"

if __name__ == "__main__":
    report = {"wayback": {}, "crtsh": {}, "whois": {}}

    log("🚀 Iniciando varredura de domínios Ferrana / Dama Acessórios...")

    for d in DOMAINS:
        log(f"🌐 Wayback → {d}")
        report["wayback"][d] = wayback_checks(d)
        time.sleep(1)

    for term in ["ferrana", "dama", "damabolsas", "damaacessorios"]:
        log(f"🔍 crt.sh → {term}")
        report["crtsh"][term] = crt_sh_search(term)
        time.sleep(1)

    for d in DOMAINS:
        log(f"📄 WHOIS → {d}")
        report["whois"][d] = whois_lookup(d)
        time.sleep(1)

    output_file = "ferrana_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log(f"✅ Relatório salvo em {output_file}")
