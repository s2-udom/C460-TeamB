# Amazon Linux 2023, x86_64. x86 on purpose: images built on a normal laptop or
# Jenkins agent run here unchanged (no multi-arch builds needed).
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# The web app is public on port 80. Nothing else is open: no SSH (use SSM Session Manager),
# and Grafana/Prometheus are reached through SSM port forwarding, not the internet.
resource "aws_vpc_security_group_ingress_rule" "app_http" {
  for_each = toset(var.web_ingress_cidrs)

  security_group_id = aws_security_group.app.id
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  description       = "HTTP from ${each.value}"
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.app_instance_type
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region     = var.region
    secret_arn = aws_db_instance.main.master_user_secret[0].secret_arn
    db_host    = aws_db_instance.main.address
    db_port    = aws_db_instance.main.port
    db_name    = aws_db_instance.main.db_name
  })
  # Editing the boot script replaces the host. Fine here: the host holds no data,
  # Jenkins redeploys the containers.
  user_data_replace_on_change = true

  # IMDSv2 only. Hop limit 2 lets containers use the instance role too.
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_size = var.app_root_volume_gb
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "${local.name}-app" }

  lifecycle {
    # A newer AMI being published must not replace a running host.
    # To pick one up on purpose: terraform apply -replace=aws_instance.app
    ignore_changes = [ami]
  }
}

# Fixed public IP so the demo URL and the Jenkins deploy target survive a stop/start.
resource "aws_eip" "app" {
  domain   = "vpc"
  instance = aws_instance.app.id

  tags = { Name = "${local.name}-app-eip" }

  depends_on = [aws_internet_gateway.main]
}
