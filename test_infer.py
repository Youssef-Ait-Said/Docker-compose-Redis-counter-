import json
import urllib.request


def post(path, payload):
    req = urllib.request.Request(
        f"http://localhost:8000{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req))


# Un exemple par classe (valeurs typiques du jeu iris)
cases = {
    "setosa": [5.1, 3.5, 1.4, 0.2],
    "versicolor": [6.0, 2.9, 4.5, 1.5],
    "virginica": [6.7, 3.0, 5.8, 2.2],
}
for expected, values in cases.items():
    r = post("/predict", {"values": values})
    print(expected, "->", r, "OK" if r["class"] == expected else "ECART")

print(post("/predict/batch", {"samples": list(cases.values())}))
