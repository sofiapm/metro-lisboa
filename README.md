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
| `build_graph.py` | Constrói o grafo da rede (tempos por troço) → `graph.json` |
| `route.py` | Planeia viagem morada→destino (trocas, saídas); `--real` usa tempos reais |
| `ml_api.py` | Acesso à API de tempos reais (chaves no Keychain, refresh de token) |
| `tempos.py` | Tempos de espera reais numa estação (nome/morada/coords) |
| `docs/` | Web app: mapa com estações + saídas ao clicar |
| `update_gtfs.sh` | Redescarrega o GTFS e reconstrói `stations.json` + grafo + saídas |

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
- **Tempos de espera em tempo real**: API do Metro (`EstadoServicoML`) no gateway
  `api.metrolisboa.pt:8243`. Credenciais no macOS Keychain (não versionadas).
  Usado por `ml_api.py` / `tempos.py` / `route.py --real`.
    ```bash
    python3 tempos.py Saldanha                       # próximos comboios reais
    python3 route.py "Rato" "Aeroporto" --real       # rota com espera real
    ```

## Próximos passos

- [ ] Web app com mapa (Leaflet/MapLibre) + Geolocation API
- [ ] Roteamento na rede (morada → melhor estação → destino)
- [ ] Integrar tempos de espera reais (API do Metro)
