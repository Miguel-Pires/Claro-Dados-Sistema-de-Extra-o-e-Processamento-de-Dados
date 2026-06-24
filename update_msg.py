# -*- coding: utf-8 -*-
import json, urllib.request

API_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiJhYjM3YTQ1ZS1iZDNlLTQwNTMtYjZjZi1kZmZjNmY2YjFmMjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMmEzZjE3NmQtMTMxMS00N2Q0LTlmYjItYzI1OWY4MWUwM2FjIiwiaWF0IjoxNzgxNzk1ODYzLCJleHAiOjE3ODQzNDM2MDB9"
    ".7egOW1FvnmnEAIe3M0GXCvBaCco6CgqULSitL5M80ws"
)
BASE = "http://localhost:5678/api/v1"
WF_ID = "fPMAqUelk488JzXe"
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}


def api(method, path, body=None):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode("utf-8") if body else None,
        method=method,
        headers=HEADERS,
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))


wf = api("GET", f"/workflows/{WF_ID}")

NEW_TEXT = (
    "=✅ *Planilha Claro pronta!*\n\n"
    "📊 {{ $json.total_linhas }} linhas extraídas\n\n"
    "⬇️ *Baixar planilha:*\n{{ $json.url }}"
)

for node in wf["nodes"]:
    if node["name"] == "Enviar Excel WAHA":
        node["parameters"]["text"] = NEW_TEXT
        break

payload = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
    "staticData": wf.get("staticData"),
}

api("PUT", f"/workflows/{WF_ID}", payload)
print("PUT OK")
api("POST", f"/workflows/{WF_ID}/activate")
print("Ativo")
