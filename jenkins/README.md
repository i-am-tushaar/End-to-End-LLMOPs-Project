# Jenkins CI/CD

All Jenkins pipelines for the End to End LLMOps project live in this folder. Each setup has its own subfolder with its own Jenkinsfile and guide.

## Which one should I use?

| Folder | What it does | Use it when | Guide |
|---|---|---|---|
| `docker/` | Runs Jenkins inside Docker and runs the CI test pipeline (checkout, install, `pytest`, reports) | You want the quickest, most repeatable setup on any machine with Docker | [JENKINS_DOCKER_CI_PIPELINE.md](docker/JENKINS_DOCKER_CI_PIPELINE.md) |
| `windows/` | Runs the same CI test pipeline on a native Windows Jenkins install | You prefer Jenkins installed directly on Windows | [JENKINS_WINDOWS_CI.md](windows/JENKINS_WINDOWS_CI.md) |
| `eks/` | Builds the app image, pushes it to Amazon ECR and deploys it to Amazon EKS | You want the full CI/CD flow to Kubernetes on AWS | [JENKINS_EKS_CICD.md](eks/JENKINS_EKS_CICD.md) (plan), [JENKINS_AWS_EKS_DEPLOYMENT_GUIDE.md](eks/JENKINS_AWS_EKS_DEPLOYMENT_GUIDE.md) (setup record) |

## Folder layout

```text
jenkins/
├── docker/
│   ├── Dockerfile.jenkins
│   ├── docker-compose.jenkins.yml
│   ├── plugins.txt
│   ├── Jenkinsfile
│   └── JENKINS_DOCKER_CI_PIPELINE.md
├── windows/
│   ├── Jenkinsfile
│   └── JENKINS_WINDOWS_CI.md
└── eks/
    ├── Jenkinsfile
    ├── JENKINS_EKS_CICD.md
    └── JENKINS_AWS_EKS_DEPLOYMENT_GUIDE.md
```

## Jenkins job Script Paths

When you create a Pipeline job with "Pipeline script from SCM", use the matching path:

| Job | Script Path |
|---|---|
| Docker CI | `jenkins/docker/Jenkinsfile` |
| Windows CI | `jenkins/windows/Jenkinsfile` |
| EKS deployment | `jenkins/eks/Jenkinsfile` |

## Related folders outside this one

| Folder | Purpose |
|---|---|
| `infra/eks/` | EKS cluster configuration for `eksctl` |
| `k8s/` | Kubernetes manifests |
| `docs/` | General project wide documentation |
| `.github/workflows/` | GitHub Actions workflow (separate from Jenkins) |

## Rules

1. The three pipelines are independent. Changing one must not break the others.
2. Never commit private keys, certificates, API keys or `.env` files.
3. If both Jenkins and GitHub Actions are enabled, avoid running duplicate pipelines.
