<div align="center">

<h1>Claro Dados</h1>

<p>Sistema de extração e processamento de dados de faturas Claro Empresas —<br/>converte PDFs de detalhamento em planilhas Excel estruturadas.</p>

<p>
  <img src="https://img.shields.io/badge/Status-Ativo-22c55e?style=flat-square"/>
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask&logoColor=white"/>
  <img src="https://img.shields.io/badge/PyMuPDF-1.24-blue?style=flat-square"/>
</p>

</div>

---

## Sobre o projeto

Claro Dados automatiza a extração de informações de faturas PDF da Claro Empresas. O sistema lê arquivos de detalhamento, identifica cada linha telefônica com seu plano, valor, consumo de dados e data de fidelidade, e exporta tudo em um Excel padronizado — eliminando horas de digitação manual.

O projeto oferece três interfaces de uso: linha de comando, API REST para integração com outros sistemas (como n8n e automações WhatsApp), e um aplicativo desktop com interface gráfica dark theme.

---

## Funcionalidades

**Extração de dados**
- Leitura de PDFs de fatura Claro Empresas com PyMuPDF
- Identificação de planos: Plugin Smartphone, Tablet e Modem, Claro Pós, Claro Controle, Claro Flex
- Extração de número, plano, valor, GB compartilhado, consumo (MB) e fidelidade
- Deduplicação automática de linhas repetidas entre PDFs

**Exportação**
- Geração de Excel (.xlsx) no layout padrão DETALHAMENTO com openpyxl
- Suporte a múltiplos PDFs processados em lote com dados unificados

**Três interfaces**
- CLI (`main.py`) — uso direto no terminal com flag `--debug`
- API REST (`api.py`) — Flask com endpoints `/upload`, `/generate` e `/extract` para integração externa
- GUI Desktop (`app_gui.py`) — interface gráfica dark theme com drag-and-drop (customtkinter + tkinterdnd2)

**API REST**
- Buffer de sessão: envie múltiplos PDFs e processe tudo de uma vez
- Upload automático do Excel gerado para link público (uguu.se)
- Limpeza automática de arquivos temporários após 1 hora

---

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.9+ |
| Leitura de PDF | PyMuPDF (fitz) |
| API REST | Flask 3.0 |
| Interface gráfica | customtkinter · tkinterdnd2 |
| Exportação Excel | openpyxl |
| Empacotamento | PyInstaller |

---

## Rodando localmente

```bash
git clone https://github.com/Miguel-Pires/Claro-Dados-Sistema-de-Extra-o-e-Processamento-de-Dados.git
cd Claro-Dados-Sistema-de-Extra-o-e-Processamento-de-Dados

pip install -r requirements.txt
```

**CLI — processar um PDF:**

```bash
python main.py fatura.pdf
python main.py fatura.pdf resultado.xlsx --debug
```

**API REST:**

```bash
python api.py
# Sobe em http://localhost:8765
```

Endpoints disponíveis:

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Status da API |
| POST | `/upload` | Envia PDF para buffer da sessão |
| POST | `/generate` | Processa todos os PDFs do buffer e retorna Excel |
| POST | `/extract` | Processa um único PDF diretamente |

**GUI Desktop:**

```bash
python app_gui.py
```

**Gerar executável .exe:**

```bash
build.bat
```

---

## Estrutura do projeto

```
Claro-dados/
├── main.py                  # Ponto de entrada CLI
├── api.py                   # API REST Flask
├── app_gui.py               # Interface gráfica desktop
├── build.bat                # Script de build PyInstaller
├── requirements.txt
└── src/
    ├── models/
    │   └── line.py          # Dataclass PhoneLine
    ├── parser/
    │   ├── pdf_reader.py    # Orquestrador — abre PDF e coordena extração
    │   ├── block_parser.py  # Parser de blocos com bounding boxes
    │   ├── phone_parser.py  # Extração de números de telefone
    │   ├── value_parser.py  # Extração de valores monetários
    │   ├── mb_parser.py     # Extração de consumo em MB
    │   ├── shared_plan.py   # Detecção de plano compartilhado e GB
    │   └── fidelity_parser.py # Extração de datas de fidelidade
    └── export/
        └── excel_exporter.py # Geração do Excel no layout DETALHAMENTO
```

---

<div align="center">
  <sub>Desenvolvido por <a href="https://github.com/Miguel-Pires">Miguel Pires</a></sub>
</div>
