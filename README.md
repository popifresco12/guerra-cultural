# 🌡️ Termómetro de la Guerra Cultural

Dashboard de análisis diario de la guerra cultural en **X (España)**: intensidad del debate por tema, tendencias, polémicas recientes y directorio de cuentas por espectro político.

**URL en producción:** https://popifresco12.github.io/guerra-cultural/

## ¿Qué es?

Un panel que monitoriza cómo evoluciona la conversación política en X sobre 12 temas de la guerra cultural española (Sanchismo, Inmigración, Okupación, Wokismo, Ley Trans, Memoria Histórica, etc.):

- 📊 **Intensidad del debate** por tema (0-100) + matriz de inclinación ideológica
- 📈 **Evolución semanal** con alertas de subidas bruscas
- 🃏 **Tarjetas por tema**: resumen del debate, cita destacada, volumen, sentimiento
- 📰 **Polémicas recientes** y **tuits virales**
- 👥 **Directorio de cuentas** por espectro político

## Cómo se generan los datos

Los datos se actualizan **automáticamente cada día a las 08:00** mediante un cron de Hermes (agente de IA):

1. Búsqueda en X con **Grok (xAI)** por tema (queries específicas por tema + ventana temporal)
2. **Análisis e interpretación con IA** (DeepSeek/Grok): intensidad, momentum, sentimiento
3. Generación de `data.json` + `history.json` (historial)
4. Publicación automática en GitHub Pages

> ⚠️ **Disclaimer:** los datos reflejan el volumen e intensidad del debate en X, **no** encuestas representativas de la población. El análisis es generado por IA y puede contener sesgos.

## Stack

- **Frontend:** HTML/CSS/JS vanilla + Chart.js (sin frameworks, ~75KB total)
- **Datos:** JSON estáticos (`data.json`, `history.json`)
- **Hosting:** GitHub Pages (gratis)
- **Generación de datos:** Hermes agent + cron + Grok (xAI) + DeepSeek

## Estructura

```
├── index.html      # Dashboard completo
├── data.json       # Datos actuales (12 temas, noticias, cuentas, virales)
├── history.json    # Historial para la evolución semanal
```

## Desarrollo

El proyecto es estático: abre `index.html` localmente o súbelo a cualquier hosting estático (GitHub Pages, Netlify, Vercel). Los datos se regeneran con el cron.

## Licencia

MIT
