# Deploying the LLMOps RAG Application to AWS

This guide shows how to deploy the FastAPI RAG application to AWS using **Docker, Amazon ECR, Amazon ECS on AWS Fargate, CloudFormation, Secrets Manager, IAM, VPC networking, and CloudWatch Logs**.

> **Deployment model:** ECS Fargate, not EC2. AWS manages the servers, and you provide a Docker container.
>
> **Values used in this guide:** region `eu-north-1`, ECR repository `llmopsrepolive`, ECS cluster `llmops-live-cluster`, ECS service `llmops-service`, task family `llmops-task`, container port `8080`. Replace `YOUR_ACCOUNT_ID` with your 12 digit AWS account ID.

## Table of contents

- [1. Architecture overview](#1-architecture-overview)
- [2. Project files](#2-project-files)
- [3. Application configuration](#3-application-configuration)
- [4. Build and test Docker locally](#4-build-and-test-docker-locally)
- [5. AWS prerequisites](#5-aws-prerequisites)
- [6. Step 1: Create the infrastructure](#6-step-1-create-the-infrastructure)
- [7. Step 2: Store the API keys in Secrets Manager](#7-step-2-store-the-api-keys-in-secrets-manager)
- [8. Step 3: Build and push the image to ECR](#8-step-3-build-and-push-the-image-to-ecr)
- [9. Step 4: Register the ECS task definition](#9-step-4-register-the-ecs-task-definition)
- [10. Step 5: Update the ECS service](#10-step-5-update-the-ecs-service)
- [11. Step 6: Find the public IP](#11-step-6-find-the-public-ip)
- [12. Step 7: Open and test the application](#12-step-7-open-and-test-the-application)
- [13. Step 8: Check the logs](#13-step-8-check-the-logs)
- [14. Troubleshooting](#14-troubleshooting)
- [15. Release checklist](#15-release-checklist)
- [16. Security and production notes](#16-security-and-production-notes)
- [17. Useful AWS Console links](#17-useful-aws-console-links)


## 1. Architecture overview

Deployment flow:

1. Build the application Docker image.
2. Push the image to Amazon ECR.
3. Register an ECS task definition that says which image to run, with what CPU, memory, port, variables, and secrets.
4. ECS starts the task on Fargate in a public subnet, and the task gets a public IP.
5. A security group allows inbound TCP traffic on port `8080` from your IP.
6. You open the API at `http://PUBLIC_IP:8080` and Swagger UI at `http://PUBLIC_IP:8080/docs`.

| AWS service                          | Role                                              |
| ------------------------------------ | ------------------------------------------------- |
| CloudFormation                       | Creates the infrastructure from `infra/cloudformation.yml` |
| ECR                                  | Stores Docker images                              |
| ECS                                  | Schedules and manages the container               |
| Fargate                              | Runs the container without EC2 servers to manage  |
| IAM                                  | Controls deployment and task permissions          |
| Secrets Manager                      | Stores API keys                                   |
| VPC, subnet, internet gateway, route table | Provide networking                          |
| Security Group                       | Controls inbound access to port `8080`            |
| CloudWatch Logs                      | Stores container logs                             |

## 2. Project files

| File                         | Purpose                                                  |
| ---------------------------- | -------------------------------------------------------- |
| `Dockerfile`                 | How to build the application image                       |
| `.dockerignore`              | Files left out of the Docker build                       |
| `.env`                       | Local settings and keys. **Never commit it**             |
| `.env.example`               | Variable names with placeholder values. Safe to commit   |
| `requirements.txt`           | Python dependencies                                      |
| `infra/cloudformation.yml`   | AWS infrastructure as code                               |
| `infra/task-definition.json` | ECS container and task settings                          |

The YAML and JSON files in the repository are the source of truth. This guide explains the workflow.

## 3. Application configuration

| Part         | Setting                                                                 |
| ------------ | ----------------------------------------------------------------------- |
| LLM          | Groq, `openai/gpt-oss-20b`                                              |
| Embeddings   | Hugging Face, `sentence-transformers/all-MiniLM-L6-v2` (no API key needed) |
| Vector store | FAISS                                                                   |
| Retriever    | MMR with `top_k: 10`, `fetch_k: 20`, `lambda_mult: 0.5`                 |
| API          | FastAPI on port `8080`                                                  |

The Google model integrations were removed from `model_loader.py` and `config.yaml`. Keep `.env.example`, `config.yaml`, and the code consistent whenever you change a model.

**Secret rules**

- Real keys belong only in your local `.env`, which is never committed.
- Commit `.env.example` with placeholders only.
- Never put key values in the Dockerfile, the task definition, the source code, or GitHub.
- In AWS, keep the Groq and LangSmith keys in Secrets Manager and reference them from the task definition.

## 4. Build and test Docker locally

The Dockerfile uses Python 3.11 slim, installs the dependencies, copies the app into `/app`, and starts Uvicorn on port `8080`:

```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

Build and run the image (Command Prompt):

```bat
docker build -t llmopsrepolive:latest .
docker run -d -p 8080:8080 --name llmops-test llmopsrepolive:latest
```

Open `http://localhost:8080/docs`. If Swagger UI loads, the container is serving FastAPI. Then clean up:

```bat
docker stop llmops-test
docker rm llmops-test
```

## 5. AWS prerequisites

Install Docker Desktop and the AWS CLI, then confirm which AWS identity you are using:

```bat
aws sts get-caller-identity
aws configure get region
```

| Setting           | Value                                     |
| ----------------- | ----------------------------------------- |
| AWS account       | `YOUR_ACCOUNT_ID`                         |
| Region            | `eu-north-1`                              |
| IAM CLI user      | `llmops-user`                             |
| GitHub repository | `i-am-tushaar/End-to-End-LLMOPs-Project`  |

The deployment identity needs permission for CloudFormation, ECR login and push, ECS task definition and service updates, EC2 network interface descriptions, Secrets Manager descriptions, and a narrowly scoped `iam:PassRole` for the ECS task execution role.

**Use least privilege.** Do not fix an access denied error by attaching `AdministratorAccess` permanently. Find the denied action and grant only that permission on the narrowest resource.

## 6. Step 1: Create the infrastructure

The CloudFormation template `infra/cloudformation.yml` creates:

- A VPC (`10.0.0.0/16`), a public subnet (`10.0.1.0/24`), an internet gateway, and a public route
- A security group that allows inbound TCP `8080` from `AllowedCidr`
- The ECR repository `llmopsrepolive`
- The ECS cluster `llmops-live-cluster`
- The CloudWatch log group `/ecs/llmopstdlive`
- The ECS task execution role, which can pull ECR images, write logs, and read secrets under `llmops/*`
- The GitHub OIDC provider and the GitHub Actions deployment role

**Set the allowed IP.** Find your public IP and add `/32`, which means one single address:

```bat
curl https://checkip.amazonaws.com
```

If your IP changes later, update the `AllowedCidr` parameter.

**Deploy the stack** from the project root. Replace `YOUR_PUBLIC_IP/32` with your real address:

```bat
aws cloudformation deploy --template-file infra/cloudformation.yml --stack-name llmops-infrastructure --capabilities CAPABILITY_NAMED_IAM --parameter-overrides GitHubOwner=i-am-tushaar GitHubRepo=End-to-End-LLMOPs-Project AllowedCidr=YOUR_PUBLIC_IP/32 --region eu-north-1
```

| Argument                              | Meaning                                              |
| ------------------------------------- | ---------------------------------------------------- |
| `--template-file`                     | The CloudFormation template                          |
| `--stack-name`                        | The name of the stack                                |
| `--capabilities CAPABILITY_NAMED_IAM` | Confirms the template creates named IAM resources    |
| `GitHubOwner`, `GitHubRepo`           | The repository the OIDC deployment role trusts       |
| `AllowedCidr`                         | The IP range allowed to reach port `8080`            |

**Read the outputs:**

```bat
aws cloudformation describe-stacks --stack-name llmops-infrastructure --region eu-north-1 --query "Stacks[0].Outputs" --output table
```

The outputs list the ECS cluster, ECR URI, log group, public subnet, security group, task execution role, and GitHub Actions role. Subnet and security group IDs and role name endings are generated, so always copy them from your own outputs.

## 7. Step 2: Store the API keys in Secrets Manager

Create these secrets in `eu-north-1`:

| Secret name                | Secret value        |
| -------------------------- | ------------------- |
| `llmops/GROQ_API_KEY`      | Your Groq API key   |
| `llmops/LANGCHAIN_API_KEY` | Your LangSmith key  |

Store each key as plain text, not as a JSON object, because the task definition maps each secret to one variable. The names must start with `llmops/`, because the execution role can only read that path.

**Rotating a key.** ECS reads a secret only when a task starts, so a running container keeps the old value. After you update a secret, force a new deployment:

```bat
aws ecs update-service --cluster llmops-live-cluster --service llmops-service --force-new-deployment --region eu-north-1 --no-cli-pager
```

## 8. Step 3: Build and push the image to ECR

Set a few variables for this Command Prompt session. They keep the commands short:

```bat
set ACCOUNT_ID=YOUR_ACCOUNT_ID
set ECR_URI=%ACCOUNT_ID%.dkr.ecr.eu-north-1.amazonaws.com/llmopsrepolive
set TAG=v2
```

Log in to ECR, then build, tag, and push:

```bat
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin %ACCOUNT_ID%.dkr.ecr.eu-north-1.amazonaws.com
docker build -t llmopsrepolive:%TAG% .
docker tag llmopsrepolive:%TAG% %ECR_URI%:%TAG%
docker push %ECR_URI%:%TAG%
```

Check the images in the repository:

```bat
aws ecr describe-images --repository-name llmopsrepolive --region eu-north-1 --query "imageDetails[*].[imageTags,imageDigest]" --output table
```

The repository uses immutable tags, so use a new unique tag for every release and never reuse one, including `latest`.

## 9. Step 4: Register the ECS task definition

`infra/task-definition.json` is the recipe ECS follows to run your container. It does not create the VPC or the ECR repository.

| Setting               | Value                                              |
| --------------------- | -------------------------------------------------- |
| Family                | `llmops-task`                                      |
| Compatibility         | `FARGATE`                                          |
| Network mode          | `awsvpc`                                           |
| CPU                   | `1024` (1 vCPU)                                    |
| Memory                | `4096` MiB (4 GB)                                  |
| Container             | `llmops-container`                                 |
| Container and host port | `8080`                                           |
| Image                 | The ECR image with a version tag                   |
| Log group             | `/ecs/llmopstdlive`, stream prefix `ecs`           |
| Execution role        | The task execution role created by CloudFormation  |

**Environment variables** mirror `.env.example` with production values, for example `APP_ENV=production`, `DEBUG=False`, `LLM_PROVIDER=groq`, `EMBEDDING_PROVIDER=huggingface`, `VECTOR_STORE=faiss`, `HOST=0.0.0.0`, and `PORT=8080`.

**Secrets** map Secrets Manager ARNs to variable names inside the container. Use the full ARNs from your account and never put key values in this file:

```json
"secrets": [
  {
    "name": "GROQ_API_KEY",
    "valueFrom": "FULL_GROQ_SECRET_ARN"
  },
  {
    "name": "LANGCHAIN_API_KEY",
    "valueFrom": "FULL_LANGCHAIN_SECRET_ARN"
  }
]
```

**For each release,** set the `image` field to the new tag:

```json
"image": "YOUR_ACCOUNT_ID.dkr.ecr.eu-north-1.amazonaws.com/llmopsrepolive:v2"
```

Validate the JSON and register a new revision:

```bat
python -m json.tool infra/task-definition.json
aws ecs register-task-definition --cli-input-json file://infra/task-definition.json --region eu-north-1
```

Each registration creates the next revision, such as `llmops-task:3`. Note the revision number in the output. If the CLI shows `-- More --`, press `Q` to exit.

## 10. Step 5: Update the ECS service

The service keeps the wanted number of tasks running. Create it once, then update it for each release.

| Setting       | Value                 |
| ------------- | --------------------- |
| Cluster       | `llmops-live-cluster` |
| Service       | `llmops-service`      |
| Desired count | `1`                   |
| Launch type   | `FARGATE`             |
| Public IP     | `ENABLED`             |
| Load balancer | None                  |

Point the service at the new revision (replace `REVISION` with the number from Step 4):

```bat
aws ecs update-service --cluster llmops-live-cluster --service llmops-service --task-definition llmops-task:REVISION --region eu-north-1 --no-cli-pager
```

Wait until the service is stable:

```bat
aws ecs wait services-stable --cluster llmops-live-cluster --services llmops-service --region eu-north-1
```

Check the result:

```bat
aws ecs describe-services --cluster llmops-live-cluster --services llmops-service --region eu-north-1 --query "services[0].deployments[*].[taskDefinition,status,runningCount,desiredCount,rolloutState]" --output table
```

A good result shows one running task, one desired task, and rollout state `COMPLETED`. If it stays `IN_PROGRESS`, see section 14. Do not stop the old healthy task by hand while a new one is still starting.

## 11. Step 6: Find the public IP

A Fargate task can get a new public IP whenever ECS replaces it, so look up the current IP after every deployment or restart.

1. Get the running task:

   ```bat
   aws ecs list-tasks --cluster llmops-live-cluster --service-name llmops-service --desired-status RUNNING --region eu-north-1 --query "taskArns[0]" --output text
   ```

2. Get its network interface ID (replace `TASK_ARN`):

   ```bat
   aws ecs describe-tasks --cluster llmops-live-cluster --tasks TASK_ARN --region eu-north-1 --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text
   ```

3. Get the public IP (replace `ENI_ID`):

   ```bat
   aws ec2 describe-network-interfaces --network-interface-ids ENI_ID --region eu-north-1 --query "NetworkInterfaces[0].Association.PublicIp" --output text
   ```

## 12. Step 7: Open and test the application

Open these addresses with the IP from step 6:

```text
http://PUBLIC_IP:8080
http://PUBLIC_IP:8080/docs
```

Then test the whole flow:

1. Open `/docs` and confirm that Swagger UI loads.
2. Use the upload endpoint to index a document.
3. Confirm that the app reports the document as indexed.
4. Ask a question whose answer is in that document.
5. If the answer fails, check the CloudWatch logs and the Groq secret.

Indexing alone does not prove the Groq key is valid, so always test both indexing and question answering.

## 13. Step 8: Check the logs

Open the AWS Console and go to **CloudWatch → Logs → Log groups → `/ecs/llmopstdlive`**. Use the logs to diagnose startup errors, missing variables, secret problems, model loading, document ingestion, retrieval, and Groq errors. Never log secret values.

## 14. Troubleshooting

### Docker push: TLS handshake timeout

Retry the same `docker push`. Docker reuses the layers that were already uploaded. A TLS timeout by itself is not an IAM permission problem.

### ECS deployment stays IN_PROGRESS

Read the service events and the task status:

```bat
aws ecs describe-services --cluster llmops-live-cluster --services llmops-service --region eu-north-1 --query "services[0].events[:10].[createdAt,message]" --output table
aws ecs describe-tasks --cluster llmops-live-cluster --tasks TASK_ARN --region eu-north-1 --query "tasks[0].[lastStatus,healthStatus,taskDefinitionArn,stopReason]" --output table
```

`healthStatus: UNKNOWN` is normal when no container health check is set. Judge the task by its status, the rollout state, the logs, and the HTTP endpoint.

### Groq returns 401 Invalid API Key

If indexing works but questions fail with `401 Invalid API Key`, the secret holds a wrong or old key, for example after the key was regenerated. Update `llmops/GROQ_API_KEY` with the current key, then force a new deployment so the new task receives it:

```bat
aws ecs update-service --cluster llmops-live-cluster --service llmops-service --force-new-deployment --region eu-north-1 --no-cli-pager
```

Wait for the service to stabilize, find the new public IP (step 6), and test again.

### The task cannot start or cannot read a secret

Check that the secret names start with `llmops/`, that the secrets are in `eu-north-1`, and that the full ARNs in the task definition are correct. Then read the service events and the logs.

### The public IP no longer works

A replacement task may have a new IP, so look it up again (step 6). Also check these:

- The task status is `RUNNING`.
- The security group allows TCP `8080` from your current public IP. If your IP changed, update `AllowedCidr`.
- The app listens on `0.0.0.0:8080`.
- The subnet has a route to the internet gateway.

Keep access limited to your IP. Do not open port `8080` to the whole internet without thinking through the risks.

### Hugging Face warnings

The first start downloads `sentence-transformers/all-MiniLM-L6-v2`. A warning about unauthenticated requests and 404 messages for optional metadata files are harmless if the model loads.

## 15. Release checklist

Use this for each new release after the infrastructure, service, and secrets exist:

1. Build, tag, and push the image with a new tag:

   ```bat
   set TAG=v3
   aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin %ACCOUNT_ID%.dkr.ecr.eu-north-1.amazonaws.com
   docker build -t llmopsrepolive:%TAG% .
   docker tag llmopsrepolive:%TAG% %ECR_URI%:%TAG%
   docker push %ECR_URI%:%TAG%
   ```

2. Change the `image` field in `infra/task-definition.json` to the new tag.
3. Validate the JSON and register a new revision (step 4).
4. Update the service with the revision number that AWS returns (step 5).
5. Wait for the service to be stable (step 5).
6. Find the new public IP (step 6).
7. Open `/docs`, upload a document, and ask a question (step 7).

## 16. Security and production notes

This setup exposes FastAPI directly on the task's public IP, with no load balancer and no domain name. That is fine for a controlled demo. For production, consider:

- An Application Load Balancer with HTTPS and a domain name
- Authentication for the API endpoints
- A stable endpoint, because task public IPs change
- Container health checks
- Monitoring, alarms, and log retention (the stack keeps logs for 14 days)
- Image scanning and dependency updates

A desired count of one keeps one task running all the time, which costs money. Scale the service down or delete the resources when you no longer need them, and check Fargate, ECR storage, CloudWatch Logs, and data transfer costs.

## 17. Useful AWS Console links

- [CloudFormation stacks](https://eu-north-1.console.aws.amazon.com/cloudformation/home?region=eu-north-1#/stacks)
- [ECR repositories](https://eu-north-1.console.aws.amazon.com/ecr/repositories?region=eu-north-1)
- [ECS clusters](https://eu-north-1.console.aws.amazon.com/ecs/v2/clusters?region=eu-north-1)
- [Secrets Manager](https://eu-north-1.console.aws.amazon.com/secretsmanager/listsecrets?region=eu-north-1)
- [CloudWatch log groups](https://eu-north-1.console.aws.amazon.com/cloudwatch/home?region=eu-north-1#logsV2:log-groups)
