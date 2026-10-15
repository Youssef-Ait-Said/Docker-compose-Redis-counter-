# iris-docker

1. Test local (venv Python 3.11) :
   $env:MODEL_DIR=".\models"; python train.py
   $env:MODEL_PATH=".\models\model.joblib"; uvicorn serve:app --port 8000
   python test_infer.py
2. Test Docker : docker compose up --build  (puis python test_infer.py)
3. Reset : docker compose down -v
4. Mesures : .\mesures.ps1
5. Trivy : docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --severity HIGH,CRITICAL iris-infer:opt
