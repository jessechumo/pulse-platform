# Hand-written rather than a community module, unlike vpc/eks -- a single
# Postgres instance with a subnet group and a security group is simple
# enough that wrapping it in a third-party module would add more
# indirection than it saves.

resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db"
  subnet_ids = var.subnet_ids
  tags       = var.tags
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.name}-rds-"
  description = "Allow Postgres from the EKS node security group"
  vpc_id      = var.vpc_id

  tags = var.tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "postgres_ingress" {
  for_each = toset(var.allowed_security_group_ids)

  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = each.value
}

resource "aws_db_instance" "this" {
  identifier     = var.name
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage = var.allocated_storage
  storage_encrypted = true

  db_name  = var.db_name
  username = var.username
  password = var.password

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Demo cluster: applied once for screenshots, then destroyed. A real
  # environment would want this false, a final snapshot, and backup
  # retention tuned beyond whatever default applies.
  skip_final_snapshot = true
  deletion_protection = false

  tags = var.tags
}
