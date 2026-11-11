# App host (EC2). Inbound rules are added later, together with the EC2 instance.
resource "aws_security_group" "app" {
  name        = "${local.name}-app-sg"
  description = "App host (EC2)"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name}-app-sg" }
}

resource "aws_vpc_security_group_egress_rule" "app_https_out" {
  security_group_id = aws_security_group.app.id

  ip_protocol = "tcp"
  from_port   = 443
  to_port     = 443

  cidr_ipv4   = "10.0.0.0/24"
  description = "Allow HTTPS to required destinations"
}

# Database. The only way in is PostgreSQL from the app security group.
resource "aws_security_group" "db" {
  name        = "${local.name}-db-sg"
  description = "RDS PostgreSQL, reachable only from the app security group"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name}-db-sg" }
}

resource "aws_vpc_security_group_ingress_rule" "db_from_app" {
  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
  description                  = "PostgreSQL from app hosts"
}
