"""Adaptador de Bluesky para el monitor de Guerra Cultural.

Busca los MISMOS 12 temas que se miden en X, pero en Bluesky, usando la API
publica (sin clave ni token). Guarda bluesky.json con las metricas por tema.

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

# id del tema -> consulta corta equivalente (en X las consultas son largas y con
# operadores; en Bluesky se busca texto, asi que se usa el termino nuclear)
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
    "lenguaje-inclusivo": "lenguaje inclusivo",
    "espana-vaciada": "España vaciada",
    "facha": "facha",
}


def buscar(consulta, limite=100, reintentos=2):
    """Devuelve la lista de posts o None si falla."""
    url = API + "?" + urllib.parse.urlencode(
        {"q": consulta, "limit": limite, "sort": "latest"}
    )
    for intento in range(reintentos + 1):
        try:
            peticion = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "gc-monitor/1.0 (+https://guerracultural.es)",
                },
            )
            with urllib.request.urlopen(peticion, timeout=35) as respuesta:
                datos = json.load(respuesta)
            return datos.get("posts", [])
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            if intento == reintentos:
                print(f"    ! error: {exc}")
                return None
    return None


def medir(posts):
    """Metricas agregadas de un tema."""
    likes = sum(p.get("likeCount", 0) or 0 for p in posts)
    reposts = sum(p.get("repostCount", 0) or 0 for p in posts)
    replies = sum(p.get("replyCount", 0) or 0 for p in posts)
    eng = likes + reposts + replies
    top = None
    if posts:
        mejor = max(posts, key=lambda p: (p.get("likeCount", 0) or 0) + (p.get("repostCount", 0) or 0))
        texto = (mejor.get("record", {}) or {}).get("text", "") or ""
        top = {
            "texto": texto.replace("\n", " ")[:220],
            "likes": mejor.get("likeCount", 0),
            "reposts": mejor.get("repostCount", 0),
            "autor": ((mejor.get("author", {}) or {}).get("handle", "")),
            "fecha": mejor.get("indexedAt", ""),
        }
    return {
        "posts": len(posts),
        "likes": likes,
        "reposts": reposts,
        "respuestas": replies,
        "engagement": eng,
        "engagement_medio": round(eng / len(posts), 1) if posts else 0,
        "top": top,
    }


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
            f"{m['reposts']:4d} reposts | eng/medio {m['engagement_medio']}"
        )

    orden = sorted(temas.items(), key=lambda kv: kv[1]["engagement"], reverse=True)
    datos = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "fuente": "Bluesky (app.bsky.feed.searchPosts, API publica)",
            "nota": (
                "Volumenes NO comparables con X: son plataformas distintas. "
                "Se comparan ordenes relativos del mismo tema, no totales."
            ),
            "temas_ok": len(temas),
            "temas_error": sin_datos,
        },
        "ranking": [
            {"id": tid, "engagement": v["engagement"], "posts": v["posts"]}
            for tid, v in orden
        ],
        "temas": temas,
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {SALIDA}")
    print("\nRanking Bluesky por engagement:")
    for i, (tid, v) in enumerate(orden, 1):
        print(f"  {i:2d}. {tid:22s} {v['engagement']:6d}")
    if sin_datos:
        print("\nSin datos:", ", ".join(sin_datos))


if __name__ == "__main__":
    main()
