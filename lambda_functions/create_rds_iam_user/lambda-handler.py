import json
import os
from typing import TYPE_CHECKING

import boto3
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.typing import LambdaContext
from psycopg2 import Error, connect, sql

# ----- Environment Variables -----
rds_fdw_host = os.environ["RDS_FDW_HOST"]
rds_fdw_db = os.environ["RDS_FDW_DB"]

rds_fdw_root_secret = parameters.get_secret(os.environ["RDS_FDW_ROOT"])

rds_fdw_root_secret_key_value = json.loads(rds_fdw_root_secret)  # type: ignore
rds_fdw_root_user = rds_fdw_root_secret_key_value["username"]
rds_fdw_root_pw = rds_fdw_root_secret_key_value["password"]

rds_iam_group_name = os.environ["BDE_ANALYTICS_GROUP"]

if TYPE_CHECKING:
    from mypy_boto3_iam import IAMClient

    client: IAMClient = boto3.client("iam")
else:
    client = boto3.client("iam")


def create_rds_user_from_iam(username: str) -> None:
    conn = connect(
        host=rds_fdw_host,
        database=rds_fdw_db,
        user=rds_fdw_root_user,
        password=rds_fdw_root_pw,
    )

    sql_create_user = sql.SQL("CREATE ROLE {username} WITH LOGIN").format(
        username=sql.Identifier(username),
    )
    sql_grant_iam_role = sql.SQL("GRANT rds_iam TO {username}").format(
        username=sql.Identifier(username),
    )

    try:
        with conn.cursor() as cur:
            try:
                cur.execute(sql_create_user)

                cur.execute(sql_grant_iam_role)

            except Error:
                conn.rollback()
                raise

            conn.commit()

    finally:
        conn.close()


def ensure_iam_user_exists(username: str) -> None:
    try:
        client.get_user(UserName=username)
    except client.exceptions.NoSuchEntityException:
        client.create_user(
            UserName=username,
        )

    client.tag_user(UserName=username, Tags=[{"Key": "BDE_Analytics_User", "Value": "True"}])


def add_iam_user_to_group(username: str, group_name: str) -> None:
    client.add_user_to_group(GroupName=group_name, UserName=username)


def handler(event: dict[str, str], _context: LambdaContext) -> None:
    ensure_iam_user_exists(username=event["username"])
    add_iam_user_to_group(username=event["username"], group_name=rds_iam_group_name)

    create_rds_user_from_iam(username=event["username"])
