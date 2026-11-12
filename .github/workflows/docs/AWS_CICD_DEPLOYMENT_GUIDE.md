# AWS CI/CD Deployment Guide

## 1. Deployment Objective

This project uses GitHub Actions to test the application and deploy it
to AWS. The application is packaged as a Docker image and runs on Amazon
ECS using AWS Fargate.

**Deployment flow:** GitHub Push → CI Testing → Docker Build → Amazon
ECR → Amazon ECS → Application Deployment

## 2. AWS Services Used

  Service               Purpose
  --------------------- ------------------------------------------
  GitHub Actions        Automates testing and deployment
  AWS IAM               Manages permissions
  GitHub OIDC           Securely connects GitHub to AWS
  Amazon ECR            Stores Docker images
  AWS Secrets Manager   Stores API keys securely
  Amazon ECS            Manages application containers
  AWS Fargate           Runs containers without managing servers
  Amazon CloudWatch     Stores application logs

## 3. Important Project Files

  File                     Responsibility
  ------------------------ ---------------------------------------
  `Dockerfile`             Defines how the Docker image is built
  `.dockerignore`          Excludes unnecessary files
  `requirements.txt`       Contains application dependencies
  `.env.example`           Shows required environment variables
  `ci.yml`                 Runs automated tests
  `deploy.yml`             Builds and deploys the application
  `task-definition.json`   Defines ECS container configuration

The actual `.env` file and API keys should never be pushed to GitHub or
copied into the Docker image.

## 4. AWS Infrastructure Configuration

  Setting           Planned Value
  ----------------- -------------------------
  AWS Region        `eu-north-1`
  ECR Repository    `llmopsrepolive`
  ECS Cluster       `llmops-live-cluster`
  ECS Service       `llmops-live-service`
  ECS Task Family   `llmopstdlive`
  Container Name    `llmops-live-container`
  Container Port    `8080`
  Launch Type       Fargate
  CPU               1 vCPU
  Memory            8 GB

These are the planned resource names and configurations. Confirm that
the resources exist with these settings before deployment.

## 5. How GitHub Connects Securely to AWS

GitHub Actions uses OpenID Connect (OIDC) to request temporary AWS
credentials.

An IAM role is created in AWS and configured to trust the intended
GitHub repository and its `main` branch. When the deployment workflow
runs, GitHub Actions assumes this role and gets permission to access
AWS.

This avoids storing permanent AWS access keys in GitHub.

## 6. Where Application Secrets Are Stored

Gemini and Groq API keys are stored in AWS Secrets Manager.

The ECS task definition references these secrets, allowing the
application to receive them as environment variables when the container
starts. The ECS task execution role needs permission to retrieve these
secrets.

## 7. First Deployment Setup

Before automated deployment, the AWS infrastructure must be created.

1.  Configure the GitHub OIDC identity provider.
2.  Create the GitHub Actions IAM deployment role.
3.  Create the ECR repository.
4.  Store API keys in Secrets Manager.
5.  Configure the ECS task execution role.
6.  Create the ECS cluster.
7.  Register the ECS task definition.
8.  Configure the VPC, public subnet, internet route, and security
    group.
9.  Create the ECS service using Fargate.

For initial testing, restrict inbound access to port `8080` to your own
IP address.

## 8. Automated Deployment Workflow

After the initial setup, deployment becomes automated.

1.  Developer pushes code to the `main` branch.
2.  GitHub Actions starts the CI workflow.
3.  Dependencies are installed and automated tests are executed.
4.  If CI succeeds, the deployment workflow starts.
5.  GitHub authenticates with AWS using OIDC.
6.  Docker builds the application image.
7.  The image is pushed to Amazon ECR.
8.  The ECS task definition is updated with the new image.
9.  ECS starts a new task and replaces the previous task when the
    deployment is healthy.

The deployment workflow updates an existing ECS service. It does not
create the AWS infrastructure automatically.

## 9. Deployment Verification

After deployment:

-   Check ECS to confirm that the task is running.
-   Check ECS service events for deployment errors.
-   Review application logs in CloudWatch.
-   Open the API documentation using `http://<PUBLIC_IP>:8080/docs`.
-   Test document upload, retrieval, and answer generation.

A running container does not necessarily mean the complete RAG
application is working correctly.

## 10. Common Issues

  Issue                      What to Check
  -------------------------- ---------------------------------------------
  AWS authentication fails   OIDC provider and IAM trust policy
  ECR push fails             IAM permissions and AWS region
  ECS cannot pull image      Image URI and execution role
  Secrets unavailable        Secret ARN and IAM permissions
  Container stops            ECS stopped-task reason and CloudWatch logs
  Application inaccessible   Public IP, security group, and port
  LLM API fails              API keys and outbound internet access

## 11. Security and Cost Considerations

-   Never push `.env` files to GitHub.
-   Store API keys in Secrets Manager.
-   Prefer OIDC instead of permanent AWS access keys.
-   Follow least-privilege IAM permissions.
-   Restrict unnecessary public network access.
-   Use commit-specific Docker image tags.
-   Monitor Fargate, ECR, CloudWatch, and networking costs.
-   Start with one Fargate task and monitor usage.

## 12. Interview Explanation

"I containerized my FastAPI-based RAG application using Docker and
created a CI/CD pipeline using GitHub Actions.

Whenever code is pushed to GitHub, the CI workflow runs automated tests.
After successful testing on the main branch, the deployment workflow
authenticates with AWS using OIDC, builds the Docker image, and pushes
it to Amazon ECR.

It then updates the ECS task definition and deploys the new image using
ECS Fargate. I use AWS Secrets Manager to securely manage API keys and
CloudWatch for application logs.

This makes application deployment automated, repeatable, and easier to
maintain."

## Useful AWS Documentation

-   [Amazon
    ECR](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html)
-   [Amazon
    ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html)
-   [AWS
    Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
-   [GitHub Actions OIDC with
    AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
-   [AWS Secrets
    Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
