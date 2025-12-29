CREATE CONSTRAINT session_id IF NOT EXISTS FOR (s:NegotiationSession) REQUIRE s.id IS UNIQUE;

CREATE INDEX offer_session IF NOT EXISTS FOR (o:Offer) ON (o.session_id);

CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE;

CREATE INDEX offer_timestamp IF NOT EXISTS FOR (o:Offer) ON (o.created_at);