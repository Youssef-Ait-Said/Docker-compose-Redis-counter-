# Envoie 100 requêtes à /predict
for ($i = 1; $i -le 100; $i++) {
    curl.exe -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{\"values\":[5.1,3.5,1.4,0.2]}' | Out-Null
}

Write-Host "100 requetes envoyees"

# Lit le compteur
curl.exe -s http://localhost:8000/stats