from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PhoneLine:
    telefone: str           # "11913386865" (sem máscara)
    telefone_mask: str      # "(11) 91338 6865" (com máscara)
    plano: str              # "Plugin Smartphone" | "Tablet e Modem" | "Claro Pós 25GB"
    gb: str                 # "900GB" | "1TB" | "15MB" (com unidade)
    fidelidade: Optional[str]  # "03/11/2026" ou None
    valor: float            # 21.37
    mb_usage: float = 0.0           # Mbytes utilizados (coluna H "Dados Local")
    consumo: str = "Sim"
    is_individual_plan: bool = False  # True se Cenário 2
