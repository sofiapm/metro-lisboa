#!/usr/bin/env python3
"""Puxa as entradas/saídas do metro do OpenStreetMap e associa-as à estação
mais próxima. Gera exits.json e app/exits.js.

O GTFS oficial do Metro não tem saídas; o OSM tem (railway=subway_entrance).
"""
import json, math, os, time, urllib.request

BASE = os.path.dirname(__file__)
MAX_DIST = 350          # m — distância máxima saída<->estação para associar
MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

stations = json.load(open(os.path.join(BASE, "stations.json"), encoding="utf-8"))
lats = [s["lat"] for s in stations]; lons = [s["lon"] for s in stations]
# bbox com folga
bbox = (min(lats)-0.01, min(lons)-0.01, max(lats)+0.01, max(lons)+0.01)

def hav(a, b, c, d):
    R = 6371000; r = math.radians
    dp = r(c-a); dl = r(d-b)
    x = math.sin(dp/2)**2 + math.cos(r(a))*math.cos(r(c))*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(x))

query = (f'[out:json][timeout:60];'
         f'node["railway"="subway_entrance"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});'
         f'out body;')

def fetch():
    data = urllib.parse.urlencode({"data": query}).encode()
    last = None
    for ep in MIRRORS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(ep, data=data,
                        headers={"User-Agent": "metro-lisboa/1.0"})
                raw = urllib.request.urlopen(req, timeout=90).read()
                if raw[:1] == b"{":
                    return json.loads(raw)["elements"]
                last = raw[:200]
            except Exception as e:
                last = e
            time.sleep(3)
    raise SystemExit(f"Overpass falhou: {last}")

import urllib.parse
elements = fetch()
print(f"{len(elements)} entradas OSM na bbox")

# associar cada entrada à estação mais próxima (<= MAX_DIST)
by_station = {s["id"]: [] for s in stations}
orphans = 0
for e in elements:
    best, bd = None, 1e9
    for s in stations:
        d = hav(e["lat"], e["lon"], s["lat"], s["lon"])
        if d < bd:
            bd, best = d, s
    if bd > MAX_DIST:
        orphans += 1
        continue
    t = e.get("tags", {})
    by_station[best["id"]].append({
        "nome": t.get("name") or t.get("ref") or "Saída sem nome",
        "lat": e["lat"], "lon": e["lon"],
        "dist_m": round(bd),
        "acesso_cadeira": t.get("wheelchair"),   # yes / no / limited / None
        "elevador": t.get("highway") == "elevator",
    })

# fundir duplicados: saídas com nome idêntico a < MERGE_DIST uma da outra
# (no OSM cada escada é um nó; para o utilizador é a mesma "saída").
# Saídas com nomes diferentes NÃO são fundidas, mesmo que próximas.
MERGE_DIST = 60
import re
def norm(n): return re.sub(r"\s+", " ", n).replace(" (", "(").strip().lower()

def merge_station(exits):
    n = len(exits)
    parent = list(range(n))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i in range(n):
        for j in range(i+1, n):
            if norm(exits[i]["nome"]) == norm(exits[j]["nome"]) and \
               hav(exits[i]["lat"], exits[i]["lon"], exits[j]["lat"], exits[j]["lon"]) < MERGE_DIST:
                parent[find(i)] = find(j)
    groups = {}
    for i in range(n): groups.setdefault(find(i), []).append(exits[i])
    out = []
    for g in groups.values():
        wc = next((x["acesso_cadeira"] for x in g if x["acesso_cadeira"] in ("yes", "limited")),
                  g[0]["acesso_cadeira"])
        out.append({
            "nome": g[0]["nome"],
            "lat": sum(x["lat"] for x in g)/len(g),
            "lon": sum(x["lon"] for x in g)/len(g),
            "dist_m": min(x["dist_m"] for x in g),
            "acesso_cadeira": wc,
            "elevador": any(x["elevador"] for x in g),
            "escadas": len(g),          # nº de nós OSM fundidos
        })
    return out

merged_total = 0
for sid in by_station:
    before = len(by_station[sid])
    by_station[sid] = merge_station(by_station[sid])
    merged_total += before - len(by_station[sid])
    by_station[sid].sort(key=lambda x: x["nome"])
print(f"{merged_total} nós duplicados fundidos (mesmo nome, < {MERGE_DIST} m)")

total = sum(len(v) for v in by_station.values())
com = sum(1 for v in by_station.values() if v)
print(f"{total} saídas associadas a {com}/{len(stations)} estações "
      f"({orphans} fora do raio de {MAX_DIST} m, ignoradas)")

json.dump(by_station, open(os.path.join(BASE, "exits.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
appjs = os.path.join(BASE, "app", "exits.js")
if os.path.isdir(os.path.dirname(appjs)):
    open(appjs, "w", encoding="utf-8").write(
        "window.EXITS = " + json.dumps(by_station, ensure_ascii=False) + ";\n")
print("-> exits.json + app/exits.js")
