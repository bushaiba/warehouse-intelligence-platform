# AWS deployment

This folder is the optional cloud deployment for the same application that runs locally.

It creates:

- VPC across two availability zones
- public subnets for the ALB and Fargate tasks
- isolated database subnets for RDS
- S3 raw/curated object storage
- ECR repository
- ECS Fargate API service
- separate ECS pipeline task
- Application Load Balancer
- RDS PostgreSQL
- Secrets Manager database URL
- CloudWatch logs
- EventBridge Scheduler
- IAM roles with scoped S3 access

## Cost warning

This is real AWS infrastructure. **RDS, ALB and Fargate are billable resources.** The defaults deliberately keep `api_desired_count = 0` and `schedule_enabled = false`, but simply creating the RDS instance and ALB can still cost money.

The repository does not need AWS to demonstrate the working pipeline.

## Deployment flow

### 1. Initialise Terraform

```bash
cd infrastructure/aws
terraform init
terraform plan
```

### 2. Create the infrastructure with the API scaled to zero

```bash
terraform apply -var='api_desired_count=0' -var='schedule_enabled=false'
```

### 3. Build and push the Docker image

Get the ECR URL:

```bash
terraform output -raw ecr_repository_url
```

Authenticate Docker to ECR, then from the repository root:

```bash
docker build -t warehouse-intelligence .
docker tag warehouse-intelligence:latest <ECR_URL>:latest
docker push <ECR_URL>:latest
```

### 4. Start the API

```bash
terraform apply -var='api_desired_count=1'
```

### 5. Optional scheduled pipeline

Only enable this if you intentionally want the Fargate task to run on the configured schedule:

```bash
terraform apply \\
  -var='api_desired_count=1' \\
  -var='schedule_enabled=true' \\
  -var='schedule_expression=rate(1 day)'
```

## Destroy it when finished

```bash
terraform destroy
```

Do not leave a portfolio environment running just because it exists. If the goal is GitHub evidence, the local implementation is enough.
