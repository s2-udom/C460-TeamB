output "vpc_id" {
  description = "VPC ID."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnets (app host)."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnets (database)."
  value       = aws_subnet.private[*].id
}

output "app_security_group_id" {
  description = "Security group of the EC2 app host (the only one allowed to reach the database)."
  value       = aws_security_group.app.id
}

output "db_host" {
  description = "Database hostname (no port). Only reachable from inside the VPC."
  value       = aws_db_instance.main.address
}

output "db_port" {
  description = "Database port."
  value       = aws_db_instance.main.port
}

output "db_name" {
  description = "Database name."
  value       = aws_db_instance.main.db_name
}

output "db_username" {
  description = "Master username."
  value       = aws_db_instance.main.username
}

output "db_secret_arn" {
  description = "Secrets Manager secret holding the generated master password (JSON with username and password)."
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}

output "app_instance_id" {
  description = "EC2 instance ID of the app host."
  value       = aws_instance.app.id
}

output "app_public_ip" {
  description = "Fixed public IP of the app host."
  value       = aws_eip.app.public_ip
}

output "app_url" {
  description = "Where the app will be reachable once a container listens on port 80."
  value       = "http://${aws_eip.app.public_ip}"
}

output "ecr_repository_url" {
  description = "Image repository. Jenkins pushes here, the app host pulls from here."
  value       = aws_ecr_repository.app.repository_url
}

output "ssm_session_command" {
  description = "Open a shell on the app host (needs the Session Manager plugin). The EC2 console's Connect > Session Manager tab works without it."
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.app.id}"
}

output "db_tunnel_command" {
  description = "Run on your laptop, then point any Postgres client at localhost:15432. Tunnels through the app host to RDS."
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.app.id} --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host=${aws_db_instance.main.address},portNumber=${aws_db_instance.main.port},localPortNumber=15432"
}
