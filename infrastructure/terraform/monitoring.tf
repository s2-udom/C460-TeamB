# Monitoring host: Prometheus, Alertmanager, Blackbox exporter, Loki, Alloy and Grafana
# from monitoring-config/, on one EC2 instance. Nothing is open to the internet:
# reach Grafana and Prometheus with SSM port forwarding (see the outputs).
# Needs jenkins.tf in the same folder (it defines data.aws_caller_identity.current).

variable "monitoring_instance_type" {
  description = "Instance type for the monitoring host. Six containers need about 2 GB, so t3.medium."
  type        = string
  default     = "t3.medium"
}

variable "monitoring_root_volume_gb" {
  description = "Root volume size in GB. Metrics and logs are stored here."
  type        = number
  default     = 30
}

variable "slack_webhook_parameter" {
  description = "SSM Parameter Store name (SecureString) holding the Slack incoming-webhook URL. Create it by hand."
  type        = string
  default     = "/ticketing/monitoring/slack-webhook-url"
}

locals {
  # Prometheus scrapes and probes the app host over the private network, on the port Docker publishes.
  app_target = "${aws_instance.app.private_ip}:80"

  # Every file in monitoring-config/ is uploaded as is. prometheus.yml is rendered from a template.
  monitoring_files = fileset("${path.module}/monitoring-config", "**")
}

# ---- Config bucket: the instance pulls its config from here, so config changes need no new host ----

resource "aws_s3_bucket" "monitoring" {
  bucket        = "${local.name}-monitoring-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "monitoring" {
  bucket                  = aws_s3_bucket.monitoring.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "monitoring" {
  bucket = aws_s3_bucket.monitoring.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_object" "monitoring_file" {
  for_each = local.monitoring_files

  bucket = aws_s3_bucket.monitoring.id
  key    = "config/${each.value}"
  source = "${path.module}/monitoring-config/${each.value}"
  etag   = filemd5("${path.module}/monitoring-config/${each.value}")
}

resource "aws_s3_object" "prometheus_config" {
  bucket       = aws_s3_bucket.monitoring.id
  key          = "config/prometheus/prometheus.yml"
  content      = templatefile("${path.module}/prometheus.yml.tftpl", { app_target = local.app_target })
  content_type = "text/yaml"
}

# ---- Network ----

resource "aws_security_group" "monitoring" {
  name        = "${local.name}-monitoring-sg"
  description = "Monitoring host: no inbound, all outbound"
  vpc_id      = aws_vpc.main.id
}
# Accepted risk: needs HTTPS to Docker Hub, S3 and SSM, and there is no NAT gateway or prefix list to narrow it.
#trivy:ignore:AWS-0104
resource "aws_vpc_security_group_egress_rule" "monitoring_https_out" {
  security_group_id = aws_security_group.monitoring.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "HTTPS: image pulls, S3, SSM"
}

resource "aws_vpc_security_group_egress_rule" "monitoring_to_app" {
  security_group_id            = aws_security_group.monitoring.id
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 80
  to_port                      = 80
  description                  = "Scrape and probe the app"
}

# The app host accepts the monitoring host on port 80 (it already accepts the public web CIDRs).
resource "aws_vpc_security_group_ingress_rule" "app_from_monitoring" {
  security_group_id            = aws_security_group.app.id
  referenced_security_group_id = aws_security_group.monitoring.id
  ip_protocol                  = "tcp"
  from_port                    = 80
  to_port                      = 80
  description                  = "Prometheus scrapes and probes from the monitoring host"
}

# ---- Identity: SSM access, read the config bucket, read the Slack webhook parameter ----

resource "aws_iam_role" "monitoring" {
  name = "${local.name}-monitoring-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "monitoring_ssm" {
  role       = aws_iam_role.monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "monitoring" {
  statement {
    sid       = "ReadConfigBucket"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.monitoring.arn}/config/*"]
  }

  statement {
    sid       = "ListConfigBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.monitoring.arn]
  }

  statement {
    sid     = "ReadSlackWebhook"
    actions = ["ssm:GetParameter"]
    resources = [
      "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter${var.slack_webhook_parameter}",
    ]
  }
}

resource "aws_iam_role_policy" "monitoring" {
  name   = "${local.name}-monitoring-access"
  role   = aws_iam_role.monitoring.id
  policy = data.aws_iam_policy_document.monitoring.json
}

resource "aws_iam_instance_profile" "monitoring" {
  name = "${local.name}-monitoring-profile"
  role = aws_iam_role.monitoring.name
}

# ---- Host ----

resource "aws_instance" "monitoring" {
  ami                         = data.aws_ami.al2023.id
  instance_type               = var.monitoring_instance_type
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.monitoring.id]
  iam_instance_profile        = aws_iam_instance_profile.monitoring.name
  associate_public_ip_address = true # outbound only: there is no NAT gateway, and no inbound rule exists

  user_data = templatefile("${path.module}/monitoring_user_data.sh.tftpl", {
    region          = var.region
    bucket          = aws_s3_bucket.monitoring.id
    slack_parameter = var.slack_webhook_parameter
  })
  user_data_replace_on_change = true

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  root_block_device {
    volume_size = var.monitoring_root_volume_gb
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "${local.name}-monitoring" }

  # Config must be in S3, and the role must be usable, before the first-boot script runs.
  depends_on = [
    aws_s3_object.monitoring_file,
    aws_s3_object.prometheus_config,
    aws_iam_role_policy_attachment.monitoring_ssm,
    aws_iam_role_policy.monitoring,
    aws_internet_gateway.main,
  ]

  lifecycle {
    ignore_changes = [ami]
  }
}

output "monitoring_instance_id" {
  value = aws_instance.monitoring.id
}

output "grafana_tunnel_command" {
  description = "Run on your laptop, then open http://localhost:3001"
  value       = "aws ssm start-session --target ${aws_instance.monitoring.id} --document-name AWS-StartPortForwardingSession --parameters '{\"portNumber\":[\"3001\"],\"localPortNumber\":[\"3001\"]}' --region ${var.region}"
}

output "prometheus_tunnel_command" {
  description = "Run on your laptop, then open http://localhost:9091"
  value       = "aws ssm start-session --target ${aws_instance.monitoring.id} --document-name AWS-StartPortForwardingSession --parameters '{\"portNumber\":[\"9091\"],\"localPortNumber\":[\"9091\"]}' --region ${var.region}"
}

output "monitoring_sync_command" {
  description = "After changing monitoring-config/ and applying, run this to reload the stack."
  value       = "aws ssm send-command --document-name AWS-RunShellScript --instance-ids ${aws_instance.monitoring.id} --parameters 'commands=[\"/usr/local/bin/monitoring-sync\"]' --region ${var.region}"
}
