# Terraform apply/destroy runbook

This infrastructure exists to prove the code works and to screenshot it, not to run continuously. Applied once, verified, destroyed the same day.

## Before you start

- AWS credentials with permission to create VPC/EKS/RDS resources.
- Rough cost while running (check AWS's current pricing before relying on this -- these are ballpark, not quoted): EKS control plane (~$0.10/hr) + 2x t3.medium nodes + one NAT gateway (~$0.045/hr plus data processing) + a db.t4g.micro RDS instance. Call it $0.30-0.40/hr all in, roughly $7-10 if left running a full day. Not something to leave up overnight by accident.
- Set the DB password without committing it:
  ```bash
  export TF_VAR_db_password="something-not-in-git-history"
  ```

## Apply

```bash
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

EKS control plane + managed node group takes roughly 15-20 minutes to become ready. `terraform apply` doesn't return until it does.

## Verify

```bash
aws eks update-kubeconfig --name "$(terraform output -raw cluster_name)"
kubectl get nodes
kubectl get pods -A
```

What to capture before tearing it down:

- `kubectl get nodes` showing the node group `Ready`
- AWS Console: EKS cluster status `Active`, RDS instance status `Available`
- Optionally, deploy the app itself (`helm install ...`, see the main README) and capture it actually serving a request through the cluster -- that's the real proof, not just the infrastructure existing

*(Add screenshots here after running the steps above -- not included in this repo since producing them requires actually applying this against a real AWS account.)*

## Destroy

```bash
terraform destroy
```

Confirm in the AWS Console that the EKS cluster, node group, NAT gateway, and RDS instance are actually gone, not just that `terraform destroy` exited 0 -- a stuck ENI or a security group another resource still references can occasionally block part of a clean teardown, and the CLI won't always surface that clearly.

## Why apply-then-destroy, not a standing environment

The Terraform code is the artifact this project is demonstrating, not a 24/7 cluster. A screenshot proves it works once; leaving it running past that just racks up cost for infrastructure nothing is using.
