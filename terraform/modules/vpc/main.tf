data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  # Two AZs: enough for a realistic multi-AZ demo without paying for a
  # third NAT path or subnet set nobody's going to use before this gets
  # destroyed.
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.0"

  name = var.name
  cidr = var.cidr_block

  azs             = local.azs
  private_subnets = [for i, az in local.azs : cidrsubnet(var.cidr_block, 4, i)]
  public_subnets  = [for i, az in local.azs : cidrsubnet(var.cidr_block, 4, i + 8)]

  enable_nat_gateway   = true
  single_nat_gateway   = true # one NAT for a dev cluster, not one per AZ -- cost over redundancy here
  enable_dns_hostnames = true

  # EKS auto-discovers subnets by these tags for ELB/internal-ELB placement.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = var.tags
}
