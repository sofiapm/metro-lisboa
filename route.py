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

import unicodedata
def _norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower())
                   if unicodedata.category(c) != "Mn").strip()

def forward_stations(a, b, line):
    """Conjunto de estações à frente na direção a->b, na mesma linha (evita voltar)."""
    seen = {a}; frontier = [b]; out = set()
    while frontier:
        cur = frontier.pop()
        if cur in seen: continue
        seen.add(cur); out.add(cur)
        for (nb, sec, nl) in GRAPH[cur]:
            if nl == line and nb not in seen:
                frontier.append(nb)
    return out

def real_board_wait(rt, station, first_seq, line):
    """Espera real (s) do próximo comboio na direção do percurso. None se indisponível."""
    if not rt or len(first_seq) < 2:
        return None
    fwd = {_norm(STATIONS[s]["nome"]) for s in forward_stations(first_seq[0], first_seq[1], line)}
    best = None
    for r in rt["rows"].get(station, []):
        if r.get("sairServico") in (1, "1"):
            continue
        dest = _norm(rt["destinos"].get(str(r.get("destino")), ""))
        if dest in fwd:
            t = r.get("tempoChegada1")
            if t not in (None, "", 0, "0"):
                best = min(best if best is not None else 1e9, int(t))
    return best

def plan(o_lat, o_lon, d_lat, d_lon, rt=None):
    origs = candidates(o_lat, o_lon)
    dests = candidates(d_lat, d_lon)
    best = None
    for (wo, os_, oex) in origs[:6]:
        for (wd, ds_, dex) in dests[:6]:
            walk_in = wo / WALK
            walk_out = wd / WALK
            if os_ == ds_:
                cand = (walk_in + walk_out, os_, oex, wo, ds_, dex, wd, [], 0, None)
            else:
                path, ride = dijkstra(os_, ds_)
                if not path:
                    continue
                real_b = None
                if rt:
                    line0, seq0 = summarize_legs(path)[0]
                    real_b = real_board_wait(rt, os_, seq0, line0)
                # substitui a espera fixa (BOARD) pela espera real, quando existe
                eff_ride = ride - BOARD + real_b if real_b is not None else ride
                total = walk_in + eff_ride + walk_out
                cand = (total, os_, oex, wo, ds_, dex, wd, path, eff_ride, real_b)
            if best is None or cand[0] < best[0]:
                best = cand
    return best

def fmt_min(sec): return f"{round(sec/60)} min"

def load_realtime():
    """Contexto de tempo real (tempos + destinos + estado das linhas). None se falhar."""
    try:
        import ml_api
        rows = {}
        for r in ml_api.tempos_todas():
            rows.setdefault(r["stop_id"], []).append(r)
        destinos = {d["id_destino"]: d["nome_destino"] for d in ml_api.info_destinos()}
        return {"rows": rows, "destinos": destinos, "estado": ml_api.estado_linhas()}
    except Exception as e:
        print(f"(aviso: tempos reais indisponíveis — {e}. A usar horário teórico.)\n")
        return None

def main():
    a = sys.argv[1:]
    real = "--real" in a
    a = [x for x in a if x != "--real"]
    try:  # coords coords
        o = (float(a[0]), float(a[1]), "coordenadas"); d = (float(a[2]), float(a[3]), "coordenadas")
    except (ValueError, IndexError):
        if len(a) < 2:
            raise SystemExit(__doc__)
        o = geocode(a[0]); d = geocode(a[1])

    rt = load_realtime() if real else None
    print(f"Origem:  {o[2]}\nDestino: {d[2]}\n")
    if rt:
        maus = [k for k in ("azul", "amarela", "verde", "vermelha")
                if _norm(rt["estado"].get(k, "")) not in ("ok", "")]
        print("🟢 Todas as linhas Ok\n" if not maus
              else "⚠️  Perturbações: " + ", ".join(maus) + "\n")

    r = plan(o[0], o[1], d[0], d[1], rt)
    if not r:
        raise SystemExit("Sem rota encontrada.")
    total, os_, oex, wo, ds_, dex, wd, path, ride, real_b = r

    oname = f" (saída {oex['nome']})" if oex else ""
    print(f"🚶 {fmt_min(wo/WALK)} a pé até **{STATIONS[os_]['nome']}**{oname}")
    if real_b is not None:
        print(f"   ⏱️ próximo comboio na tua direção: {'a chegar' if real_b<30 else fmt_min(real_b)} (tempo real)")
    if path:
        for line, seq in summarize_legs(path):
            nome, cor = LINE[line]
            n = len(seq) - 1
            de, ate = STATIONS[seq[0]]['nome'], STATIONS[seq[-1]]['nome']
            par = "paragem" if n == 1 else "paragens"
            print(f"🚇 Linha {nome}: {de} → {ate}  ({n} {par}, {fmt_min(sum_seg(seq, line))})")
        if real_b is None:
            print(f"   (inclui ~{fmt_min(BOARD)} de espera + trocas)")
    dname = f" (saída {dex['nome']})" if dex else ""
    print(f"🚶 sai em **{STATIONS[ds_]['nome']}**{dname} — {fmt_min(wd/WALK)} a pé até ao destino")
    print(f"\n⏱️  Total estimado: ~{fmt_min(total)}" + ("  (com tempos reais)" if rt else ""))

def sum_seg(seq, line):
    tot = 0
    for a, b in zip(seq, seq[1:]):
        for (nb, sec, nl) in GRAPH[a]:
            if nb == b and nl == line:
                tot += sec; break
    return tot

if __name__ == "__main__":
    main()
