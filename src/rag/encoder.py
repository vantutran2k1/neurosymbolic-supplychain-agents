import logging
import threading
from typing import Iterable

import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class TextEncoder:
    _instance = None
    _lock = threading.Lock()

    MODEL_NAME = "all-MiniLM-L6-v2"
    VECTOR_DIM = 384
    DEFAULT_BATCH_SIZE = 32

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        logger.info(
            "Loading embedding model '%s' on device '%s'",
            self.MODEL_NAME,
            self.device,
        )

        self.model = SentenceTransformer(
            self.MODEL_NAME,
            device=self.device,
        )

        self._warmup()

    def _warmup(self):
        try:
            with torch.no_grad():
                self.model.encode(["warmup"], convert_to_tensor=False)
            logger.info("TextEncoder warmup completed")
        except Exception:
            logger.exception("TextEncoder warmup failed")

    def encode(
        self,
        texts: list[str],
        batch_size: int | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []

        if not all(isinstance(t, str) and t.strip() for t in texts):
            raise ValueError("All input texts must be non-empty strings")

        batch_size = batch_size or self.DEFAULT_BATCH_SIZE

        embeddings: list[list[float]] = []

        with torch.no_grad():
            for batch in self._batch(texts, batch_size):
                batch_embeddings = self.model.encode(
                    batch,
                    convert_to_tensor=False,
                    show_progress_bar=False,
                )
                embeddings.extend(batch_embeddings)

        return embeddings

    @staticmethod
    def _batch(items: list[str], size: int) -> Iterable[list[str]]:
        for i in range(0, len(items), size):
            yield items[i : i + size]

    @property
    def dimension(self) -> int:
        return self.VECTOR_DIM
