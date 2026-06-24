"""
Analisador de Faturas v3.2
- Botão Analisar centralizado com largura máxima responsiva
- Animações suaves: drop zone pulse, hover em linhas, progress bar
- Visual mais refinado: header accent, cards com borda, ícone de marca
"""
from __future__ import annotations

import os
import sys
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog
from typing import Optional

if getattr(sys, "frozen", False):
    _BASE = Path(sys._MEIPASS)          # type: ignore[attr-defined]
    sys.path.insert(0, str(_BASE))
else:
    _BASE = Path(__file__).parent

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from src.parser import read_pdf
from src.export import export_excel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Paleta ──────────────────────────────────────────────────────────────────
BG      = "#111111"
CARD    = "#1a1a1a"
CARD2   = "#222222"
CARD3   = "#2c2c2c"
BORDER  = "#333333"
BORDER2 = "#484848"
ACCENT  = "#4f8ef7"
ACCENT2 = "#6ba3fa"
ACCENTD = "#2563eb"
SUCCESS = "#22c55e"
ERROR   = "#ef4444"
WARN    = "#f97316"
TEXT    = "#f1f5f9"
TEXT2   = "#94a3b8"
MUTED   = "#64748b"
MUTED2  = "#3f4f5f"

PLAN_BADGE: dict[str, tuple[str, str]] = {
    "Plugin Smartphone": ("#1e3a5f", "#60a5fa"),
    "Tablet e Modem":    ("#1e3a4a", "#7dd3fc"),
    "Claro Pos":         ("#1e2d5f", "#818cf8"),
    "Claro Controle":    ("#1e3560", "#6366f1"),
    "Claro Flex":        ("#1e3555", "#a78bfa"),
}


def _plan_badge(name: str) -> tuple[str, str]:
    for key, val in PLAN_BADGE.items():
        if key.lower() in name.lower():
            return val
    return ("#2a2a2a", MUTED)


def _unique_path(base: Path) -> Path:
    if not base.exists():
        return base
    for i in range(2, 999):
        candidate = base.with_stem(f"{base.stem}_{i}")
        if not candidate.exists():
            return candidate
    return base


# ── Estado por arquivo ───────────────────────────────────────────────────────
@dataclass
class Entry:
    path: Path
    status: str = "pending"       # pending | running | done | error | cancelled
    out_path: Optional[Path] = None
    n_lines: int = 0
    error_msg: str = ""
    out_dir: Optional[Path] = None


# ── Widget de linha de arquivo ───────────────────────────────────────────────
class FileRow(ctk.CTkFrame):
    _H = 48

    def __init__(self, master, entry: Entry, on_remove):
        super().__init__(master, fg_color=CARD2, corner_radius=12, height=self._H)
        self.pack_propagate(False)
        self._entry = entry

        self._icon = ctk.CTkLabel(
            self, text="○", width=26,
            font=ctk.CTkFont(size=13), text_color=MUTED2,
        )
        self._icon.pack(side="left", padx=(12, 4))

        name = entry.path.name
        if len(name) > 46:
            name = name[:43] + "…"
        self._name_lbl = ctk.CTkLabel(
            self, text=name, anchor="w",
            font=ctk.CTkFont(size=12), text_color=TEXT,
        )
        self._name_lbl.pack(side="left", fill="x", expand=True)

        self._open_btn = ctk.CTkButton(
            self, text="Abrir ↗", width=72, height=28, corner_radius=14,
            fg_color="#1a3a1a", hover_color="#1f4d1f",
            border_width=1, border_color=SUCCESS,
            text_color=SUCCESS, font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_file,
        )

        try:
            kb = entry.path.stat().st_size // 1024
            size_txt = f"{kb} KB"
        except OSError:
            size_txt = ""
        self._size_lbl = ctk.CTkLabel(
            self, text=size_txt, width=54,
            font=ctk.CTkFont(size=11), text_color=MUTED,
        )
        self._size_lbl.pack(side="right", padx=(0, 4))

        self._rm = ctk.CTkButton(
            self, text="✕", width=28, height=28, corner_radius=14,
            fg_color="transparent", hover_color="#3d1414",
            text_color=MUTED, font=ctk.CTkFont(size=11),
            command=on_remove,
        )
        self._rm.pack(side="right", padx=(0, 10))

        # Hover highlight
        for w in (self, self._icon, self._name_lbl, self._size_lbl):
            w.bind("<Enter>", self._on_hover_in)
            w.bind("<Leave>", self._on_hover_out)

    def _on_hover_in(self, _=None):
        if self._entry.status not in ("done", "running", "error"):
            self.configure(fg_color=CARD3)

    def _on_hover_out(self, _=None):
        if self._entry.status not in ("done", "running", "error"):
            self.configure(fg_color=CARD2)

    def to_running(self) -> None:
        self._icon.configure(text="◌", text_color=ACCENT)
        self.configure(fg_color=CARD2)
        self._rm.configure(state="disabled")
        self._spin_step = 0
        self._spin()

    def _spin(self) -> None:
        if self._entry.status != "running":
            return
        chars = "◌◍●◍"
        self._icon.configure(text=chars[self._spin_step % len(chars)])
        self._spin_step += 1
        self.after(300, self._spin)

    def to_done(self) -> None:
        self._entry.status = "done"
        self._icon.configure(text="✓", text_color=SUCCESS)
        self.configure(fg_color="#0f2318")
        self._name_lbl.configure(text_color="#86efac")
        self._size_lbl.pack_forget()
        self._rm.pack_forget()
        self._open_btn.pack(side="right", padx=(0, 10), pady=8)

    def to_error(self, msg: str) -> None:
        self._entry.status = "error"
        self._icon.configure(text="✗", text_color=ERROR)
        self.configure(fg_color="#1e0f0f")
        self._name_lbl.configure(
            text=f"{self._entry.path.name}  — {msg[:40]}", text_color="#fca5a5"
        )
        self._rm.configure(state="normal", text_color="#f87171")

    def to_cancelled(self) -> None:
        self._entry.status = "cancelled"
        self._icon.configure(text="–", text_color=MUTED)
        self.configure(fg_color=CARD2)
        self._rm.configure(state="normal")

    def _open_file(self) -> None:
        if self._entry.out_path and self._entry.out_path.exists():
            os.startfile(str(self._entry.out_path))


# ── Aplicação ────────────────────────────────────────────────────────────────
class App(TkinterDnD.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Analisador de Faturas")
        self.geometry("900x640")
        self.minsize(560, 460)
        self.configure(bg=BG)
        self.resizable(True, True)
        self.state("zoomed")

        self._entries: list[Entry]         = []
        self._rows:    dict[Path, FileRow] = {}
        self._cancel:  threading.Event     = threading.Event()
        self._running: bool                = False
        self._out_dir: Optional[Path]      = None
        self._prog_target: float           = 0.0
        self._dragging: bool               = False
        self._pulse_id: Optional[str]      = None

        ico = _BASE / "icon.ico"
        if ico.exists():
            self.iconbitmap(str(ico))

        self._build()
        self.bind("<Return>", lambda _: self._on_analyze())
        self.bind("<Escape>", lambda _: self._on_cancel())
        self.bind("<Configure>", self._on_resize)

        # Inicia animação idle da drop zone
        self.after(2500, self._pulse_drop)

    # ── Responsividade ───────────────────────────────────────────────────────

    def _on_resize(self, event) -> None:
        if event.widget is not self:
            return
        w = event.width
        # Botão com largura máx de 760px, centralizado, margem mínima de 20px
        max_btn = min(w - 40, 760)
        px = max(20, (w - max_btn) // 2)
        try:
            self._act.pack_configure(padx=px)
        except Exception:
            pass

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        root = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        root.pack(fill="both", expand=True)

        # ── Footer ────────────────────────────────────────────────────────────
        bot = ctk.CTkFrame(root, fg_color=CARD, corner_radius=0, height=46)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)

        self._bar = ctk.CTkProgressBar(
            bot, height=3, corner_radius=0,
            fg_color=CARD, progress_color=ACCENT,
        )
        self._bar.pack(fill="x", side="top")
        self._bar.set(0)

        self._status_lbl = ctk.CTkLabel(
            bot, text="Pronto.",
            font=ctk.CTkFont(size=12), text_color=MUTED, anchor="w",
        )
        self._status_lbl.pack(side="left", padx=16, fill="y")

        ctk.CTkFrame(bot, fg_color=BORDER, width=1).pack(side="left", fill="y", pady=8)

        self._dest_lbl = ctk.CTkLabel(
            bot, text="📂  mesma pasta do PDF",
            font=ctk.CTkFont(size=11), text_color=MUTED,
            anchor="w", cursor="hand2",
        )
        self._dest_lbl.pack(side="left", padx=(10, 4), fill="y")
        self._dest_lbl.bind("<Button-1>", self._open_dest_folder)
        self._dest_lbl.bind("<Enter>",    lambda _: self._dest_lbl.configure(text_color=ACCENT2))
        self._dest_lbl.bind("<Leave>",    lambda _: self._dest_lbl.configure(
            text_color=MUTED if self._out_dir is None else ACCENT))

        self._step_lbl = ctk.CTkLabel(
            bot, text="",
            font=ctk.CTkFont(size=11), text_color=MUTED, anchor="e",
        )
        self._step_lbl.pack(side="right", padx=16, fill="y")

        ctk.CTkFrame(bot, fg_color=BORDER, width=1).pack(side="right", fill="y", pady=10)

        gh = ctk.CTkLabel(
            bot, text="GitHub ↗",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=ACCENT, cursor="hand2",
        )
        gh.pack(side="right", padx=(4, 16), fill="y")
        gh.bind("<Button-1>", lambda _: webbrowser.open("https://github.com/Miguel-Pires"))
        gh.bind("<Enter>",    lambda _: gh.configure(text_color=ACCENT2))
        gh.bind("<Leave>",    lambda _: gh.configure(text_color=ACCENT))

        ctk.CTkLabel(
            bot, text="Miguel Pires",
            font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT2,
        ).pack(side="right", padx=(8, 2), fill="y")

        ctk.CTkLabel(
            bot, text="desenvolvido por",
            font=ctk.CTkFont(size=10), text_color=MUTED2,
        ).pack(side="right", padx=(12, 4), fill="y")

        # ── Header ────────────────────────────────────────────────────────────
        # Faixa de destaque no topo
        ctk.CTkFrame(root, fg_color=ACCENT, height=3, corner_radius=0).pack(
            fill="x", side="top"
        )

        hdr = ctk.CTkFrame(root, fg_color=CARD, corner_radius=0, height=58)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        brand = ctk.CTkFrame(hdr, fg_color="transparent")
        brand.pack(side="left", padx=(16, 8), fill="y")

        ctk.CTkLabel(
            brand, text="📊",
            font=ctk.CTkFont(size=20), text_color=ACCENT,
        ).pack(side="left", pady=14)

        ctk.CTkLabel(
            brand, text="  Analisador de Faturas",
            font=ctk.CTkFont(size=17, weight="bold"), text_color=TEXT, anchor="w",
        ).pack(side="left", fill="y")

        self._folder_btn = ctk.CTkButton(
            hdr, text="📁  Pasta de destino",
            width=170, height=34, corner_radius=17,
            fg_color=CARD2, hover_color=CARD3,
            border_width=1, border_color=BORDER2,
            text_color=TEXT2, font=ctk.CTkFont(size=12),
            command=self._pick_folder,
        )
        self._folder_btn.pack(side="right", padx=16, pady=12)

        # Separador
        ctk.CTkFrame(root, fg_color=BORDER, height=1).pack(fill="x", side="top")

        # ── Área de conteúdo ──────────────────────────────────────────────────
        main = ctk.CTkFrame(root, fg_color=BG, corner_radius=0)
        main.pack(fill="both", expand=True)

        # Drop zone
        self._drop = ctk.CTkFrame(
            main, height=118, corner_radius=14,
            fg_color=CARD, border_width=2, border_color=BORDER,
        )
        self._drop.pack(padx=20, pady=(16, 0), fill="x")
        self._drop.pack_propagate(False)

        self._drop_icon = ctk.CTkLabel(
            self._drop, text="↑",
            font=ctk.CTkFont(size=30, weight="bold"), text_color=MUTED2,
        )
        self._drop_icon.pack(pady=(12, 0))

        self._drop_lbl = ctk.CTkLabel(
            self._drop,
            text="Arraste as faturas PDF aqui  ·  ou  ·  clique para selecionar",
            font=ctk.CTkFont(size=13), text_color=MUTED,
        )
        self._drop_lbl.pack(pady=(2, 0))

        self._drop_hint = ctk.CTkLabel(
            self._drop, text="Suporta múltiplos arquivos  ·  .pdf",
            font=ctk.CTkFont(size=10), text_color=MUTED2,
        )
        self._drop_hint.pack(pady=(2, 0))

        for w in (self._drop, self._drop_icon, self._drop_lbl, self._drop_hint):
            w.drop_target_register(DND_FILES)
            w.dnd_bind("<<Drop>>",      self._on_drop)
            w.dnd_bind("<<DragEnter>>", self._drag_enter)
            w.dnd_bind("<<DragLeave>>", self._drag_leave)
            w.bind("<Button-1>",        lambda _: self._browse())
            w.configure(cursor="hand2")

        # Cabeçalho da lista
        list_hdr = ctk.CTkFrame(main, fg_color="transparent", height=30)
        list_hdr.pack(fill="x", padx=20, pady=(10, 0))
        list_hdr.pack_propagate(False)

        self._count_lbl = ctk.CTkLabel(
            list_hdr, text="Nenhum arquivo",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=MUTED, anchor="w",
        )
        self._count_lbl.pack(side="left")

        ctk.CTkButton(
            list_hdr, text="Limpar concluídos", width=130, height=26, corner_radius=13,
            fg_color="transparent", hover_color=CARD2,
            text_color=MUTED, font=ctk.CTkFont(size=11),
            command=self._clear_done,
        ).pack(side="right")

        ctk.CTkButton(
            list_hdr, text="Limpar tudo", width=90, height=26, corner_radius=13,
            fg_color="transparent", hover_color=CARD2,
            text_color=MUTED, font=ctk.CTkFont(size=11),
            command=self._clear_all,
        ).pack(side="right", padx=(0, 6))

        # Botões de ação — centralizados e responsivos via _on_resize
        self._act = ctk.CTkFrame(main, fg_color="transparent")
        self._act.pack(fill="x", padx=20, pady=(8, 18), side="bottom")

        self._analyze_btn = ctk.CTkButton(
            self._act, text="▶  Analisar",
            height=44, corner_radius=22,
            fg_color=ACCENT, hover_color=ACCENTD,
            border_width=1, border_color=ACCENT2,
            text_color="#fff", font=ctk.CTkFont(size=15, weight="bold"),
            command=self._on_analyze,
        )
        self._analyze_btn.pack(fill="x")

        self._cancel_btn = ctk.CTkButton(
            self._act, text="◼  Cancelar",
            height=44, corner_radius=22,
            fg_color="#200e0e", hover_color="#3d1414",
            border_width=1, border_color="#5a1c1c",
            text_color="#f87171", font=ctk.CTkFont(size=14),
            command=self._on_cancel,
        )

        # Lista com scroll
        self._list = ctk.CTkScrollableFrame(
            main, fg_color="transparent",
            scrollbar_fg_color=BG,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=BORDER2,
        )
        self._list.pack(fill="both", expand=True, padx=20, pady=(4, 0))

        self._empty_lbl = ctk.CTkLabel(
            self._list, text="Nenhum arquivo adicionado",
            text_color=MUTED2, font=ctk.CTkFont(size=12),
        )
        self._empty_lbl.pack(pady=20)

    # ── Animação idle da drop zone ────────────────────────────────────────────

    def _pulse_drop(self) -> None:
        if self._dragging or self._running:
            self.after(3000, self._pulse_drop)
            return

        frames = [
            (BORDER,    MUTED2),
            ("#3a4f6a", "#5a7fa0"),
            ("#4a6080", "#6a90b0"),
            ("#3a4f6a", "#5a7fa0"),
            (BORDER,    MUTED2),
        ]

        def step(i: int) -> None:
            if self._dragging or self._running:
                return
            border, icon = frames[i]
            try:
                self._drop.configure(border_color=border)
                self._drop_icon.configure(text_color=icon)
            except Exception:
                return
            if i + 1 < len(frames):
                self.after(180, lambda: step(i + 1))
            else:
                self.after(4500, self._pulse_drop)

        step(0)

    # ── Drop / Browse ─────────────────────────────────────────────────────────

    def _drag_enter(self, _e=None) -> None:
        self._dragging = True
        self._drop.configure(border_color=ACCENT, fg_color="#0d1e38")
        self._drop_icon.configure(text="↓", text_color=ACCENT)
        self._drop_lbl.configure(text="Solte aqui para adicionar", text_color=ACCENT2)
        self._drop_hint.configure(text_color=ACCENT2)

    def _drag_leave(self, _e=None) -> None:
        self._dragging = False
        self._drop.configure(border_color=BORDER, fg_color=CARD)
        self._drop_icon.configure(text="↑", text_color=MUTED2)
        self._drop_lbl.configure(
            text="Arraste as faturas PDF aqui  ·  ou  ·  clique para selecionar",
            text_color=MUTED,
        )
        self._drop_hint.configure(
            text="Suporta múltiplos arquivos  ·  .pdf", text_color=MUTED2
        )

    def _on_drop(self, event) -> None:
        self._dragging = False
        paths = [Path(f) for f in self.tk.splitlist(event.data)
                 if f.lower().endswith(".pdf")]
        added = self._add_entries(paths)

        if added:
            self._drop.configure(border_color="#16a34a", fg_color="#0a1f10")
            self._drop_icon.configure(text="✓", text_color=SUCCESS)
            self._drop_lbl.configure(
                text=f"✓  {added} arquivo(s) adicionado(s)", text_color=SUCCESS
            )
            self._drop_hint.configure(text_color=SUCCESS)
            self.after(1500, self._drag_leave)
        else:
            self._drag_leave()

    def _browse(self) -> None:
        if self._running:
            return
        files = filedialog.askopenfilenames(
            title="Selecionar faturas Claro Empresas",
            filetypes=[("PDF", "*.pdf")],
        )
        self._add_entries([Path(f) for f in files])

    def _pick_folder(self) -> None:
        d = filedialog.askdirectory(title="Pasta de destino dos arquivos Excel")
        if not d:
            return
        self._out_dir = Path(d)
        short = str(self._out_dir)
        if len(short) > 38:
            short = "…" + short[-35:]
        self._folder_btn.configure(text=f"📁  {short}", text_color=TEXT)
        self._update_dest_label(self._out_dir)

    def _update_dest_label(self, path: Optional[Path]) -> None:
        if path is None:
            self._dest_lbl.configure(text="📂  mesma pasta do PDF", text_color=MUTED)
        else:
            short = str(path)
            if len(short) > 42:
                short = "…" + short[-39:]
            self._dest_lbl.configure(text=f"📂  {short}", text_color=ACCENT)

    def _open_dest_folder(self, _=None) -> None:
        target = self._out_dir
        if target is None:
            for e in reversed(self._entries):
                if e.out_path:
                    target = e.out_path.parent
                    break
        if target and target.exists():
            os.startfile(str(target))

    # ── Gerenciamento de entradas ─────────────────────────────────────────────

    def _add_entries(self, paths: list[Path]) -> int:
        existing = {e.path for e in self._entries}
        added = 0
        for p in paths:
            if p not in existing:
                entry = Entry(path=p)
                self._entries.append(entry)
                self._add_row(entry)
                added += 1
        if added:
            self._refresh_count()
        return added

    def _add_row(self, entry: Entry) -> None:
        if self._empty_lbl.winfo_ismapped():
            self._empty_lbl.pack_forget()

        row = FileRow(
            self._list, entry,
            on_remove=lambda e=entry: self._remove(e),
        )
        row.pack(fill="x", pady=3)
        self._rows[entry.path] = row

    def _remove(self, entry: Entry) -> None:
        if self._running and entry.status == "running":
            return
        row = self._rows.pop(entry.path, None)
        if row:
            row.destroy()
        self._entries = [e for e in self._entries if e.path != entry.path]
        if not self._entries:
            self._empty_lbl.pack(pady=20)
        self._refresh_count()

    def _clear_done(self) -> None:
        for e in list(self._entries):
            if e.status == "done":
                self._remove(e)

    def _clear_all(self) -> None:
        if self._running:
            return
        for e in list(self._entries):
            self._remove(e)

    def _refresh_count(self) -> None:
        n       = len(self._entries)
        pending = sum(1 for e in self._entries if e.status == "pending")
        done    = sum(1 for e in self._entries if e.status == "done")

        if n == 0:
            self._count_lbl.configure(text="Nenhum arquivo", text_color=MUTED)
        else:
            parts = [f"{n} arquivo(s)"]
            if done:
                parts.append(f"{done} concluído(s)")
            if pending:
                parts.append(f"{pending} pendente(s)")
            self._count_lbl.configure(text="  ·  ".join(parts), text_color=TEXT)

    # ── Análise ───────────────────────────────────────────────────────────────

    def _on_analyze(self) -> None:
        if self._running:
            return
        pending = [e for e in self._entries if e.status == "pending"]
        if not pending:
            if self._entries:
                self._set_status("Todos os arquivos já foram processados.", WARN)
            else:
                self._drop.configure(border_color=WARN)
                self.after(1200, lambda: self._drop.configure(border_color=BORDER))
                self._set_status("Adicione pelo menos um PDF.", WARN)
            return

        self._running = True
        self._cancel.clear()

        self._analyze_btn.pack_forget()
        self._cancel_btn.pack(fill="x")
        self._bar.configure(progress_color=ACCENT)
        self._prog_target = 0.0
        self._bar.set(0)
        self._tick()

        threading.Thread(target=self._run, args=(pending,), daemon=True).start()

    def _on_cancel(self) -> None:
        if self._running:
            self._cancel.set()
            self._set_status("Cancelando…", WARN)

    # ── Thread de processamento ───────────────────────────────────────────────

    def _run(self, pending: list[Entry]) -> None:
        n = len(pending)
        for i, entry in enumerate(pending):
            if self._cancel.is_set():
                for e in pending[i:]:
                    e.status = "cancelled"
                    self.after(0, lambda r=self._rows.get(e.path): r and r.to_cancelled())
                break

            entry.status = "running"
            self.after(0, lambda r=self._rows.get(entry.path): r and r.to_running())
            self._prog_target = (i / n) * 0.9
            self._set_status(f"Processando  {entry.path.name}  ({i+1}/{n})…")

            try:
                lines = read_pdf(entry.path)

                out_dir  = self._out_dir or entry.path.parent
                out_path = _unique_path(out_dir / (entry.path.stem + ".xlsx"))
                export_excel(lines, out_path)

                entry.out_path = out_path
                entry.n_lines  = len(lines)
                entry.status   = "done"
                self.after(0, lambda r=self._rows.get(entry.path): r and r.to_done())
                if self._out_dir is None:
                    self.after(0, lambda p=out_path.parent: self._update_dest_label(p))

            except Exception as exc:
                entry.status    = "error"
                entry.error_msg = str(exc)
                self.after(
                    0,
                    lambda r=self._rows.get(entry.path), m=str(exc): r and r.to_error(m),
                )

            self._prog_target = (i + 1) / n

        self._prog_target = 1.0

        done      = sum(1 for e in self._entries if e.status == "done")
        cancelled = self._cancel.is_set()

        if cancelled:
            self.after(0, lambda: self._set_status("Análise cancelada.", WARN))
            self.after(0, lambda: self._bar.configure(progress_color=WARN))
        else:
            msg = f"Concluído!  {done} arquivo(s) gerado(s)."
            self.after(0, lambda: self._set_status(msg, SUCCESS))
            self.after(0, lambda: self._bar.configure(progress_color=SUCCESS))

        self.after(0, self._end_run)

    def _end_run(self) -> None:
        self._running = False
        self._cancel_btn.pack_forget()
        self._analyze_btn.pack(fill="x")
        self._refresh_count()
        # Reinicia pulse após conclusão
        self.after(3000, self._pulse_drop)

    # ── Progress tick (~30 fps) ───────────────────────────────────────────────

    def _tick(self) -> None:
        if not self._running and abs(self._bar.get() - self._prog_target) < 0.01:
            return
        cur  = self._bar.get()
        diff = self._prog_target - cur
        if abs(diff) > 0.003:
            self._bar.set(cur + diff * 0.12)
        else:
            self._bar.set(self._prog_target)
        self.after(33, self._tick)

    # ── Status ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.after(0, lambda: (
            self._status_lbl.configure(text=f"  {text}", text_color=color),
        ))


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    App().mainloop()
