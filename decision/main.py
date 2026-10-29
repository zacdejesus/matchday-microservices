"""Decision service (port 8002) – Team 4, equipment store.

Run from this folder:
    uvicorn main:app --port 8002 --reload
Docs: http://localhost:8002/docs
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Decisión – Equipo 4")

MAX_INSTALLMENT_RATIO = 0.30  # installment can be at most 30 % of monthly income


# Example route, already done: use it as a model for the others
@app.get("/salud")
def health():
    return {"estado": "ok"}


# --- POST /financiacion ---------------------------------------------------

# TODO 1: input model. A class that inherits from BaseModel with the three
# fields of the contract: importe, ingresos_mensuales, plazos.
# Use Field(...) to enforce the rules (> 0, between 1 and 24).
class FinancingRequest(BaseModel):
    pass


# TODO 2: the route. Decorator for POST /financiacion, receives a
# FinancingRequest and returns a dict with aprobada, cuota_mensual, motivo.
