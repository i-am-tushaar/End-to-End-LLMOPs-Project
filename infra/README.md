# AWS Infrastructure

This folder contains the AWS infrastructure configurations and deployment documentation for the End-to-End LLMOps RAG Application.

The project supports two AWS container deployment approaches:

1. **Amazon ECS with AWS Fargate**
2. **Amazon EKS with Kubernetes**

Both approaches deploy the Dockerized LLMOps application, but they use different container orchestration services.

## 1. Folder Structure

```text
infra/
│
├── README.md
│
├── ecs/
│   ├── AWS_DEPLOYMENT_DOCUMENTATION.md
│   ├── cloudformation.yml
│   └── task-definition.json
│
└── eks/
    └── cluster.yaml
```

## 2. ECS Deployment (Fargate)

**Location:** `infra/ecs/`

Amazon Elastic Container Service (ECS) manages and runs containers. AWS Fargate provides serverless compute, so we do not need to manage EC2 worker nodes.

### Files

| File | Purpose |
|---|---|
| `cloudformation.yml` | Defines AWS infrastructure such as VPC, networking, ECR, ECS, IAM roles and CloudWatch resources |
| `task-definition.json` | Defines the container configuration, CPU, memory, ports, environment variables and secrets |
| `AWS_DEPLOYMENT_DOCUMENTATION.md` | Documents the ECS deployment architecture, GitHub Actions CI/CD, troubleshooting and cleanup |

### Deployment Flow

```text
Developer
    |
    v
GitHub Repository
    |
    v
GitHub Actions
    |
    v
Run Tests
    |
    v
Build Docker Image
    |
    v
Amazon ECR
    |
    v
Amazon ECS
    |
    v
AWS Fargate
    |
    v
Running Application Container
```

### When to use ECS with Fargate?

- When you want to run containers without managing Kubernetes.
- When you prefer AWS-managed container orchestration.
- When you want to avoid managing EC2 worker nodes.

**Detailed documentation:** [AWS ECS Deployment Guide](ecs/AWS_DEPLOYMENT_DOCUMENTATION.md)

## 3. EKS Deployment (Kubernetes)

**Location:** `infra/eks/`

Amazon Elastic Kubernetes Service (EKS) is AWS's managed Kubernetes service. It provides a managed Kubernetes control plane, while worker nodes run application workloads.

### Files

| File | Purpose |
|---|---|
| `cluster.yaml` | Defines the EKS cluster, Kubernetes version, AWS region, networking, managed node group, instance type and storage |

The cluster configuration is managed using `eksctl`.

### Deployment Flow

```text
Developer
    |
    v
GitHub Repository
    |
    v
Jenkins (Windows)
    |
    v
Run Tests
    |
    v
Build Docker Image
    |
    v
Push Image to Amazon ECR
    |
    v
Amazon EKS
    |
    v
Kubernetes Deployment
    |
    v
Application Pod
    |
    v
Running LLMOps Application
```

### Current EKS Configuration

| Setting | Configuration |
|---|---|
| Cluster name | `llmops-eks-cluster` |
| Region | `eu-north-1` |
| Kubernetes version | `1.37` |
| Worker instance | `t3.large` |
| Desired worker nodes | `1` |
| Storage | `30 GiB gp3` |
| NAT Gateway | Disabled |
| Worker networking | Public subnets |

**Note:** The configuration file defines the infrastructure. AWS resources are created only when the cluster creation command is executed.

### Create the EKS Cluster

From the project root:

```bash
eksctl create cluster -f infra/eks/cluster.yaml
```

### When to use EKS?

- When you want to deploy applications using Kubernetes.
- When you need Kubernetes features such as Pods, Deployments, Services and Namespaces.
- When you want to learn and manage Kubernetes-based deployments.

## 4. ECS vs EKS

| Feature | ECS with Fargate | EKS |
|---|---|---|
| Orchestration | Amazon ECS | Kubernetes |
| Compute | AWS Fargate | EC2 worker nodes in our current configuration |
| Infrastructure management | AWS manages the underlying Fargate compute | AWS manages the control plane; we manage worker configuration |
| Configuration | ECS Task Definition | Kubernetes YAML manifests |
| Deployment tool | AWS ECS APIs / CLI | `kubectl` and `eksctl` |
| Learning focus | AWS container deployment | Kubernetes and cloud-native deployment |

## 5. Important Notes

- Both approaches use Docker images stored in Amazon ECR.
- ECS and EKS are separate deployment approaches. They do not need to run simultaneously.
- ECS deployment automation is documented under `infra/ecs/`.
- EKS cluster infrastructure configuration is maintained under `infra/eks/`.
- Jenkins pipeline files and Kubernetes application manifests are maintained in their respective project folders.
- Never commit API keys, AWS credentials, certificates or private keys to GitHub.
- AWS resources can incur charges while running. Delete temporary resources after testing and verify cleanup in AWS Console.

## 6. Which Deployment Should You Choose?

Choose **ECS with Fargate** if you want a simpler AWS-managed container deployment without managing Kubernetes.

Choose **EKS** if you want to deploy and manage the application using Kubernetes and practise Kubernetes-based CI/CD with Jenkins.

Both approaches demonstrate different ways of deploying the same LLMOps application on AWS.