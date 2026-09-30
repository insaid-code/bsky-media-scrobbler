# 📊 Motor de Estadísticas, Informes y Collages Visuales

`bsky-media-scrobbler` incluye un completo motor analítico que analiza tus hábitos de consumo multimedia, calcula balances temporales cerrados, monta collages visuales en alta definición y celebra hitos en tu perfil de Bluesky.

---

## 🗓️ Calendario de Publicaciones Periódicas

| Informe | Momento de Publicación | Período Analizado | Formato y Contenido |
| :--- | :--- | :--- | :--- |
| **Balance Semanal** | **Lunes a las 09:30h** *(o posterior)* | Semana natural completa cerrada (Lunes 00:00 a Domingo 23:59:59) | Collage de carátulas (**3x3** o **2x2**), episodios vistos, minutos y horas totales, películas y series finalizadas. |
| **Balance Mensual** | **Día 1 de mes a las 09:30h** *(o posterior)* | Mes natural completo cerrado (Día 1 00:00 a fin de mes 23:59:59) | Collage visual, minutos totales, series completadas y películas registradas durante el mes vencido. |
| **Curiosidad / Fun Fact** | **Día 15 de mes a las 12:00h** *(o posterior)* | Historial analítico consolidado | Rotación de 3 curiosidades: patrón de día/hora favorita de maratón, serie más larga terminada (medalla a la fidelidad) o tasa de finalización. |
| **Rachas de Días Activos** | Al sincronizar actividad diaria | Días consecutivos con visionados | Celebración de racha al alcanzar **7 días continuos** y en incrementos semanales (14, 21, 28, 35...). |
| **Hitos Históricos** | En tiempo real tras completar fichas | Contador acumulado global | Celebración al cruzar marcas redondas (ej. 18.000 episodios, 400 series terminadas, 450 películas). |

---

## 🖼️ Generación de Collages con Pillow

El motor genera automáticamente imágenes compuestas optimizadas para Bluesky (`collage.py`):

1. **Cuadrícula 3x3 (Por defecto):**
   * Muestra hasta **9 carátulas** en formato póster vertical (relación estándar 2:3).
   * Tamaño final: **1200 x 1800 px** en formato JPEG de alta calidad con compresión adaptativa `< 950 KB` (respetando los límites de subida de Bluesky).
   * Selección inteligente: Prioriza carátulas de series distintas y películas vistas en la semana/mes. Si el catálogo es menor a 9 pero mayor a 3, conmuta automáticamente a 2x2.
2. **Cuadrícula 2x2:**
   * Muestra **4 carátulas** principales.
   * Tamaño final: **1200 x 1800 px**.
   * Ideal para semanas con menos variedad de títulos o maratones centrados en pocas series.

---

## ⚡ Disparadores Manuales bajo Demanda (`Triggers`)

No necesitas esperar al lunes o al día 1 para probar o previsualizar un balance. El bucle de `app/main.py` comprueba cada 5 segundos la presencia de archivos señal en `/data`:

### 1. Forzar Resumen Semanal
```bash
# Cuadrícula estándar 3x3
echo "3x3" > data/trigger_weekly

# O cuadrícula compacta 2x2
echo "2x2" > data/trigger_weekly
```

### 2. Forzar Resumen Mensual
```bash
# Cuadrícula estándar 3x3
echo "3x3" > data/trigger_monthly

# O cuadrícula compacta 2x2
echo "2x2" > data/trigger_monthly
```

### 3. Forzar Curiosidad / Fun Fact
```bash
touch data/trigger_fun_fact
```

> **Comportamiento automático:** En cuanto el contenedor detecta el archivo señal, ejecuta la tarea inmediatamente, genera el informe con su imagen, lo publica en Bluesky y elimina el archivo para evitar re-ejecuciones. También puedes crearlos mediante Docker: `docker exec bsky-media-scrobbler touch /data/trigger_fun_fact`.

---

## 🎛️ Integración con Paneles de Control (OliveTin / HomeLab)

Si dispones de un panel de acciones web como **OliveTin**, puedes agregar botones directos a tu archivo `config.yaml` para disparar estas funciones con un solo toque:

```yaml
  # --- BLUESKY MEDIA SCROBBLER ---
  - title: "🦋 Bluesky: Forzar Resumen Mensual"
    icon: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='24' height='24'><path fill='#1185fe' d='M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566 1.018 1.561 1.748 1.561 3.254c0 3.28 1.83 13.435 8.439 13.435 3.398 0 4.887-2.98 5.86-5.889z'/></svg>"
    shell: "echo '{{ grid }}' > /ruta/a/bsky-media-scrobbler/data/trigger_monthly && echo 'Disparador mensual enviado con collage {{ grid }}'"
    timeout: 30
    arguments:
      - name: grid
        title: "Tipo de Cuadrícula"
        choices:
          - title: "🎨 Cuadrícula 3x3 (9 carátulas)"
            value: "3x3"
          - title: "🖼️ Cuadrícula 2x2 (4 carátulas)"
            value: "2x2"

  - title: "🦋 Bluesky: Forzar Curiosidad / Fun Fact"
    icon: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='24' height='24'><path fill='#f59e0b' d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z'/></svg>"
    shell: "touch /ruta/a/bsky-media-scrobbler/data/trigger_fun_fact && echo 'Petición de Curiosidad / Fun Fact enviada al scrobbler.'"
    timeout: 15
```
