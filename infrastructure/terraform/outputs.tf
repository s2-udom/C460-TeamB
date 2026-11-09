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
  description = "Attach this to the EC2 app host so it can reach the database."
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
