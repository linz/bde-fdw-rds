from aws_cdk import Duration, RemovalPolicy, Stack, aws_ec2, aws_lambda, aws_rds, aws_secretsmanager, triggers
from constructs import Construct

from stack.lambda_bundling import lambda_pip_install_requirements, zip_lambda_assets


class Application(Stack):
    def __init__(  # type: ignore[no-untyped-def]  # pylint: disable=too-many-arguments, too-many-locals
        self,
        scope: Construct,
        construct_id: str,
        vpc_id: str,
        subnet_ids: list[str],
        rds_fdw_instance_type: dict[str, str],
        bde_host_name: str,
        bde_analytics_user_secret: str,
        bde_rds_security_group: str,
        bastion_host_security_group: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ----- Networking -----

        vpc = aws_ec2.Vpc.from_lookup(self, "BDEHostVPC", vpc_id=vpc_id)
        subnets = []
        for subnet_id in subnet_ids:
            subnets.append(
                aws_ec2.Subnet.from_subnet_attributes(
                    self,
                    subnet_id.replace("-", "").replace("_", "").replace(" ", ""),
                    subnet_id=subnet_id,
                )
            )

        vpc_subnets = aws_ec2.SubnetSelection(subnets=subnets)

        # ----- Postgres RDS with FDW -----

        # Generate ROOT credentials for postgresql rds with fdw and store it in secret manager
        postgres_fdw_rds_root_cred_secret = aws_secretsmanager.Secret(
            self,
            "PostgresRDSCredentialSecretManagerRoot",
            generate_secret_string=aws_secretsmanager.SecretStringGenerator(
                exclude_characters="\"@/\\ '",
                generate_string_key="password",
                password_length=30,
                secret_string_template='{"username": "postgres"}',
            ),
        )

        postgres_fdw_rds_db_name = "bde_analytics"

        # Create postgres rds instance with fdw
        postgres_fdw_rds_instance = aws_rds.DatabaseInstance(
            self,
            "PostgresRDS_with_FDW_for_BDE_query",
            database_name=postgres_fdw_rds_db_name,
            instance_type=aws_ec2.InstanceType.of(
                getattr(aws_ec2.InstanceClass, rds_fdw_instance_type["class"]),
                getattr(aws_ec2.InstanceSize, rds_fdw_instance_type["size"]),
            ),
            allocated_storage=10,
            engine=aws_rds.DatabaseInstanceEngine.POSTGRES,
            credentials=aws_rds.Credentials.from_secret(postgres_fdw_rds_root_cred_secret, "postgres"),
            vpc=vpc,
            vpc_subnets=vpc_subnets,
            port=5432,
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False,
            backup_retention=Duration.days(10),  # Retention period must be between 0 and 35
        )

        # User with read-only permission to production bde needs to be created separately outside of this cdk.
        # This credential needs to exist in secrets manager before it can be used for fdw query here.
        production_bde_rds_ro_user_cred = aws_secretsmanager.Secret.from_secret_name_v2(
            self,
            "Prod-BDE-RDS-Credential-SecretManager-RO-User",
            secret_name=bde_analytics_user_secret,
        )

        # ----- Run rds init script from lambda -----

        lambda_ = "rds_init"
        lambda_working_dir = f"lambda_functions/.out/{lambda_}"

        lambda_pip_install_requirements(f"{lambda_working_dir}/packages", f"lambda_functions/{lambda_}/requirements.txt")
        lambda_assets = zip_lambda_assets(lambda_working_dir, lambda_)

        lambda_rds_init = triggers.TriggerFunction(
            self,
            "RDS Init",
            vpc=vpc,
            vpc_subnets=vpc_subnets,
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="lambda-handler.handler",
            timeout=Duration.minutes(10),  # Might take some time to connect to rds
            code=aws_lambda.Code.from_asset(lambda_assets),
            environment={
                "BDE_HOST_NAME": bde_host_name,
                "BDE_ANALYTICS_USER_SECRET": production_bde_rds_ro_user_cred.secret_name,
                "RDS_FDW_HOST": postgres_fdw_rds_instance.db_instance_endpoint_address,
                "RDS_FDW_DB": postgres_fdw_rds_db_name,
                "RDS_FDW_ROOT": postgres_fdw_rds_root_cred_secret.secret_name,
            },
        )

        # We could create our own IAM role and specify / assign permission to lambda and secrets,
        # but it is easier to let cdk create a default role for lambda and assign secrets permission here
        postgres_fdw_rds_root_cred_secret.grant_read(lambda_rds_init.role)  # type: ignore[arg-type]
        production_bde_rds_ro_user_cred.grant_read(lambda_rds_init.role)  # type: ignore[arg-type]

        postgres_fdw_rds_instance.connections.allow_from(lambda_rds_init, port_range=aws_ec2.Port.tcp(5432))

        # Security group attached to production bde, allowing access from linz network
        bde_rds_security_group_by_id = aws_ec2.SecurityGroup.from_lookup_by_id(
            self, "Prod BDE Security Group", bde_rds_security_group
        )
        postgres_fdw_rds_instance.connections.allow_from(
            bde_rds_security_group_by_id.connections, port_range=aws_ec2.Port.tcp(5432)
        )

        bastion_host_security_group_by_id = aws_ec2.SecurityGroup.from_lookup_by_id(
            self, "Bastion Host Security Group", bastion_host_security_group
        )
        postgres_fdw_rds_instance.connections.allow_from(
            bastion_host_security_group_by_id.connections, port_range=aws_ec2.Port.tcp(5432)
        )
