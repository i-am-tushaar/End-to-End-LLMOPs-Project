# Jenkins CI/CD Pipeline for AWS EKS

## 1. Project Overview

This document explains the Jenkins CI/CD pipeline used to automate the deployment of the End-to-End LLMOps application to Amazon Elastic Kubernetes Service (EKS).

Jenkins runs natively on Windows and automates testing, Docker image creation, pushing images to Amazon ECR, and deploying the application to EKS.

## 2. Technologies Used

- **Jenkins:** CI/CD automation.
- **GitHub:** Source code management.
- **Python / Pytest:** Application testing.
- **Docker:** Application containerization.
- **Amazon ECR:** Docker image storage.
- **Amazon EKS:** Managed Kubernetes service.
- **kubectl:** Kubernetes cluster management.
- **AWS CLI:** AWS service interaction.
- **IAM Roles Anywhere:** AWS authentication for Jenkins.

## 3. Pipeline Stages

| Stage | Purpose |
|---|---|
| Checkout | Downloads project source code from GitHub. |
| Verify Tools | Checks Python, Docker, AWS CLI and kubectl. |
| Run Tests | Executes project tests using Pytest. |
| AWS Authentication | Verifies Jenkins AWS identity. |
| Docker Build | Builds the application Docker image. |
| Image Validation | Checks whether the Docker image exists. |
| ECR Login | Authenticates Docker with Amazon ECR. |
| Push Image to ECR | Uploads the Docker image to ECR. |
| Configure EKS | Configures kubectl to connect to EKS. |
| Verify Kubernetes Connection | Checks Kubernetes worker nodes. |
| Deploy to EKS | Applies Kubernetes files and updates the application image. |
| Verify Deployment | Checks rollout status, pods and services. |

## 4. Kubernetes Configuration Files

The pipeline uses the following files from the `k8s/` directory:

- `namespace.yaml`: Creates the application namespace.
- `configmap.yaml`: Stores non-sensitive configuration.
- `secret.yaml`: Defines the Kubernetes Secret resource.
- `deployment.yaml`: Defines the application deployment.
- `service.yaml`: Defines internal application networking.

## 5. AWS Configuration

| Configuration | Value |
|---|---|
| AWS Region | eu-north-1 |
| AWS Profile | jenkins-eks |
| ECR Repository | end-to-end-llmops |
| EKS Cluster | llmops-eks-cluster |
| Kubernetes Namespace | llmops |

Jenkins uses IAM Roles Anywhere for AWS authentication through the configured AWS CLI profile.

## 6. Docker Image Tagging

The pipeline generates a unique Docker image tag using the Git commit hash.

This helps identify which source-code version was used to build an image.

## 7. Deployment Workflow

1. Jenkins checks out the latest source code.
2. Project tests are executed.
3. Jenkins authenticates with AWS.
4. Docker builds the application image.
5. The image is pushed to Amazon ECR.
6. Jenkins connects to the EKS cluster.
7. Kubernetes configuration files are applied.
8. The deployment is updated with the new image.
9. Jenkins verifies the deployment.

## 8. Important Requirements

- Jenkins must have access to Python, Docker, AWS CLI and kubectl.
- IAM Roles Anywhere must be configured.
- The Jenkins IAM role must have ECR and EKS permissions.
- Kubernetes access must be granted to the Jenkins IAM role.
- Actual application credentials must be configured securely in Kubernetes Secrets.
- The Kubernetes Deployment and container names must match the Jenkinsfile commands.

## 9. Expected Result

After successful execution:

- Docker image is available in Amazon ECR.
- Application is deployed to Amazon EKS.
- Kubernetes pods reach the running state.
- Jenkins reports successful deployment verification.

**Note:** This pipeline deploys to an existing EKS cluster. It does not create the AWS infrastructure.