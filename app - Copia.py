import requests
import time
import json
import subprocess
from urllib.parse import quote
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


DOMAINS = [
  "ferrana.com.br","ferranaacessorios.com.br","ferranaacessorios.com","ferrana-acessorios.com.br",
  "damabolsas.com.br","damabolsas.com","damaacessorios.com.br","damaacessorio.com.br"
]

def wayback_checks(domain):
    url = f"http://web.archive.org/cdx/search/cdx?url={domain}/*&output=json"
    r = requests.get(url, timeout=60)
    try:
        data = r.json()
    except Exception:
        return []
    # first row is header
    return data[1:] if len(data)>1 else []

def crt_sh_search(term, retries=3):
    url = f"https://crt.sh/?q=%25{quote(term)}%25&output=json"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=60)  # aumentei o timeout para 60s
            if r.status_code == 200:
                return r.json()
        except requests.exceptions.ReadTimeout:
            print(f"Timeout em crt.sh na tentativa {attempt+1}, tentando novamente...")
            time.sleep(5)
    return []

def whois_lookup(dom):
    # try calling system whois (depends on OS)
    try:
        out = subprocess.check_output(["whois", dom], stderr=subprocess.DEVNULL, timeout=60)
        return out.decode(errors="ignore")
    except Exception as e:
        return f"whois failed: {e}"

if __name__ == "__main__":
    report = {"wayback":{}, "crtsh":{}, "whois":{}}
    for d in DOMAINS:
        print("Checking Wayback:", d)
        report["wayback"][d] = wayback_checks(d)
        time.sleep(1)

    for term in ["ferrana","dama","damabolsas","damaacessorios"]:
        print("Checking crt.sh:", term)
        report["crtsh"][term] = crt_sh_search(term)
        time.sleep(1)

    for d in DOMAINS:
        print("Whois for:", d)
        report["whois"][d] = whois_lookup(d)
        time.sleep(1)

    with open("ferrana_report.json","w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
    print("Saved ferrana_report.json")
