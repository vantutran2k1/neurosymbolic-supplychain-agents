from typing import LiteralString

from src.database.connector import Neo4jConnector
from src.database.migrations.base import Migration


class AddNegotiationSchema(Migration):
    name = "add_negotiation_schema"
    version = 2

    def up(self, db: Neo4jConnector):
        stms: list[LiteralString] = [
            "CREATE CONSTRAINT session_id IF NOT EXISTS FOR (s:NegotiationSession) REQUIRE s.id IS UNIQUE;",
            "CREATE INDEX offer_session IF NOT EXISTS FOR (o:Offer) ON (o.session_id);",
            "CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE;",
            "CREATE INDEX offer_timestamp IF NOT EXISTS FOR (o:Offer) ON (o.created_at);",
        ]

        for stm in stms:
            db.run_query(stm)
