#!/usr/bin/env python3
"""Planeador de viagem no Metro de Lisboa.

Dá duas moradas (ou coordenadas) e devolve a melhor viagem:
qual estação apanhar, trocas de linha, por que saída sair, e o tempo estimado.

Uso:
  python3 route.py "Instituto Superior Técnico, Lisboa" "Aeroporto de Lisboa"
  python3 route.py 38.7367 -9.1384  38.7686 -9.1283
"""
import heapq, json, math, os, sys, urllib.parse, urllib.request

BASE = os.path.dirname(__file__)
GRAPH = json.load(open(os.path.join(BASE, "graph.json"), encoding="utf-8"))
STATIONS = {s["id"]: s for s in json.load(open(os.path.join(BASE, "stations.json"), encoding="utf-8"))}
EXITS = json.load(open(os.path.join(BASE, "exits.json"), encoding="utf-8"))
LINE = {"A": ("Azul", "#6699cc"), "B": ("Amarela", "#ffcc00"),
        "C": ("Verde", "#00cc99"), "D": ("Vermelha", "#ff3366")}

WALK = 1.33            # m/s (~80 m/min)
TRANSFER = 240         # s por troca de linha (mudar de cais + esperar)
BOARD = 180            # s de espera média ao embarcar
MAX_WALK = 1500        # m — raio máximo a pé até/desde uma estação

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
    if not d:
        raise SystemExit(f"Morada não encontrada: {q!r}")
    return float(d[0]["lat"]), float(d[0]["lon"]), d[0]["display_name"]

def nearest_exit(sid, lat, lon):
    """Saída da estação sid mais perto do ponto (lat,lon). Devolve (exit|None, dist_m)."""
    best, bd = None, hav(lat, lon, STATIONS[sid]["lat"], STATIONS[sid]["lon"])
    for ex in EXITS.get(sid, []):
        d = hav(lat, lon, ex["lat"], ex["lon"])
        if d < bd:
            bd, best = d, ex
    return best, round(bd)

def candidates(lat, lon):
    """Estações a pé (<= MAX_WALK), pela saída mais próxima; sempre inclui a +perto."""
    scored = []
    for sid in GRAPH:
        ex, d = nearest_exit(sid, lat, lon)
        scored.append((d, sid, ex))
    scored.sort()
    out = [c for c in scored if c[0] <= MAX_WALK]
    return out or scored[:1]

def dijkstra(orig, dest):
    """Melhor caminho estação->estação. Estado = (estação, linha)."""
    pq = []
    dist = {}
    # embarque: entrar em `orig` em qualquer linha que lá pare
    lines_at = {line for (_, line) in ((n[0], n[2]) for n in GRAPH[orig])}
    for line in lines_at:
        st = (orig, line)
        dist[st] = BOARD
        heapq.heappush(pq, (BOARD, orig, line, [("board", orig, line)]))
    best_path, best_time = None, math.inf
    while pq:
        t, st, line, path = heapq.heappop(pq)
        if t > dist.get((st, line), math.inf):
            continue
        if st == dest and t < best_time:
            best_time, best_path = t, path
            continue
        for (nb, sec, nl) in GRAPH[st]:
            nt = t + sec + (TRANSFER if nl != line else 0)
            if nt < dist.get((nb, nl), math.inf):
                dist[(nb, nl)] = nt
                step = path + ([("transfer", st, nl)] if nl != line else []) + [("ride", nb, nl)]
                heapq.heappush(pq, (nt, nb, nl, step))
    return best_path, best_time

def summarize_legs(path):
    """Converte a lista de passos em pernas por linha: [(linha, [estações], nº paragens)]."""
    legs = []
    cur_line = None; seq = []
    for kind, sid, line in path:
        if kind == "board":
            cur_line = line; seq = [sid]
        elif kind == "transfer":
            legs.append((cur_line, seq)); cur_line = line; seq = [sid]
        elif kind == "ride":
            seq.append(sid)
    if seq:
        legs.append((cur_line, seq))
    return legs

def plan(o_lat, o_lon, d_lat, d_lon):
    origs = candidates(o_lat, o_lon)
    dests = candidates(d_lat, d_lon)
    best = None
    for (wo, os_, oex) in origs[:6]:
        for (wd, ds_, dex) in dests[:6]:
            walk_in = wo / WALK
            walk_out = wd / WALK
            if os_ == ds_:
                total = walk_in + walk_out
                cand = (total, os_, oex, wo, ds_, dex, wd, [], 0)
            else:
                path, ride = dijkstra(os_, ds_)
                if not path:
                    continue
                total = walk_in + ride + walk_out
                cand = (total, os_, oex, wo, ds_, dex, wd, path, ride)
            if best is None or cand[0] < best[0]:
                best = cand
    return best

def fmt_min(sec): return f"{round(sec/60)} min"

def main():
    a = sys.argv[1:]
    try:  # coords coords
        o = (float(a[0]), float(a[1]), "coordenadas"); d = (float(a[2]), float(a[3]), "coordenadas")
    except (ValueError, IndexError):
        if len(a) < 2:
            raise SystemExit(__doc__)
        o = geocode(a[0]); d = geocode(a[1])

    print(f"Origem:  {o[2]}\nDestino: {d[2]}\n")
    r = plan(o[0], o[1], d[0], d[1])
    if not r:
        raise SystemExit("Sem rota encontrada.")
    total, os_, oex, wo, ds_, dex, wd, path, ride = r

    oname = f" (saída {oex['nome']})" if oex else ""
    print(f"🚶 {fmt_min(wo/WALK)} a pé até **{STATIONS[os_]['nome']}**{oname}")
    if path:
        for line, seq in summarize_legs(path):
            nome, cor = LINE[line]
            n = len(seq) - 1
            de, ate = STATIONS[seq[0]]['nome'], STATIONS[seq[-1]]['nome']
            par = "paragem" if n == 1 else "paragens"
            print(f"🚇 Linha {nome}: {de} → {ate}  ({n} {par}, {fmt_min(sum_seg(seq, line))})")
        print(f"   (inclui ~{fmt_min(BOARD)} de espera + trocas)")
    dname = f" (saída {dex['nome']})" if dex else ""
    print(f"🚶 sai em **{STATIONS[ds_]['nome']}**{dname} — {fmt_min(wd/WALK)} a pé até ao destino")
    print(f"\n⏱️  Total estimado: ~{fmt_min(total)}")

def sum_seg(seq, line):
    tot = 0
    for a, b in zip(seq, seq[1:]):
        for (nb, sec, nl) in GRAPH[a]:
            if nb == b and nl == line:
                tot += sec; break
    return tot

if __name__ == "__main__":
    main()
