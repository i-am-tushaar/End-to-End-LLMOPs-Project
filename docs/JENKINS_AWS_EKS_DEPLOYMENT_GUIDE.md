# Jenkins, Docker, ECR and EKS Deployment Guide (Short Version)

**Project:** End to End LLMOps | **Repo:** `i-am-tushaar/End-to-End-LLMOPs-Project` | **Region:** `eu-north-1`
**Status:** ECR push is done and verified. EKS deployment is still pending.

> **Public copy:** Account specific values are replaced with placeholders. Use your own values when following the steps.

| Placeholder | Meaning |
|---|---|
| `<AWS_ACCOUNT_ID>` | Your 12 digit AWS account ID |
| `<VPC_ID>` | Your VPC ID |
| `<CERT_DIR>` | Local folder holding your root CA and Jenkins client certificates (keep it out of Git) |
| `<TOOLS_DIR>` | Local folder holding `aws_signing_helper.exe` |

## 1. Goal

Push code to GitHub, then Jenkins automatically tests it, builds a Docker image, pushes it to Amazon ECR, and deploys it to Amazon EKS (Kubernetes).

```text
GitHub → Jenkins (Windows) → Tests → Docker build → AWS login → ECR → EKS → Running app
```

## 2. Key Details

| Item | Value |
|---|---|
| Jenkins | `http://localhost:8080`, Windows service, runs as `LocalSystem` |
| AWS account | `<AWS_ACCOUNT_ID>` |
| ECR repo | `end-to-end-llmops` |
| EKS cluster | `llmops-eks-cluster` |
| Kubernetes namespace | `llmops` |
| Jenkinsfile | `jenkins-eks/Jenkinsfile` |
| Cluster config | `infra/eks/cluster.yaml` |
| Manifests | `k8s/` (namespace, configmap, secret, deployment, service) |

The new EKS pipeline is separate from the existing GitHub Actions and Windows Jenkins CI pipelines. Do not overwrite them.

## 3. Why the Jenkins Account Matters

Jenkins runs as the SYSTEM user, not your normal user. SYSTEM has its own home folder (`C:\Windows\System32\config\systemprofile\`), so AWS config, Docker config and certificates must be readable by SYSTEM. Always test commands as SYSTEM, because something that works in your own CMD can still fail in Jenkins. We used Windows Task Scheduler to run tests as SYSTEM.

## 4. AWS Login (IAM Roles Anywhere)

Jenkins gets temporary AWS credentials using a certificate, so no permanent access keys are stored.

```text
Jenkins → certificate → Trust Anchor → Profile → IAM Role → temporary credentials
```

| Resource | Name |
|---|---|
| Trust Anchor | `llmops-windows-jenkins-root-ca` |
| Profile | `jenkins-eks-profile` |
| IAM Role | `JenkinsEKSDeploymentRole` |
| Certificates | `<CERT_DIR>\` (root CA and Jenkins client cert and key) |
| Signing helper | `<TOOLS_DIR>\aws_signing_helper.exe` |
| AWS CLI profile | `jenkins-eks`, copied to the SYSTEM profile's `.aws\config` |

Verify:

```cmd
aws sts get-caller-identity --profile jenkins-eks --region eu-north-1
```

Expect account `<AWS_ACCOUNT_ID>` and role `JenkinsEKSDeploymentRole`. This passed under SYSTEM.

**Permissions on the role:**

1. `JenkinsECRPushPolicy`: login, upload layers and push images to the ECR repo.
2. `JenkinsEKSDescribePolicy`: only `eks:DescribeCluster`.

This is not enough to deploy to Kubernetes. An EKS access entry is still needed (see section 8).

## 5. Docker and ECR

Docker Desktop (Linux containers) builds from the root `Dockerfile` (Python 3.12 slim, FastAPI with Uvicorn, port 8080). `.dockerignore` keeps out virtual environments, Git history and `.env` files. Never put API keys in the image.

**Problem:** `docker login` under SYSTEM failed with "The stub received bad data."

**Fix:** Use the ECR Credential Helper instead of storing a password. Put this in `C:\Windows\System32\config\systemprofile\.docker\config.json`:

```json
{
  "credHelpers": {
    "<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com": "ecr-login"
  }
}
```

The helper asks AWS for a temporary token each time Docker needs one. It needs these environment variables:

```cmd
set AWS_PROFILE=jenkins-eks
set AWS_REGION=eu-north-1
set AWS_SDK_LOAD_CONFIG=true
```

## 6. Verified Under SYSTEM

```cmd
docker build -t llmops-jenkins-test:latest .
docker tag llmops-jenkins-test:latest <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/end-to-end-llmops:jenkins-test
docker push <AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/end-to-end-llmops:jenkins-test
aws ecr describe-images --repository-name end-to-end-llmops --region eu-north-1 --profile jenkins-eks
```

The build, tag, push and ECR check all succeeded. The image (3.67 GB) is in ECR with tag `jenkins-test`. Two untagged artifacts were also found, so inspect them before cleaning up.

## 7. Jenkins Pipeline

**Stages:**

1. Checkout
2. Verify tools
3. Tests
4. AWS authentication
5. Docker build
6. Image validation
7. ECR login check
8. Push image
9. Configure EKS (kubeconfig)
10. Verify kubectl
11. Deploy
12. Verify rollout

**Image tags** use the Git commit ID (for example `end-to-end-llmops:7ed8f496`), not just `latest`, so you always know which code is deployed.

**Create the job:** New Item, name it `LLMOps-EKS-Deployment`, choose Pipeline, then "Pipeline script from SCM", Git, your repo URL, the correct branch, and Script Path `jenkins-eks/Jenkinsfile`. The full pipeline has not been run yet.

## 8. EKS Cluster (Not Created Yet)

| Setting | Planned value |
|---|---|
| Kubernetes version | `1.37` (check that EKS supports it) |
| Worker node | 1 x `t3.large`, 30 GiB gp3 |
| NAT Gateway | Disabled, to save cost |
| API endpoint | Public and private, limited to your public IP |
| Network | Default VPC `<VPC_ID>`, public subnets |

The config passed an `eksctl` dry run. With NAT disabled, confirm that nodes can still reach the AWS services and internet access they need.

```cmd
eksctl create cluster -f infra/eks/cluster.yaml
aws eks update-kubeconfig --region eu-north-1 --name llmops-eks-cluster --profile jenkins-eks
kubectl get nodes
```

Creating the cluster costs money. Do it only after the checks above are done.

**Kubernetes access:** A kubeconfig only says how to connect, not what you may do. Create an EKS access entry for `JenkinsEKSDeploymentRole` with least-privilege rights in the `llmops` namespace (ConfigMaps, Secrets, Deployments, Services, Pods). Avoid cluster-admin. Make sure the kubeconfig is also available to SYSTEM.

## 9. Kubernetes Files

| File | Purpose |
|---|---|
| `namespace.yaml` | Creates `llmops` |
| `configmap.yaml` | Non-secret settings only |
| `secret.yaml` | `GOOGLE_API_KEY`, `GROQ_API_KEY` (metadata only now, fill in securely) |
| `deployment.yaml` | Image, ports, env, resources, probes |
| `service.yaml` | Use ClusterIP first, because a LoadBalancer adds cost |

The Jenkinsfile expects the deployment and container to both be named `llmops-app` in namespace `llmops`. Check that the YAML matches.

**Manual deploy (for troubleshooting):**

```cmd
kubectl apply -f k8s/
kubectl set image deployment/llmops-app llmops-app=<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/end-to-end-llmops:IMAGE_TAG -n llmops
kubectl rollout status deployment/llmops-app -n llmops
kubectl get pods -n llmops
kubectl logs deployment/llmops-app -n llmops
```

## 10. Things to Check Before Calling It Done

1. **API keys:** Keep them out of GitHub, the Dockerfile, the image and the Jenkinsfile. Use Jenkins credentials or AWS Secrets Manager. Kubernetes Secrets are only base64 encoded by default.
2. **Hugging Face embeddings:** Model loading was slow locally, so test the download inside the cluster.
3. **FAISS index:** It is not in the image and has no persistent storage, so it is lost when a pod restarts. Add persistent storage or an external vector database.
4. **Real test:** A successful rollout does not prove the RAG app works. Test PDF ingestion and retrieval inside EKS.

## 11. Different Logins

| Where | How it authenticates |
|---|---|
| AWS Console | Your browser login |
| AWS CLI | `jenkins-eks` profile via IAM Roles Anywhere |
| Docker and ECR | ECR Credential Helper |
| Jenkins UI | Jenkins's own login |
| Kubernetes | kubeconfig plus an EKS access entry |

## 12. Cleanup and Cost

Costs come from the EKS control plane (charged while the cluster exists), EC2 nodes, EBS volumes, load balancers, NAT, ECR storage and data transfer.

```cmd
kubectl delete -f k8s/ --ignore-not-found=true
eksctl delete cluster --name llmops-eks-cluster --region eu-north-1
aws eks list-clusters --region eu-north-1 --profile jenkins-eks
```

Then check for leftovers (EC2, load balancers, NAT gateways, EBS volumes) and delete unused ECR images. Keep the ECR repo unless you no longer need it. Review the billing dashboard afterward.

## 13. Progress

**Done:**

- [x] Jenkins on Windows (LocalSystem)
- [x] Docker build under SYSTEM
- [x] IAM Roles Anywhere, role and policies
- [x] AWS CLI profile (also in the SYSTEM profile)
- [x] ECR credential helper
- [x] Image pushed to ECR and verified

**Remaining:**

- [ ] Finalize IAM and EKS access entry
- [ ] Check the Kubernetes version and API CIDR (your current public IP)
- [ ] Review the NAT-off network design
- [ ] Create the cluster
- [ ] Configure kubeconfig for SYSTEM
- [ ] Finalize YAML files and secrets
- [ ] Handle the FAISS storage issue
- [ ] Create the Jenkins job and run the full pipeline
- [ ] Test the app and PDF ingestion in EKS
- [ ] Review costs and delete temporary resources

## 14. Security Rules

1. Never commit private keys (`rootCA.key`, `jenkins.key`) or API keys.
2. No permanent AWS access keys in Jenkins or the Jenkinsfile.
3. Use least-privilege IAM and Kubernetes permissions.
4. Never open the Kubernetes API to `0.0.0.0/0`.
5. No secrets in ConfigMaps and no `.env` files in images.
6. Use Git commit based image tags.
7. Never share ECR tokens.
8. Delete temporary infrastructure and review billing after testing.
