#!/usr/bin/env python3
"""Estação de metro mais próxima de uma localização ou morada.

Uso:
  python3 nearest.py 38.7223 -9.1393        # por coordenadas
  python3 nearest.py "Praça do Comércio, Lisboa"   # por morada
  python3 nearest.py "Rua Augusta 100, Lisboa" -n 3 # top 3
"""
import json, math, os, sys, urllib.parse, urllib.request

STATIONS = json.load(open(os.path.join(os.path.dirname(__file__), "stations.json"),
                          encoding="utf-8"))

def haversine(lat1, lon1, lat2, lon2):
    """Distância em metros entre dois pontos (fórmula de haversine)."""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def geocode(morada):
    """Converte morada -> (lat, lon) via Nominatim (OpenStreetMap)."""
    q = urllib.parse.urlencode({"q": morada, "format": "json", "limit": 1,
                                "countrycodes": "pt"})
    url = "https://nominatim.openstreetmap.org/search?" + q
    req = urllib.request.Request(url, headers={"User-Agent": "metro-lisboa-demo/1.0"})
    data = json.load(urllib.request.urlopen(req, timeout=15))
    if not data:
        raise SystemExit(f"Morada não encontrada: {morada!r}")
    return float(data[0]["lat"]), float(data[0]["lon"]), data[0]["display_name"]

def nearest(lat, lon, n=1):
    ranked = sorted(STATIONS, key=lambda s: haversine(lat, lon, s["lat"], s["lon"]))
    for s in ranked[:n]:
        s = dict(s, dist_m=round(haversine(lat, lon, s["lat"], s["lon"])))
        yield s

def main():
    args = [a for a in sys.argv[1:] if a != "-n"]
    n = 1
    if "-n" in sys.argv:
        n = int(sys.argv[sys.argv.index("-n") + 1]); args = args[:-1]
    if not args:
        raise SystemExit(__doc__)

    # duas floats -> coordenadas; senão -> morada
    try:
        lat, lon = float(args[0]), float(args[1]); origem = "coordenadas"
    except (ValueError, IndexError):
        lat, lon, origem = geocode(" ".join(args))

    print(f"Origem: {origem}\n  ({lat:.5f}, {lon:.5f})\n")
    for i, s in enumerate(nearest(lat, lon, n), 1):
        linhas = "  ".join(f"{l['nome']} ({l['cor']})" for l in s["linhas"])
        andar = round(s["dist_m"] / 80)  # ~80 m/min a pé
        print(f"{i}. {s['nome']}  —  {s['dist_m']} m  (~{andar} min a pé)")
        print(f"     Linhas: {linhas}")

if __name__ == "__main__":
    main()
