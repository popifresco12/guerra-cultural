#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recolector del apartado de elecciones para el dashboard de guerra cultural.

Descarga titulares de los medios (RSS publicos, sin API key) y los tweets
destacados que se hayan curado a mano (via la API de syndication de X, que
tampoco necesita clave). Genera elecciones.json, que es lo que consume
elecciones.html.

Sin dependencias externas: urllib + xml.etree.
"""
import json
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone, date
from xml.etree import ElementTree as ET

OUT = r"C:\Users\carlo\gc-deploy\elecciones.json"
FECHA_ELECCION = date(2026, 11, 29)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Medios de distinto signo editorial: el valor del panel es ver el MISMO dia
# contado por cabeceras que no coinciden en nada.
FUENTES = [
    ("elDiario.es",      "https://www.eldiario.es/rss/"),
    ("El Pais",          "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"),
    ("ABC",              "https://www.abc.es/rss/feeds/abc_EspanaEspana.xml"),
    ("El Mundo",         "https://e00-elmundo.uecdn.es/rss/espana.xml"),
    ("OKDiario",         "https://okdiario.com/feed"),
    ("The Objective",    "https://theobjective.com/feed/"),
]

# Titular relevante para las elecciones o para los temas del termometro.
CLAVES = [
    "eleccion", "electoral", "29-n", "29n", "generales", "campana", "candidat",
    "urnas", "encuesta", "debate", "mitin", "votar", "voto", "escanos", "escano",
    "congreso", "senado", "investidura", "disoluc", "boe", "junta electoral",
    "sanchez", "feijoo", "abascal", "puigdemont", "yolanda diaz", "ayuso",
    "psoe", "pp", "vox", "sumar", "podemos", "junts", "erc", "bildu",
]

HITOS = [
    {"fecha": "2026-10-06", "titulo": "Publicacion del Real Decreto en el BOE",
     "detalle": "Arranca el reloj: las elecciones se celebran 54 dias despues."},
    {"fecha": "2026-10-21", "titulo": "Presentacion de candidaturas (21-26 oct)",
     "detalle": "Los partidos registran sus listas ante la Junta Electoral."},
    {"fecha": "2026-11-02", "titulo": "Proclamacion de las candidaturas",
     "detalle": "Listas definitivas validadas por la Junta Electoral."},
    {"fecha": "2026-11-13", "titulo": "Comienzo de la campana electoral",
     "detalle": "Quince dias de campana, hasta el 27 de noviembre."},
    {"fecha": "2026-11-28", "titulo": "Jornada de reflexion",
     "detalle": "Prohibido pedir el voto."},
    {"fecha": "2026-11-29", "titulo": "Elecciones generales",
     "detalle": "Votacion en toda Espana."},
    {"fecha": "2026-12-24", "titulo": "Constitucion de las Cortes",
     "detalle": "Plazo maximo de 25 dias tras los comicios."},
]

# Tweets destacados: se curan a mano. Un id por linea; el texto real se trae
# de la API de syndication. Anadir aqui los que interesen, uno a uno.
TWEETS_IDS = [
    "2107213442847531148",  # The Objective: Aznar sobre el 29-N
]


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def limpiar(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = (s.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
          .replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">"))
    return re.sub(r"\s+", " ", s).strip()


def es_relevante(t):
    tl = t.lower()
    return any(k in tl for k in CLAVES)


def leer_feed(medio, url):
    out = []
    try:
        raw = get(url)
    except Exception as e:
        return {"medio": medio, "url": url, "error": str(e), "noticias": []}
    try:
        root = ET.fromstring(raw)
    except Exception as e:
        return {"medio": medio, "url": url, "error": "xml: " + str(e), "noticias": []}
    items = root.iter("item")
    for it in items:
        t = limpiar(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        if not t or not link:
            continue
        if not es_relevante(t):
            continue
        out.append({"titular": t, "url": link, "fecha": pub})
        if len(out) >= 10:
            break
    return {"medio": medio, "url": url, "noticias": out}


def leer_tweet(tid):
    url = f"https://cdn.syndication.twimg.com/tweet-result?id={tid}&lang=es&token=x"
    try:
        d = json.loads(get(url).decode("utf-8", "replace"))
    except Exception as e:
        return {"id": tid, "error": str(e), "url": f"https://x.com/i/status/{tid}"}
    u = d.get("user") or {}
    return {
        "id": tid,
        "url": f"https://x.com/{u.get('screen_name','i')}/status/{tid}",
        "autor": u.get("name") or "",
        "usuario": "@" + (u.get("screen_name") or ""),
        "texto": re.sub(r"\s*https?://t\.co/\S+", "", d.get("text") or "").strip(),
        "fecha": d.get("created_at") or "",
        "likes": d.get("favorite_count"),
        "rts": d.get("conversation_count"),
    }


def main():
    hoy = datetime.now(timezone.utc)
    dias = (FECHA_ELECCION - hoy.date()).days
    fuentes = [leer_feed(m, u) for (m, u) in FUENTES]
    tweets = [leer_tweet(t) for t in TWEETS_IDS]
    data = {
        "generado": hoy.isoformat(timespec="seconds"),
        "eleccion": {
            "nombre": "Elecciones Generales 2026",
            "fecha": FECHA_ELECCION.isoformat(),
            "dias_restantes": dias,
        },
        "hitos": HITOS,
        "fuentes": fuentes,
        "tweets": tweets,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    total = sum(len(f["noticias"]) for f in fuentes)
    print(f"escrito {OUT}")
    print(f"dias restantes: {dias} | noticias: {total} | tweets: {len(tweets)}")
    for f in fuentes:
        est = f"ERROR {f['error']}" if f.get("error") else f"{len(f['noticias'])} noticias"
        print(f"  {f['medio']:16s} {est}")
        for n in f["noticias"][:2]:
            print(f"      - {n['titular'][:88]}")


if __name__ == "__main__":
    main()
