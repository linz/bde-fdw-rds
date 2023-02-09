#!/usr/bin/env python3
import aws_cdk as cdk

from stack.bde_fdw_rds_stack import Application

app = cdk.App()

# Parse user provided context for environment parameter (i.e. prod / non-prod)
environment = app.node.try_get_context("environment")

if environment not in ("prod", "non-prod"):
    raise ValueError(f"Invalid deployment environment: “{environment}”. Available options: prod / non-prod")

# Instantiate additional context specified in cdk.json based on environment type
available_environments = app.node.try_get_context("available_environments")
deployment_environment = available_environments.get(environment)
aws_account = deployment_environment.get("account_id")
aws_region = deployment_environment.get("region")
aws_vpc_id = deployment_environment.get("vpc_id")
aws_subnets = deployment_environment.get("subnets")

cdk_env = cdk.Environment(account=aws_account, region=aws_region)

Application(
    app,
    "BdeFdwRdsStack",
    description="Provision AWS Postgres RDS with FDW, to query BDE Processor RDS.",
    env=cdk_env,
    vpc_id=aws_vpc_id,
    subnet_ids=aws_subnets,
)


# RUN: cdk synth -c environment=non-prod --profile bde-processor-nonprod
app.synth()
