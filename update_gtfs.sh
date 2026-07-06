#!/usr/bin/env bash
# Descarrega o GTFS oficial do Metro de Lisboa e reconstrói stations.json.
# Nota: o servidor bloqueia pedidos sem User-Agent de browser -> daí o -A.
set -euo pipefail
cd "$(dirname "$0")"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
curl -sL --max-time 60 -A "$UA" -H "Referer: https://www.metrolisboa.pt/" \
  -o gtfs.zip "https://www.metrolisboa.pt/google_transit/googleTransit.zip"
rm -rf gtfs && unzip -oq gtfs.zip -d gtfs && rm gtfs.zip
python3 build_stations.py
python3 build_graph.py
# saídas vêm do OpenStreetMap (não do GTFS); falha não é fatal
python3 build_exits.py || echo "aviso: build_exits falhou (Overpass ocupado?), saídas mantêm-se as anteriores"
