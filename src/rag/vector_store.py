import logging
from typing import Any, Iterable

from qdrant_client import QdrantClient
from qdrant_client.http import models

logger = logging.getLogger(__name__)


class VectorStore:
    DEFAULT_COLLECTION = "supply_chain_knowledge"
    DEFAULT_DISTANCE = models.Distance.COSINE
    DEFAULT_BATCH_SIZE = 64

    def __init__(
        self,
        collection_name: str | None = None,
        host: str = "localhost",
        port: int = 6333,
    ):
        self.collection_name = collection_name or self.DEFAULT_COLLECTION

        self.client = QdrantClient(
            host=host,
            port=port,
            timeout=30,
        )

    def ensure_collection(self, vector_size: int) -> None:
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if exists:
                return

            logger.info("Creating Qdrant collection '%s'", self.collection_name)

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=self.DEFAULT_DISTANCE,
                ),
            )

        except Exception as exc:
            logger.exception("Failed to ensure collection")
            raise RuntimeError("Vector collection initialization failed") from exc

    def upsert_vectors(
        self,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        batch_size: int | None = None,
    ) -> None:
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("ids, vectors, and payloads must have equal length")

        batch_size = batch_size or self.DEFAULT_BATCH_SIZE

        for batch in self._batch(zip(ids, vectors, payloads), batch_size):
            points = [
                models.PointStruct(
                    id=idx,
                    vector=vector,
                    payload=payload,
                )
                for idx, vector, payload in batch
            ]

            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                )
            except Exception as exc:
                logger.exception("Vector upsert failed")
                raise RuntimeError("Vector upsert failed") from exc

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float | None = 0.5,
    ):
        try:
            return self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
            )
        except Exception as exc:
            logger.exception("Vector search failed")
            raise RuntimeError("Vector search failed") from exc

    @staticmethod
    def _batch(
        items: Iterable,
        size: int,
    ) -> Iterable[list]:
        batch = []
        for item in items:
            batch.append(item)
            if len(batch) == size:
                yield batch
                batch = []
        if batch:
            yield batch
