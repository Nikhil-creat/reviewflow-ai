"""Free, local embeddings (fastembed / ONNX, 384-d). Groq has no embeddings endpoint.
If the model cannot be downloaded (offline), falls back to a deterministic hashed
bag-of-words vector so the whole pipeline still runs."""
import asyncio
import hashlib
import logging
import math
import re

from .config import settings

log = logging.getLogger("reviewflow.embed")
_model = None
_failed = False


def _load():
    global _model, _failed
    if _model is not None or _failed:
        return _model
    try:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=settings.embedding_model,
                               cache_dir="/root/.cache/huggingface/fastembed")
        log.info("embedding model ready: %s", settings.embedding_model)
    except Exception as exc:
        _failed = True
        log.warning("fastembed unavailable (%s) - using hashed fallback embeddings", exc)
    return _model


def _hash_embed(text: str) -> list[float]:
    dim = settings.embedding_dim
    v = [0.0] * dim
    for tok in re.findall(r"[a-z0-9']+", text.lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        v[h % dim] += 1.0 if (h >> 8) % 2 else -1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _embed_sync(texts: list[str]) -> list[list[float]]:
    m = _load()
    if m is None:
        return [_hash_embed(t) for t in texts]
    return [list(map(float, e)) for e in m.embed(texts)]


async def embed_many(texts: list[str]) -> list[list[float]]:
    return await asyncio.to_thread(_embed_sync, texts)


async def embed_one(text: str) -> list[float]:
    return (await embed_many([text]))[0]
