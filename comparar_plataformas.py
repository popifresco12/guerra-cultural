"""Comparativa X vs Bluesky para el monitor de Guerra Cultural.

Lee data.json (X, del cron) + bluesky.json (adaptador) y genera comparativa.json
con ambas plataformas normalizadas a orden relativo (no se suman volumenes).

Uso:  py -3 comparar_plataformas.py
"""
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))


def cargar(nombre):
    ruta = os.path.join(AQUI, nombre)
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def main():
    def a_num(valor):
        """Tolera numeros como texto ('95', '95%', 'alta')."""
        try:
            return float(str(valor).replace(",", ".").replace("%", "").strip())
        except (TypeError, ValueError):
            return 0.0

    x = cargar("data.json")
    bs = cargar("bluesky.json")
    if not x or not bs:
        print("Faltan datos (data.json o bluesky.json)")
        return

    temas_x = {}
    for t in x.get("topics", []):
        if isinstance(t, dict) and t.get("id"):
            temas_x[t["id"]] = {
                "nombre": t.get("name", t["id"]),
                "icono": t.get("icon", ""),
                "intensidad": a_num(t.get("intensity")),
                "momentum": a_num(t.get("momentum")),
                "tag": t.get("tag", ""),
            }

    temas_bs = bs.get("temas", {})

    filas = []
    for tid, tx in temas_x.items():
        b = temas_bs.get(tid)
        if not b:
            continue
        filas.append(
            {
                "id": tid,
                "nombre": tx["nombre"],
                "icono": tx["icono"],
                "x_intensidad": tx["intensidad"],
                "x_momentum": tx["momentum"],
                "bs_posts": b["posts"],
                "bs_engagement": b["engagement"],
                "bs_engagement_medio": b["engagement_medio"],
                "bs_consulta": b["consulta"],
            }
        )

    # orden relativo dentro de cada plataforma (0-100), que es lo unico comparable
    def a_num(valor):
        """Tolera numeros como texto ('95', '95%', 'alta')."""
        try:
            return float(str(valor).replace(",", ".").replace("%", "").strip())
        except (TypeError, ValueError):
            return 0.0

    def orden_relativo(valores):
        vals = {k: a_num(v) for k, v in valores.items()}
        if not vals:
            return {}
        lo, hi = min(vals.values()), max(vals.values())
        if hi == lo:
            return {k: 50.0 for k in vals}
        return {k: round((v - lo) / (hi - lo) * 100, 1) for k, v in vals.items()}

    rel_x = orden_relativo({f["id"]: f["x_intensidad"] for f in filas})
    rel_bs = orden_relativo({f["id"]: f["bs_engagement"] for f in filas})

    for f in filas:
        f["x_rel"] = rel_x[f["id"]]
        f["bs_rel"] = rel_bs[f["id"]]
        f["brecha"] = round(f["x_rel"] - f["bs_rel"], 1)

    filas.sort(key=lambda f: f["brecha"])

    solo_x = [f for f in filas if f["brecha"] > 20]
    solo_bs = [f for f in filas if f["brecha"] < -20]
    ambos = [f for f in filas if -20 <= f["brecha"] <= 20]

    datos = {
        "meta": {
            "generated_at": bs["meta"]["generated_at"],
            "fuente_x": x.get("meta", {}).get("generated_at"),
            "aviso": (
                "X y Bluesky son poblaciones distintas: los volumenes NO son comparables. "
                "Se comparan posiciones relativas normalizadas 0-100 dentro de cada plataforma."
            ),
            "temas_comparados": len(filas),
        },
        "solo_x": [f["id"] for f in solo_x],
        "solo_bluesky": [f["id"] for f in solo_bs],
        "alineados": [f["id"] for f in ambos],
        "temas": filas,
    }
    with open(os.path.join(AQUI, "comparativa.json"), "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2)

    print(f"{'tema':24s} {'X':>5s} {'BS':>5s} {'brecha':>7s}   lectura")
    print("-" * 68)
    for f in filas:
        if f["brecha"] > 20:
            lectura = "solo en X"
        elif f["brecha"] < -20:
            lectura = "solo en Bluesky"
        else:
            lectura = "en ambas"
        print(
            f"{f['nombre'][:23]:24s} {f['x_rel']:5.0f} {f['bs_rel']:5.0f} "
            f"{f['brecha']:+7.1f}   {lectura}"
        )
    print()
    print("Solo en X (lo amplifica X):", ", ".join(solo_x[i]["nombre"] for i in range(len(solo_x))) or "ninguno")
    print("Solo en Bluesky:", ", ".join(solo_bs[i]["nombre"] for i in range(len(solo_bs))) or "ninguno")
    print("En ambas (tema transversal):", ", ".join(ambos[i]["nombre"] for i in range(len(ambos))) or "ninguno")
    print("\nGuardado: comparativa.json")


if __name__ == "__main__":
    main()
