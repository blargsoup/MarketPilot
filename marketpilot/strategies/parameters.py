"""
Parameter definitions for A-RVol.
"""

from dataclasses import dataclass


@dataclass
class ARVolParameters:

    # TQQQ -> QLD
    rvol_to_qld: float = 0.18
    vr_to_qld: float = 1.25
    spy_to_qld: float = -3.0

    # QLD -> Defensive
    rvol_to_def: float = 0.36
    vr_to_def: float = 1.40
    spy_to_def: float = -3.0
    credit_to_def: float = -4.0

    # QLD -> TQQQ
    rvol_to_tqqq: float = 0.14
    vr_to_tqqq: float = 0.90
    spy_to_tqqq: float = 3.0

    # Defensive -> QLD
    rvol_to_qld_return: float = 0.25
    vr_to_qld_return: float = 1.10
    spy_to_qld_return: float = -1.5