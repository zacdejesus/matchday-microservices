"""Decision service (port 8002) – Team 4, equipment store.

Run from this folder:
    uvicorn main:app --port 8002 --reload
Docs: http://localhost:8002/docs
"""

from typing import Literal

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Decisión – Equipo 4")

DATA_URL = "http://localhost:8001"
TIMEOUT_SECONDS = 3
MAX_INSTALLMENT_RATIO = 0.30  # installment can be at most 30 % of monthly income
MAX_RECOMMENDATIONS = 3

# (max number of installments, interest rate) – first match wins
INTEREST_BRACKETS = [(3, 0.00), (6, 0.03), (12, 0.06), (24, 0.10)]

Size = Literal["XS", "S", "M", "L", "XL", "XXL"]


def euros(amount: float) -> str:
    """Format a number the Spanish way: 30.88 -> '30,88 €'."""
    return f"{amount:.2f}".replace(".", ",") + " €"


def percent(ratio: float) -> str:
    """Format a ratio as a percentage: 0.026 -> '2,6 %'."""
    return f"{ratio * 100:.1f}".replace(".", ",").replace(",0", "") + " %"


@app.get("/salud")
def health():
    return {"estado": "ok"}


# --- POST /financiacion ---------------------------------------------------

class FinancingRequest(BaseModel):
    importe: float = Field(..., gt=0)
    ingresos_mensuales: float = Field(..., gt=0)
    plazos: int = Field(..., ge=1, le=24)


def interest_for(installments: int) -> float:
    for max_installments, rate in INTEREST_BRACKETS:
        if installments <= max_installments:
            return rate
    return INTEREST_BRACKETS[-1][1]


@app.post("/financiacion")
def financing(request: FinancingRequest):
    rate = interest_for(request.plazos)
    total = round(request.importe * (1 + rate), 2)
    installment = round(request.importe * (1 + rate) / request.plazos, 2)
    ratio = installment / request.ingresos_mensuales
    approved = ratio <= MAX_INSTALLMENT_RATIO

    if approved:
        reason = (f"La cuota ({euros(installment)}) es el {percent(ratio)} de tus "
                  f"ingresos, por debajo del límite del 30 %")
    else:
        reason = (f"La cuota ({euros(installment)}) es el {percent(ratio)} de tus "
                  f"ingresos y supera el límite del 30 %")

    if rate == 0:
        interest_text = "Con 3 plazos o menos no se aplica interés."
    else:
        interest_text = (f"Al ser {request.plazos} plazos se aplica un "
                         f"{percent(rate)} de interés, así que el total pasa de "
                         f"{euros(request.importe)} a {euros(total)}.")
    verdict = "Te lo aprobamos." if approved else (
        "No te lo podemos aprobar: prueba con más plazos o un importe menor.")
    explanation = (f"Pagarías {request.plazos} cuota(s) de {euros(installment)}. "
                   f"{interest_text} {verdict}")

    return {
        "aprobada": approved,
        "cuota_mensual": installment,
        "motivo": reason,
        "interes_aplicado": rate,
        "total_a_pagar": total,
        "explicacion": explanation,
    }


# --- POST /recomendar -----------------------------------------------------

class RecommendationRequest(BaseModel):
    equipo: str = Field(..., min_length=1)
    presupuesto: float = Field(..., gt=0)
    talla: Size


def season_start(item: dict) -> int:
    """'2025/26' -> 2025, so seasons can be sorted as numbers."""
    try:
        return int(str(item.get("temporada", "0")).split("/")[0])
    except ValueError:
        return 0


@app.post("/recomendar")
def recommend(request: RecommendationRequest):
    team = request.equipo.strip()
    if not team:
        raise HTTPException(status_code=422, detail="El equipo no puede estar vacío")

    try:
        response = requests.get(f"{DATA_URL}/equipaciones",
                                params={"equipo": team},
                                timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        items = response.json()
    except (requests.RequestException, ValueError):
        raise HTTPException(status_code=503, detail="El servicio de Datos no responde")

    matches = [
        item for item in items
        if item.get("talla") == request.talla
        and item.get("precio", 0) <= request.presupuesto
        and item.get("stock", 0) > 0
    ]
    # Newest season first; same season -> cheapest first
    matches.sort(key=lambda item: (-season_start(item), item.get("precio", 0)))
    best = matches[:MAX_RECOMMENDATIONS]

    budget = euros(request.presupuesto)
    if best:
        reason = (f"{len(best)} equipacion(es) del {team} en talla {request.talla} "
                  f"por {budget} o menos, de la más nueva a la más antigua")
    elif not items:
        reason = f"No hay equipaciones del {team} en el catálogo"
    else:
        reason = (f"No hay equipaciones del {team} en talla {request.talla} con stock "
                  f"por {budget} o menos")

    return {"recomendaciones": best, "motivo": reason}
