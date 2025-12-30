import logging
import uuid
from typing import Iterable, Any

from src.database.connector import Neo4jConnector
from src.rag.encoder import TextEncoder
from src.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class GraphIndexer:
    DEFAULT_BATCH_SIZE = 64

    def __init__(self, batch_size: int | None = None):
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE

        self.encoder = TextEncoder()
        self.store = VectorStore()

        self.store.ensure_collection(self.encoder.dimension)

    def index_products(self) -> None:
        logger.info("Starting product indexing")

        with Neo4jConnector() as db:
            records = self._fetch_products(db)

            if not records:
                logger.warning("No products found for indexing")
                return

            self._index_records(records)

        logger.info("Product indexing completed successfully")

    def _index_records(self, records: list[dict[str, Any]]) -> None:
        logger.info("Indexing %d products", len(records))

        for batch in self._batch(records, self.batch_size):
            texts, payloads, ids = self._prepare_batch(batch)

            logger.debug("Encoding batch of size %d", len(texts))
            vectors = self.encoder.encode(texts)

            self.store.upsert_vectors(
                ids=ids,
                vectors=vectors,
                payloads=payloads,
            )

    def _prepare_batch(
        self, batch: list[dict[str, Any]]
    ) -> tuple[list[str], list[dict[str, Any]], list[str]]:
        texts: list[str] = []
        payloads: list[dict[str, Any]] = []
        ids: list[str] = []

        for record in batch:
            text = self._linearize_product(record)

            texts.append(text)
            payloads.append(
                {
                    "type": "product",
                    "sku": record["sku"],
                    "supplier": record["supplier"],
                    "original_text": text,
                }
            )
            ids.append(str(uuid.uuid4()))

        return texts, payloads, ids

    @staticmethod
    def _fetch_products(db: Neo4jConnector) -> list[dict[str, Any]]:
        query = """
            MATCH (p:Product)<-[:SUPPLIES]-(c:Company)
            RETURN
                p.sku AS sku,
                p.name AS name,
                p.category AS category,
                p.base_price AS price,
                c.name AS supplier
            """

        logger.debug("Fetching products from Neo4j")
        return db.run_query(query)

    @staticmethod
    def _linearize_product(record: dict[str, Any]) -> str:
        return (
            f"Product: {record['name']}. "
            f"Category: {record['category']}. "
            f"Supplied by {record['supplier']}. "
            f"Base market price is around ${record['price']}."
        )

    @staticmethod
    def _batch(
        items: list[Any],
        size: int,
    ) -> Iterable[list[Any]]:
        for i in range(0, len(items), size):
            yield items[i : i + size]
