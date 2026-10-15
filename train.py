import os
import joblib
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Dossier de sortie du modèle (surchargé par une variable d'environnement)
MODEL_DIR = os.getenv("MODEL_DIR", "/models")

X, y = load_iris(return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

clf = RandomForestClassifier(n_estimators=100, random_state=42).fit(X_tr, y_tr)
print(f"Accuracy: {clf.score(X_te, y_te):.3f}")

os.makedirs(MODEL_DIR, exist_ok=True)
joblib.dump(clf, f"{MODEL_DIR}/model.joblib")
print(f"Modèle sauvegardé dans {MODEL_DIR}/model.joblib")
