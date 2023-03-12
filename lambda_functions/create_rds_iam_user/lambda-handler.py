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


def ensure_iam_user_exists(username: str, iam_policy_arn: str) -> None:
    try:
        client.get_user(UserName=username)
    except client.exceptions.NoSuchEntityException:
        client.create_user(
            UserName=username,
        )
    client.attach_role_policy(RoleName=username, PolicyArn=iam_policy_arn)
    client.tag_user(UserName=username, Tags=[{"Key": "BDE_Analytics_User", "Value": "True"}])


def generate_iam_user_policy(username: str) -> str:
    # Resource arn needs to be specific to a particular user to prevent individuals from connecting as another user.
    resource_arn = f"arn:aws:rds:ap-southeast-2:167241006131:db:{rds_fdw_host}/{username}"

    iam_user_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Action": "rds-db:connect", "Resource": resource_arn, "Effect": "Allow"}],
    }

    response = client.create_policy(
        PolicyName=f"bde-analytics-iam-policy-{username}",
        Path="bde-analytics-policies",
        PolicyDocument=json.dumps(iam_user_policy_document),
        Description="IAM policy allowing user access to bde analytics.",
    )

    return response["Policy"]["Arn"]


def handler(event: dict[str, str], _context: LambdaContext) -> None:
    iam_policy_arn = generate_iam_user_policy(username=event["username"])
    ensure_iam_user_exists(username=event["username"], iam_policy_arn=iam_policy_arn)

    create_rds_user_from_iam(username=event["username"])
