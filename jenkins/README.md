# Jenkins CI/CD

This folder holds every Jenkins pipeline for the End to End LLMOps project. There are three setups. Each one lives in its own subfolder with its own Jenkinsfile and guide, so you can pick the one that fits your needs and ignore the rest.

## Quick Chooser

| I want to... | Use this folder |
|---|---|
| Only run tests on every push, on a Windows PC | `windows-ci/` |
| Run tests, then deploy to Kubernetes on AWS EKS, using Jenkins on Windows | `windows-cicd-eks/` |
| Run Jenkins in Docker and deploy to AWS ECS Fargate | `docker-cicd-ecs/` |

## Folder Layout

```text
jenkins/
├── README.md
├── windows-ci/
│   ├── Jenkinsfile
│   └── JENKINS_WINDOWS_CI.md
├── windows-cicd-eks/
│   ├── Jenkinsfile
│   ├── JENKINS_EKS_CICD.md
│   └── JENKINS_AWS_EKS_DEPLOYMENT_GUIDE.md
└── docker-cicd-ecs/
    ├── Dockerfile.jenkins
    ├── docker-compose.jenkins.yml
    ├── plugins.txt
    ├── Jenkinsfile
    └── JENKINS_DOCKER_CI_PIPELINE.md
```

## How the Names Work

Each folder name follows the pattern `where Jenkins runs` + `what the pipeline does` + `deployment target`.

| Part | Meaning |
|---|---|
| `windows` or `docker` | Where Jenkins itself runs: installed on Windows, or inside a Docker container |
| `ci` | Continuous integration only: checkout, install, test, report. No AWS deployment |
| `cicd` | Continuous integration and deployment: it also builds an image and deploys it |
| `eks` or `ecs` | The AWS service the app is deployed to |

---

## 1. `windows-ci/`: Tests Only on Native Windows

**What it is:** A test pipeline running on Jenkins installed directly on Windows (`http://localhost:8080`). It checks out the code, sets up a Python environment, installs dependencies, runs `pytest` and publishes test and coverage reports. It does not touch AWS.

**Why it exists:** It is the simplest setup. It gives fast feedback on every push without needing Docker, AWS accounts or cloud costs, and it proves your tests pass before anything is deployed.

**Use it when:**

1. You work on Windows and want automatic tests after each commit.
2. You are learning Jenkins and want a first pipeline with nothing to pay for.
3. You want a quality check that runs before any deployment setup.

**How to use it:**

1. Install Java, Git and Python on the Windows machine, then install Jenkins from https://www.jenkins.io/download/.
2. Open `http://localhost:8080`, finish the setup wizard and install the suggested plugins.
3. Create a Pipeline job with "Pipeline script from SCM", point it at your GitHub repo, branch `main`, and set the Script Path to `jenkins/windows-ci/Jenkinsfile`.
4. Click **Build Now** and read **Console Output**.

**Watch out for:** The Jenkins Windows service may run under a different account than yours, so that account must be able to reach Git, Python and `pip`. Windows agents need `bat` commands, not `sh`.

**Full guide:** [windows-ci/JENKINS_WINDOWS_CI.md](windows-ci/JENKINS_WINDOWS_CI.md)

---

## 2. `windows-cicd-eks/`: Test, Build and Deploy to AWS EKS

**What it is:** A full CI/CD pipeline on native Windows Jenkins. After the tests pass, it builds a Docker image, pushes it to Amazon ECR and deploys it to an Amazon EKS (Kubernetes) cluster, then checks that the rollout succeeded.

**Why it exists:** It shows the complete path from a code push to a running Kubernetes deployment. AWS access uses IAM Roles Anywhere, so Jenkins signs in with a certificate and receives temporary credentials. No permanent AWS access keys are stored anywhere.

**Use it when:**

1. You want to deploy the app on Kubernetes, not just test it.
2. You want to practice a real DevOps workflow: ECR, EKS, kubectl, IAM and secure credentials.
3. Your Jenkins runs on a Windows machine outside AWS.

**How to use it:**

1. Complete the `windows-ci/` setup first, so the test stage already works.
2. Follow the setup record in the deployment guide: IAM Roles Anywhere (trust anchor, profile, role), the AWS CLI profile, Docker with the ECR credential helper, and the ECR repository.
3. Create the EKS cluster from `infra/eks/cluster.yaml`, then give the Jenkins IAM role Kubernetes access (an EKS access entry).
4. Finalize the manifests in `k8s/` and store API keys securely, never in Git.
5. Create a Pipeline job with Script Path `jenkins/windows-cicd-eks/Jenkinsfile` and run it.
6. When you finish the demo, delete the cluster to stop AWS charges.

**Watch out for:** Creating an EKS cluster costs money while it exists. Test everything as the Jenkins SYSTEM account, not only as your own user. The guide's status checklist shows what is done and what is still pending.

**Guides:**

1. [windows-cicd-eks/JENKINS_EKS_CICD.md](windows-cicd-eks/JENKINS_EKS_CICD.md) explains the plan, phases and security rules.
2. [windows-cicd-eks/JENKINS_AWS_EKS_DEPLOYMENT_GUIDE.md](windows-cicd-eks/JENKINS_AWS_EKS_DEPLOYMENT_GUIDE.md) records the actual setup, commands and progress.

---

## 3. `docker-cicd-ecs/`: Jenkins in Docker, Deploy to AWS ECS Fargate

**What it is:** A setup where Jenkins itself runs inside a Docker container, started with Docker Compose at `http://localhost:8083`. The pipeline tests the code, builds the application image, pushes it to Amazon ECR and deploys it to AWS ECS using Fargate, which runs containers without managing servers.

**Why it exists:** Running Jenkins in Docker makes the setup repeatable. Java, plugins and tools are baked into one image, so anyone can start the same Jenkins on any machine with two commands. ECS Fargate is also a lighter and cheaper way to run containers than Kubernetes.

**Use it when:**

1. You want a portable Jenkins that behaves the same on every machine.
2. You want the simplest path to a running AWS deployment, without managing Kubernetes.
3. You want to rebuild or reset Jenkins quickly without a manual install.

**How to use it:**

1. Install Docker Desktop (or Docker Engine) with Docker Compose.
2. From the project root, build and start Jenkins:

```powershell
docker compose -f jenkins/docker-cicd-ecs/docker-compose.jenkins.yml build
docker compose -f jenkins/docker-cicd-ecs/docker-compose.jenkins.yml up -d
```

3. Open `http://localhost:8083` and get the first admin password:

```powershell
docker exec jenkins-local cat /var/jenkins_home/secrets/initialAdminPassword
```

4. Finish the setup wizard, then create a Pipeline job with Script Path `jenkins/docker-cicd-ecs/Jenkinsfile`.
5. Add your AWS and API credentials through **Jenkins Credentials**, never in the repo.

**Watch out for:** Mounting the Docker socket gives Jenkins broad control of the host, so use it only on a trusted machine and never expose Jenkins to the public internet. Do not run `down -v` unless you want to delete all Jenkins data. Missing tools go into `Dockerfile.jenkins`, followed by a rebuild.

**Full guide:** [docker-cicd-ecs/JENKINS_DOCKER_CI_PIPELINE.md](docker-cicd-ecs/JENKINS_DOCKER_CI_PIPELINE.md)

---

## Side by Side

| | `windows-ci` | `windows-cicd-eks` | `docker-cicd-ecs` |
|---|---|---|---|
| Jenkins runs on | Windows | Windows | Docker container |
| Jenkins URL | `localhost:8080` | `localhost:8080` | `localhost:8083` |
| Runs tests | Yes | Yes | Yes |
| Builds app image | No | Yes | Yes |
| Deploys to AWS | No | EKS (Kubernetes) | ECS Fargate |
| AWS cost | None | Higher (EKS cluster and node) | Lower (pay per task) |
| Setup effort | Low | High | Medium |
| Best for | Learning and quick test feedback | Kubernetes practice | Simple, repeatable container deployment |

## Related Folders Outside `jenkins/`

| Folder | Purpose |
|---|---|
| `infra/eks/` | EKS cluster configuration for `eksctl` |
| `infra/ecs/` | ECS deployment files (CloudFormation and task definition) |
| `k8s/` | Kubernetes manifests used by the EKS pipeline |
| `docs/` | General project wide documentation |
| `.github/workflows/` | GitHub Actions workflow, separate from Jenkins |

## Rules for All Pipelines

1. Each pipeline is independent. Changing one must not break the others.
2. Never commit private keys, certificates, API keys, passwords or `.env` files. Use Jenkins Credentials or a secrets service.
3. Give Jenkins only the AWS permissions it needs (least privilege).
4. Use Git commit based image tags, not only `latest`.
5. Delete temporary AWS resources after testing and review the billing dashboard.
6. If both Jenkins and GitHub Actions are enabled, avoid running duplicate pipelines.
