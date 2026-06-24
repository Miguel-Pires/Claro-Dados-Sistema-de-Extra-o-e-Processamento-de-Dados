"""
Adiciona nó de filtro 'E Mensagem?' entre WAHA Trigger e Extrair Dados.
Faz GET, modifica só o necessário, faz PUT de volta.
"""
import json
import urllib.request

API_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiJhYjM3YTQ1ZS1iZDNlLTQwNTMtYjZjZi1kZmZjNmY2YjFmMjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMmEzZjE3NmQtMTMxMS00N2Q0LTlmYjItYzI1OWY4MWUwM2FjIiwiaWF0IjoxNzgxNzk1ODYzLCJleHAiOjE3ODQzNDM2MDB9"
    ".7egOW1FvnmnEAIe3M0GXCvBaCco6CgqULSitL5M80ws"
)
WF_ID = "fPMAqUelk488JzXe"
BASE = "http://localhost:5678/api/v1"
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}


def api_get(path):
    req = urllib.request.Request(f"{BASE}{path}", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def api_put(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        method="PUT",
        headers=HEADERS,
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print("HTTP Error:", e.code, e.read().decode()[:500])
        raise


def api_post(path):
    req = urllib.request.Request(
        f"{BASE}{path}", data=b"{}", method="POST", headers=HEADERS
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# 1. GET estado atual
wf = api_get(f"/workflows/{WF_ID}")
print("Nodes atuais:", [n["name"] for n in wf["nodes"]])

# 2. Verifica se o filtro já existe
if any(n["name"] == "E Mensagem?" for n in wf["nodes"]):
    print("Nó 'E Mensagem?' já existe — nada a fazer.")
else:
    # Nó filtro: só passa eventos que têm payload com 'from' (mensagens reais)
    filtro = {
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                "conditions": [
                    {
                        "id": "f1",
                        "leftValue": "={{ $json.payload?.from }}",
                        "rightValue": "",
                        "operator": {"type": "string", "operation": "notEmpty", "singleValue": True},
                    }
                ],
                "combinator": "and",
            },
            "looseTypeValidation": True,
            "options": {},
        },
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [110, 0],   # Entre WAHA Trigger (x=0) e Extrair Dados (x=220)
        "id": "b2000001-0001-0001-0001-000000000001",
        "name": "E Mensagem?",
    }
    wf["nodes"].append(filtro)

    # 3. Atualiza as conexões:
    #    WAHA Trigger → E Mensagem? → Extrair Dados (branch 0 = TRUE)
    #    Branch 1 (FALSE) → sem conexão (descarta silenciosamente)
    conns = wf.setdefault("connections", {})
    conns["WAHA Trigger"] = {"main": [[{"node": "E Mensagem?", "type": "main", "index": 0}]]}
    conns["E Mensagem?"]  = {"main": [[{"node": "Extrair Dados", "type": "main", "index": 0}], []]}

    # n8n API PUT só aceita estes campos
    payload = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
        "staticData": wf.get("staticData"),
    }

    print("Adicionando 'E Mensagem?' e atualizando conexões...")
    result = api_put(f"/workflows/{WF_ID}", payload)
    print("PUT OK —", result["name"])
    print("Nodes agora:", [n["name"] for n in result["nodes"]])

    # 4. Reativar
    act = api_post(f"/workflows/{WF_ID}/activate")
    print("Ativo:", act.get("active"))
