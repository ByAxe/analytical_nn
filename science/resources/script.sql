DROP SCHEMA IF EXISTS poloniex CASCADE;
CREATE SCHEMA poloniex;

COMMENT ON SCHEMA poloniex IS 'Schema that contains all the data for interacting with market called Poloniex';

SET SEARCH_PATH TO poloniex;

DROP TABLE IF EXISTS poloniex.currencies CASCADE;
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

COMMENT ON TABLE poloniex.currencies IS 'Actual information about currencies on poloniex (its statuses and so on)';
COMMENT ON COLUMN poloniex.currencies.symbol IS 'Currency symbol. Short upper-case sequence';
COMMENT ON COLUMN poloniex.currencies.name IS 'Full currency name';
COMMENT ON COLUMN poloniex.currencies.min_conf IS 'Amount of minimal confirmations to assert the transaction';
COMMENT ON COLUMN poloniex.currencies.deposit_address IS 'Address where to send currency';
COMMENT ON COLUMN poloniex.currencies.disabled IS 'Whether is operations with currency disabled';
COMMENT ON COLUMN poloniex.currencies.delisted IS 'Whether is currency removed';
COMMENT ON COLUMN poloniex.currencies.frozen IS 'Whether is currency temporary frozen';


DROP TABLE IF EXISTS poloniex.chart_data CASCADE;
CREATE TABLE chart_data (
  main_currency      VARCHAR(20),
  secondary_currency VARCHAR(20),
  date               BIGINT,
  period             INT,
  high               NUMERIC,
  low                NUMERIC,
  open               NUMERIC,
  close              NUMERIC,
  volume             NUMERIC,
  quote_volume       NUMERIC,
  weighted_average   NUMERIC,
  PRIMARY KEY (main_currency, secondary_currency, date, period)
);

COMMENT ON TABLE poloniex.chart_data IS 'Master table of all chart data for actual currencies. Partitioned into bunch of tables those are differs in currency pair';
COMMENT ON COLUMN poloniex.chart_data.main_currency IS 'Main currency of pair (left one). Also, used as part of partition key';
COMMENT ON COLUMN poloniex.chart_data.secondary_currency IS 'Secondary currency of pair (right one). Also, used as part of partition key';
COMMENT ON COLUMN poloniex.chart_data.date IS 'Date in seconds for such these data was actual';
COMMENT ON COLUMN poloniex.chart_data.period IS 'Periodicity of data in seconds';
COMMENT ON COLUMN poloniex.chart_data.high IS 'Maximal value of currency for this period';
COMMENT ON COLUMN poloniex.chart_data.low IS 'Minimal value of currency for this period';
COMMENT ON COLUMN poloniex.chart_data.open IS 'Opening value of currency for this period';
COMMENT ON COLUMN poloniex.chart_data.close IS 'Closing value of currency for this period';
COMMENT ON COLUMN poloniex.chart_data.volume IS 'Traded volume of main (left) currency of pair during this period';
COMMENT ON COLUMN poloniex.chart_data.quote_volume IS 'Traded volume of secondary (right) currency of pair during this period';
COMMENT ON COLUMN poloniex.chart_data.weighted_average IS 'Average value of price for this period';

CREATE INDEX chart_data_date_idx
  ON poloniex.chart_data (date, period);

COMMENT ON INDEX poloniex.chart_data_date_idx IS 'For speeding up a selections';

CREATE OR REPLACE FUNCTION poloniex.chart_data_insert_trigger()
  RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
  RES             RECORD;
  v_parition_name VARCHAR;
BEGIN

  v_parition_name := NEW.main_currency || '_' || NEW.secondary_currency || '_' || NEW.period;
  EXECUTE 'INSERT INTO poloniex.chart_data_' || v_parition_name || ' VALUES ( ($1).* )RETURNING *'
  INTO RES
  USING NEW;
  RETURN NULL;
  EXCEPTION WHEN undefined_table
  THEN
    PERFORM 1
    FROM pg_tables t
    WHERE t.tablename = 'chart_data_' || v_parition_name AND t.schemaname = 'poloniex'
    LIMIT 1;
    IF NOT FOUND
    THEN
      EXECUTE
      'CREATE TABLE poloniex.chart_data_' || v_parition_name || ' ( CHECK ( period = ' || NEW.period ||
      ')) INHERITS ( poloniex.chart_data) /*TABLESPACE pgstore_table*/;';
      EXECUTE 'CREATE INDEX chart_data_' || v_parition_name || '_date_idx  ON poloniex.chart_data_' ||
              v_parition_name || ' using btree  (date, period) /*TABLESPACE pgstore_idx*/;';
    END IF;
    EXECUTE 'INSERT INTO poloniex.chart_data_' || v_parition_name || ' VALUES ( ($1).* )RETURNING *'
    INTO RES
    USING NEW;
    RETURN NULL;
END;
$$;

CREATE TRIGGER insert_trigger
  BEFORE INSERT
  ON poloniex.chart_data
  FOR EACH ROW EXECUTE PROCEDURE poloniex.chart_data_insert_trigger();

COMMENT ON FUNCTION poloniex.chart_data_insert_trigger() IS 'Partitions tables for Pairs and Period. Example: chart_data_ETH_STEEM_14400';