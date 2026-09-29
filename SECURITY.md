# Security and data handling

This repository intentionally contains synthetic data only.

It must not contain:

- company-confidential source code
- internal hostnames or APIs
- employee names, logins or IDs
- production credentials or cookies
- warehouse routing configuration
- customer or inventory data copied from a workplace system

Secrets are supplied through environment variables or AWS Secrets Manager. `.env` is ignored by Git.
