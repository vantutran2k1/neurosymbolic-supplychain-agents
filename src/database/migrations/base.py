from abc import ABC, abstractmethod

from src.database.connector import Neo4jConnector


class Migration(ABC):
    version: int
    name: str

    @abstractmethod
    def up(self, db: Neo4jConnector):
        pass
