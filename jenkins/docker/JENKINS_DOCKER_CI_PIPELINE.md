# Jenkins CI Pipeline Using Docker (Short Guide)

**Project:** End to End LLMOps | **Repo:** `i-am-tushaar/End-to-End-LLMOPs-Project`

## 1. What This Is

A test CI pipeline that runs on Jenkins inside a Docker container. Jenkins watches GitHub, checks out the code, sets up Python, installs dependencies, runs `pytest` and publishes test and coverage reports.

AWS deployment (ECR and ECS) is a future step and is not part of this pipeline.

**Why Docker?** The whole Jenkins setup (Java, plugins, tools) lives in one image, so anyone can start the same Jenkins with two commands, and the Linux container runs the `sh` commands in the Jenkinsfile without changes.

## 2. Project Details

| Setting | Value |
|---|---|
| Branch | `main` |
| Pipeline file | `jenkins/Jenkinsfile` |
| Job type | Pipeline, "Pipeline script from SCM" |
| SCM polling | `H/5 * * * *` (about every 5 minutes) |
| Jenkins URL | `http://localhost:8083` |
| Container name | `jenkins-local` |

```text
jenkins/
├── Dockerfile.jenkins
├── docker-compose.jenkins.yml
├── plugins.txt
└── Jenkinsfile
```

## 3. How It Works

```text
Push to main → Jenkins detects the commit → Checkout → Prepare Python
→ Install dependencies → Run pytest → Publish reports (pass or fail)
```

A failing test must fail the build. Never add `|| true` to the pytest command, because it hides failures.

## 4. Before You Start

1. Docker Desktop (or Docker Engine) with Docker Compose
2. Access to the GitHub repo

Java, Git and Python are installed inside the Jenkins image, so you do not need them for Jenkins itself.

## 5. Docker Files

| File or setting | Purpose |
|---|---|
| `Dockerfile.jenkins` | Jenkins image with the tools the pipeline needs |
| `docker-compose.jenkins.yml` | Builds and starts the container, maps port `8083` to `8080` |
| `plugins.txt` | Plugins installed in the image |
| `jenkins_home` volume | Keeps settings, jobs, plugins and build history when the container is replaced |
| Docker socket mount | Lets Jenkins use the host Docker engine |

**Security warning:** Docker socket access can give Jenkins broad control of the host. Use it only on a trusted machine and never expose it to the public internet.

## 6. Start Jenkins

Run these from the project root in PowerShell.

1. Check Docker is running:

```powershell
docker --version
docker compose version
```

2. Build and start Jenkins:

```powershell
docker compose -f jenkins/docker-compose.jenkins.yml build
docker compose -f jenkins/docker-compose.jenkins.yml up -d
docker ps
```

3. Open `http://localhost:8083` and get the first admin password:

```powershell
docker exec jenkins-local cat /var/jenkins_home/secrets/initialAdminPassword
```

4. Install plugins, create the admin account, confirm the Jenkins URL and finish setup.

**Daily commands:**

```powershell
docker compose -f jenkins/docker-compose.jenkins.yml restart   # restart
docker compose -f jenkins/docker-compose.jenkins.yml down      # stop, data kept
docker logs jenkins-local                                      # logs
docker exec -it jenkins-local bash                             # shell inside the container
```

Do not use `down -v` unless you want to delete all Jenkins data.

## 7. Create the Pipeline Job

**Plugins needed:** Pipeline, Git, Git client, Pipeline: Stage View, JUnit, Credentials, Timestamper.

1. Dashboard, then **New Item**. Name it (for example `LLMOps-CI-CD`), choose **Pipeline**, click **OK**.
2. Set **Definition** to `Pipeline script from SCM` and **SCM** to `Git`.
3. Repository URL: `https://github.com/i-am-tushaar/End-to-End-LLMOPs-Project.git`
4. Branch: `*/main`
5. Script Path: `jenkins/Jenkinsfile`
6. Save, click **Build Now** and read **Console Output**.

A private repo needs a Jenkins credential selected in the job.

## 8. Pipeline Stages

| Stage | What it does |
|---|---|
| Checkout | Gets code from the repo and branch |
| Setup Python Environment | Prepares Python and a virtual environment |
| Install Dependencies | Installs project and test packages |
| Run Tests | Runs `pytest` |
| Publish Reports | Publishes JUnit results and archives coverage |

## 9. SCM Polling

```groovy
triggers {
    pollSCM('H/5 * * * *')
}
```

Jenkins checks the repo about every 5 minutes and builds when it finds a change. The `H` picks a steady hashed minute to spread the load. Use `pollSCM` to build after commits, and `cron` for scheduled jobs that run even without code changes.

To test it, push a small change to `main` and wait for the next poll. It is not instant.

## 10. Build Results

| Status | Meaning |
|---|---|
| Success | All required steps passed |
| Failure | A required step, such as tests, failed |
| Unstable | Build finished but test or report conditions flagged it |
| Aborted | Build was stopped early |

## 11. Troubleshooting

| Problem | What to check |
|---|---|
| Jenkins does not open | `docker ps` shows `jenkins-local` running, port `8083` is free, read `docker logs jenkins-local` |
| Container exits right away | Read `docker logs jenkins-local`, then rebuild with the `build` command |
| Jenkinsfile not found | Repo URL, branch `*/main`, Script Path `jenkins/Jenkinsfile`, file is pushed |
| Git checkout fails | URL, network, repo visibility, credentials |
| Python or `uv` not found | Add it to `Dockerfile.jenkins`, then rebuild the image. Installing it on your PC does not help |
| Tests fail | Read the first pytest error in Console Output, check dependencies and environment variables, reproduce locally, fix and push |
| Auto build does not start | Polling is set, the job has run once, branch is correct, the container can reach GitHub |
| Jenkins settings lost | The `jenkins_home` volume was removed (for example by `down -v`) |

## 12. Best Practices

1. Never commit API keys or passwords. Use Jenkins Credentials.
2. Give Jenkins only the permissions it needs.
3. Do not expose Jenkins publicly without authentication and hardening.
4. Rebuild the image regularly to keep Jenkins and plugins updated, and back up the `jenkins_home` volume.
5. Do not suppress pytest exit codes.
6. The project also has a GitHub Actions workflow. Avoid running duplicate pipelines if both are on.

## 13. Scope

**Done:** GitHub connection, Pipeline from SCM, Python setup, dependency install, `pytest`, SCM polling, build status, and test and coverage reports.

**Future:** Build the application Docker image after tests, push to Amazon ECR, deploy to ECS with Fargate, use AWS Secrets Manager, add notifications and approval gates.

## 14. References

1. https://www.jenkins.io/doc/
2. https://www.jenkins.io/doc/book/pipeline/
3. https://www.jenkins.io/doc/book/installing/docker/
4. https://docs.docker.com/compose/

Update this guide whenever the Jenkinsfile, Dockerfile, plugins, stages or ports change.
