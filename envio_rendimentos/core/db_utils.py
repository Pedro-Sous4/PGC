import time
import random
import unicodedata
from django.db import IntegrityError


def _resilient_get_or_create(model, nome_value, nome_field='nome', defaults=None, max_retries=6):
    """Try to get or create an instance on `model` by `nome_field` in a race-safe way.

    Strategy:
    - Try model.objects.get_or_create(...) directly inside a few retries
    - On IntegrityError, re-query using case-insensitive / normalized filters
    - Return (obj, created)
    """
    # Normalize the provided name for some fallback lookups
    normalized = unicodedata.normalize("NFKC", str(nome_value).strip())

    for attempt in range(1, max_retries + 1):
        try:
            obj, created = model.objects.get_or_create(**{nome_field: nome_value}, defaults=(defaults or {}))
            return obj, created
        except IntegrityError:
            # Try a conservative re-query to recover from race
            obj = model.objects.filter(**{f"{nome_field}__iexact": nome_value}).first()
            if obj:
                return obj, False
            obj = model.objects.filter(**{f"{nome_field}__iexact": normalized}).first()
            if obj:
                return obj, False
            # mild backoff
            if attempt < max_retries:
                time.sleep(0.05 * attempt + random.random() * 0.02)
                continue
            # last try: let exception bubble
            raise


__all__ = ["_resilient_get_or_create"]