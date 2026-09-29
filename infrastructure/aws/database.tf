resource "random_password" "db" {
  length  = 24
  special = false
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db"
  subnet_ids = aws_subnet.private_db[*].id
}

resource "aws_db_instance" "postgres" {
  identifier                  = var.project_name
  engine                      = "postgres"
  engine_version              = "16"
  instance_class              = var.db_instance_class
  allocated_storage           = var.db_allocated_storage
  max_allocated_storage       = 100
  storage_type                = "gp3"
  storage_encrypted           = true
  db_name                     = "warehouse"
  username                    = "warehouse_app"
  password                    = random_password.db.result
  port                        = 5432
  db_subnet_group_name        = aws_db_subnet_group.main.name
  vpc_security_group_ids      = [aws_security_group.db.id]
  publicly_accessible         = false
  multi_az                    = false
  backup_retention_period     = 1
  auto_minor_version_upgrade  = true
  deletion_protection         = false
  skip_final_snapshot         = true
  apply_immediately           = true
  performance_insights_enabled = false
}

resource "aws_secretsmanager_secret" "database_url" {
  name = "${var.project_name}/database-url-${random_id.suffix.hex}"
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = format(
    "postgresql+psycopg://warehouse_app:%s@%s:5432/warehouse",
    random_password.db.result,
    aws_db_instance.postgres.address,
  )
}
