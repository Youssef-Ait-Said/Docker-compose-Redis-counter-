# Mesures de la version NAIVE puis OPTIMISEE (PowerShell). A lancer depuis le dossier du projet.
# Les chiffres obtenus alimentent le tableau de l'etape 5.

function Mesurer($label, $dockerfile, $tag) {
    Write-Host "=== $label : build a froid ==="
    docker builder prune -af | Out-Null
    $froid = Measure-Command { docker build -f $dockerfile -t $tag . | Out-Null }
    Write-Host ("A froid : {0:N1} s" -f $froid.TotalSeconds)

    Add-Content serve.py "# change"
    Write-Host "=== $label : build a chaud (serve.py modifie) ==="
    $chaud = Measure-Command { docker build -f $dockerfile -t $tag . | Out-Null }
    Write-Host ("A chaud : {0:N1} s" -f $chaud.TotalSeconds)

    # Retire la ligne ajoutee
    (Get-Content serve.py | Select-Object -SkipLast 1) | Set-Content serve.py
    docker images $tag
}

Mesurer "NAIVE inference"     "Dockerfile.infer.naive" "iris-infer:naive"
Mesurer "OPTIMISEE inference" "Dockerfile.infer"       "iris-infer:opt"
Mesurer "NAIVE train"         "Dockerfile.train.naive" "iris-train:naive"
Mesurer "OPTIMISEE train"     "Dockerfile.train"       "iris-train:opt"
