#!/usr/bin/env python3
"""Extrai um stations.json limpo a partir do GTFS do Metro de Lisboa.

Cada estação tem: id, nome, lat, lon, e as linhas que a servem (com cor).
Colapsa os stops-filhos (cais) na estação-pai.
"""
import csv, json, os, collections

GTFS = os.path.join(os.path.dirname(__file__), "gtfs")

def read(name):
    with open(os.path.join(GTFS, name), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

# 1) linhas (route_id -> {nome, cor})
routes = {r["route_id"]: {"nome": r["route_long_name"],
                          "curto": r["route_short_name"],
                          "cor": "#" + r["route_color"]}
          for r in read("routes.txt")}

# 2) stops: mapa stop_id -> estação canónica (pai se existir, senão o próprio)
stops = read("stops.txt")
parent_of = {}          # stop_id -> station_id
stations = {}           # station_id -> dados
for s in stops:
    sid = s["stop_id"]
    loc = s.get("location_type") or "0"
    parent = s.get("parent_station") or ""
    if loc == "1":                     # estação (station)
        stations[sid] = {"id": sid, "nome": s["stop_name"],
                         "lat": float(s["stop_lat"]), "lon": float(s["stop_lon"]),
                         "linhas": set()}
        parent_of[sid] = sid
# segunda passagem: filhos e stops simples (sem location_type)
for s in stops:
    sid = s["stop_id"]
    loc = s.get("location_type") or "0"
    parent = s.get("parent_station") or ""
    if loc == "1":
        continue
    if parent and parent in stations:
        parent_of[sid] = parent
    else:                              # stop simples sem pai -> é a própria estação
        stations[sid] = {"id": sid, "nome": s["stop_name"],
                         "lat": float(s["stop_lat"]), "lon": float(s["stop_lon"]),
                         "linhas": set()}
        parent_of[sid] = sid

# 3) que linhas param em cada estação: trips -> stop_times
trip_route = {t["trip_id"]: t["route_id"] for t in read("trips.txt")}
for st in read("stop_times.txt"):
    rid = trip_route.get(st["trip_id"])
    station = parent_of.get(st["stop_id"])
    if rid and station and station in stations:
        stations[station]["linhas"].add(rid)

# 4) serializar
out = []
for st in stations.values():
    linhas = sorted(st["linhas"])
    if not linhas:                     # ignora entradas sem serviço
        continue
    out.append({
        "id": st["id"],
        "nome": st["nome"],
        "lat": st["lat"], "lon": st["lon"],
        "linhas": [{"id": l, "nome": routes[l]["nome"], "cor": routes[l]["cor"]}
                    for l in linhas],
    })
out.sort(key=lambda x: x["nome"])

dest = os.path.join(os.path.dirname(__file__), "stations.json")
with open(dest, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"{len(out)} estações -> {dest}")
