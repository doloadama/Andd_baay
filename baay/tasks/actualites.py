# baay/tasks/actualites.py
"""
Tâche Celery — agrégation de l'actualité agro-météo sénégalaise.

Sources :
  • ANACIM  — https://www.anacim.sn  (agroclimat, alertes météo)
  • MAE     — https://agriculture.gouv.sn  (politique, programmes)
  • FAO SN  — https://www.fao.org/senegal/  (RSS disponible)

Stratégie :
  1. Tentative RSS (feedparser) — rapide, structuré
  2. Fallback scraping HTML (requests + BeautifulSoup) — plus fragile
  3. Stockage idempotent (url_originale = clé unique) via update_or_create
  4. Cache Redis 6h pour éviter de re-scraper entre deux planifications Beat

Planifié toutes les 6h dans settings.CELERY_BEAT_SCHEDULE.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone as _tz
from typing import Generator

import requests
from celery import shared_task
from django.core.cache import cache
from django.utils.timezone import make_aware

logger = logging.getLogger(__name__)

_SESSION_TIMEOUT = 10   # secondes par requête HTTP
_MAX_ARTICLES_PAR_SOURCE = 30
_CACHE_KEY_LOCK = "fetch_actualites_lock"
_CACHE_LOCK_TTL = 3600  # évite double-exécution si la tâche tourne encore


# ─── Sources configurées ──────────────────────────────────────────────────────

_SOURCES: list[dict] = [
    # ── ANACIM — RSS officiel ─────────────────────────────────────────────────
    {
        "source": "anacim",
        "categorie": "meteo",
        "label": "ANACIM",
        "rss_urls": [
            "https://www.anacim.sn/feed/",
            "https://www.anacim.sn/rss.xml",
        ],
        "fallback_url": "https://www.anacim.sn/actualites/",
        "fallback_article_selector": "article, .post-item, .news-item",
        "fallback_title_selector": "h2, h3, .title",
        "fallback_link_selector": "a",
    },
    # ── Ministère de l'Agriculture ─────────────────────────────────────────────
    {
        "source": "mae",
        "categorie": "politique",
        "label": "Ministère Agriculture Sénégal",
        "rss_urls": [
            "https://agriculture.gouv.sn/feed/",
            "https://www.agriculture.gouv.sn/feed/",
        ],
        "fallback_url": "https://agriculture.gouv.sn/actualites/",
        "fallback_article_selector": "article, .view-row, .news-item",
        "fallback_title_selector": "h2, h3, .views-field-title",
        "fallback_link_selector": "a",
    },
    # ── FAO Sénégal ───────────────────────────────────────────────────────────
    {
        "source": "fao",
        "categorie": "conseil",
        "label": "FAO Sénégal",
        "rss_urls": [
            "https://www.fao.org/senegal/news/rss/fr/",
            "https://www.fao.org/senegal/feed/",
        ],
        "fallback_url": None,
    },
]

_HEADERS = {
    "User-Agent": (
        "AnddBaay/1.0 (agricultural intelligence platform; "
        "contact: contact@anddbaay.com)"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.7",
    "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_date(date_str: str | None) -> datetime | None:
    """Convertit une date RSS/string en datetime aware UTC."""
    if not date_str:
        return None
    try:
        import email.utils
        parsed = email.utils.parsedate_to_datetime(date_str)
        return parsed.astimezone(_tz.utc)
    except Exception:
        pass
    # Formats courants ISO
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S+00:00",
                "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str.strip()[:25], fmt)
            return make_aware(dt, _tz.utc) if dt.tzinfo is None else dt.astimezone(_tz.utc)
        except ValueError:
            continue
    return None


def _fetch_rss(rss_url: str) -> list[dict] | None:
    """Tente de parser un flux RSS. Retourne une liste d'entrées ou None."""
    try:
        import feedparser
    except ImportError:
        logger.debug("feedparser non installé — scraping HTML uniquement.")
        return None

    try:
        resp = requests.get(rss_url, headers=_HEADERS, timeout=_SESSION_TIMEOUT)
        if resp.status_code != 200:
            return None
        feed = feedparser.parse(resp.content)
        if not feed.entries:
            return None
        return feed.entries
    except Exception as exc:
        logger.debug("RSS %s inaccessible : %s", rss_url, exc)
        return None


def _scrape_fallback(cfg: dict) -> Generator[dict, None, None]:
    """Scraping HTML basique en fallback si le flux RSS est absent/vide."""
    fallback_url = cfg.get("fallback_url")
    if not fallback_url:
        return

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.debug("beautifulsoup4 non installé — fallback désactivé.")
        return

    try:
        resp = requests.get(fallback_url, headers=_HEADERS, timeout=_SESSION_TIMEOUT)
        if resp.status_code != 200:
            return
        soup = BeautifulSoup(resp.text, "html.parser")

        articles = soup.select(cfg.get("fallback_article_selector", "article"))
        count = 0
        for article in articles[:_MAX_ARTICLES_PAR_SOURCE]:
            title_el = article.select_one(cfg.get("fallback_title_selector", "h2, h3"))
            link_el  = article.select_one(cfg.get("fallback_link_selector", "a"))
            if not title_el or not link_el:
                continue
            titre = title_el.get_text(strip=True)
            href  = link_el.get("href", "")
            if not href or not titre:
                continue
            # Résolution URL relative
            if href.startswith("/"):
                from urllib.parse import urlparse
                parts = urlparse(fallback_url)
                href = f"{parts.scheme}://{parts.netloc}{href}"
            elif not href.startswith("http"):
                continue

            yield {"title": titre, "link": href, "summary": "", "published": None}
            count += 1
        logger.debug("Scraping %s : %d articles trouvés.", fallback_url, count)
    except Exception as exc:
        logger.warning("Scraping HTML %s échoué : %s", fallback_url, exc)


def _upsert_article(
    source: str,
    categorie: str,
    titre: str,
    resume: str,
    url: str,
    date_pub: datetime | None,
    image_url: str = "",
) -> tuple[bool, bool]:
    """
    Crée ou met à jour un ArticleActualite.
    Retourne (created: bool, updated: bool).
    """
    from baay.models import ArticleActualite

    if not url or not titre:
        return False, False

    titre = titre.strip()[:490]
    resume = (resume or "").strip()[:2000]

    obj, created = ArticleActualite.objects.update_or_create(
        url_originale=url,
        defaults={
            "source": source,
            "categorie": categorie,
            "titre": titre,
            "resume": resume,
            "image_url": (image_url or "")[:2000],
            "date_publication": date_pub,
            "actif": True,
        },
    )
    return created, not created


# ─── Tâche principale ─────────────────────────────────────────────────────────

@shared_task(
    name="baay.tasks.fetch_actualites_task",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    ignore_result=True,
)
def fetch_actualites_task(self):
    """
    Parcourt toutes les sources configurées, récupère les articles via RSS
    ou scraping HTML, et les stocke/met à jour dans ArticleActualite.

    Planifié toutes les 6h dans CELERY_BEAT_SCHEDULE.
    Un verrou Redis d'une heure évite les exécutions concurrentes.
    """
    # ── Verrou anti-concurrence ───────────────────────────────────────────────
    if cache.get(_CACHE_KEY_LOCK):
        logger.info("fetch_actualites : tâche déjà en cours — ignorée.")
        return
    cache.set(_CACHE_KEY_LOCK, True, timeout=_CACHE_LOCK_TTL)

    total_created = 0
    total_updated = 0
    total_errors  = 0

    try:
        for cfg in _SOURCES:
            source   = cfg["source"]
            categorie = cfg["categorie"]
            entries  = []

            # 1. Tentative RSS ────────────────────────────────────────────────
            for rss_url in cfg.get("rss_urls", []):
                raw = _fetch_rss(rss_url)
                if raw:
                    entries = raw[:_MAX_ARTICLES_PAR_SOURCE]
                    logger.info(
                        "fetch_actualites [%s] : %d entrées via RSS %s.",
                        source, len(entries), rss_url,
                    )
                    break

            if entries:
                for entry in entries:
                    try:
                        titre    = getattr(entry, "title", None) or ""
                        url      = getattr(entry, "link",  None) or ""
                        resume   = getattr(entry, "summary", None) or ""
                        date_pub = _parse_date(
                            getattr(entry, "published", None)
                            or str(getattr(entry, "updated", None) or "")
                        )
                        # Image depuis media_content ou enclosures
                        image_url = ""
                        media = getattr(entry, "media_content", [])
                        if media and isinstance(media, list):
                            image_url = media[0].get("url", "") if media[0] else ""
                        if not image_url:
                            enclosures = getattr(entry, "enclosures", [])
                            for enc in enclosures or []:
                                if "image" in enc.get("type", ""):
                                    image_url = enc.get("href", "")
                                    break

                        created, updated = _upsert_article(
                            source, categorie, titre, resume, url, date_pub, image_url
                        )
                        total_created += int(created)
                        total_updated += int(updated)
                    except Exception as exc:
                        total_errors += 1
                        logger.debug("fetch_actualites [%s] erreur entrée : %s", source, exc)
            else:
                # 2. Fallback scraping HTML ───────────────────────────────────
                for item in _scrape_fallback(cfg):
                    try:
                        date_pub = _parse_date(item.get("published"))
                        created, updated = _upsert_article(
                            source, categorie,
                            item["title"], item.get("summary", ""),
                            item["link"], date_pub,
                        )
                        total_created += int(created)
                        total_updated += int(updated)
                    except Exception as exc:
                        total_errors += 1
                        logger.debug("fetch_actualites [%s] erreur scraping : %s", source, exc)

        logger.info(
            "fetch_actualites terminé : +%d créés, ~%d mis à jour, %d erreurs.",
            total_created, total_updated, total_errors,
        )
    except Exception as exc:
        logger.error("fetch_actualites : erreur globale : %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        cache.delete(_CACHE_KEY_LOCK)

    return {
        "created": total_created,
        "updated": total_updated,
        "errors": total_errors,
    }
