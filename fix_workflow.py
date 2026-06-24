"""Corrige o nó Extrair Dados no workflow Leitura dados Claro."""
import json
import urllib.request

API_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiJhYjM3YTQ1ZS1iZDNlLTQwNTMtYjZjZi1kZmZjNmY2YjFmMjgiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMmEzZjE3NmQtMTMxMS00N2Q0LTlmYjItYzI1OWY4MWUwM2FjIiwiaWF0IjoxNzgxNzk1ODYzLCJleHAiOjE3ODQzNDM2MDB9"
    ".7egOW1FvnmnEAIe3M0GXCvBaCco6CgqULSitL5M80ws"
)
WORKFLOW_ID = "fPMAqUelk488JzXe"
BASE = "http://localhost:5678/api/v1"
HEADERS = {"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}


def api(method, path, body=None):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode() if body else None,
        method=method,
        headers=HEADERS,
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


workflow = {
    "name": "Leitura dados Claro",
    "settings": {"executionOrder": "v1"},
    "nodes": [
        {
            "parameters": {},
            "type": "@devlikeapro/n8n-nodes-waha.wahaTrigger",
            "typeVersion": 202502,
            "position": [0, 0],
            "id": "340bcd3a-def3-457f-8b66-5ba9f151b98d",
            "name": "WAHA Trigger",
            "webhookId": "f6558b27-3029-48cd-8c15-49625dcc80d1",
        },
        {
            "parameters": {
                "assignments": {
                    "assignments": [
                        {"id": "s1", "name": "session",       "value": "={{ $json.session }}", "type": "string"},
                        {"id": "s2", "name": "from",          "value": "={{ $json.payload.from }}", "type": "string"},
                        {"id": "s4", "name": "has_media",     "value": "={{ $json.payload.hasMedia || false }}", "type": "boolean"},
                        # replace localhost→host.docker.internal para download funcionar dentro do Docker
                        {"id": "s5", "name": "media_url",     "value": "={{ ($json.payload.media?.url || '').replace('http://localhost:3000', 'http://host.docker.internal:3000') }}", "type": "string"},
                        {"id": "s6", "name": "media_mimetype","value": "={{ $json.payload.media?.mimetype || '' }}", "type": "string"},
                        {"id": "s7", "name": "from_me",       "value": "={{ $json.payload.fromMe || false }}", "type": "boolean"},
                    ]
                },
                "options": {},
            },
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [220, 0],
            "id": "a1000001-0001-0001-0001-000000000001",
            "name": "Extrair Dados",
        },
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                    "conditions": [
                        {"id": "c1", "leftValue": "={{ $json.from_me }}",       "rightValue": False, "operator": {"type": "boolean", "operation": "equals"}},
                        {"id": "c2", "leftValue": "={{ $json.has_media }}",     "rightValue": True,  "operator": {"type": "boolean", "operation": "equals"}},
                        {"id": "c3", "leftValue": "={{ $json.media_mimetype }}", "rightValue": "pdf", "operator": {"type": "string",  "operation": "contains"}},
                    ],
                    "combinator": "and",
                },
                "looseTypeValidation": True,
                "options": {},
            },
            "type": "n8n-nodes-base.if",
            "typeVersion": 2.2,
            "position": [440, 0],
            "id": "a1000002-0002-0002-0002-000000000002",
            "name": "E PDF",
        },
        {
            "parameters": {
                "resource": "Chatting",
                "operation": "Send Text",
                "session": "={{ $(\"Extrair Dados\").item.json.session }}",
                "chatId": "={{ $(\"Extrair Dados\").item.json.from }}",
                "text": "=⏳ PDF recebido! Processando a fatura Claro, aguarde...",
                "requestOptions": {},
            },
            "type": "@devlikeapro/n8n-nodes-waha.WAHA",
            "typeVersion": 202502,
            "position": [660, -80],
            "id": "a1000003-0003-0003-0003-000000000003",
            "name": "Aguardando",
            "credentials": {"wahaApi": {"id": "NOUNjHnsj7kUbPnW", "name": "WAHA account"}},
        },
        {
            "parameters": {
                "url": "={{ $(\"Extrair Dados\").item.json.media_url }}",
                "options": {"response": {"response": {"responseFormat": "file"}}},
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [880, -80],
            "id": "a1000004-0004-0004-0004-000000000004",
            "name": "Download PDF",
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://host.docker.internal:8765/extract",
                "sendBody": True,
                "contentType": "multipart-form-data",
                "bodyParameters": {
                    "parameters": [
                        {"name": "pdf", "value": "data", "parameterType": "formBinaryData", "inputDataFieldName": "data"}
                    ]
                },
                "options": {"timeout": 180000},
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1100, -80],
            "id": "a1000005-0005-0005-0005-000000000005",
            "name": "Processar Fatura",
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://host.docker.internal:3000/api/sendFile",
                "sendHeaders": True,
                "headerParameters": {"parameters": [{"name": "Content-Type", "value": "application/json"}]},
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": (
                    "={{ JSON.stringify({"
                    " session: $(\"Extrair Dados\").item.json.session,"
                    " chatId: $(\"Extrair Dados\").item.json.from,"
                    " file: { url: $json.url, filename: $json.filename },"
                    " caption: '📈 *Planilha Claro pronta!*\\n\\n✅ ' + $json.total_linhas + ' linhas\\n📦 GB: ' + $json.gb_compartilhado + 'GB\\n📅 Fidelidade: ' + $json.fidelidade"
                    " }) }}"
                ),
                "options": {},
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [1320, -80],
            "id": "a1000006-0006-0006-0006-000000000006",
            "name": "Enviar Excel WAHA",
        },
        {
            "parameters": {
                "resource": "Chatting",
                "operation": "Send Text",
                "session": "={{ $(\"Extrair Dados\").item.json.session }}",
                "chatId": "={{ $(\"Extrair Dados\").item.json.from }}",
                "text": "=❌ Envie apenas arquivos PDF da fatura Claro Empresas.",
                "requestOptions": {},
            },
            "type": "@devlikeapro/n8n-nodes-waha.WAHA",
            "typeVersion": 202502,
            "position": [660, 120],
            "id": "a1000007-0007-0007-0007-000000000007",
            "name": "Nao e PDF",
            "credentials": {"wahaApi": {"id": "NOUNjHnsj7kUbPnW", "name": "WAHA account"}},
        },
    ],
    "connections": {
        "WAHA Trigger":     {"main": [[{"node": "Extrair Dados",    "type": "main", "index": 0}]]},
        "Extrair Dados":    {"main": [[{"node": "E PDF",            "type": "main", "index": 0}]]},
        "E PDF":            {"main": [
            [{"node": "Aguardando",       "type": "main", "index": 0}],
            [{"node": "Nao e PDF",        "type": "main", "index": 0}],
        ]},
        "Aguardando":       {"main": [[{"node": "Download PDF",     "type": "main", "index": 0}]]},
        "Download PDF":     {"main": [[{"node": "Processar Fatura", "type": "main", "index": 0}]]},
        "Processar Fatura": {"main": [[{"node": "Enviar Excel WAHA","type": "main", "index": 0}]]},
    },
}

print("Atualizando workflow...")
result = api("PUT", f"/workflows/{WORKFLOW_ID}", workflow)
print("PUT OK —", result.get("name"))

# Verificar os valores gravados no nó Extrair Dados
for node in result["nodes"]:
    if node["name"] == "Extrair Dados":
        print("\nValores em Extrair Dados:")
        for a in node["parameters"]["assignments"]["assignments"]:
            print(f"  {a['name']}: {repr(a['value'])}")

# Reativar
print("\nReativando workflow...")
act = api("POST", f"/workflows/{WORKFLOW_ID}/activate")
print("Ativo:", act.get("active"))
