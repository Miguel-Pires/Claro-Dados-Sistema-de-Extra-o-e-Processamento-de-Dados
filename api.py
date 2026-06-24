from __future__ import annotations

import io
import logging
import os
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from src.parser import read_pdf
from src.export import export_excel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

OUTPUT_DIR = Path(__file__).parent / "output"
SESSIONS_DIR = Path(__file__).parent / "sessions"
OUTPUT_DIR.mkdir(exist_ok=True)
SESSIONS_DIR.mkdir(exist_ok=True)

FILE_TTL = 3600       # 1 hora para arquivos de saída
SESSION_TTL = 7200    # 2 horas para sessões de upload


# ---------------------------------------------------------------------------
# Upload para uguu.se (link público acessível no celular)
# ---------------------------------------------------------------------------

def _upload_file(file_path: Path) -> str | None:
    import urllib.request
    import json as _json

    boundary = uuid.uuid4().hex
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    with open(file_path, "rb") as f:
        data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files[]"; filename="{file_path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        "https://uguu.se/upload",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "curl/8.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = _json.loads(r.read())
            return resp["files"][0]["url"]
    except Exception as e:
        app.logger.warning("Upload uguu.se falhou: %s", e)
        return None


# ---------------------------------------------------------------------------
# Limpeza automática
# ---------------------------------------------------------------------------

def _cleanup_old_files() -> None:
    now = time.time()
    for f in OUTPUT_DIR.glob("resultado_*.xlsx"):
        try:
            if now - f.stat().st_mtime > FILE_TTL:
                f.unlink()
        except OSError:
            pass


def _cleanup_session(session_dir: Path) -> None:
    now = time.time()
    if session_dir.exists():
        try:
            if now - session_dir.stat().st_mtime > SESSION_TTL:
                import shutil
                shutil.rmtree(session_dir, ignore_errors=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_dir(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_@.")
    d = SESSIONS_DIR / safe
    d.mkdir(exist_ok=True)
    return d


def _build_response(lines, excel_path) -> dict:
    public_url = _upload_file(excel_path)
    base_url = request.host_url.rstrip("/").replace("localhost", "host.docker.internal")
    local_url = f"{base_url}/output/{excel_path.name}"

    plans: dict[str, int] = {}
    for line in lines:
        plans[line.plano] = plans.get(line.plano, 0) + 1

    gb_set = list({line.gb for line in lines})

    return {
        "success": True,
        "url": public_url or local_url,
        "url_local": local_url,
        "filename": excel_path.name,
        "total_linhas": len(lines),
        "planos": plans,
        "gb_compartilhado": gb_set[0] if len(gb_set) == 1 else gb_set,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "claro-extractor"})


@app.route("/output/<filename>")
def serve_output(filename: str):
    return send_from_directory(str(OUTPUT_DIR), filename)


@app.route("/upload", methods=["POST"])
def upload():
    """
    Recebe um PDF e salva no buffer da sessão.
    Body: multipart/form-data com 'pdf' e 'session_id'.
    Retorna: {count: N} — quantos PDFs estão no buffer.
    """
    session_id = request.form.get("session_id", "default")
    if "pdf" not in request.files:
        return jsonify({"error": "Campo 'pdf' obrigatório"}), 400

    pdf_file = request.files["pdf"]
    sess_dir = _session_dir(session_id)

    # Salva com nome único para não sobrescrever
    filename = f"fatura_{uuid.uuid4().hex[:8]}.pdf"
    pdf_file.save(sess_dir / filename)
    app.logger.info("PDF salvo na sessão %s: %s", session_id, filename)

    count = len(list(sess_dir.glob("*.pdf")))
    return jsonify({"success": True, "count": count})


@app.route("/generate", methods=["POST"])
def generate():
    """
    Processa todos os PDFs do buffer da sessão e retorna Excel unificado.
    Body: JSON com 'session_id'.
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "default")
    sess_dir = _session_dir(session_id)

    pdfs = sorted(sess_dir.glob("*.pdf"))
    if not pdfs:
        return jsonify({"error": "Nenhum PDF no buffer. Envie os arquivos primeiro."}), 400

    app.logger.info("Gerando Excel para sessão %s: %d PDFs", session_id, len(pdfs))

    threading.Thread(target=_cleanup_old_files, daemon=True).start()

    all_lines = []
    seen = set()
    for pdf_path in pdfs:
        try:
            lines = read_pdf(pdf_path)
            for line in lines:
                if line.telefone not in seen:
                    seen.add(line.telefone)
                    all_lines.append(line)
        except Exception as e:
            app.logger.exception("Falha ao processar %s", pdf_path.name)

    if not all_lines:
        return jsonify({"error": "Nenhuma linha extraída dos PDFs"}), 422

    file_id = uuid.uuid4().hex[:8]
    excel_path = OUTPUT_DIR / f"resultado_{file_id}.xlsx"
    export_excel(all_lines, excel_path)

    # Limpa buffer da sessão
    import shutil
    shutil.rmtree(sess_dir, ignore_errors=True)
    app.logger.info("Sessão %s limpa após geração", session_id)

    return jsonify({**_build_response(all_lines, excel_path), "arquivos_processados": len(pdfs)})


@app.route("/extract", methods=["POST"])
def extract():
    """
    Processa um único PDF diretamente (sem buffer de sessão).
    Mantido para compatibilidade.
    """
    if "pdf" not in request.files:
        return jsonify({"error": "Campo 'pdf' obrigatório"}), 400

    pdf_file = request.files["pdf"]
    if not pdf_file.filename or not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Arquivo deve ser um .pdf"}), 400

    threading.Thread(target=_cleanup_old_files, daemon=True).start()

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "fatura.pdf"
        pdf_file.save(pdf_path)
        app.logger.info("PDF recebido: %s (%.1f KB)", pdf_file.filename, pdf_path.stat().st_size / 1024)

        try:
            lines = read_pdf(pdf_path)
        except Exception as e:
            app.logger.exception("Falha na extração")
            return jsonify({"error": f"Falha na extração: {str(e)}"}), 500

        if not lines:
            return jsonify({"error": "Nenhuma linha extraída do PDF"}), 422

        file_id = uuid.uuid4().hex[:8]
        excel_path = OUTPUT_DIR / f"resultado_{file_id}.xlsx"
        export_excel(lines, excel_path)

        return jsonify(_build_response(lines, excel_path))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    app.logger.info("Iniciando Claro Extractor API na porta %d", port)
    app.run(host="0.0.0.0", port=port, debug=False)
