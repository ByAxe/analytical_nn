DROP SCHEMA IF EXISTS poloniex CASCADE;
CREATE SCHEMA poloniex;

SET SEARCH_PATH TO poloniex;

CREATE TABLE currencies (
  id              BIGINT PRIMARY KEY,
  symbol          VARCHAR(20),
  name            VARCHAR(40),
  min_conf        SMALLINT,
  deposit_address VARCHAR(255),
  disabled        SMALLINT,
  delisted        SMALLINT,
  frozen          SMALLINT
);