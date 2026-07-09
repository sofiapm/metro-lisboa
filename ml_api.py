#!/usr/bin/env python3
"""Camada de acesso à API de tempos reais do Metro de Lisboa (EstadoServicoML).

As credenciais vivem no macOS Keychain (nunca em ficheiro). O access token é
renovado automaticamente (OAuth client_credentials) se expirar/for revogado.

Uso como módulo:
    import ml_api
    ml_api.estado_linhas()
    ml_api.tempos_todas()          # tempos de espera de todas as estações
    ml_api.tempos_estacao("SA")    # por stop_id (igual ao GTFS)
"""
import base64, json, ssl, subprocess, urllib.parse, urllib.request

GATEWAY = "https://api.metrolisboa.pt:8243/estadoServicoML/1.0.1"
TOKEN_URL = "https://api.metrolisboa.pt:8243/token"
KC_KEYS = "api.metrolisboa.pt keys (EstadoServicoML)"
KC_ACC = "sofiapm"
# o gateway :8243 usa um certificado não confiável por omissão (curl precisou de -k)
_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE


def _keychain_read():
    out = subprocess.run(["security", "find-generic-password", "-s", KC_KEYS,
                          "-a", KC_ACC, "-w"], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError("Credenciais não encontradas no Keychain.")
    return json.loads(out.stdout.strip())


def _keychain_write(creds):
    subprocess.run(["security", "add-generic-password", "-s", KC_KEYS, "-a", KC_ACC,
                    "-w", json.dumps(creds), "-U"], check=True)


def _refresh_token(creds):
    """Novo access token via client_credentials; grava no Keychain."""
    basic = base64.b64encode(f"{creds['consumerKey']}:{creds['consumerSecret']}".encode()).decode()
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(TOKEN_URL, data=data,
            headers={"Authorization": "Basic " + basic,
                     "Content-Type": "application/x-www-form-urlencoded"})
    tok = json.load(urllib.request.urlopen(req, timeout=20, context=_SSL))
    creds["accessToken"] = tok["access_token"]
    _keychain_write(creds)
    return creds


def _get(path, _retry=True):
    creds = _keychain_read()
    req = urllib.request.Request(GATEWAY + path,
            headers={"Authorization": "Bearer " + creds["accessToken"]})
    try:
        return json.load(urllib.request.urlopen(req, timeout=25, context=_SSL))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403) and _retry:
            _refresh_token(creds)
            return _get(path, _retry=False)
        raise


# ---- endpoints ----
def estado_linhas():
    return _get("/estadoLinha/todos")["resposta"]

def tempos_todas():
    return _get("/tempoEspera/Estacao/todos")["resposta"]

def tempos_estacao(stop_id):
    return _get(f"/tempoEspera/Estacao/{stop_id}")["resposta"]

def info_destinos():
    return _get("/infoDestinos/todos")["resposta"]


if __name__ == "__main__":
    print("Estado das linhas:", estado_linhas())
    print("Nº de registos de tempos:", len(tempos_todas()))
