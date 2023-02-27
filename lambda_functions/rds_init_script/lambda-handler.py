import json
import os

import psycopg2
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.typing import LambdaContext

# ----- Production BDE -----
bde_host_name = os.environ["BDE_HOST_NAME"]
bde_analytics_user_secret = parameters.get_secret(os.environ["BDE_ANALYTICS_USER_SECRET"])

bde_analytics_user_secret = json.loads(bde_analytics_user_secret)  # type: ignore
bde_analytics_user_name = bde_analytics_user_secret["username"]  # type: ignore
bde_analytics_user_pw = bde_analytics_user_secret["password"]  # type: ignore


# ----- FDW Analytics -----
rds_fdw_host = os.environ["RDS_FDW_HOST"]
rds_fdw_db = os.environ["RDS_FDW_DB"]

rds_fdw_root_secret = parameters.get_secret(os.environ["RDS_FDW_ROOT"])

rds_fdw_root_secret = json.loads(rds_fdw_root_secret)  # type: ignore
rds_fdw_root_user = rds_fdw_root_secret["username"]  # type: ignore
rds_fdw_root_pw = rds_fdw_root_secret["password"]  # type: ignore


# This lambda function is only meant to be run once during cdk initialization,
# as post-db creation initialization script
def handler(_event: dict[str, str], _context: LambdaContext) -> None:
    conn = psycopg2.connect(
        host=rds_fdw_host,
        database=rds_fdw_db,
        user=rds_fdw_root_user,
        password=rds_fdw_root_pw,
    )

    try:
        with conn.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION postgis")
                cur.execute("CREATE EXTENSION postgres_fdw")

                cur.execute(
                    "CREATE SERVER bde_processor FOREIGN DATA WRAPPER postgres_fdw OPTIONS (host %s, port '5432', "
                    "dbname 'bde', extensions 'postgis')",
                    (bde_host_name,),
                )

                cur.execute("ALTER SERVER bde_processor OPTIONS (SET fetch_size '100000')")

                cur.execute(
                    "CREATE USER MAPPING FOR postgres SERVER bde_processor OPTIONS (user %s, password %s)",
                    (bde_analytics_user_name, bde_analytics_user_pw),
                )

                cur.execute("CREATE SCHEMA bde")
                cur.execute("IMPORT FOREIGN SCHEMA bde FROM SERVER bde_processor INTO bde")

                cur.execute("CREATE SCHEMA table_version")
                cur.execute("IMPORT FOREIGN SCHEMA table_version FROM SERVER bde_processor INTO table_version")

                cur.execute("CREATE SCHEMA lds")
                cur.execute("IMPORT FOREIGN SCHEMA lds FROM SERVER bde_processor INTO lds")

                cur.execute("CREATE SCHEMA bde_ext")
                cur.execute("IMPORT FOREIGN SCHEMA bde_ext FROM SERVER bde_processor INTO bde_ext")

                cur.execute("CREATE SCHEMA bde_control")
                cur.execute("IMPORT FOREIGN SCHEMA bde_control FROM SERVER bde_processor INTO bde_control")

            except psycopg2.Error:
                conn.rollback()
                raise

            conn.commit()

    finally:
        conn.close()
