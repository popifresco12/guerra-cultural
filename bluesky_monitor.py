"""Adaptador de Bluesky para el monitor de Guerra Cultural.

Mide los MISMOS 12 temas que se siguen en X, pero en Bluesky, usando la API
publica (sin clave ni token). Ademas de las metricas por tema, agrega los
AUTORES que mas hablan de cada tema y guarda un historial diario para poder
dibujar la evolucion, igual que el dashboard de X.

Salidas:
  - bluesky.json          metricas por tema + autores + directorio global
  - bluesky_history.json  una entrada por dia con el engagement de cada tema

Uso:  py -3 bluesky_monitor.py
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"
AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "bluesky.json")
HISTORIAL = os.path.join(AQUI, "bluesky_history.json")

LIMITE = 100          # maximo que devuelve la API por consulta
AUTORES_POR_TEMA = 8  # autores destacados guardados por tema
DIRECTORIO = 24       # cuentas en el directorio global

TEMAS = {
    "sanchismo": "sanchismo",
    "inmigracion": "inmigración España",
    "okupacion": "okupación",
    "independentismo": "independentismo",
    "memoria": "memoria histórica",
    "feminismo": "feminismo radical",
    "woke": "woke",
    "cultura-cancelacion": "cultura de la cancelación",
    "ley-trans": "ley trans",
    "elecciones": "29N",
    "espana-vaciada": "España vaciada",
    "facha": "facha",
}


def buscar(consulta, limite=LIMITE, idioma="es", reintentos=2):
    """Posts de una consulta, o None si falla. Si el servidor no acepta el
    filtro de idioma, reintenta sin el."""
    for usar_idioma in ([idioma] if idioma else []) + [None]:
        parametros = {"q": consulta, "limit": limite, "sort": "latest"}
        if usar_idioma:
            parametros["lang"] = usar_idioma
        url = API + "?" + urllib.parse.urlencode(parametros)
        for intento in range(reintentos + 1):
            try:
                peticion = urllib.request.Request(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "gc-monitor/2.0 (+https://guerracultural.es)",
                    },
                )
                with urllib.request.urlopen(peticion, timeout=35) as respuesta:
                    datos = json.load(respuesta)
                return datos.get("posts", [])
            except urllib.error.HTTPError as exc:
                if exc.code == 400 and usar_idioma:
                    break  # el filtro de idioma molesta: probamos sin el
                if intento == reintentos:
                    print(f"    ! error: {exc}")
                    return None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if intento == reintentos:
                    print(f"    ! error: {exc}")
                    return None
    return None


def texto_de(post):
    return ((post.get("record", {}) or {}).get("text", "") or "").replace("\n", " ").strip()


def metricas_de(post):
    return (
        post.get("likeCount", 0) or 0,
        post.get("repostCount", 0) or 0,
        post.get("replyCount", 0) or 0,
    )


def medir(posts):
    """Metricas agregadas de un tema + autores destacados."""
    likes = reposts = replies = 0
    por_autor = {}
    for p in posts:
        lk, rp, rs = metricas_de(p)
        likes += lk
        reposts += rp
        replies += rs
        autor = p.get("author", {}) or {}
        handle = (autor.get("handle", "") or "").strip()
        if not handle:
            continue
        a = por_autor.setdefault(
            handle,
            {"handle": handle, "nombre": (autor.get("displayName", "") or "").strip(),
             "posts": 0, "likes": 0, "reposts": 0, "respuestas": 0, "engagement": 0,
             "ejemplo": "", "ejemplo_likes": -1},
        )
        a["posts"] += 1
        a["likes"] += lk
        a["reposts"] += rp
        a["respuestas"] += rs
        a["engagement"] += lk + rp + rs
        if lk > a["ejemplo_likes"]:
            a["ejemplo"] = texto_de(p)[:180]
            a["ejemplo_likes"] = lk
            if not a["nombre"]:
                a["nombre"] = (autor.get("displayName", "") or "").strip()

    autores = sorted(por_autor.values(), key=lambda a: a["engagement"], reverse=True)[:AUTORES_POR_TEMA]
    for a in autores:
        a.pop("ejemplo_likes", None)

    eng = likes + reposts + replies
    top = None
    if posts:
        mejor = max(posts, key=lambda p: (p.get("likeCount", 0) or 0) + (p.get("repostCount", 0) or 0))
        lk, rp, rs = metricas_de(mejor)
        autor = mejor.get("author", {}) or {}
        top = {
            "texto": texto_de(mejor)[:220],
            "likes": lk,
            "reposts": rp,
            "respuestas": rs,
            "engagement": lk + rp + rs,
            "autor": (autor.get("handle", "") or ""),
            "nombre": (autor.get("displayName", "") or "").strip(),
            "fecha": mejor.get("indexedAt", ""),
        }
    return {
        "posts": len(posts),
        "likes": likes,
        "reposts": reposts,
        "respuestas": replies,
        "engagement": eng,
        "engagement_medio": round(eng / len(posts), 1) if posts else 0,
        "autores": autores,
        "top": top,
    }


def actualizar_historial(temas):
    """Anade/actualiza la entrada de HOY en bluesky_history.json."""
    hoy = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    hist = {}
    if os.path.exists(HISTORIAL):
        try:
            with open(HISTORIAL, encoding="utf-8") as f:
                hist = json.load(f)
            if not isinstance(hist, dict):
                hist = {}
        except (ValueError, OSError):
            hist = {}
    serie = hist.setdefault("dias", {})
    serie[hoy] = {tid: v["engagement"] for tid, v in temas.items()}
    hist["dias"] = dict(sorted(serie.items())[-90:])  # ultimos 90 dias
    hist["meta"] = {
        "actualizado": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "nota": "Engagement por tema y dia. Se acumula desde la primera ejecucion.",
        "dias": len(hist["dias"]),
    }
    tmp = HISTORIAL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    os.replace(tmp, HISTORIAL)
    return hist


def main():
    print("Consultando Bluesky (API publica, sin credenciales)...")
    temas = {}
    sin_datos = []
    for tid, consulta in TEMAS.items():
        posts = buscar(consulta)
        if posts is None:
            sin_datos.append(tid)
            print(f"  {tid:22s} -> ERROR")
            continue
        temas[tid] = {"consulta": consulta, **medir(posts)}
        m = temas[tid]
        print(
            f"  {tid:22s} -> {m['posts']:3d} posts | {m['likes']:5d} likes | "
            f"{m['reposts']:4d} reposts | eng {m['engagement']:6d} | autores {len(m['autores'])}"
        )

    orden = sorted(temas.items(), key=lambda kv: kv[1]["engagement"], reverse=True)

    # Directorio global: cuentas que mas hablan del conjunto de temas
    global_autores = {}
    for tid, v in temas.items():
        for a in v["autores"]:
            g = global_autores.setdefault(
                a["handle"],
                {"handle": a["handle"], "nombre": a.get("nombre", ""), "posts": 0, "likes": 0,
                 "reposts": 0, "engagement": 0, "temas": []},
            )
            g["posts"] += a["posts"]
            g["likes"] += a["likes"]
            g["reposts"] += a["reposts"]
            g["engagement"] += a["engagement"]
            if not g.get("nombre") and a.get("nombre"):
                g["nombre"] = a["nombre"]
            if tid not in g["temas"]:
                g["temas"].append(tid)

    directorio = sorted(global_autores.values(), key=lambda a: a["engagement"], reverse=True)[:DIRECTORIO]

    datos = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "fuente": "Bluesky (app.bsky.feed.searchPosts, API publica, filtro idioma es)",
            "nota": (
                "Volumenes NO comparables con X: son plataformas distintas. "
                "Se comparan ordenes relativos del mismo tema, no totales."
            ),
            "temas_ok": len(temas),
            "temas_error": sin_datos,
            "total_posts": sum(v["posts"] for v in temas.values()),
            "total_engagement": sum(v["engagement"] for v in temas.values()),
            "total_likes": sum(v["likes"] for v in temas.values()),
            "total_reposts": sum(v["reposts"] for v in temas.values()),
            "total_respuestas": sum(v["respuestas"] for v in temas.values()),
            "cuentas_unicas": len(global_autores),
        },
        "ranking": [
            {"id": tid, "engagement": v["engagement"], "posts": v["posts"],
             "engagement_medio": v["engagement_medio"]}
            for tid, v in orden
        ],
        "directorio": directorio,
        "temas": temas,
    }
    tmp = SALIDA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SALIDA)

    hist = actualizar_historial(temas)

    print(f"\nGuardado: {SALIDA}")
    print(f"Historial: {HISTORIAL} ({len(hist['dias'])} dia(s) acumulados)")
    print(f"Cuentas unicas: {len(global_autores)} | directorio: {len(directorio)}")
    print("\nRanking Bluesky por engagement:")
    for i, (tid, v) in enumerate(orden, 1):
        print(f"  {i:2d}. {tid:22s} {v['engagement']:6d}")
    if sin_datos:
        print("\nSin datos:", ", ".join(sin_datos))
    print("\nTop cuentas:")
    for a in directorio[:10]:
        print(f"  {a['handle']:36s} {a['posts']:3d} posts | eng {a['engagement']:6d} | temas {len(a['temas'])}")


if __name__ == "__main__":
    main()
