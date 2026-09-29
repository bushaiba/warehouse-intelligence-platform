# Architecture notes

## Design goal

Keep the project small enough to understand in an interview, but include the reliability controls that matter in a real data pipeline.

## Local path

```text
Generator -> NDJSON -> Local/MinIO raw -> validation -> Parquet -> Postgres -> FastAPI
```

## AWS path

```text
EventBridge Scheduler
        |
        v
ECS pipeline task ----------------------+
        |                               |
        v                               v
       S3                            RDS PostgreSQL
 raw + curated                         |
                                       v
                                ECS FastAPI service
                                       |
                                       v
                                      ALB
```

CloudWatch receives container logs. Secrets Manager stores database credentials. The services run in a VPC and the database is not publicly accessible.

## Failure behaviour

- invalid rows are rejected before warehouse load
- duplicate source batches are skipped by checksum
- duplicate event IDs are ignored
- object-store I/O retries are finite
- the run is only marked successful after quality checks pass
- current state is rebuilt from fact history to avoid silent drift
