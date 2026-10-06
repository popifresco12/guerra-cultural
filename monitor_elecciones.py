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
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone, date
from xml.etree import ElementTree as ET

OUT = r"C:\Users\carlo\gc-deploy\elecciones.json"
FECHA_ELECCION = date(2026, 11, 29)

# Nada anterior al anuncio de la convocatoria (5-oct-2026) cuenta: si habla de
# "elecciones" antes de ese momento, habla de otra cosa.
CONVOCATORIA = "2026-10-05T00:00:00+00:00"

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

# --- Bluesky -------------------------------------------------------------
# Busqueda publica (app.bsky.feed.searchPosts), sin clave. Se piden las
# consultas electorales y luego se filtra: solo pasa lo que habla de estas
# elecciones, y se cae todo lo que suene a comicios de otros paises.
BSKY_API = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"
BSKY_CONSULTAS = [
    "elecciones 29N",
    "29-N elecciones",
    "elecciones generales Espana",
    "Sanchez elecciones anticipadas",
    "Feijoo elecciones",
    "Vox elecciones",
]
BSKY_REQUIERE = [
    "29n", "29-n", "29 n", "29 de noviembre", "elecciones generales",
    "elecciones anticipadas", "adelanto electoral", "urnas", "convocatoria electoral",
]
BSKY_DESCARTA = [
    "venezuela", "machado", "portugal", "lula", "brasil", "chile", "argentina",
    "mexico", "colombia", "peru", "eeuu", "estados unidos", "uruguay", "bolivia",
]
BSKY_CUANTOS = 12


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


def buscar_bluesky(consulta, limite=25):
    """Posts de una consulta en Bluesky, ordenados por relevancia."""
    params = {"q": consulta, "limit": limite, "sort": "top", "lang": "es"}
    url = BSKY_API + "?" + urllib.parse.urlencode(params)
    try:
        return json.loads(get(url).decode("utf-8", "replace")).get("posts", []) or []
    except Exception:
        return []


def posterior_a_la_convocatoria(iso):
    """True solo si el post es del dia de la convocatoria (5-oct-2026) o posterior."""
    if not iso:
        return False
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return False
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d >= datetime.fromisoformat(CONVOCATORIA)


def vale_el_post(texto):
    tl = texto.lower()
    if any(b in tl for b in BSKY_DESCARTA):
        return False
    return any(m in tl for m in BSKY_REQUIERE)


def recolectar_bluesky():
    """Junta las consultas, se queda con lo que habla de ESTAS elecciones y
    ordena por engagement (un repost pesa mas que un like)."""
    vistos = {}
    for q in BSKY_CONSULTAS:
        for p in buscar_bluesky(q):
            uri = p.get("uri")
            txt = ((p.get("record") or {}).get("text") or "").replace("\n", " ").strip()
            fecha = (p.get("record") or {}).get("createdAt") or p.get("indexedAt") or ""
            if not uri or not txt or uri in vistos or not vale_el_post(txt):
                continue
            if not posterior_a_la_convocatoria(fecha):
                continue
            au = p.get("author") or {}
            handle = au.get("handle") or ""
            vistos[uri] = {
                "texto": txt,
                "autor": (au.get("displayName") or "").strip(),
                "usuario": "@" + handle,
                "url": "https://bsky.app/profile/%s/post/%s" % (handle, uri.rsplit("/", 1)[-1]),
                "fecha": fecha,
                "likes": p.get("likeCount") or 0,
                "rts": p.get("repostCount") or 0,
                "resp": p.get("replyCount") or 0,
            }
    posts = sorted(vistos.values(), key=lambda x: x["likes"] + 2 * x["rts"], reverse=True)
    return posts[:BSKY_CUANTOS]


def main():
    hoy = datetime.now(timezone.utc)
    dias = (FECHA_ELECCION - hoy.date()).days
    fuentes = [leer_feed(m, u) for (m, u) in FUENTES]
    tweets = [t for t in (leer_tweet(x) for x in TWEETS_IDS)
              if posterior_a_la_convocatoria(t.get("fecha"))]
    bluesky = recolectar_bluesky()
    data = {
        "generado": hoy.isoformat(timespec="seconds"),
        "eleccion": {
            "nombre": "Elecciones Generales 2026",
            "fecha": FECHA_ELECCION.isoformat(),
            "dias_restantes": dias,
        },
        "convocatoria": CONVOCATORIA[:10],
        "hitos": HITOS,
        "fuentes": fuentes,
        "tweets": tweets,
        "bluesky": bluesky,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    total = sum(len(f["noticias"]) for f in fuentes)
    print(f"escrito {OUT}")
    print(f"dias restantes: {dias} | noticias: {total} | tweets: {len(tweets)} | bluesky: {len(bluesky)}")
    for b in bluesky[:5]:
        print(f"   {b['likes']:5d}L {b['rts']:4d}RT {b['usuario']}: {b['texto'][:78]}")
    for f in fuentes:
        est = f"ERROR {f['error']}" if f.get("error") else f"{len(f['noticias'])} noticias"
        print(f"  {f['medio']:16s} {est}")
        for n in f["noticias"][:2]:
            print(f"      - {n['titular'][:88]}")


if __name__ == "__main__":
    main()
