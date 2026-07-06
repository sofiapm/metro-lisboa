# Metro de Lisboa — estação mais próxima

Ferramentas para trabalhar com dados do Metro de Lisboa: extrair estações
(coordenadas + linhas/cores) do GTFS oficial e encontrar a estação mais
próxima de uma localização ou morada.

## Ficheiros

| Ficheiro | O que faz |
|----------|-----------|
| `gtfs/` | GTFS oficial do Metro (dados-fonte) |
| `build_stations.py` | Extrai `stations.json` a partir do GTFS |
| `stations.json` | 50 estações: `nome`, `lat`, `lon`, `linhas` (nome + cor hex) |
| `nearest.py` | Estação mais próxima de coordenadas ou morada |
| `build_exits.py` | Puxa as saídas do OpenStreetMap e associa-as às estações |
| `exits.json` | Saídas por estação (nome, coords, acesso cadeira de rodas) |
| `app/` | Web app: mapa com estações + saídas ao clicar |
| `update_gtfs.sh` | Redescarrega o GTFS e reconstrói `stations.json` + saídas |

## Usar

```bash
# por coordenadas
python3 nearest.py 38.7075 -9.1364 -n 3

# por morada (geocoding via OpenStreetMap/Nominatim, grátis, sem chave)
python3 nearest.py "Instituto Superior Técnico, Lisboa" -n 3
```

## Atualizar dados

```bash
./update_gtfs.sh
```

O URL do GTFS (`metrolisboa.pt/google_transit/googleTransit.zip`) bloqueia
pedidos sem User-Agent de browser — o script já trata disso.

## Fontes de dados

- **GTFS estático** (horários, paragens, rotas, coordenadas): o próprio Metro.
- **Cores das linhas**: `route_color` no GTFS — Azul `#6699cc`, Amarela
  `#ffcc00`, Verde `#00cc99`, Vermelha `#ff3366`.
- **Entradas/saídas**: NÃO estão no GTFS. Vêm do **OpenStreetMap**
  (`railway=subway_entrance`), obtidas via Overpass API em `build_exits.py`.
- **Tempos de espera em tempo real**: API do Metro em `api.metrolisboa.pt`
  (requer registo/chave). Ainda por integrar.

## Próximos passos

- [ ] Web app com mapa (Leaflet/MapLibre) + Geolocation API
- [ ] Roteamento na rede (morada → melhor estação → destino)
- [ ] Integrar tempos de espera reais (API do Metro)
