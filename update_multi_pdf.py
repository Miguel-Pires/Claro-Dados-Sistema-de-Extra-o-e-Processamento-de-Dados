"""
Atualiza o workflow n8n para suportar múltiplos PDFs.

Novo fluxo:
  PDF recebido → /upload → "PDF {N} recebido! Mande mais ou envie 'gerar' para criar a planilha."
  Texto "gerar" → /generate → envia link do Excel

Para isso, modifica:
  1. Nó "Processar Fatura" → chama /upload em vez de /extract
  2. Nó "Enviar Excel WAHA" após upload → manda mensagem de confirmação
  3. Adiciona condição "É Gerar?" no ramo FALSE do filtro "E PDF?"
  4. Adiciona nó "Gerar Planilha" → chama /generate
  5. Adiciona nó "Enviar Link Excel" → manda o link
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
API_BASE = "http://host.docker.internal:8765"


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
        print("HTTP Error:", e.code, e.read().decode()[:1000])
        raise


def api_post(path):
    req = urllib.request.Request(
        f"{BASE}{path}", data=b"{}", method="POST", headers=HEADERS
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# ─── GET estado atual ────────────────────────────────────────────────────────
wf = api_get(f"/workflows/{WF_ID}")
nodes = {n["name"]: n for n in wf["nodes"]}
conns = wf.get("connections", {})

print("Nodes atuais:", list(nodes.keys()))

# ─── 1. Atualiza "Processar Fatura" → chama /upload ─────────────────────────
UPLOAD_NODE = "Processar Fatura"
if UPLOAD_NODE in nodes:
    nodes[UPLOAD_NODE]["parameters"] = {
        "method": "POST",
        "url": f"{API_BASE}/upload",
        "sendBody": True,
        "contentType": "multipart-form-data",
        "bodyParameters": {
            "parameters": [
                {
                    "parameterType": "formBinaryData",
                    "name": "pdf",
                    "inputDataFieldName": "data",
                },
                {
                    "name": "session_id",
                    "value": "={{ $('Extrair Dados').item.json.chatId }}",
                },
            ]
        },
        "options": {"response": {"response": {"responseFormat": "json"}}},
    }
    nodes[UPLOAD_NODE]["type"] = "n8n-nodes-base.httpRequest"
    nodes[UPLOAD_NODE]["typeVersion"] = 4.2
    print(f"OK: '{UPLOAD_NODE}' atualizado para /upload")

# ─── 2. Atualiza "Enviar Excel WAHA" → confirmação de upload ────────────────
CONFIRM_NODE = "Enviar Excel WAHA"
if CONFIRM_NODE in nodes:
    nodes[CONFIRM_NODE]["parameters"] = {
        "method": "POST",
        "url": "http://host.docker.internal:3000/api/sendText",
        "sendBody": True,
        "contentType": "json",
        "body": "={{ JSON.stringify({\n"
                "  session: 'default',\n"
                "  chatId: $('Extrair Dados').item.json.chatId,\n"
                "  text: '✅ PDF ' + $json.count + ' recebido(s). Envie mais faturas ou envie *gerar* para criar a planilha.'\n"
                "}) }}",
        "options": {},
    }
    nodes[CONFIRM_NODE]["type"] = "n8n-nodes-base.httpRequest"
    nodes[CONFIRM_NODE]["typeVersion"] = 4.2
    print(f"OK: '{CONFIRM_NODE}' atualizado para confirmacao de upload")

# ─── 3. Adiciona nó "É Gerar?" (bifurca o FALSE do filtro "E PDF?") ─────────
E_GERAR_ID = "b2000010-0001-0001-0001-000000000010"
if "É Gerar?" not in nodes:
    nodes["É Gerar?"] = {
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": False, "leftValue": "", "typeValidation": "loose", "version": 3},
                "conditions": [
                    {
                        "id": "g1",
                        "leftValue": "={{ $json.text ?? $json.body?.text ?? $json.payload?.body ?? '' }}",
                        "rightValue": "gerar",
                        "operator": {"type": "string", "operation": "equals"},
                    }
                ],
                "combinator": "and",
            },
            "looseTypeValidation": True,
            "options": {},
        },
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [880, 220],
        "id": E_GERAR_ID,
        "name": "É Gerar?",
    }
    print("OK: No 'E Gerar?' criado")

# ─── 4. Adiciona nó "Gerar Excel" → chama /generate ────────────────────────
GERAR_ID = "b2000011-0001-0001-0001-000000000011"
if "Gerar Excel" not in nodes:
    nodes["Gerar Excel"] = {
        "parameters": {
            "method": "POST",
            "url": f"{API_BASE}/generate",
            "sendBody": True,
            "contentType": "json",
            "body": '={{ JSON.stringify({ session_id: $("Extrair Dados").item.json.chatId }) }}',
            "options": {"response": {"response": {"responseFormat": "json"}}},
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1100, 180],
        "id": GERAR_ID,
        "name": "Gerar Excel",
    }
    print("OK: No 'Gerar Excel' criado")

# ─── 5. Adiciona nó "Enviar Link" → manda o link uguu.se ────────────────────
LINK_ID = "b2000012-0001-0001-0001-000000000012"
if "Enviar Link" not in nodes:
    nodes["Enviar Link"] = {
        "parameters": {
            "method": "POST",
            "url": "http://host.docker.internal:3000/api/sendText",
            "sendBody": True,
            "contentType": "json",
            "body": "={{ JSON.stringify({\n"
                    "  session: 'default',\n"
                    "  chatId: $('Extrair Dados').item.json.chatId,\n"
                    "  text: '📊 Planilha gerada com ' + $json.total_linhas + ' linhas!\\n\\n🔗 ' + $json.url\n"
                    "}) }}",
            "options": {},
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1320, 180],
        "id": LINK_ID,
        "name": "Enviar Link",
    }
    print("OK: No 'Enviar Link' criado")

# ─── 6. Adiciona "Instrucoes" para quando não é PDF nem gerar ────────────────
INST_ID = "b2000013-0001-0001-0001-000000000013"
if "Instrucoes" not in nodes:
    nodes["Instrucoes"] = {
        "parameters": {
            "method": "POST",
            "url": "http://host.docker.internal:3000/api/sendText",
            "sendBody": True,
            "contentType": "json",
            "body": "={{ JSON.stringify({\n"
                    "  session: 'default',\n"
                    "  chatId: $('Extrair Dados').item.json.chatId,\n"
                    "  text: '📎 Envie o(s) arquivo(s) PDF da fatura Claro Empresas.\\n\\nApós enviar todos os arquivos, envie *gerar* para criar a planilha Excel.'\n"
                    "}) }}",
            "options": {},
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1100, 380],
        "id": INST_ID,
        "name": "Instrucoes",
    }
    print("OK: No 'Instrucoes' criado")

# ─── 7. Atualiza conexões ────────────────────────────────────────────────────
# E PDF? TRUE → Aguardando → Download PDF → Processar Fatura → Enviar Excel WAHA (confirmação)
# E PDF? FALSE → É Gerar? TRUE → Gerar Excel → Enviar Link
#                             FALSE → Instrucoes

# Garante que "Nao e PDF" vire "É Gerar?" no branch FALSE de "E PDF?"
e_pdf_node = "E PDF"
if e_pdf_node in conns:
    # Branch 0 = TRUE (já configurado para o fluxo PDF)
    # Branch 1 = FALSE → É Gerar?
    main_branches = conns[e_pdf_node].get("main", [[], []])
    # Garante 2 branches
    while len(main_branches) < 2:
        main_branches.append([])
    main_branches[1] = [{"node": "É Gerar?", "type": "main", "index": 0}]
    conns[e_pdf_node]["main"] = main_branches
else:
    conns[e_pdf_node] = {
        "main": [
            [],  # TRUE: já configurado
            [{"node": "É Gerar?", "type": "main", "index": 0}],  # FALSE
        ]
    }

# É Gerar? TRUE → Gerar Excel; FALSE → Instrucoes
conns["É Gerar?"] = {
    "main": [
        [{"node": "Gerar Excel", "type": "main", "index": 0}],
        [{"node": "Instrucoes",  "type": "main", "index": 0}],
    ]
}

# Gerar Excel → Enviar Link
conns["Gerar Excel"] = {
    "main": [[{"node": "Enviar Link", "type": "main", "index": 0}]]
}

print("OK: Conexoes atualizadas")

# ─── 8. PUT de volta ─────────────────────────────────────────────────────────
payload = {
    "name": wf["name"],
    "nodes": list(nodes.values()),
    "connections": conns,
    "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")},
    "staticData": wf.get("staticData"),
}

print("\nAplicando mudancas no workflow...")
result = api_put(f"/workflows/{WF_ID}", payload)
print("PUT OK:", result["name"])
print("Nodes finais:", [n["name"] for n in result["nodes"]])

# Reativar
act = api_post(f"/workflows/{WF_ID}/activate")
print("Ativo:", act.get("active"))
