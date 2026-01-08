from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar, Optional

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import TransientError

from src.settings.settings import settings

T = TypeVar("T")

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        *,
        max_retries: int = 3,
        retry_backoff_sec: float = 0.5,
        database: Optional[str] = None,
    ):
        self._driver: Driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_acquisition_timeout=30,
        )
        self._max_retries = max_retries
        self._retry_backoff_sec = retry_backoff_sec
        self._database = database

    def close(self) -> None:
        logger.info("Closing Neo4j driver")
        self._driver.close()

    def execute_write(self, work: Callable[[Session], T]) -> T:
        return self._execute(work, write=True)

    def execute_read(self, work: Callable[[Session], T]) -> T:
        return self._execute(work, write=False)

    def _execute(self, work: Callable[[Session], T], *, write: bool) -> T:
        attempt = 0
        while True:
            try:
                with self._driver.session(database=self._database) as session:
                    if write:
                        return session.execute_write(lambda tx: work(tx))
                    else:
                        return session.execute_read(lambda tx: work(tx))
            except TransientError as e:
                attempt += 1
                if attempt > self._max_retries:
                    logger.exception("Exceeded Neo4j retry limit")
                    raise
                sleep_time = self._retry_backoff_sec * attempt
                logger.warning(
                    "Transient Neo4j error, retrying (%s/%s) in %.2fs",
                    attempt,
                    self._max_retries,
                    sleep_time,
                )
                time.sleep(sleep_time)

    def clear_database(self) -> None:
        def _clear(tx):
            tx.run("MATCH (n) DETACH DELETE n")

        self.execute_write(_clear)
        logger.warning("Neo4j database cleared")


neo4j_client = Neo4jClient(uri=settings.NEO4J_URI, user=settings.NEO4J_USER, password=settings.NEO4J_PASSWORD)
