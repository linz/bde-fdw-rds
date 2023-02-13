from aws_cdk import Duration, RemovalPolicy, Stack, aws_ec2, aws_rds, aws_secretsmanager
from constructs import Construct


class Application(Stack):
    def __init__(  # type: ignore[no-untyped-def]  # pylint: disable=too-many-arguments
        self,
        scope: Construct,
        construct_id: str,
        deployment_env: str,
        vpc_id: str,
        subnet_ids: list[str],
        rds_fdw_instance_type: dict[str, str],
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

        # ----- Postgres with FDW RDS -----

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

        # Create postgres rds instance with fdw
        aws_rds.DatabaseInstance(
            self,
            "PostgresRDS_with_FDW_for_BDE_query",
            database_name="PostgresRDS_with_FDW_for_BDE_query",
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
            deletion_protection=deployment_env == "prod",
            backup_retention=Duration.days(100),
        )
