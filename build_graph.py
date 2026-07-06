#!/usr/bin/env python3
"""Constrói o grafo da rede do Metro a partir do GTFS: para cada par de
estações adjacentes, o tempo de viagem (segundos) e a linha.

Gera graph.json e docs/graph.js:
  { "AM": [ ["AR", 74, "C"], ["AN", 88, "D"], ... ], ... }
  (estação -> lista de [vizinha, segundos, linha])
"""
import csv, json, os, collections

BASE = os.path.dirname(__file__)
G = os.path.join(BASE, "gtfs")

def read(n):
    return list(csv.DictReader(open(os.path.join(G, n), encoding="utf-8-sig")))

# stop_id -> estação canónica (pai se existir)
parent = {}
for s in read("stops.txt"):
    sid = s["stop_id"]; p = s.get("parent_station") or ""
    parent[sid] = p if p else sid
def canon(sid): return parent.get(sid, sid)

trip_route = {t["trip_id"]: t["route_id"] for t in read("trips.txt")}

def secs(hms):
    h, m, s = map(int, hms.split(":"))
    return h*3600 + m*60 + s

# agrupar stop_times por trip, manter ordem
trips = collections.defaultdict(list)
for r in read("stop_times.txt"):
    trips[r["trip_id"]].append(r)

# menor tempo observado por (a,b,linha)
seg = {}
for tid, rows in trips.items():
    rows.sort(key=lambda r: int(r["stop_sequence"]))
    line = trip_route.get(tid)
    for a, b in zip(rows, rows[1:]):
        ca, cb = canon(a["stop_id"]), canon(b["stop_id"])
        if ca == cb:
            continue
        dt = secs(b["departure_time"]) - secs(a["departure_time"])
        if dt <= 0:
            continue
        key = (ca, cb, line)
        seg[key] = min(seg.get(key, 1e9), dt)

# adjacência (grafo não-dirigido: a linha serve os dois sentidos)
graph = collections.defaultdict(dict)   # a -> {(b,line): sec}
for (a, b, line), dt in seg.items():
    graph[a][(b, line)] = min(graph[a].get((b, line), 1e9), dt)
    graph[b][(a, line)] = min(graph[b].get((a, line), 1e9), dt)

out = {a: [[b, int(dt), line] for (b, line), dt in sorted(nb.items())]
       for a, nb in graph.items()}

json.dump(out, open(os.path.join(BASE, "graph.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
appjs = os.path.join(BASE, "docs", "graph.js")
if os.path.isdir(os.path.dirname(appjs)):
    open(appjs, "w", encoding="utf-8").write(
        "window.GRAPH = " + json.dumps(out, ensure_ascii=False) + ";\n")

edges = sum(len(v) for v in out.values())
print(f"{len(out)} estações, {edges} arestas -> graph.json + docs/graph.js")
