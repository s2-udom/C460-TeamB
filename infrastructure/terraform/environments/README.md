# AWS environment settings

Local development uses Docker Compose and `ENVIRONMENT=local` in `.env`.
AWS deployments use Terraform with one of the environment files in this
directory.

Each AWS environment must use its own Terraform state key. For example:

```text
staging/terraform.tfstate
production/terraform.tfstate
```

Apply staging with:

```bash
terraform init -backend-config=backend.hcl
terraform plan -var-file=environments/staging.tfvars.example
terraform apply -var-file=environments/staging.tfvars.example
```

Before applying production, replace the example trusted CIDR in the production
file and use a production backend state key. Never reuse the staging state file.
