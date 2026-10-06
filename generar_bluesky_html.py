"""Genera bluesky.html con la misma estructura y estilo que el dashboard de X.

Reutiliza el <style> y el menu de index.html para que las dos paginas sean
identicas en aspecto, y pinta los datos de bluesky.json: KPIs, evolucion,
tarjetas por tema (con el post mas fuerte y los usuarios que mas hablan) y
directorio de cuentas.

Uso:  py -3 generar_bluesky_html.py
"""
import io
import json
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(AQUI, "index.html")
DATOS = os.path.join(AQUI, "bluesky.json")
HIST = os.path.join(AQUI, "bluesky_history.json")
SALIDA = os.path.join(AQUI, "bluesky.html")

# id del tema -> nombre y emoji, identicos a los del dashboard de X
TEMAS_UI = {
    "sanchismo": ("Sanchismo", "\U0001F451"),
    "inmigracion": ("Inmigración", "\U0001F6A7"),
    "okupacion": ("Okupación", "\U0001F3E0"),
    "independentismo": ("Independentismo / Procés", "\U0001F5FA\uFE0F"),
    "memoria": ("Memoria Histórica", "\U0001F4DC"),
    "feminismo": ("Feminismo Radical", "\u26A1"),
    "woke": ("Wokismo / Ideología Woke", "\U0001F33F"),
    "cultura-cancelacion": ("Cultura de la Cancelación", "\U0001F507"),
    "ley-trans": ("Ley Trans", "\u26A7\uFE0F"),
    "elecciones": ("Elecciones", "\U0001F5F3\uFE0F"),
    "espana-vaciada": ("España Vaciada", "\U0001F3D8\uFE0F"),
    "facha": ("Facha / Insulto Político", "\U0001F5E3\uFE0F"),
}


def esc(t):
    return (
        str(t if t is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def leer_json(ruta, defecto):
    try:
        with io.open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defecto


def extraer(patron, texto, defecto=""):
    m = re.search(patron, texto, re.S)
    return m.group(0) if m else defecto


def main():
    html_index = io.open(INDEX, encoding="utf-8").read()
    datos = leer_json(DATOS, {})
    hist = leer_json(HIST, {})

    estilos = "\n".join(re.findall(r"<style>.*?</style>", html_index, re.S))
    nav = extraer(r"<nav class=\"gc-nav\">.*?</nav>", html_index)
    temas = datos.get("temas", {})
    meta = datos.get("meta", {})
    ranking = datos.get("ranking", [])
    directorio = datos.get("directorio", [])
    dias = (hist.get("meta", {}) or {}).get("dias", 0)

    max_eng = max([r.get("engagement", 0) for r in ranking] or [1])

    # ---- filas del ranking (barras, igual que el bloque comparativo) ----
    filas = []
    for i, r in enumerate(ranking, 1):
        tid = r.get("id")
        nombre, emoji = TEMAS_UI.get(tid, (tid, ""))
        pct = round(100.0 * r.get("engagement", 0) / max_eng, 1)
        filas.append(
            '<div class="gc-tema"><div class="gc-fila"><span class="gc-nombre">'
            f'{i}. {emoji} {esc(nombre)}</span>'
            f'<span class="gc-valor">{r.get("engagement", 0):,}</span></div>'.replace(",", ".")
            + '<div class="gc-pista"><div class="gc-relleno" style="width:'
            + f'{pct}%"></div></div>'
            + f'<div class="gc-sub">{r.get("posts", 0)} posts · media {r.get("engagement_medio", 0)} por post</div></div>'
        )

    # ---- tarjetas por tema ----
    tarjetas = []
    for r in ranking:
        tid = r.get("id")
        v = temas.get(tid, {})
        nombre, emoji = TEMAS_UI.get(tid, (tid, ""))
        top = v.get("top") or None
        aut = v.get("autores", [])[:6]
        bloques_aut = []
        a_max = max([a.get("engagement", 0) for a in aut] or [1])
        for a in aut:
            w = round(100.0 * a.get("engagement", 0) / a_max, 1)
            bloques_aut.append(
                '<div class="gc-autor">'
                f'<div class="gc-autor-cab"><b>@{esc(a.get("handle",""))}</b>'
                f'<span class="gc-autor-eng">{a.get("engagement",0):,} eng · {a.get("posts",0)} posts</span></div>'
                .replace(",", ".")
                + f'<div class="gc-pista"><div class="gc-relleno gc-naranja" style="width:{w}%"></div></div>'
                + (f'<div class="gc-autor-ej">"{esc(a.get("ejemplo","")[:150])}"</div>' if a.get("ejemplo") else "")
                + "</div>"
            )
        tarjeta = [
            f'<article class="gc-card">',
            f'<h4>{emoji} {esc(nombre)}</h4>',
            f'<div class="gc-kpis"><span><b>{v.get("engagement",0):,}</b> engagement</span>'
            f'<span><b>{v.get("posts",0)}</b> posts</span>'
            f'<span><b>{v.get("likes",0):,}</b> me gusta</span>'
            f'<span><b>{v.get("reposts",0):,}</b> reposts</span></div>'.replace(",", "."),
            f'<p class="gc-consulta">Búsqueda: <code>{esc(v.get("consulta",""))}</code> · media {v.get("engagement_medio",0)} por post</p>',
        ]
        if top:
            tarjeta.append(
                '<div class="gc-top"><div class="gc-top-cab">'
                f'<b>@{esc(top.get("autor",""))}</b>'
                f'<span>{top.get("likes",0):,} me gusta · {top.get("reposts",0)} reposts</span></div>'
                .replace(",", ".")
                + f'<p>"{esc(top.get("texto",""))}"</p></div>'
            )
        if bloques_aut:
            tarjeta.append('<h5>Quiénes hablan más de este tema</h5>' + "".join(bloques_aut))
        tarjeta.append("</article>")
        tarjetas.append("".join(tarjeta))

    # ---- directorio ----
    filas_dir = []
    for a in directorio:
        temas_txt = ", ".join(TEMAS_UI.get(t, (t, ""))[0] for t in a.get("temas", []))
        filas_dir.append(
            '<div class="gc-cuenta">'
            f'<div class="gc-cuenta-cab"><b>@{esc(a.get("handle",""))}</b>'
            f'<span>{a.get("engagement",0):,} eng</span></div>'.replace(",", ".")
            + (f'<div class="gc-cuenta-nombre">{esc(a.get("nombre",""))}</div>' if a.get("nombre") else "")
            + f'<div class="gc-cuenta-meta">{a.get("posts",0)} posts · {a.get("likes",0):,} me gusta</div>'.replace(",", ".")
            + f'<div class="gc-cuenta-temas">{esc(temas_txt)}</div></div>'
        )

    aviso_hist = (
        f'<p class="gc-aviso">La serie temporal empieza hoy: llevamos <b>{dias}</b> '
        f'{"día" if dias == 1 else "días"}</b> de datos. Cada día a las 08:45 se añade un punto, '
        f'así que en una semana ya se podrá dibujar la evolución como en el dashboard de X.</p>'
    )

    etiquetas = json.dumps([TEMAS_UI.get(r.get("id"), (r.get("id"), ""))[0].split(" /")[0] for r in ranking], ensure_ascii=False)
    valores = json.dumps([r.get("engagement", 0) for r in ranking])

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Bluesky — Termómetro de la Guerra Cultural</title>
{estilos}
<style>
  .gc-wrap {{ max-width: 1200px; margin: 0 auto; padding: 1.5rem 1rem 4rem; }}
  .gc-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 130px), 1fr)); gap: .6rem; margin: 1rem 0 1.5rem; }}
  .gc-kpis > div {{ border: 1px solid rgba(148,163,184,.28); border-radius: 12px; padding: .7rem .8rem; }}
  .gc-kpis b {{ display: block; font-size: 1.3rem; }}
  .gc-kpis span {{ font-size: .74rem; opacity: .75; }}
  .gc-tema {{ margin-bottom: .75rem; }}
  .gc-fila {{ display: flex; justify-content: space-between; font-size: .85rem; }}
  .gc-valor {{ font-variant-numeric: tabular-nums; opacity: .85; }}
  .gc-pista {{ background: rgba(148,163,184,.18); border-radius: 99px; height: 9px; overflow: hidden; margin: .25rem 0 .15rem; }}
  .gc-relleno {{ background: #3b82f6; height: 100%; border-radius: 99px; }}
  .gc-naranja, .gc-relleno.gc-naranja {{ background: #f59e0b; }}
  .gc-sub {{ font-size: .72rem; opacity: .6; }}
  .gc-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 1rem; }}
  .gc-card {{ border: 1px solid rgba(148,163,184,.28); border-radius: 14px; padding: 1rem; min-width: 0; overflow-wrap: anywhere; }}
  .gc-card h4 {{ margin: 0 0 .5rem; font-size: 1rem; }}
  .gc-card h5 {{ margin: 1rem 0 .5rem; font-size: .8rem; opacity: .8; text-transform: uppercase; letter-spacing: .04em; }}
  .gc-card .gc-kpis {{ display: flex; flex-wrap: wrap; gap: .5rem .9rem; margin: 0 0 .5rem; font-size: .76rem; }}
  .gc-card .gc-kpis b {{ display: inline; font-size: .95rem; }}
  .gc-card .gc-kpis > span {{ border: 0; padding: 0; }}
  .gc-consulta {{ font-size: .72rem; opacity: .6; margin: .2rem 0 .6rem; }}
  .gc-top {{ border-left: 3px solid #3b82f6; padding: .5rem .7rem; background: rgba(59,130,246,.07); border-radius: 0 10px 10px 0; margin-bottom: .5rem; }}
  .gc-top-cab {{ display: flex; justify-content: space-between; font-size: .74rem; gap: .6rem; }}
  .gc-top p {{ margin: .35rem 0 0; font-size: .82rem; line-height: 1.5; overflow-wrap: anywhere; }}
  .gc-autor {{ margin-bottom: .55rem; }}
  .gc-autor-cab {{ display: flex; justify-content: space-between; font-size: .78rem; gap: .5rem; }}
  .gc-autor-eng {{ opacity: .7; font-size: .72rem; }}
  .gc-autor-ej {{ font-size: .74rem; opacity: .65; margin-top: .2rem; font-style: italic; overflow-wrap: anywhere; }}
  .gc-cuentas {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)); gap: .7rem; }}
  .gc-cuenta {{ border: 1px solid rgba(148,163,184,.25); border-radius: 12px; padding: .7rem .8rem; }}
  .gc-cuenta-cab {{ display: flex; justify-content: space-between; font-size: .82rem; gap: .5rem; }}
  .gc-cuenta-nombre {{ font-size: .76rem; opacity: .75; }}
  .gc-cuenta-meta {{ font-size: .72rem; opacity: .6; }}
  .gc-cuenta-temas {{ font-size: .72rem; opacity: .7; margin-top: .25rem; color: #f59e0b; }}
  .gc-aviso {{ font-size: .8rem; opacity: .75; border: 1px dashed rgba(148,163,184,.4); border-radius: 12px; padding: .7rem .9rem; }}
  h3.gc-h {{ margin: 2rem 0 .8rem; }}
  @media (max-width: 700px) {{
    .gc-wrap {{ padding: 1rem .7rem 3rem; }}
    .gc-grid, .gc-cuentas, .gc-kpis {{ grid-template-columns: 1fr; }}
    .gc-tema .gc-nombre {{ font-size: .8rem; }}
    .gc-valor {{ font-size: .78rem; }}
    .gc-card {{ padding: .8rem; }}
    .gc-top-cab, .gc-autor-cab, .gc-cuenta-cab {{ flex-wrap: wrap; }}
  }}
  html, body {{ max-width: 100%; overflow-x: hidden; }}
  .gc-wrap, .gc-card, .gc-tema, .gc-cuenta {{ min-width: 0; }}
</style>
</head>
<body>
{nav}
<div class="gc-wrap">
  <h1 style="margin:.2rem 0 .1rem">\U0001F98B Termómetro de la Guerra Cultural</h1>
  <p style="opacity:.7;font-size:.9rem;margin:0 0 1rem">Análisis de la conversación en Bluesky · Enfoque: España · Mismos 12 temas que el dashboard de X</p>
  <p class="gc-aviso" style="margin-bottom:1rem">\u26A0\uFE0F Los volúmenes de Bluesky y de X <b>no se suman</b>: son poblaciones distintas. Lo que se compara son las posiciones relativas de cada tema dentro de cada plataforma.</p>

  <div class="gc-kpis">
    <div><b>{meta.get('total_engagement',0):,}</b><span>engagement total</span></div>
    <div><b>{meta.get('total_posts',0):,}</b><span>posts analizados</span></div>
    <div><b>{meta.get('total_likes',0):,}</b><span>me gusta</span></div>
    <div><b>{meta.get('total_reposts',0):,}</b><span>reposts</span></div>
    <div><b>{meta.get('cuentas_unicas',0)}</b><span>cuentas únicas</span></div>
    <div><b>{meta.get('temas_ok',0)}</b><span>temas medidos</span></div>
  </div>

  <h3 class="gc-h">\U0001F4CA Intensidad del debate por tema</h3>
  <div style="height:300px"><canvas id="gcChart"></canvas></div>

  <h3 class="gc-h">\U0001F525 Ranking por engagement</h3>
  {''.join(filas)}

  <h3 class="gc-h">\U0001F4C8 Evolución</h3>
  {aviso_hist}

  <h3 class="gc-h">\U0001F4F0 Temas, posts más fuertes y quiénes hablan de ellos</h3>
  <div class="gc-grid">{''.join(tarjetas)}</div>

  <h3 class="gc-h">\U0001F465 Directorio de cuentas que más hablan de estos temas</h3>
  <div class="gc-cuentas">{''.join(filas_dir)}</div>

  <hr style="margin:2rem 0 1rem;opacity:.2">
  <p style="font-size:.74rem;opacity:.6">Datos: {esc(meta.get('fuente',''))} · Actualizado: {esc(meta.get('generated_at',''))} · {esc(meta.get('nota',''))}</p>
</div>
<script src="chart.js"></script>
<script>
  (function () {{
    const ctx = document.getElementById('gcChart');
    if (!ctx || typeof Chart === 'undefined') return;
    new Chart(ctx, {{
      type: 'bar',
      data: {{
        labels: {etiquetas},
        datasets: [{{ label: 'Engagement', data: {valores}, backgroundColor: '#3b82f6' }}]
      }},
      options: {{
        indexAxis: 'y',
        responsive: true, maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{ x: {{ beginAtZero: true }}, y: {{ ticks: {{ autoSkip: false }} }} }}
      }}
    }});
  }})();
</script>
</body>
</html>
"""

    tmp = SALIDA + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(html)
    os.replace(tmp, SALIDA)
    print(f"Generado: {SALIDA} ({len(html)} bytes)")
    print(f"  temas: {len(ranking)} | autores por tema: {len(temas.get('okupacion',{}).get('autores',[]))} | directorio: {len(directorio)} | dias historial: {dias}")


if __name__ == "__main__":
    main()
