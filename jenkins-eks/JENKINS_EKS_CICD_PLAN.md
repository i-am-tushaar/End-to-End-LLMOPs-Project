# Jenkins CI/CD Deployment to AWS EKS (Short Plan)

**Project:** End to End LLMOps | **Repo:** `i-am-tushaar/End-to-End-LLMOps-Project` | **Region:** `eu-north-1`
**Stack:** GitHub, Jenkins, Docker, Amazon ECR, Amazon EKS (Kubernetes)

> **Public copy:** Account specific values are replaced with placeholders. Use your own values when following the steps.

| Placeholder | Meaning |
|---|---|
| `<AWS_ACCOUNT_ID>` | Your 12 digit AWS account ID |

## 1. Goal

Push code to GitHub and let Jenkins do the rest: test, build a Docker image, push it to ECR, deploy it to EKS and verify the rollout.

```text
GitHub → Jenkins → Tests → Docker build → AWS login → ECR → EKS → Kubernetes deployment
```

| Component | Job |
|---|---|
| GitHub | Stores code, Dockerfile, manifests and Jenkinsfile |
| Jenkins | Runs the pipeline |
| Docker | Packages the app into an image |
| IAM Roles Anywhere | Gives Jenkins temporary AWS credentials using a certificate |
| ECR | Stores versioned images |
| EKS | Managed Kubernetes cluster |
| kubectl | Talks to the cluster |

## 2. Current Jenkins Setup

Jenkins is installed natively on Windows (not in Docker) at `http://localhost:8080`. It runs as a Windows service under the `LocalSystem` account.

An existing CI job, `LLMOps-Windows-CI` (branch `main`, file `jenkins-windows/Jenkinsfile`), already checks out code, sets up a Python virtual environment, installs dependencies, runs Pytest and archives JUnit and coverage reports. Keep it. The EKS pipeline gets its own file: `jenkins-eks/Jenkinsfile`.

## 3. AWS Resources Already Created

| Resource | Name | Notes |
|---|---|---|
| Trust Anchor | `llmops-windows-jenkins-root-ca` | Trusts our own Root CA certificate |
| IAM Role | `JenkinsEKSDeploymentRole` | No admin access, trusted by `rolesanywhere.amazonaws.com` |
| Roles Anywhere Profile | `jenkins-eks-profile` | Links the role to the trust anchor, 1 hour sessions |
| ECR repository | `end-to-end-llmops` | URI: `<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/end-to-end-llmops` |
| Policy | `JenkinsECRPushPolicy` | Login and push images, limited to this repo |
| Policy | `JenkinsEKSDescribePolicy` | Only `eks:DescribeCluster`, limited to `llmops-eks-cluster` |

**Not created yet:** the EKS cluster `llmops-eks-cluster` and its worker nodes.

**How the login works:**

1. Jenkins presents its client certificate.
2. AWS checks it against the trust anchor.
3. The profile maps it to the IAM role.
4. AWS returns temporary credentials. No permanent access keys are stored anywhere.

**Certificates:** We made our own Root CA (`rootCA.crt`, `rootCA.key`) and a Jenkins client certificate (`jenkins.crt`, `jenkins.key`, valid one year, for client authentication only). The Root CA private key is never given to Jenkins. Only the Jenkins key is readable by SYSTEM, Administrators and your user.

## 4. Planned Folder Structure

```text
jenkins-windows/   Existing Windows CI pipeline (keep)
jenkins-eks/       New EKS Jenkinsfile and notes
infra/eks/         cluster.yaml for eksctl
k8s/               namespace, deployment, service, configmap, hpa
scripts/           Optional build and deploy helper scripts
Dockerfile         Application image
```

Existing ECS and Windows Jenkins files stay as they are.

## 5. Steps to Complete

### Phase 1: Dockerize and test locally

Review the Dockerfile (Python version, dependencies, entry point, port, environment variables). Then:

```powershell
docker build -t llmops-app:local .
docker run -d --name llmops-local -p 8080:8080 llmops-app:local
docker ps
docker logs llmops-local
```

Done when the image builds, the container starts and the health endpoint responds.

### Phase 2: Kubernetes manifests (`k8s/`)

| File | Purpose |
|---|---|
| `namespace.yaml` | Separate namespace `llmops` |
| `deployment.yaml` | Image, replicas (start with 1), port, resources, readiness and liveness probes |
| `service.yaml` | Start with `ClusterIP` to avoid a billable load balancer |
| `configmap.yaml` | Non-secret settings only (environment, log level, port) |
| `hpa.yaml` | Autoscaling, added later once cluster metrics are set up |

API keys never go in a ConfigMap. Supply them through a proper secrets solution.

### Phase 3: Jenkins login to AWS

1. Install the AWS Roles Anywhere signing helper (`aws_signing_helper.exe`) in a secure folder.
2. Set up an AWS CLI profile `jenkins-eks` using `credential_process`.
3. Make sure the SYSTEM account can read the helper, certificate and Jenkins key.
4. Test as SYSTEM:

```powershell
aws sts get-caller-identity --profile jenkins-eks
```

The result should show the assumed role `JenkinsEKSDeploymentRole`.

### Phase 4: Create the EKS cluster

Define the cluster in `infra/eks/cluster.yaml` and create it with `eksctl`. Create it only after the app, manifests and pipeline are ready.

| Setting | Plan |
|---|---|
| Name and region | `llmops-eks-cluster`, `eu-north-1` |
| Kubernetes version | A currently supported version |
| Nodes | One small managed node |

**Cost controls:** no NAT Gateway, no load balancer at first, one small node, no extra volumes, and delete everything after the demo.

### Phase 5: Give Jenkins Kubernetes access

IAM permission to describe the cluster does not allow deploying to it. Create an EKS access entry for `JenkinsEKSDeploymentRole`, then grant rights through an EKS access policy or Kubernetes RBAC, limited to the `llmops` namespace. Avoid cluster-admin. Verify:

```powershell
kubectl get nodes
kubectl get namespaces
```

### Phase 6: Jenkins pipeline (`jenkins-eks/Jenkinsfile`)

| Stage | What it does |
|---|---|
| Checkout | Gets code from GitHub |
| Environment check | Verifies Python, Docker and AWS tools |
| Unit tests | Runs automated tests |
| Docker build and validation | Builds and checks the image |
| AWS authentication | Gets temporary credentials |
| ECR login and push | Uploads the tagged image |
| Configure kubectl | Connects to EKS |
| Validate manifests | Checks the YAML |
| Deploy | Applies the Kubernetes resources |
| Verify rollout | Confirms pods are ready |
| Summary | Shows deployment information |

**Image tags:** Use the Git commit ID, such as `end-to-end-llmops:<git-commit-sha>`, instead of only `latest`. Every deployment can then be traced to exact code.

### Phase 7: Test the running app

Use `kubectl port-forward`, pod logs, deployment status, service endpoints and the health endpoint. Add a LoadBalancer or Ingress later only if external access is needed, because it adds AWS charges.

### Phase 8: End to End test

Change the app, push to GitHub, and confirm that Jenkins tests, builds, pushes and deploys it, and that EKS runs the new pods. Check:

```powershell
kubectl get deployments -n llmops
kubectl get pods -n llmops
kubectl get services -n llmops
kubectl rollout status deployment/llmops-app -n llmops
```

Final deployment and container names will be set when the manifests are written.

### Phase 9: Cleanup

1. Delete Kubernetes resources, including any load balancer or ingress.
2. Delete the node group, then the EKS cluster.
3. Remove networking created only for this demo.
4. Delete ECR images or the repository if no longer needed.
5. Check EC2, EBS, NAT Gateway and public IP leftovers.
6. Review AWS Billing and Cost Explorer.

Keep the IAM setup unless you have a reason to remove it.

## 6. Security Rules

1. No permanent AWS access keys in Jenkins. Use IAM Roles Anywhere and temporary credentials.
2. Keep the Root CA private key away from Jenkins and protect certificate files with Windows permissions.
3. Use least privilege: ECR rights limited to this repo, EKS rights limited to this cluster, namespace level Kubernetes access, no AdministratorAccess.
4. Never put API keys in Docker images. Use secure secret handling, small images, no unnecessary root, and scan images before production.
5. Never commit private keys, AWS secret keys, API keys, passwords or certificate material. Add `*.key`, `*.crt`, `*.srl`, `*.csr`, `.env` and your certificate folders to `.gitignore`.

## 7. Completion Checklist

- [ ] Dockerfile verified, image builds and container runs locally
- [ ] Kubernetes manifests created
- [ ] Jenkins gets temporary AWS credentials
- [ ] Jenkins logs in to ECR and pushes images
- [ ] EKS cluster created and Jenkins has deployment access
- [ ] Pipeline completes and the app runs in EKS
- [ ] Rollout verified and application tested
- [ ] AWS resources cleaned up
- [ ] Documentation updated

## 8. Expected Outcome

A developer pushes code to GitHub and Jenkins automatically tests, packages and deploys it to Kubernetes on EKS. The project shows practical skills in Jenkins automation, Docker, IAM and IAM Roles Anywhere, ECR, EKS, secure credentials and cloud cost cleanup.
