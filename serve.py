import os
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import redis

MODEL_PATH = os.getenv("MODEL_PATH", "/models/model.joblib")
CLASSES = ["setosa", "versicolor", "virginica"]

if not os.path.exists(MODEL_PATH):
    raise RuntimeError(f"Modèle introuvable : {MODEL_PATH} (l'entraînement a-t-il tourné ?)")

# Chargé une seule fois au démarrage, pas à chaque requête
model = joblib.load(MODEL_PATH)
db = redis.Redis(host= os.getenv("REDIS_HOST", "base"), port=6379, decode_responses=True)
app = FastAPI(title="Iris inference")


class Features(BaseModel):
    values: list[float] = Field(..., min_length=4, max_length=4)


class Batch(BaseModel):
    samples: list[list[float]] = Field(..., min_length=1)


@app.get("/health")
def health():
    return {"status": "ok", "model_path": MODEL_PATH}


@app.post("/predict")
def predict(f: Features):
    idx = int(model.predict([f.values])[0])
    proba = model.predict_proba([f.values])[0]
    db.incr("prediction:total")           #Ajouter 1 au conteur redis sinon le cree et l'initialise a 0
    return {"class": CLASSES[idx], "confidence": round(float(proba[idx]), 3)}

@app.get("/stats")
def stats():
    return {"total": int(db.get("prediction:total") or 0)}


@app.post("/predict/batch")
def predict_batch(b: Batch):
    if any(len(s) != 4 for s in b.samples):
        raise HTTPException(422, "Chaque échantillon doit avoir 4 valeurs")
    preds = model.predict(b.samples)
    return {"classes": [CLASSES[int(i)] for i in preds]}

