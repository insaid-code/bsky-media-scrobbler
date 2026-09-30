import io
import logging
import requests
from PIL import Image

log = logging.getLogger("simkl-bluesky")


def create_poster_collage(
    poster_urls: list[str],
    target_count: int = 9,
    poster_width: int = 300,
    poster_height: int = 450,
    border_size: int = 8,
    bg_color: tuple[int, int, int] = (18, 22, 34),
) -> bytes | None:
    """
    Descarga una lista de carátulas y genera un collage compuesto en cuadrícula (2x2 o 3x3).
    Devuelve los bytes en formato JPEG comprimido optimizado para Bluesky (< 950 KB).
    """
    if not poster_urls:
        return None

    # Filtrar URLs válidas y eliminar duplicados manteniendo el orden
    seen = set()
    unique_urls = []
    for u in poster_urls:
        if u and u not in seen:
            seen.add(u)
            unique_urls.append(u)

    # Descargar imágenes
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    images: list[Image.Image] = []

    for url in unique_urls:
        if len(images) >= target_count:
            break
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200 and resp.content:
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                img = img.resize((poster_width, poster_height), Image.Resampling.LANCZOS)
                images.append(img)
        except Exception as e:
            log.warning("No se pudo descargar carátula para collage %s: %s", url, e)

    if not images:
        return None

    # Adaptar la cuadrícula dinámicamente según la cantidad de carátulas (hasta 9)
    images = images[:target_count]
    count = len(images)
    if count == 0:
        return None

    if count >= 7:
        cols, rows = 3, 3
    elif count in (5, 6):
        cols, rows = 3, 2
    elif count == 4:
        cols, rows = 2, 2
    elif count == 3:
        cols, rows = 3, 1
    elif count == 2:
        cols, rows = 2, 1
    else:
        cols, rows = 1, 1

    total_width = (cols * poster_width) + ((cols + 1) * border_size)
    total_height = (rows * poster_height) + ((rows + 1) * border_size)

    canvas = Image.new("RGB", (total_width, total_height), color=bg_color)

    for row_idx in range(rows):
        start_idx = row_idx * cols
        end_idx = min(start_idx + cols, count)
        row_images = images[start_idx:end_idx]
        num_in_row = len(row_images)
        if num_in_row == 0:
            continue

        row_content_width = (num_in_row * poster_width) + ((num_in_row - 1) * border_size)
        start_x = (total_width - row_content_width) // 2
        y = border_size + row_idx * (poster_height + border_size)

        for col_idx, img in enumerate(row_images):
            x = start_x + col_idx * (poster_width + border_size)
            canvas.paste(img, (x, y))

    output = io.BytesIO()
    canvas.save(output, format="JPEG", quality=85, optimize=True)
    jpeg_bytes = output.getvalue()

    # Asegurar que no supere 950KB (límite de Bluesky es 1MB por imagen)
    quality = 80
    while len(jpeg_bytes) > 950_000 and quality > 40:
        output = io.BytesIO()
        canvas.save(output, format="JPEG", quality=quality, optimize=True)
        jpeg_bytes = output.getvalue()
        quality -= 10

    log.info("Collage generado con éxito (%d imágenes, %d bytes).", len(images), len(jpeg_bytes))
    return jpeg_bytes
