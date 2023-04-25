#!/usr/bin/env python3
import aws_cdk as cdk

from stack.bde_fdw_rds_stack import Application

app = cdk.App()

# Instantiate additional context specified in cdk.json based on environment type
environment = app.node.try_get_context("prod_env")

aws_account = environment.get("account_id")
aws_region = environment.get("region")
aws_vpc_id = environment.get("vpc_id")
aws_subnets = environment.get("subnets")

rds_fdw_instance_type = environment.get("rds_fdw_instance_type")

cdk_env = cdk.Environment(account=aws_account, region=aws_region)

bde_host_name = environment.get("bde_host_name")
bde_analytics_user_secret = environment.get("bde_analytics_user_secret")

bde_rds_security_group = environment.get("bde_rds_security_group")
bastion_host_security_group = environment.get("bastion_host_security_group")


Application(
    app,
    "BdeFdwRdsStack",
    description="Provision AWS Postgres RDS with FDW, to query BDE Processor RDS.",
    env=cdk_env,
    aws_account=aws_account,
    vpc_id=aws_vpc_id,
    subnet_ids=aws_subnets,
    rds_fdw_instance_type=rds_fdw_instance_type,
    bde_host_name=bde_host_name,
    bde_analytics_user_secret=bde_analytics_user_secret,
    bde_rds_security_group=bde_rds_security_group,
    bastion_host_security_group=bastion_host_security_group,
)


# RUN: cdk synth -c environment=non-prod --profile bde-processor-nonprod
app.synth()
