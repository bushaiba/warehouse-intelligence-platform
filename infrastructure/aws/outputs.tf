output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "api_url" {
  value = "http://${aws_lb.api.dns_name}"
}

output "s3_bucket" {
  value = aws_s3_bucket.data.bucket
}

output "database_endpoint" {
  value     = aws_db_instance.postgres.address
  sensitive = true
}
