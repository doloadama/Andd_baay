import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import cloudinary.uploader
from PIL import Image

from baay.cloudinary_paths import cloudinary_media_folder

logger = logging.getLogger(__name__)

CROP_FOLDER = cloudinary_media_folder("analyses/plant")


def _upload_crop(args: tuple) -> tuple[int, str | None]:
    idx, buffer, class_name = args
    try:
        result = cloudinary.uploader.upload(buffer, folder=CROP_FOLDER)
        return idx, result.get("secure_url")
    except Exception as exc:
        logger.warning("Échec upload Cloudinary pour '%s': %s", class_name, exc)
        return idx, None


def crop_and_upload(image_bytes: bytes, detections: List[dict]) -> List[dict]:
    """Découpe les zones détectées et les envoie sur Cloudinary (parallèle)."""
    try:
        original = Image.open(io.BytesIO(image_bytes))
        width, height = original.size
    except Exception as exc:
        logger.warning("Impossible d'ouvrir l'image pour recadrage: %s", exc)
        return detections

    upload_tasks = []
    for i, detection in enumerate(detections):
        detection.setdefault("croppedImageUrl", None)
        bbox = detection.get("boundingBox")
        if not bbox:
            continue
        try:
            coords = (
                int(bbox["x_min"] * width),
                int(bbox["y_min"] * height),
                int(bbox["x_max"] * width),
                int(bbox["y_max"] * height),
            )
            if coords[0] >= coords[2] or coords[1] >= coords[3]:
                continue
            cropped = original.crop(coords)
            buffer = io.BytesIO()
            cropped.save(buffer, format="PNG")
            buffer.seek(0)
            upload_tasks.append((i, buffer, detection.get("className", "?")))
        except Exception as exc:
            logger.warning("Recadrage échoué: %s", exc)

    if upload_tasks:
        max_workers = min(len(upload_tasks), 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_upload_crop, task): task[0] for task in upload_tasks}
            for future in as_completed(futures):
                idx, url = future.result()
                if url:
                    detections[idx]["croppedImageUrl"] = url

    return detections
