# AWS Deployment Documentation
## End-to-End LLMOps RAG Application

> **Deployment record: 17 November 2026.** GitHub Actions CI passed (166 tests). The CD workflow successfully built and pushed the Docker image to Amazon ECR, and the ECS service deployment completed with `rolloutState=COMPLETED`. The FastAPI Swagger page was reachable through the task's public IP, and document upload/indexing worked. Chat question answering still returned Groq `401 Invalid API Key`; application-level LLM authentication remained unresolved at the time of writing.

## 1. Project and AWS details

| Item | Value |
|---|---|
| GitHub repository | `i-am-tushaar/End-to-End-LLMOPs-Project` |
| AWS account | `452975373208` |
| Region | `eu-north-1` (Europe/Stockholm) |
| CloudFormation stack | `llmops-infrastructure` |
| ECR repository | `llmopsrepolive` |
| ECR URI | `452975373208.dkr.ecr.eu-north-1.amazonaws.com/llmopsrepolive` |
| ECS cluster | `llmops-live-cluster` |
| ECS service | `llmops-service` |
| ECS task family | `llmops-task` |
| Container name | `llmops-container` |
| Container port | `8080` |
| CloudWatch log group | `/ecs/llmopstdlive` |
| Swagger URL | `http://PUBLIC_IP:8080/docs` |

Never publish credentials, API key values, AWS access keys, session tokens, or secret contents in this document or in GitHub.

## 2. Architecture and deployment flow

```text
Developer pushes to GitHub (main)
             |
             v
       GitHub Actions CI
       - install dependencies
       - run pytest
             |
       CI succeeds on main
             |
             v
       GitHub Actions CD
       - obtain GitHub OIDC token
       - assume AWS IAM deployment role
       - build Docker image
       - push image to ECR
       - register ECS task definition
       - update ECS service
             |
             v
       ECS cluster -> Fargate task in public subnet
                         |                 |
                         v                 v
                  CloudWatch Logs    Public IPv4 address
                                     http://PUBLIC_IP:8080/docs
```

| AWS service | Purpose |
|---|---|
| GitHub Actions | Automates tests, image build, and deployment |
| GitHub OIDC | Gives GitHub Actions temporary AWS credentials without storing long-lived AWS keys in GitHub |
| IAM | Controls deployment and task permissions |
| CloudFormation | Creates supporting AWS infrastructure from code |
| ECR | Stores Docker images |
| ECS | Manages the task and service |
| Fargate | Runs the container without managing EC2 instances |
| VPC, subnet, Internet Gateway, route table | Provide task networking and internet connectivity |
| Security Group | Controls inbound traffic to port 8080 |
| Secrets Manager | Stores Groq and LangSmith API keys |
| CloudWatch Logs | Stores container logs |

**Important:** CloudFormation creates the supporting infrastructure. The GitHub Actions CD workflow builds and pushes the image, registers the task definition, and updates the ECS service.

## 3. CloudFormation infrastructure

Template: `infra/cloudformation.yml`  
Stack: `llmops-infrastructure`

| Resource | Configuration / purpose |
|---|---|
| VPC | `10.0.0.0/16` |
| Public subnet | `10.0.1.0/24` |
| Internet Gateway and route | Internet connectivity for the public subnet |
| Security Group | Inbound TCP `8080` from configured `AllowedCidr` |
| ECR repository | `llmopsrepolive`; immutable image tags and scan on push |
| ECS cluster | `llmops-live-cluster` |
| CloudWatch log group | `/ecs/llmopstdlive`, 14-day retention |
| ECS task execution role | Pulls ECR images, writes logs, and reads secrets under `llmops/*` |
| GitHub OIDC provider | `token.actions.githubusercontent.com`, audience `sts.amazonaws.com` |
| GitHub Actions deployment role | Trusted by the configured GitHub repository/branch and used by CD |

### Recorded resource identifiers

| Resource | Recorded value |
|---|---|
| Task execution role ARN | `arn:aws:iam::452975373208:role/llmops-infrastructure-ECSTaskExecutionRole-QcYpbiOF9ptZ` |
| GitHub deployment role ARN | `arn:aws:iam::452975373208:role/llmops-infrastructure-GitHubActionsDeployRole-jaquCWQnU98D` |
| Public subnet ID | `subnet-01201cb393808dda4` |
| Security Group ID | `sg-08c4d19eae3cbfaa4` |
| Groq secret ARN | `arn:aws:secretsmanager:eu-north-1:452975373208:secret:llmops/GROQ_API_KEY-majbby` |
| LangSmith secret ARN | `arn:aws:secretsmanager:eu-north-1:452975373208:secret:llmops/LANGCHAIN_API_KEY-KPnnBJ` |

These are deployment-time identifiers. If infrastructure is recreated, retrieve the new outputs and ARNs rather than assuming generated IDs remain unchanged.

## 4. ECS task and application configuration

Task definition file: `infra/task-definition.json`

| Setting | Configuration |
|---|---|
| Family | `llmops-task` |
| Launch type | Fargate |
| Network mode | `awsvpc` |
| CPU | `1024` (1 vCPU) |
| Memory | `4096` MiB (4 GB) |
| Container | `llmops-container` |
| Container port | `8080` |
| ECS service | `llmops-service` |
| Demo desired count | `1` |
| Public IP assignment | Enabled |
| Log group | `/ecs/llmopstdlive` |

| Application component | Configuration |
|---|---|
| API | FastAPI with Uvicorn |
| LLM provider/model | Groq, `openai/gpt-oss-20b` |
| Embedding provider/model | Hugging Face, `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | FAISS |
| Port | `8080` |

The container starts the API with:

```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Secrets

| Container variable | Secrets Manager secret |
|---|---|
| `GROQ_API_KEY` | `llmops/GROQ_API_KEY` |
| `LANGCHAIN_API_KEY` | `llmops/LANGCHAIN_API_KEY` |

Store each key as a plain text value when the task definition maps the whole secret to one environment variable. Do not put key values in the task definition, Dockerfile, source code, or GitHub.

ECS injects secret values when a task starts. Updating a secret does not change the value inside an already-running container. After changing a secret, force a new deployment or start a new task.

## 5. GitHub Actions CI/CD

Workflow files:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`

### CI

CI runs on pushes and pull requests targeting `main`. It checks out the repository, sets up Python, installs dependencies with `uv`, and runs:

```bash
uv run pytest tests/ -v
```

Recorded result: **166 passed, 0 failed**. Deprecation warnings were present but did not fail the run.

### CD

The CD workflow runs after the `CI` workflow completes successfully on `main`. It:

1. Checks the CI conclusion, repository, and branch.
2. Checks out the commit that passed CI.
3. Requests a GitHub OIDC token for audience `sts.amazonaws.com`.
4. Assumes the AWS GitHub Actions deployment role.
5. Verifies the AWS identity.
6. Logs in to ECR.
7. Builds and tags the Docker image with the commit SHA.
8. Pushes the image to ECR.
9. Renders/registers the ECS task definition.
10. Updates `llmops-service` and waits for service stability.

### GitHub repository variable

| Name | Value |
|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::452975373208:role/llmops-infrastructure-GitHubActionsDeployRole-jaquCWQnU98D` |

The workflow reads it as `${{ vars.AWS_ROLE_ARN }}`. The role ARN belongs in GitHub **Variables**. Do not store long-lived AWS access keys in GitHub when OIDC is configured.

### OIDC trust-policy issue that was resolved

The original trust policy expected this subject:

```text
repo:i-am-tushaar/End-to-End-LLMOPs-Project:ref:refs/heads/main
```

The GitHub OIDC debugger showed the actual `sub` claim for this repository/workflow as:

```text
repo:i-am-tushaar@173897819/End-to-End-LLMOPs-Project@1305556805:ref:refs/heads/main
```

The IAM role trust policy was updated to match the actual subject, with audience `sts.amazonaws.com`. AWS role assumption then succeeded. If OIDC fails in the future, compare the non-secret claims (`iss`, `aud`, `sub`, `repository`, `ref`, and `event_name`) with the role trust policy. Never print or share the complete OIDC token.

### ECR push permission issue that was resolved

The first ECR push failed on a manifest operation with HTTP `403 Forbidden`. A repository-scoped policy named `LLMOpsECRPushPolicy` was created and attached to the GitHub Actions deployment role.

It grants `ecr:GetAuthorizationToken` on `*` and these actions on the `llmopsrepolive` repository: `ecr:BatchCheckLayerAvailability`, `ecr:InitiateLayerUpload`, `ecr:UploadLayerPart`, `ecr:CompleteLayerUpload`, `ecr:PutImage`, `ecr:BatchGetImage`, `ecr:DescribeImages`, `ecr:DescribeRepositories`, and `ecr:ListImages`.

Repository ARN:

```text
arn:aws:ecr:eu-north-1:452975373208:repository/llmopsrepolive
```

After attaching the policy, image push and ECS rollout succeeded.

## 6. Deploy a code change

For normal releases, push changes to `main`:

```bash
git add .
git commit -m "Describe the change"
git push origin main
```

Then open GitHub → Actions and confirm:

1. CI completes successfully.
2. CD starts after CI.
3. Docker build and ECR push succeed.
4. ECS reports `rolloutState=COMPLETED`.
5. The ECS service has a running task.
6. `/docs`, document indexing, and question answering are tested.

The ECR repository uses immutable tags. The workflow uses the commit SHA as the image tag. Use a unique tag for each release; do not reuse an existing immutable tag.

## 7. Find the current public IP and test

A Fargate task can receive a new public IP when ECS replaces or restarts it. Retrieve the current IP after each deployment.

Console steps:

1. ECS → Clusters → `llmops-live-cluster`.
2. Open service `llmops-service`.
3. Open **Tasks** and select the running task.
4. Find its network interface (ENI).
5. Open the ENI in EC2 and locate **Public IPv4 address**.

Test:

```text
http://PUBLIC_IP:8080/docs
```

Swagger loading proves that the API is reachable. It does not prove that the LLM provider key works. For a complete test, upload a document, confirm indexing, then ask a question whose answer is in that document.

## 8. Logs and troubleshooting

CloudWatch location:

```text
CloudWatch → Logs → Log groups → /ecs/llmopstdlive
```

Use the latest task log stream to inspect startup, model initialization, secret-related errors, ingestion, retrieval, and LLM provider errors. Never log secret values.

### Known issue: Groq 401 Invalid API Key

Observed error:

```text
groq.AuthenticationError: Error code: 401
{'error': {'message': 'Invalid API Key',
           'type': 'invalid_request_error',
           'code': 'invalid_api_key'}}
```

Observed behavior: the app loads, document upload/indexing succeeds, but asking a question fails when the application calls Groq. This is a Groq authentication failure, not an ECS deployment failure.

When resuming troubleshooting:

1. Generate or confirm a valid key in the Groq Console.
2. Update `llmops/GROQ_API_KEY` in Secrets Manager in `eu-north-1`.
3. Confirm it is stored as a plain text key if the task definition maps the whole secret.
4. Confirm `GROQ_API_KEY` in the active task definition points to the intended secret ARN.
5. Force a new ECS deployment so a new task receives the updated value.
6. Wait for rollout completion, find the new task's public IP, and test again.

Force a new deployment:

```bash
aws ecs update-service --cluster llmops-live-cluster --service llmops-service --force-new-deployment --region eu-north-1 --no-cli-pager
```

Do not paste the actual Groq key into GitHub, task-definition JSON, logs, screenshots, or chat.

### ECS deployment does not stabilize

Inspect ECS service events, stopped task reasons, and the CloudWatch log stream. Common causes include an incorrect image reference, missing task permissions, a secret ARN mismatch, container startup errors, or networking problems.

### Public IP stops working

Check that the task is `RUNNING`, retrieve its current public IP, and verify that the security group allows inbound TCP `8080` from the current client IP. If the client's public IP changed, update `AllowedCidr`.

## 9. Cost control and safe pause

A running Fargate task incurs compute charges. Other resources may also incur charges, including public IPv4 usage, ECR image storage, CloudWatch Logs ingestion/storage, Secrets Manager secrets, and data transfer. Check AWS Billing and Cost Explorer for actual account charges; pricing varies by region and usage.

To stop the app while retaining the infrastructure:

1. ECS → `llmops-live-cluster` → `llmops-service`.
2. Update desired task count to `0`.
3. Wait until running task count is `0`.

This stops the Fargate task compute. It does not delete ECR, CloudWatch Logs, Secrets Manager secrets, VPC resources, or IAM roles. Billing data can be delayed, so review Billing and Cost Explorer after stopping resources.

## 10. Full cleanup procedure

Delete resources only after saving this documentation, screenshots, and any Docker image/configuration needed for future redeployment.

Before deletion:

- Save successful CI and CD run URLs/screenshots.
- Save the ECR image tag/digest if useful.
- Keep the CloudFormation template, task definition, and workflow files in Git.
- Record secret names and ARNs, never their values.
- Confirm that the online application is no longer needed.

Recommended order:

1. Set ECS service desired count to `0` and wait for tasks to stop.
2. Delete the ECS service.
3. Delete the ECS cluster if it has no remaining services/tasks.
4. Optionally deregister old task definition revisions.
5. Empty the ECR repository if you intend to delete it. Confirm images are no longer needed first.
6. Delete the CloudFormation stack `llmops-infrastructure`.
7. Check for manually created resources not managed by the stack, especially Secrets Manager secrets and separately created ECS resources.
8. Review IAM for temporary broad permissions. Remove `AdministratorAccess` from the CLI user if it was attached during troubleshooting and is no longer required.
9. Review AWS Billing and Cost Explorer and inspect the region for leftovers.

Delete the stack only after the preceding checks:

```bash
aws cloudformation delete-stack --stack-name llmops-infrastructure --region eu-north-1
```

Check deletion status:

```bash
aws cloudformation describe-stacks --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager
```

If deletion fails because ECR is not empty, remove images only after confirming they are no longer needed, then retry. Check CloudFormation stack events for `DELETE_FAILED` and its reason. Secrets Manager secrets may have been created manually and may not be part of the stack, so review them separately.

## 11. Security checklist

- [ ] Never commit `.env` or real API keys.
- [ ] Keep `.env.example` limited to variable names and placeholders.
- [ ] Use GitHub OIDC instead of long-lived AWS keys in GitHub.
- [ ] Scope IAM permissions to required actions and resources.
- [ ] Do not leave `AdministratorAccess` attached as a permanent workaround.
- [ ] Restrict port `8080` ingress to the required IP range for a personal demo.
- [ ] Rotate credentials that may have been exposed.
- [ ] Never print secrets or complete OIDC tokens in workflow logs.
- [ ] Review AWS billing and stop/delete resources when not in use.

## 12. Evidence to keep for portfolio/interviews

Capture screenshots of:

1. GitHub Actions CI showing 166 tests passed.
2. GitHub Actions CD showing successful ECR push and ECS rollout completed.
3. ECR repository showing the commit-SHA image tag.
4. ECS cluster/service showing the Fargate task or completed deployment.
5. CloudFormation stack showing `CREATE_COMPLETE` and its resources.
6. FastAPI Swagger UI at `/docs`.
7. Successful document upload/indexing.
8. CloudWatch logs showing application startup.

When presenting the project, distinguish deployment success from inference success: AWS deployment and API reachability were verified, document indexing worked, but the Groq 401 issue remained unresolved at the time this record was written.

## 13. Useful AWS Console pages

- [CloudFormation stacks](https://eu-north-1.console.aws.amazon.com/cloudformation/home?region=eu-north-1#/stacks)
- [ECR repositories](https://eu-north-1.console.aws.amazon.com/ecr/repositories?region=eu-north-1)
- [ECS clusters](https://eu-north-1.console.aws.amazon.com/ecs/v2/clusters?region=eu-north-1)
- [Secrets Manager](https://eu-north-1.console.aws.amazon.com/secretsmanager/listsecrets?region=eu-north-1)
- [CloudWatch log groups](https://eu-north-1.console.aws.amazon.com/cloudwatch/home?region=eu-north-1#logsV2:log-groups)

## 14. Suggested README section

Add this to the root `README.md` (adjust links if your filenames differ):

```markdown
## AWS Deployment

The application is deployed as a Docker container on Amazon ECS with AWS Fargate.
GitHub Actions runs CI tests and uses GitHub OIDC to authenticate to AWS, push
images to Amazon ECR, and update the ECS service.

- [AWS Deployment Documentation](infra/AWS_DEPLOYMENT_DOCUMENTATION.md)
- [AWS Infrastructure Guide](infra/AWS_INFRASTRUCTURE_GUIDE.md)
- [AWS Deployment Runbook](infra/AWS_DEPLOYMENT_GUIDE_LLMOPS.md)

Region: `eu-north-1` | ECS cluster: `llmops-live-cluster` |
ECS service: `llmops-service` | ECR repository: `llmopsrepolive` |
Application port: `8080`
```

This file is the consolidated deployment record. Keep the existing infrastructure guide and step-by-step deployment guide as deeper references.
