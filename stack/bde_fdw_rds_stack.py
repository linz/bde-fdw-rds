from aws_cdk import Stack, aws_ec2
from constructs import Construct


class Application(Stack):
    def __init__(  # type: ignore[no-untyped-def]
        self,
        scope: Construct,
        construct_id: str,
        vpc_id: str,
        subnet_ids: list[str],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ----- Networking -----
        aws_ec2.Vpc.from_lookup(self, "BDEHostVPC", vpc_id=vpc_id)
        subnets = []
        for subnet_id in subnet_ids:
            subnets.append(
                aws_ec2.Subnet.from_subnet_attributes(
                    self,
                    subnet_id.replace("-", "").replace("_", "").replace(" ", ""),
                    subnet_id=subnet_id,
                )
            )

        aws_ec2.SubnetSelection(subnets=subnets)
