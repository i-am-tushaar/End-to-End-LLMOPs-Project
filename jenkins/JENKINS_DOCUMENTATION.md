# Jenkins CI Pipeline Documentation

## 1. Purpose

This guide explains how to run Jenkins for the End-to-End LLMOps project, with Docker and without Docker.

The current pipeline is a test CI pipeline. Jenkins watches GitHub, checks out code, sets up Python, installs dependencies, runs `pytest`, and publishes test and coverage reports. AWS deployment (ECR/ECS) is a future enhancement, not part of the current pipeline.

## 2. Project details

| Setting | Value |
|---|---|
| Repository | https://github.com/i-am-tushaar/End-to-End-LLMOPs-Project |
| Branch | `main` |
| Pipeline file | `jenkins/Jenkinsfile` |
| Job type | Pipeline, "Pipeline script from SCM" |
| SCM polling | `H/5 * * * *` (about every 5 minutes) |
| Docker Jenkins URL | `http://localhost:8083` |
| Native Jenkins URL | `http://localhost:8080` |

```text
jenkins/
├── Dockerfile.jenkins
├── docker-compose.jenkins.yml
├── plugins.txt
└── Jenkinsfile
```

## 3. CI workflow

```text
Push to GitHub (main) -> Jenkins polls and detects commit -> Checkout
-> Prepare Python -> Install dependencies -> Run pytest
-> Pass: build success, publish reports / Fail: build failure
```

A failing test must fail the build. Never add `|| true` to the pytest command, because it hides failures.

## 4. Prerequisites

- Jenkins and a supported Java runtime
- Git and the Python version used by the Jenkinsfile
- Access to the GitHub repository
- For Docker setup: Docker Desktop (or Docker Engine) and Docker Compose

**OS note:** The existing Jenkinsfile uses Linux `sh` commands. It works on a Linux agent or a Linux Jenkins container. A native Windows agent needs `bat`/PowerShell commands instead.

---

# Part A: Jenkins with Docker

## 5. Setup

Run these from the project root in PowerShell.

1. Check Docker is running:

```powershell
docker --version
docker compose version
```

2. Build and start Jenkins (container name: `jenkins-local`):

```powershell
docker compose -f jenkins/docker-compose.jenkins.yml build
docker compose -f jenkins/docker-compose.jenkins.yml up -d
docker ps
```

3. Open `http://localhost:8083` and get the admin password:

```powershell
docker exec jenkins-local cat /var/jenkins_home/secrets/initialAdminPassword
```

4. Install plugins, create the admin account, confirm the Jenkins URL, and finish setup.

## 6. Docker configuration

| File or setting | Purpose |
|---|---|
| `Dockerfile.jenkins` | Custom Jenkins image with the tools the pipeline needs |
| `docker-compose.jenkins.yml` | Builds and starts the container, maps port `8083` to `8080` |
| `plugins.txt` | Plugins installed in the image |
| `jenkins_home` volume | Keeps settings, jobs, plugins and build history |
| Docker socket mount | Lets Jenkins talk to the host Docker engine |

**Security warning:** Docker socket access can give Jenkins broad control over the host. Use it only on a trusted machine and never expose it to the public internet.

Useful commands:

```powershell
docker compose -f jenkins/docker-compose.jenkins.yml up -d     # start
docker compose -f jenkins/docker-compose.jenkins.yml restart   # restart
docker compose -f jenkins/docker-compose.jenkins.yml down      # stop (data kept)
docker logs jenkins-local                                      # logs
docker exec -it jenkins-local bash                             # shell
```

Do not use `down -v` unless you want to delete all Jenkins data.

---

# Part B: Jenkins without Docker

## 7. Windows install

1. Install Java (Java 21 works for current releases) and check with `java -version`.
2. Install Git from https://git-scm.com/downloads.
3. Install the Python version used by the Jenkinsfile (check the file first).
4. Download the Windows installer from https://www.jenkins.io/download/ and run it.
5. Open `http://localhost:8080`. The admin password is usually at `C:\ProgramData\Jenkins\.jenkins\secrets\initialAdminPassword`.
6. Install plugins, create the admin account, and finish setup.

The Jenkins service may run under a different Windows account than yours. Make sure that account can reach Git, Python, `pip` and `uv`. Restart the service after changing system environment variables.

## 8. Windows pipeline compatibility

A native Windows agent does not support `sh`. Either convert commands to `bat`, or use a Linux agent for the existing Jenkinsfile.

Example (not a verified drop-in replacement, so check env vars, test config and reports first):

```groovy
pipeline {
    agent any
    triggers { pollSCM('H/5 * * * *') }
    stages {
        stage('Checkout') { steps { checkout scm } }
        stage('Create Virtual Environment') {
            steps { bat 'python -m venv .venv' }
        }
        stage('Install Dependencies') {
            steps {
                bat '.venv\\Scripts\\python.exe -m pip install --upgrade pip'
                bat '.venv\\Scripts\\python.exe -m pip install -r requirements.txt'
                bat '.venv\\Scripts\\python.exe -m pip install pytest pytest-cov'
            }
        }
        stage('Run Tests') {
            steps { bat '.venv\\Scripts\\python.exe -m pytest tests -v' }
        }
    }
}
```

## 9. Linux install

Install a supported Java version, then follow https://www.jenkins.io/doc/book/installing/ for your distribution. A Linux agent runs the existing pipeline without changes.

---

# Part C: Configure and run the pipeline

## 10. Plugins

Pipeline, Git, Git client, Pipeline: Stage View, JUnit, Credentials, Timestamper.

## 11. Create the Pipeline job

1. Dashboard, then **New Item**. Name it (for example `LLMOps-CI-CD`), choose **Pipeline**, click **OK**.
2. Set **Definition** to `Pipeline script from SCM` and **SCM** to `Git`.
3. Repository URL: `https://github.com/i-am-tushaar/End-to-End-LLMOPs-Project.git`
4. Branch: `*/main`
5. Script Path: `jenkins/Jenkinsfile`
6. Save, then click **Build Now** and check **Console Output**.

Private repositories need a Jenkins credential selected in the job.

## 12. Jenkinsfile stages

1. **Checkout:** gets the code from the repository and branch.
2. **Setup Python Environment:** prepares Python and a virtual environment.
3. **Install Dependencies:** installs project and test packages.
4. **Run Tests:** runs `pytest`.
5. **Publish Reports:** publishes JUnit results and archives coverage.

## 13. SCM polling

```groovy
triggers {
    pollSCM('H/5 * * * *')
}
```

Jenkins checks the repo about every 5 minutes and builds when it finds a change. `H` spreads the load by picking a steady hashed minute. Use `pollSCM` for CI after commits, and `cron` for scheduled jobs that run even without code changes.

To test it: push a small change to `main` and wait for the next poll. It is not instant.

## 14. Build results

| Status | Meaning |
|---|---|
| Success | All required steps passed |
| Failure | A required step, such as tests, failed |
| Unstable | Build finished but test or report conditions flagged it |
| Aborted | Build was stopped early |

Use **Console Output** to find errors.

---

# Part D: Troubleshooting and best practices

## 15. Common problems

| Problem | What to check |
|---|---|
| Jenkins does not open | Service or container is running, port is free. Docker: `docker ps`, `docker logs jenkins-local` |
| Jenkinsfile not found | Repo URL, branch `*/main`, Script Path `jenkins/Jenkinsfile`, file is pushed |
| Git checkout fails | URL, network, repo visibility, credentials |
| Python or `uv` not found | Install it where Jenkins runs (container or agent), not only on your PC |
| `sh` not recognized | Windows agent running a Linux Jenkinsfile. Use a Linux agent or `bat` |
| Tests fail | Read the first pytest error in Console Output, check dependencies and env vars, reproduce locally, fix and push |
| Auto build does not start | Polling is configured, job has run once, correct branch, Jenkins can reach GitHub |

## 16. Best practices

- Never commit API keys or passwords. Use Jenkins Credentials.
- Give Jenkins only the permissions it needs.
- Do not expose Jenkins publicly without authentication and hardening.
- Keep Jenkins and plugins updated, and back up Jenkins home.
- Do not suppress pytest exit codes.
- Use separate agents when operating systems or tools differ.

## 17. Jenkins and GitHub Actions

The project already has a GitHub Actions workflow. Jenkins is an extra CI option. If both are on, avoid running duplicate pipelines.

## 18. Scope and future work

**Current:** GitHub connection, Pipeline from SCM, Python setup, dependency install, `pytest`, SCM polling, build status, and test and coverage reports.

**Future (not done yet):** build the Docker image after tests, push to Amazon ECR, deploy to ECS with Fargate, use AWS Secrets Manager, add notifications and approval gates.

## 19. References

- https://www.jenkins.io/doc/
- https://www.jenkins.io/doc/book/installing/
- https://www.jenkins.io/doc/book/pipeline/
- https://docs.docker.com/compose/

---

**Maintenance:** Update this document whenever the Jenkinsfile, Docker setup, plugins, stages, ports or install steps change.
