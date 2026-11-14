# AWS Infrastructure Guide for the End-to-End LLMOps Project

> **Purpose:** This guide explains the AWS infrastructure defined in `infra/cloudformation.yml`: what each resource is for, how to deploy, check, and delete it, and what may cost money.

## Table of contents

- [AWS Infrastructure Guide for the End-to-End LLMOps Project](#aws-infrastructure-guide-for-the-end-to-end-llmops-project)
  - [Table of contents](#table-of-contents)
  - [1. Where this document belongs](#1-where-this-document-belongs)
  - [2. Deployment overview](#2-deployment-overview)
  - [3. What CloudFormation does](#3-what-cloudformation-does)
  - [4. Resources created by the template](#4-resources-created-by-the-template)
  - [5. What the template does not create](#5-what-the-template-does-not-create)
  - [6. The ECS task definition (`task-definition.json`)](#6-the-ecs-task-definition-task-definitionjson)
  - [7. Region and naming](#7-region-and-naming)
  - [8. Deploy the infrastructure](#8-deploy-the-infrastructure)
  - [9. Check the stack](#9-check-the-stack)
  - [10. Which resources cost money](#10-which-resources-cost-money)
  - [11. Delete the infrastructure](#11-delete-the-infrastructure)
  - [12. IAM and safe practice](#12-iam-and-safe-practice)
  - [13. Summary](#13-summary)

## 1. Where this document belongs

Save this file at `infra/AWS_INFRASTRUCTURE_GUIDE.md`, next to the template it documents. It explains **what exists and why**: the resources, the cost, and how to delete them. The step by step release process is in the [deployment guide](AWS_DEPLOYMENT_GUIDE_LLMOPS.md). Link to both from the main `README.md`:

```markdown
## AWS

- [AWS Infrastructure Guide](infra/AWS_INFRASTRUCTURE_GUIDE.md): CloudFormation
  resources, cost notes, and cleanup.
- [AWS Deployment Guide](infra/AWS_DEPLOYMENT_GUIDE_LLMOPS.md): build, push,
  and release the app step by step.
```

## 2. Deployment overview

Docker packages the application, Amazon ECR stores the image, and Amazon ECS with AWS Fargate runs it. The deployment flow is:

1. A developer pushes code to the GitHub repository.
2. GitHub Actions signs in to AWS with OpenID Connect (OIDC) and assumes an IAM deployment role.
3. The workflow builds the Docker image and pushes it to ECR.
4. The workflow registers the ECS task definition (`infra/task-definition.json`).
5. ECS runs the task on Fargate in the public subnet, and the task writes logs to CloudWatch Logs.
6. Users reach the application through the task's public IP on port 8080.

```text
GitHub repository -> GitHub Actions -> (OIDC) IAM deployment role
        -> Amazon ECR -> ECS task definition and service
        -> Fargate task in public subnet -> CloudWatch Logs
                                         -> Application on TCP 8080
```

The CloudFormation template creates only the **supporting infrastructure**. It does not build the image, register the task definition, create the ECS service, or start a Fargate task. The [deployment guide](AWS_DEPLOYMENT_GUIDE_LLMOPS.md) shows the same steps run by hand from the command line.

## 3. What CloudFormation does

CloudFormation is an Infrastructure as Code service. It reads `infra/cloudformation.yml` and creates the resources as one **stack**, named `llmops-infrastructure`. Because the resources belong to one stack, you can inspect, update, and delete them as a group.

| Parameter           | Default or example          | Purpose                                                 |
| ------------------- | --------------------------- | ------------------------------------------------------- |
| `GitHubOwner`       | `i-am-tushaar`              | GitHub account that owns the repository                 |
| `GitHubRepo`        | `End-to-End-LLMOPs-Project` | Repository allowed by the GitHub OIDC role trust policy |
| `ECRRepositoryName` | `llmopsrepolive`            | Name of the ECR image repository                        |
| `ECSClusterName`    | `llmops-live-cluster`       | Name of the ECS cluster                                 |
| `AllowedCidr`       | `0.0.0.0/0` in the template | IPv4 range allowed to reach TCP port 8080               |

**Security:** Do not leave `AllowedCidr` as `0.0.0.0/0` for an app that only you need. Pass your current public IPv4 address with `/32`, for example `203.0.113.10/32` (a documentation example, not a real address). If your home IP changes, update the rule.

## 4. Resources created by the template

| Resource                | CloudFormation type                        | What it is for                                                        | Where to check in the AWS Console                    |
| ----------------------- | ------------------------------------------ | --------------------------------------------------------------------- | ---------------------------------------------------- |
| VPC `llmops-vpc`        | `AWS::EC2::VPC`                            | A private, isolated network (`10.0.0.0/16`) for the Fargate task      | VPC → Your VPCs                                      |
| Public subnet           | `AWS::EC2::Subnet`                         | A smaller range (`10.0.1.0/24`) where the task runs, with auto public IPv4 | VPC → Subnets                                   |
| Internet Gateway        | `AWS::EC2::InternetGateway`                | Lets the VPC send and receive internet traffic                        | VPC → Internet Gateways                              |
| Route table and route   | `AWS::EC2::RouteTable`, `Route`, `SubnetRouteTableAssociation` | Sends internet bound traffic (`0.0.0.0/0`) to the Internet Gateway | VPC → Route Tables                       |
| Security Group          | `AWS::EC2::SecurityGroup`                  | A firewall that allows inbound TCP 8080 from `AllowedCidr`            | EC2 → Network & Security → Security Groups           |
| ECR repository `llmopsrepolive` | `AWS::ECR::Repository`             | Private storage for the Docker image                                  | ECR → Private registry → Repositories                |
| ECS cluster `llmops-live-cluster` | `AWS::ECS::Cluster`              | A group in which ECS tasks and services are managed                   | ECS → Clusters                                       |
| Log group `/ecs/llmopstdlive` | `AWS::Logs::LogGroup`                | Receives container logs, kept for 14 days                             | CloudWatch → Logs → Log groups                       |
| ECS task execution role | `AWS::IAM::Role`                           | Lets ECS pull the image from ECR, write logs, and read secrets        | IAM → Roles                                          |
| GitHub OIDC provider    | `AWS::IAM::OIDCProvider`                   | Lets AWS trust identity tokens from GitHub Actions                    | IAM → Identity providers                             |
| GitHub Actions role `GitHubActionsECSDeployRole` | `AWS::IAM::Role`  | The role the workflow assumes to deploy                               | IAM → Roles                                          |

**Details worth knowing**

- **ECR:** tags are `IMMUTABLE` (a tag cannot be overwritten), scan on push is on, and encryption is AES-256. A repository that still holds images may fail to delete with the stack, so check the template's force delete setting first.
- **Execution role:** it uses the AWS managed policy `AmazonECSTaskExecutionRolePolicy` plus an inline policy `ReadLLMOpsSecrets` that reads Secrets Manager values under `llmops/*`. It is not a task role. If your app code calls AWS APIs directly, add a separate task role with only the permissions it needs.
- **OIDC provider:** the provider URL is `https://token.actions.githubusercontent.com` and the audience is `sts.amazonaws.com`. It does not grant access by itself. The deployment role's trust policy decides who can assume it.
- **Deployment role trust:** it is limited to one repository and the `main` branch:

  ```text
  repo:i-am-tushaar/End-to-End-LLMOPs-Project:ref:refs/heads/main
  ```

  Do not replace this with a wildcard unless you have a reviewed reason.

## 5. What the template does not create

A cluster can exist while no application is running, and a repository can exist while it holds no image. These parts are separate:

| Not created by the template | What it does                                                      | When it is needed                                            |
| --------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------ |
| ECS task definition         | Describes the container image, CPU, memory, port, roles, secrets, and logging | Before ECS can run the app. It lives in `infra/task-definition.json`. See section 6 |
| ECS service                 | Keeps the wanted number of tasks running                          | To run the app as a service                                  |
| Fargate task                | The running container                                             | When a task or service starts                                |
| Public IP                   | Address a running task gets when public IP is enabled             | When the task launches                                       |
| Application Load Balancer   | A managed entry point to the tasks                                | Optional, and not used in this design                        |
| Secrets Manager secrets     | Stores the real Groq and LangSmith API key values                | Create separately as `llmops/GROQ_API_KEY` and `llmops/LANGCHAIN_API_KEY`. The names must start with `llmops/` so the execution role can read them |
| Docker image                | The packaged application                                          | Built locally or by CI, then pushed to ECR                   |

## 6. The ECS task definition (`task-definition.json`)

The task definition is the instruction sheet that tells ECS how to run your container: which image, how much CPU and memory, which port, which secrets, and where to send logs. Think of it as an order form, and the Fargate task is the meal that is made from it. The file is `infra/task-definition.json`. It is not part of the CloudFormation stack. Each time it is registered, ECS creates a new **revision**, and the service uses the revision you point it at.

The file itself is the source of truth, so this guide does not copy it. To edit, register, and release it, follow [step 4 of the deployment guide](AWS_DEPLOYMENT_GUIDE_LLMOPS.md#9-step-4-register-the-ecs-task-definition).

**How the file connects to the infrastructure.** These values in the task definition must match what the stack created:

| In `task-definition.json`                  | Must match                                                                 |
| ------------------------------------------ | -------------------------------------------------------------------------- |
| `image` (`.../llmopsrepolive:TAG`)         | The ECR repository `llmopsrepolive` in `eu-north-1`                        |
| `containerPort` `8080`                     | The inbound rule on the Security Group, and the port the app listens on    |
| `awslogs-group` `/ecs/llmopstdlive`        | The CloudWatch log group created by the stack                              |
| `awslogs-region` `eu-north-1`              | The region of the stack                                                    |
| `executionRoleArn`                         | The ECS task execution role created by the stack                           |
| `secrets` (`llmops/GROQ_API_KEY` and `llmops/LANGCHAIN_API_KEY`) | The `llmops/*` path allowed by the `ReadLLMOpsSecrets` policy |

If one of these does not match, the usual symptoms are a task that cannot pull the image, no logs, an unreachable app, or an access denied error on a secret.

**Things to remember**

- **Image tags:** ECR tags are `IMMUTABLE`, so a tag cannot be overwritten. Use a new unique tag for every release, and never reuse `latest`.
- **Secrets:** never put key values in the file. It only holds the secret ARNs.
- **Log group:** the stack creates it, so the file does not need `awslogs-create-group`.
- **Sizing:** the task uses 1024 CPU and 4096 MB memory. If the task stops with exit code 137, it ran out of memory, so raise `memory` (8192 is valid with 1024 CPU), which also raises the cost.

## 7. Region and naming

Region: **Europe (Stockholm), `eu-north-1`**. Always select it in the Console. IAM is global, so IAM pages show **Global** instead.

| Item                 | Name                    |
| -------------------- | ----------------------- |
| CloudFormation stack | `llmops-infrastructure` |
| ECR repository       | `llmopsrepolive`        |
| ECS cluster          | `llmops-live-cluster`   |
| CloudWatch log group | `/ecs/llmopstdlive`     |
| Application port     | `8080`                  |

## 8. Deploy the infrastructure

**Before you start:** install AWS CLI v2, configure credentials for the right account, and open a terminal in the project root, where the `infra` folder is. Never publish access keys.

Check the CLI and the active identity:

```bat
aws --version
aws sts get-caller-identity --region eu-north-1
```

Validate the template. This checks the template format only. It does not create anything or prove you have permission to create every resource:

```bat
aws cloudformation validate-template --template-body file://infra/cloudformation.yml --region eu-north-1 --no-cli-pager
```

Then deploy the stack with the command in [step 1 of the deployment guide](AWS_DEPLOYMENT_GUIDE_LLMOPS.md#6-step-1-create-the-infrastructure). It explains each argument and how to find the IP address for `AllowedCidr`. A successful run ends with `Successfully created/updated stack - llmops-infrastructure`.

## 9. Check the stack

| Command                                                                                                                  | What it shows                                              |
| ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| `aws cloudformation describe-stacks --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager`               | Stack status. A good result is `CREATE_COMPLETE`           |
| `aws cloudformation describe-stacks --stack-name llmops-infrastructure --query "Stacks[0].Outputs" --output table --region eu-north-1` | The stack outputs                          |
| `aws cloudformation describe-stack-resources --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager`      | Every resource the stack tracks                            |
| `aws cloudformation describe-stack-events --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager`         | The history. Look for `CREATE_FAILED` and its `ResourceStatusReason` |

Common causes of a failed resource are missing IAM permissions, a name that already exists, a quota limit, or invalid configuration.

In the Console, **CloudFormation → Stack → Resources** is the best first place to see which resources belong to the stack. Use the last column of the table in section 4 to open each one.

## 10. Which resources cost money

AWS prices change by region and usage, so treat this as a guide, not a quote.

- **No charge by themselves:** VPC, subnet, route table, Security Group, ECS cluster, IAM roles, and the OIDC provider.
- **Can cost money:**
  - ECR image storage (an empty repository normally costs nothing).
  - CloudWatch Logs ingestion and storage. The 14 day retention limits how long logs stay, but logging is not free.
  - Fargate compute while a task runs.
  - Public IPv4 addresses and data transfer.
  - An Application Load Balancer or Secrets Manager, if you add them later.
- **This template alone** does not start a Fargate task, so it does not create Fargate compute charges.

Check **Billing and Cost Management → Bills or Cost Explorer**. Billing data can be delayed, so no charge yet does not prove no usage.

## 11. Delete the infrastructure

Delete the stack instead of deleting each resource by hand. CloudFormation removes resources in the right order.

```bat
aws cloudformation delete-stack --stack-name llmops-infrastructure --region eu-north-1
```

Confirm it is gone. A "stack does not exist" error is the expected result here:

```bat
aws cloudformation describe-stacks --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager
```

Then check for things the stack did not manage:

- Secrets Manager secrets, ECR images, and repositories created by hand.
- ECS services, tasks, task definitions, or load balancers created outside the stack. Scale down the service and stop the tasks before the networking resources can be removed.
- Public IPv4 addresses, and resources in other regions.

If deletion fails because the ECR repository is not empty, remove the images first, but only after you are sure you no longer need them. Also look for `DELETE_FAILED` entries in the stack events.

## 12. IAM and safe practice

The identity that runs CloudFormation needs permission to create, change, and delete the VPC, ECR, ECS, CloudWatch Logs, and IAM resources in the template, and to pass the execution role. A valid template can still fail if the caller lacks these permissions.

**AdministratorAccess warning:** this practice setup temporarily attached `AdministratorAccess` to the IAM user while troubleshooting. It gives very broad rights over the whole account, so do not keep it. After practice:

1. Delete the CloudFormation stack and confirm it is gone.
2. Remove the `AdministratorAccess` policy from the IAM user.
3. Use a narrow IAM policy or deployment role for future work.
4. Prefer GitHub OIDC and temporary role credentials over long lived AWS access keys in GitHub.
5. Rotate or deactivate any key that was exposed, and never commit `.env`, AWS keys, or Groq and LangSmith API keys to Git.

## 13. Summary

- `infra/cloudformation.yml` defines the supporting infrastructure, and CloudFormation tracks it as one stack.
- The VPC, subnet, Internet Gateway, route table, and Security Group give the network. ECR stores the image, ECS provides the cluster, and CloudWatch Logs keeps container logs.
- IAM roles and the GitHub OIDC provider let ECS start tasks and let GitHub Actions deploy without stored keys.
- The template does not run the app. The task definition, ECS service, and Fargate task are separate steps.
- `infra/task-definition.json` tells ECS how to run the container. Its image, port, log group, role, and secret names must match the stack, and each release needs a new image tag. The [deployment guide](AWS_DEPLOYMENT_GUIDE_LLMOPS.md) covers the release steps.
- Delete the stack when practice is finished, then check for separately created resources, remove temporary admin rights, and review your billing.

**Always check current AWS pricing and the actual resources in your account before leaving anything running.**