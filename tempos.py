#!/usr/bin/env python3
"""Tempos de espera reais numa estação do Metro de Lisboa.

Uso:
  python3 tempos.py Saldanha
  python3 tempos.py "Praça do Comércio, Lisboa"     # morada -> estação +próxima
  python3 tempos.py 38.7075 -9.1364                 # coordenadas
"""
import json, math, os, sys, unicodedata, urllib.parse, urllib.request
import ml_api

BASE = os.path.dirname(__file__)
STATIONS = json.load(open(os.path.join(BASE, "stations.json"), encoding="utf-8"))
S = {s["id"]: s for s in STATIONS}

def strip(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if unicodedata.category(c) != "Mn")

def hav(a, b, c, d):
    R = 6371000; r = math.radians
    dp = r(c-a); dl = r(d-b)
    x = math.sin(dp/2)**2 + math.cos(r(a))*math.cos(r(c))*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(x))

def geocode(q):
    u = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1, "countrycodes": "pt"})
    req = urllib.request.Request(u, headers={"User-Agent": "metro-lisboa/1.0"})
    d = json.load(urllib.request.urlopen(req, timeout=15))
    if not d: raise SystemExit(f"Morada não encontrada: {q!r}")
    return float(d[0]["lat"]), float(d[0]["lon"])

def nearest(lat, lon):
    return min(STATIONS, key=lambda s: hav(lat, lon, s["lat"], s["lon"]))

def resolve(args):
    # coordenadas?
    try:
        return nearest(float(args[0]), float(args[1]))
    except (ValueError, IndexError):
        pass
    q = " ".join(args)
    # nome de estação?
    hits = [s for s in STATIONS if strip(q) in strip(s["nome"])]
    if hits:
        return hits[0]
    # senão, morada -> estação mais próxima
    return nearest(*geocode(q))

def fmt(sec):
    sec = int(sec); return "a chegar" if sec < 30 else f"{sec//60}m{sec%60:02d}"

def main():
    if not sys.argv[1:]:
        raise SystemExit(__doc__)
    st = resolve(sys.argv[1:])
    destinos = {d["id_destino"]: d["nome_destino"] for d in ml_api.info_destinos()}
    linhas = "  ".join(f"{l['nome']}" for l in st["linhas"])
    print(f"\n🚇 {st['nome']}  ({linhas})\n")

    rows = [r for r in ml_api.tempos_todas() if r["stop_id"] == st["id"]]
    if not rows:
        print("  Sem dados de tempo de espera neste momento.")
        return
    for r in rows:
        dest = destinos.get(str(r.get("destino")), f"destino {r.get('destino')}")
        ts = [r.get("tempoChegada1"), r.get("tempoChegada2"), r.get("tempoChegada3")]
        ts = [fmt(t) for t in ts if t not in (None, "", 0, "0")]
        if r.get("sairServico") in (1, "1"):
            continue
        print(f"  → {dest:22} {' · '.join(ts)}")
    print()

if __name__ == "__main__":
    main()
