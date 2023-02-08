# AWS RDS with FDW module enabled for BDE analytics queries

[![GitHub Actions Status](https://github.com/linz/bde-fdw-rds/workflows/Build/badge.svg)](https://github.com/linz/bde-fdw-rds/actions)
[![Coverage: 100% branches](https://img.shields.io/badge/Coverage-100%25%20branches-brightgreen.svg)](https://pytest.org/)
[![Kodiak](https://badgen.net/badge/Kodiak/enabled?labelColor=2e3a44&color=F39938)](https://kodiakhq.com/)
[![Dependabot Status](https://badgen.net/badge/Dependabot/enabled?labelColor=2e3a44&color=blue)](https://github.com/linz/bde-fdw-rds/network/updates)
[![License](https://badgen.net/github/license/linz/bde-fdw-rds?labelColor=2e3a44&label=License)](https://github.com/linz/bde-fdw-rds/blob/master/LICENSE)
[![Conventional Commits](https://badgen.net/badge/Commits/conventional?labelColor=2e3a44&color=EC5772)](https://conventionalcommits.org)
[![Code Style](https://badgen.net/badge/Code%20Style/black?labelColor=2e3a44&color=000000)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Code Style: prettier](https://img.shields.io/badge/code_style-prettier-ff69b4.svg)](https://github.com/prettier/prettier)

This CDK creates an RDS instance in AWS with Postgres FDW module enabled. Its main purpose is to allow LINZ analysts to query the production BDE database. Direct connection to the production RDS instance is not ideal since users should not be allowed to write or alter the database directly. This repository works around this limitation by creating a separate RDS with FDW module, to allow analysts to query the production BDE database remotely and save their changes locally (RDS instance created by this repo).

## How it works

Each analyst will have access to their own schema in the RDS instance deployed by this repository. They can perform a cross database query to the production BDE database and save their changes locally within their own designated schema. Such separation of concern will limit the risk of an analyst accidentally taking down the production BDE database.

## Prerequisite

A read-only user needs to exist in the production BDE database to allow connection from the RDS instance created here.

Resources created by this repository should be deployed in the same VPC and subnets hosting the production BDE processor database. Deploying this CDK in another AWS account has been considered, but ultimately decided against since doing so will only add additional technical debt to the existing legacy application.
