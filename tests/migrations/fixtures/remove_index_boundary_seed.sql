CREATE ROLE app_migrator LOGIN PASSWORD 'migrator-4e02';
GRANT CONNECT ON DATABASE postgres TO app_migrator;

-- Models of the primary tenant declare no Meta.schema, so their unqualified names resolve
-- through this search_path: tenant_north first, then legacy, then public. tenant_south and tenant_west
-- are reachable only by explicit schema qualification.
ALTER ROLE app_migrator SET search_path = tenant_north, legacy, public;

CREATE SCHEMA tenant_north AUTHORIZATION app_migrator;
CREATE SCHEMA tenant_south AUTHORIZATION app_migrator;
CREATE SCHEMA tenant_west AUTHORIZATION app_migrator;
CREATE SCHEMA legacy AUTHORIZATION app_migrator;

-- Tortoise names Index(fields=("customer_id",)) on table "orders" idx_orders_custome_384e97
-- regardless of schema, so every tenant that ran the same migration holds an index of that
-- name. An unqualified DROP INDEX for tenant_south resolves through search_path and silently
-- drops tenant_north's copy instead.
CREATE TABLE tenant_north.orders (
    id serial PRIMARY KEY,
    customer_id integer NOT NULL,
    external_ref text,
    status text NOT NULL DEFAULT 'pending'
);
CREATE INDEX idx_orders_custome_384e97 ON tenant_north.orders (customer_id);
CREATE UNIQUE INDEX uniq_orders_pending_ref ON tenant_north.orders (external_ref)
    WHERE status = 'pending';

CREATE TABLE tenant_south.orders (
    id serial PRIMARY KEY,
    customer_id integer NOT NULL,
    external_ref text,
    status text NOT NULL DEFAULT 'pending'
);
CREATE INDEX idx_orders_custome_384e97 ON tenant_south.orders (customer_id);
CREATE UNIQUE INDEX uniq_orders_pending_ref ON tenant_south.orders (external_ref)
    WHERE status = 'pending';

-- No same-named index on search_path: an unqualified DROP INDEX raises "does not exist".
CREATE TABLE tenant_west.orders (
    id serial PRIMARY KEY,
    customer_id integer NOT NULL
);
CREATE INDEX idx_orders_west_customer_id ON tenant_west.orders (customer_id);

-- Schema-less model whose table lives in public, the last search_path entry.
CREATE TABLE public.orders_default (
    id serial PRIMARY KEY,
    customer_id integer NOT NULL
);
CREATE INDEX idx_orders_defa_custome_89fb99 ON public.orders_default (customer_id);

-- Legacy unique constraints predating Tortoise, so they carry Postgres' own names rather than
-- the deterministic uid_customers_email_cf3ae8. The schema-less "customers" model resolves to
-- tenant_north.customers via search_path; public.customers is an older shared table with a
-- differently named constraint on the same column, so looking up the constraint name in
-- public (or in any search_path schema other than the first match) yields a name that does
-- not exist on the table the ALTER TABLE actually targets. public.customers is created first
-- so a lookup that ignores search_path order sees its constraint first.
CREATE TABLE public.customers (
    id serial PRIMARY KEY,
    email text NOT NULL,
    CONSTRAINT customers_email_uniq UNIQUE (email)
);

CREATE TABLE tenant_north.customers (
    id serial PRIMARY KEY,
    email text NOT NULL UNIQUE,
    phone text
);

-- tenant_west came from another system with its own constraint naming, so an explicit-schema
-- lookup that drifts onto the search_path finds tenant_north's customers_email_key instead.
CREATE TABLE tenant_west.customers (
    id serial PRIMARY KEY,
    email text NOT NULL,
    phone text,
    CONSTRAINT west_customers_email_uniq UNIQUE (email)
);

-- Legacy unique indexes with no constraint behind them: pg_constraint knows nothing about
-- them, so a unique_together removal must find them through pg_index. Both tenants use the
-- same name; tenant_west's copy is created first, so a lookup by index name that ignores the
-- table sees it first, and an unqualified DROP INDEX resolves to tenant_north's copy.
CREATE UNIQUE INDEX customers_phone_key ON tenant_west.customers (phone);
CREATE UNIQUE INDEX customers_phone_key ON tenant_north.customers (phone);

-- Schema-less model whose legacy table exists only in legacy, the middle search_path entry:
-- the lookup has to find the table search_path actually resolves to, not assume the first
-- schema or public.
CREATE TABLE legacy.accounts (
    id serial PRIMARY KEY,
    email text NOT NULL UNIQUE
);

INSERT INTO tenant_north.orders (customer_id, external_ref, status)
    VALUES (101, 'N-1', 'paid'), (102, 'N-2', 'pending');
INSERT INTO tenant_south.orders (customer_id, external_ref, status)
    VALUES (201, 'S-1', 'paid'), (202, 'S-2', 'pending');
INSERT INTO tenant_west.orders (customer_id) VALUES (401);
INSERT INTO public.orders_default (customer_id) VALUES (301);
INSERT INTO tenant_north.customers (email) VALUES ('ann@north.example');
INSERT INTO public.customers (email) VALUES ('legacy@shared.example');
INSERT INTO tenant_west.customers (email) VALUES ('wes@west.example');
INSERT INTO legacy.accounts (email) VALUES ('ops@shared.example');

ALTER TABLE tenant_north.orders OWNER TO app_migrator;
ALTER TABLE tenant_south.orders OWNER TO app_migrator;
ALTER TABLE tenant_west.orders OWNER TO app_migrator;
ALTER TABLE public.orders_default OWNER TO app_migrator;
ALTER TABLE tenant_north.customers OWNER TO app_migrator;
ALTER TABLE public.customers OWNER TO app_migrator;
ALTER TABLE tenant_west.customers OWNER TO app_migrator;
ALTER TABLE legacy.accounts OWNER TO app_migrator;
