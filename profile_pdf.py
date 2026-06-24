"""Verifica onde o tempo é gasto por pdfplumber pagina a pagina."""
import time, warnings, logging, sys
logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
from pathlib import Path
import pdfplumber

pdf_path = Path("EF1.CL.16012026_154456033_042.REG.0013535_M1.20260114_200038.pdf")

block_pages   = []   # paginas com bloco de cobranças
detail_pages  = []   # paginas com DETALHAMENTO
other_pages   = []   # paginas sem nada relevante

times_text    = []
times_words   = []

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        t0 = time.perf_counter()
        text = page.extract_text() or ""
        t1 = time.perf_counter()
        times_text.append(t1 - t0)

        t2 = time.perf_counter()
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        t3 = time.perf_counter()
        times_words.append(t3 - t2)

        tu = text.upper()
        if "COBRAN" in tu and "CELULAR" in tu:
            block_pages.append(i)
        elif "DETALHAMENTO" in tu:
            detail_pages.append(i)
        else:
            other_pages.append(i)

print(f"Total paginas:    {len(pdf.pages)}")
print(f"  Bloco cobr.:   {len(block_pages)} pags (precisam de extract_words)")
print(f"  Detalhamento:  {len(detail_pages)} pags (so precisam de extract_text)")
print(f"  Outras:        {len(other_pages)} pags (podem ser puladas)")
print()
print(f"Tempo extract_text  total: {sum(times_text):.2f}s  avg={sum(times_text)/len(times_text)*1000:.0f}ms/pag")
print(f"Tempo extract_words total: {sum(times_words):.2f}s  avg={sum(times_words)/len(times_words)*1000:.0f}ms/pag")
print()
# Tempo se só processar o necessário por tipo
t_bloco   = sum(times_words[i] for i in block_pages)
t_detalhe = sum(times_text[i]  for i in detail_pages)
t_outras  = sum(times_text[i]  for i in other_pages)
print(f"Tempo OTIMIZADO seria:     {t_bloco + t_detalhe:.2f}s  ({t_bloco:.2f} words + {t_detalhe:.2f} text + {t_outras:.2f} skip)")
