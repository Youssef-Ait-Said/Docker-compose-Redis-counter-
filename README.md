# iris-docker

Classifieur **Iris** (Random Forest, scikit-learn) conteneurisé avec Docker et orchestré avec Docker Compose. Une API FastAPI sert les prédictions et un compteur **Redis** persistant comptabilise le nombre de requêtes traitées.

Le projet compare aussi une image **naïve** et une image **optimisée** (taille, temps de build, sécurité).

## Architecture

```
┌──────────┐  écrit   ┌────────────────┐  lit (ro)  ┌──────────┐  incr   ┌────────────┐
│  train   │ ───────► │ volume models  │ ─────────► │  infer   │ ──────► │ base       │
│ (one-shot)│         │ model.joblib   │            │ FastAPI  │         │ Redis 7    │
└──────────┘          └────────────────┘            │ :8000    │         │ volume     │
                                                    └──────────┘         │ redis_data │
                                                                         └────────────┘
```

| Service | Image | Rôle |
|---------|-------|------|
| `train` | `Dockerfile.train` | Entraîne le modèle une fois et l'écrit dans le volume `models`, puis s'arrête. |
| `infer` | `Dockerfile.infer` | API FastAPI sur le port 8000. Démarre seulement quand `train` a terminé avec succès. Monte `models` en lecture seule et expose un `healthcheck`. |
| `base`  | `redis:7-alpine` | Compteur de prédictions, persistance AOF (`--appendonly yes`) dans le volume `redis_data`. |

## Structure du projet

```
iris-docker/
├── train.py                  # Entraînement et sauvegarde du modèle
├── serve.py                  # API FastAPI (inférence + compteur Redis)
├── test_infer.py             # Test fonctionnel de l'API
├── test-100.ps1              # Envoie 100 requêtes puis lit le compteur
├── mesures.ps1               # Mesures naïf vs optimisé (build à froid / à chaud, taille)
├── Dockerfile.train          # Image d'entraînement (optimisée)
├── Dockerfile.infer          # Image d'inférence (optimisée)
├── Dockerfile.train.naive    # Version naïve, pour comparaison
├── Dockerfile.infer.naive    # Version naïve, pour comparaison
├── docker-compose.yml
├── requirements-train.txt
├── requirements-infer.txt
├── .dockerignore
└── .gitignore
```

## Prérequis

- Docker et Docker Compose
- Python 3.11 (uniquement pour le test local sans Docker)
- PowerShell pour les scripts `.ps1`

## Lancement avec Docker (recommandé)

```bash
docker compose up --build
```

L'entraînement s'exécute d'abord, puis l'API est disponible sur `http://localhost:8000`. Dans un second terminal :

```bash
python test_infer.py
```

Arrêt et réinitialisation complète (supprime aussi les volumes, donc le modèle et le compteur) :

```bash
docker compose down -v
```

## Lancement local (sans Docker)

Nécessite un Redis accessible. Sans Docker Compose, le nom d'hôte par défaut `base` n'existe pas : il faut donc définir `REDIS_HOST`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-infer.txt

$env:MODEL_DIR = ".\models"
python train.py

$env:MODEL_PATH = ".\models\model.joblib"
$env:REDIS_HOST = "localhost"
uvicorn serve:app --port 8000
```

## API

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET`  | `/health` | État du service et chemin du modèle chargé. |
| `POST` | `/predict` | Prédit la classe d'un échantillon et incrémente le compteur Redis. |
| `POST` | `/predict/batch` | Prédit la classe de plusieurs échantillons (ne modifie pas le compteur). |
| `GET`  | `/stats` | Nombre total de prédictions effectuées via `/predict`. |

### Exemples

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"values": [5.1, 3.5, 1.4, 0.2]}'
# {"class":"setosa","confidence":...}

curl -X POST http://localhost:8000/predict/batch \
  -H "Content-Type: application/json" \
  -d '{"samples": [[5.1,3.5,1.4,0.2],[6.0,2.9,4.5,1.5],[6.7,3.0,5.8,2.2]]}'

curl http://localhost:8000/stats
# {"total":1}
```

Les features attendues sont dans l'ordre : longueur du sépale, largeur du sépale, longueur du pétale, largeur du pétale (en cm). Une liste qui ne contient pas exactement 4 valeurs est rejetée avec une erreur `422`.

### Variables d'environnement

| Variable | Défaut | Utilisée par | Rôle |
|----------|--------|--------------|------|
| `MODEL_DIR` | `/models` | `train.py` | Dossier de sortie du modèle. |
| `MODEL_PATH` | `/models/model.joblib` | `serve.py` | Chemin du modèle à charger. |
| `REDIS_HOST` | `base` | `serve.py` | Hôte Redis (nom du service Compose). |

## Test de persistance du compteur

```powershell
.\test-100.ps1                 # envoie 100 requêtes puis affiche /stats
docker compose restart infer   # ou: docker compose down (sans -v)
curl.exe -s http://localhost:8000/stats   # le compteur est conservé grâce à redis_data
```

`docker compose down -v` supprime le volume : le compteur repart de zéro.

## Optimisation des images

Les `Dockerfile.*` optimisés se distinguent des versions `.naive` par :

- **Multi-stage build** : les dépendances sont installées dans un venv au stage `builder`, seul ce venv est copié dans l'image finale.
- **Image de base `python:3.11-slim`** au lieu de `python:3.11`.
- **Ordre des couches** : `requirements-*.txt` est copié et installé avant le code, donc une modification de `serve.py` ne réinstalle pas les dépendances.
- **`--no-cache-dir`** pour ne pas conserver le cache pip dans l'image.
- **Utilisateur non-root** (`app`) à l'exécution.
- **Copie minimale** : seul le script nécessaire est copié dans chaque image, et `.dockerignore` limite le contexte de build.
- **Images séparées** : l'image d'entraînement n'embarque ni FastAPI, ni uvicorn, ni Redis.

### Mesures

```powershell
.\mesures.ps1
```

Le script construit chaque image à froid (cache vidé) puis à chaud (après modification de `serve.py`) et affiche la taille. Attention : il appelle `docker builder prune -af` et modifie temporairement `serve.py` ; il ne faut donc pas l'exécuter avec des modifications non commitées dans ce fichier.

### Analyse de vulnérabilités (Trivy)

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity HIGH,CRITICAL iris-infer:opt
```

## Notes

- `models/` est ignoré par Git et par Docker : le modèle est toujours régénéré par le service `train`.
- Le modèle est chargé une seule fois au démarrage de l'API, pas à chaque requête.
- Si Redis est indisponible, `/predict` et `/stats` échouent ; `/health` et `/predict/batch` restent fonctionnels.