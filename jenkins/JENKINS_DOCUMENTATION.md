# Jenkins CI Pipeline Documentation

## 1. Purpose and scope

This document explains how to run Jenkins for the End-to-End LLMOps project, both **with Docker** and **without Docker**.

The current CI pipeline connects Jenkins to GitHub, checks out code, prepares Python, installs dependencies, runs `pytest`, and publishes configured test/coverage reports. SCM polling checks the repository for new commits.

**Important distinction:** Docker can be used to run the Jenkins server. Separately, Docker can be used by a pipeline to build the application image. This document's current pipeline is primarily a test CI pipeline; AWS deployment and ECR/ECS stages are future enhancements unless separately implemented.

## 2. Project details

| Setting | Value |
|---|---|
| Repository | https://github.com/i-am-tushaar/End-to-End-LLMOPs-Project |
| Branch | `main` |
| Jenkins folder | `jenkins/` |
| Pipeline file | `jenkins/Jenkinsfile` |
| Job type | Pipeline |
| Definition | Pipeline script from SCM |
| SCM polling | `H/5 * * * *` (approximately every 5 minutes) |
| Docker Jenkins URL | `http://localhost:8083` |
| Native Jenkins default URL | `http://localhost:8080` |

Typical Jenkins folder:

```text
jenkins/
├── Dockerfile.jenkins
├── docker-compose.jenkins.yml
├── plugins.txt
└── Jenkinsfile
```

## 3. Jenkins concepts

| Term | Meaning |
|---|---|
| Controller | Jenkins service that manages jobs and pipelines |
| Agent | Machine/environment where pipeline steps execute |
| Job | A configured task in Jenkins |
| Pipeline | Ordered automation stages |
| Jenkinsfile | File that defines a pipeline as code |
| Stage | Major phase, such as Checkout or Run Tests |
| Step | Individual command/action inside a stage |
| Workspace | Directory where Jenkins checks out and works with code |
| SCM | Source Code Management, such as Git |
| SCM polling | Periodic check for source-code changes |

## 4. Overall CI workflow

```text
Developer changes code
        |
        v
Commit and push to GitHub (main)
        |
        v
Jenkins checks GitHub using SCM polling
        |
        v
New commit detected
        |
        v
Checkout source code
        |
        v
Prepare Python environment
        |
        v
Install dependencies
        |
        v
Run pytest
        |
        +--------------------+
        |                    |
     Tests pass           Tests fail
        |                    |
        v                    v
   Build success        Build failure
        |
        v
Publish configured test/coverage reports
```

1. A developer commits and pushes a change.
2. Jenkins periodically checks the configured GitHub branch.
3. When a change is detected, Jenkins starts the pipeline.
4. Jenkins checks out the latest source code.
5. It prepares the Python environment and installs dependencies.
6. It runs the automated tests using `pytest`.
7. A test failure should fail the Jenkins build.
8. Jenkins publishes configured reports for review.

## 5. Prerequisites

Common requirements:
- Jenkins and a Java runtime supported by the Jenkins release.
- Git.
- Python version required by the current pipeline.
- Access to the GitHub repository.
- Network access to download dependencies.

For Docker setup:
- Docker Desktop (Windows/macOS) or Docker Engine (Linux).
- Docker Compose.

**Operating-system note:** The existing project pipeline uses Linux shell commands such as `sh` and may use Linux paths. It works on a Linux Jenkins agent, including a Linux-based Jenkins container. A native Windows agent needs Windows `bat`/PowerShell commands and Windows paths, or it must use a Linux agent.

---

# Part A: Jenkins with Docker

## 6. Install and start Jenkins using Docker

### Step 1: Install Docker Desktop

Install Docker Desktop from https://www.docker.com/products/docker-desktop/. Start it and wait until its engine is running.

Verify in PowerShell:

```powershell
docker --version
docker compose version
```

### Step 2: Review the Jenkins files

- `Dockerfile.jenkins`: Defines the custom Jenkins image and tools installed in it.
- `docker-compose.jenkins.yml`: Defines how the Jenkins container is built and started.
- `plugins.txt`: Lists Jenkins plugins to install in the custom image.
- `Jenkinsfile`: Defines the project's CI pipeline.

### Step 3: Build the Jenkins image

Run from the project root:

```powershell
docker compose -f jenkins/docker-compose.jenkins.yml build
```

### Step 4: Start Jenkins

```powershell
docker compose -f jenkins/docker-compose.jenkins.yml up -d
docker ps
```

The local container is named `jenkins-local`.

### Step 5: Unlock Jenkins

Open:

```text
http://localhost:8083
```

If the initial administrator password is requested:

```powershell
docker exec jenkins-local cat /var/jenkins_home/secrets/initialAdminPassword
```

Copy the password into the setup screen.

### Step 6: Complete the initial setup

1. Install suggested plugins or the plugins required by the pipeline.
2. Create the Jenkins administrator account.
3. Confirm the Jenkins URL.
4. Finish setup and open the dashboard.

### Step 7: Verify Jenkins

```powershell
docker ps
docker logs jenkins-local
```

## 7. Understand the Docker configuration

### `Dockerfile.jenkins`

Defines the custom Jenkins image. Depending on its current contents, it installs tools needed by the pipeline, such as Python, Git, `curl`, and Docker CLI. A custom image makes the Jenkins environment more repeatable.

### `docker-compose.jenkins.yml`

The local configuration maps host port `8083` to Jenkins port `8080`, stores Jenkins data in a named `jenkins_home` volume, and may mount the Docker socket and a workspace directory.

| Configuration | Purpose |
|---|---|
| `container_name` | Names the container `jenkins-local` |
| `ports` | Makes Jenkins available on host port `8083` |
| `jenkins_home` | Persists Jenkins settings, jobs, plugins and build history |
| Docker socket mount | Allows Jenkins to communicate with the host Docker engine |
| Workspace mount | Makes the mounted project directory available inside the container |

**Security warning:** Access to `/var/run/docker.sock`, privileged mode, or running Jenkins as root can give Jenkins broad control over the host. Keep this local setup restricted to a trusted machine. Do not expose it directly to the public internet.

### Useful Docker commands

Run from the project root:

```powershell
# Start
docker compose -f jenkins/docker-compose.jenkins.yml up -d

# Stop and remove container (named data volume is preserved)
docker compose -f jenkins/docker-compose.jenkins.yml down

# Restart
docker compose -f jenkins/docker-compose.jenkins.yml restart

# Logs
docker logs jenkins-local

# Open a shell in the container
docker exec -it jenkins-local bash
```

Do not use `docker compose down -v` unless you intentionally want to delete the Jenkins data volume and its stored configuration.

---

# Part B: Jenkins without Docker

## 8. When Docker is not used

Jenkins can be installed directly on Windows or Linux. In this setup Jenkins runs as a native service/process, and jobs execute on the configured machine or agent. Docker Desktop and a Jenkins container are not required.

Python, Git and other pipeline tools must be installed and available to the Jenkins service account or agent.

## 9. Install Jenkins directly on Windows

### Step 1: Install Java

Install a Java runtime supported by the Jenkins release. Check the current Jenkins requirements; Java 21 is suitable for current releases that support it.

Verify:

```powershell
java -version
```

### Step 2: Install Git

Install Git for Windows from https://git-scm.com/downloads.

```powershell
git --version
```

### Step 3: Install Python

Install the Python version required by the current Jenkinsfile. The test-only configuration discussed for this project used Python 3.12; check the actual Jenkinsfile before selecting a version.

```powershell
python --version
py --version
```

### Step 4: Install Jenkins

1. Visit https://www.jenkins.io/download/.
2. Select the Windows installer for the required Jenkins release.
3. Run the installer and follow the wizard.
4. Configure the Java location and service account if prompted.
5. Complete the installation.

Open the Jenkins dashboard, commonly:

```text
http://localhost:8080
```

If port `8080` is already in use, configure another port.

### Step 5: Unlock Jenkins

The initial password for a Windows service installation is commonly located at:

```text
C:\ProgramData\Jenkins\.jenkins\secrets\initialAdminPassword
```

The exact path can differ based on the installer and `JENKINS_HOME`. Open the file, copy the password and paste it into the Jenkins unlock page.

### Step 6: Complete setup

1. Install suggested or required plugins.
2. Create an administrator account.
3. Confirm the Jenkins URL.
4. Finish setup.

### Step 7: Make tools available to the Jenkins service

The Jenkins service may run under a different Windows account from your personal login. Confirm that the service account can access Git, Python, `pip`, `uv` (if used), the workspace and required environment variables. Restart the service after changing system environment variables.

## 10. Windows pipeline compatibility

The current Linux-oriented pipeline may contain commands like:

```groovy
sh 'python --version'
```

A native Windows agent does not support `sh` by default. Use `bat` or PowerShell commands and Windows paths, or run the existing Linux Jenkinsfile on a Linux agent.

Illustrative Windows-compatible starting point:

```groovy
pipeline {
    agent any

    triggers {
        pollSCM('H/5 * * * *')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Verify Tools') {
            steps {
                bat 'python --version'
                bat 'git --version'
            }
        }

        stage('Create Virtual Environment') {
            steps {
                bat 'python -m venv .venv'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat '.venv\\Scripts\\python.exe -m pip install --upgrade pip'
                bat '.venv\\Scripts\\python.exe -m pip install -r requirements.txt'
                bat '.venv\\Scripts\\python.exe -m pip install pytest pytest-cov'
            }
        }

        stage('Run Tests') {
            steps {
                bat '.venv\\Scripts\\python.exe -m pytest tests -v'
            }
        }
    }
}
```

This is an example, not a verified drop-in replacement for the complete project Jenkinsfile. Reconcile dependency exclusions, environment variables, test configuration, report publishing and cleanup before using it.

**Alternative:** Install Jenkins natively on Windows but configure a Linux agent to run the existing Linux-oriented pipeline. This avoids converting the pipeline's shell commands.

## 11. Install Jenkins directly on Linux

For Linux, install a Java version supported by the selected Jenkins release, then follow the official instructions for your distribution:

https://www.jenkins.io/doc/book/installing/

Start and enable the Jenkins service, open the Jenkins web interface, unlock it, install plugins, and ensure Git/Python and other required tools are available on the agent. A Linux agent can run the existing Linux-oriented pipeline without converting `sh` commands.

---

# Part C: Configure and run the pipeline

## 12. Jenkins plugins

Common plugins used by pipelines include:

| Plugin | Purpose |
|---|---|
| Pipeline | Pipeline jobs |
| Git | Git repository integration |
| Git client | Git operations used by Jenkins |
| Pipeline: Stage View | Visual stage view |
| JUnit | Displays JUnit XML test results |
| Credentials | Secure credential storage |
| Timestamper | Adds timestamps to console output |

Install plugins required by the pipeline. Some may already be installed.

## 13. Create a Pipeline job

These steps apply to both Docker-based Jenkins and native Jenkins.

1. Open the Jenkins dashboard.
2. Select **New Item**.
3. Enter a job name, for example `LLMOps-CI-CD`.
4. Select **Pipeline**, then select **OK**.
5. Find the **Pipeline** section.
6. Set **Definition** to `Pipeline script from SCM`.
7. Set **SCM** to `Git`.
8. Enter the repository URL:

```text
https://github.com/i-am-tushaar/End-to-End-LLMOPs-Project.git
```

9. Set the branch specifier:

```text
*/main
```

10. Set **Script Path**:

```text
jenkins/Jenkinsfile
```

11. Save the job.

For a public repository, checkout may work without credentials. For a private repository, create a Jenkins credential and select it in the job configuration.

### Run the first build

1. Open the job.
2. Select **Build Now**.
3. Open the build number.
4. Select **Console Output**.
5. Check that checkout, environment setup, dependency installation and tests complete successfully.

## 14. Understand the Jenkinsfile

The Jenkinsfile defines the pipeline as code.

| Syntax | Meaning |
|---|---|
| `pipeline` | Defines the pipeline |
| `agent` | Where the pipeline runs |
| `environment` | Environment variables |
| `options` | Pipeline behavior settings |
| `triggers` | Automatic triggers |
| `stages` | Groups pipeline phases |
| `stage` | One phase |
| `steps` | Commands/actions in a stage |
| `post` | Actions after pipeline/stage completion |

Main stages in the project:

1. **Checkout:** Retrieves source code from the configured repository and branch.
2. **Setup Python Environment:** Prepares the Python runtime and virtual environment.
3. **Install Dependencies:** Installs project and test dependencies.
4. **Run Tests:** Executes automated tests using `pytest`.
5. **Publish Reports:** Publishes JUnit results and archives coverage reports when configured.

Do not use `|| true` on the pytest command. It can hide test failures and incorrectly let the build appear successful.

## 15. Automatic triggering with SCM polling

The configured trigger is:

```groovy
triggers {
    pollSCM('H/5 * * * *')
}
```

Jenkins checks the configured source repository approximately every five minutes and starts a build when it detects a change.

Cron fields:

```text
MINUTE HOUR DAY-OF-MONTH MONTH DAY-OF-WEEK
```

| Expression | Meaning |
|---|---|
| `* * * * *` | Every minute |
| `H/5 * * * *` | Approximately every five minutes |
| `H/10 * * * *` | Approximately every ten minutes |
| `H/15 * * * *` | Approximately every fifteen minutes |

`H` lets Jenkins choose a consistent hashed time for the job, spreading load across jobs.

### `pollSCM` versus `cron`

| `pollSCM` | `cron` |
|---|---|
| Checks source control for changes | Runs on a schedule |
| Builds when a change is detected | Runs even if code did not change |
| Useful for CI after commits | Useful for scheduled tasks |

For this project, SCM polling is appropriate because the goal is to test new code changes.

### Verify automatic triggering

1. Edit a tracked file, such as `README.md`.
2. Commit and push the change to `main`.
3. Keep Jenkins running.
4. Wait for the next polling check.
5. Confirm that a new build starts in Jenkins.

Polling is not an instant trigger. It may take several minutes to detect a push.

## 16. Understand build results and reports

| Status | Meaning |
|---|---|
| Success | Required pipeline steps completed successfully |
| Failure | A required step, such as tests, failed |
| Unstable | The build completed but configured test/report conditions marked it unstable |
| Aborted | The build was stopped before completion |

Use **Console Output** to locate errors. If JUnit publishing is configured, open the test result link. If coverage archiving is configured, open the archived coverage report/artifact.

---

# Part D: Troubleshooting and best practices

## 17. Common problems

### Jenkins does not open

- Confirm the Jenkins service/container is running.
- Check whether the configured port is already in use.
- For Docker:

```powershell
docker ps
docker logs jenkins-local
```

- For native Windows, check the Jenkins service in Windows Services.

### Jenkins cannot find the Jenkinsfile

Check the repository URL, branch (`*/main`), Script Path (`jenkins/Jenkinsfile`), and whether the file has been committed and pushed.

### Git checkout fails

Check the repository URL, network access, repository visibility and Jenkins credentials. Private repositories require suitable credentials.

### Python or `uv` is not found

The tool may not be installed in the Jenkins execution environment or available to the Jenkins service account. Verify it from the same agent that executes the pipeline. Installing it on your personal computer does not install it inside a Jenkins container or remote agent.

### `sh` is not recognized

A Linux-oriented Jenkinsfile is running on a native Windows agent. Use a Linux agent or convert shell commands to Windows `bat`/PowerShell commands.

### Tests fail

1. Open the failed build's Console Output.
2. Find the first relevant Python or pytest error.
3. Check dependencies, environment variables, import paths and test configuration.
4. Reproduce the failing command locally if possible.
5. Fix the issue and push a new commit.

### Automatic build does not start

Check that SCM polling is configured, the job has run after the trigger was added, the correct branch is monitored, the commit was pushed to that branch, Jenkins is running, and Jenkins can reach GitHub.

## 18. Useful Docker commands

Docker-only commands:

```powershell
docker ps
docker logs jenkins-local
docker exec -it jenkins-local bash
docker exec jenkins-local docker --version
docker compose -f jenkins/docker-compose.jenkins.yml down
docker compose -f jenkins/docker-compose.jenkins.yml up -d
```

The Docker CLI check applies only if Docker CLI is installed in the Jenkins image. Docker access also depends on socket configuration.

## 19. Security and best practices

- Never commit API keys, passwords or tokens to Git.
- Store secrets in Jenkins Credentials or an appropriate secrets manager.
- Give Jenkins and its agents only the permissions they need.
- Do not expose a local Jenkins server publicly without authentication and network/security hardening.
- Keep Jenkins and plugins updated.
- Persist and back up Jenkins home data.
- Keep test failures visible; do not suppress pytest exit codes.
- Use separate agents/environments when operating systems or tools differ.
- Review Docker socket access carefully because it can grant broad control over the host.

## 20. Jenkins and GitHub Actions

This project already has a GitHub Actions workflow. Jenkins is an additional CI/CD automation tool used to learn and implement an alternative pipeline.

| GitHub Actions | Jenkins |
|---|---|
| GitHub-hosted automation platform | Jenkins server that you manage |
| Workflow files in `.github/workflows/` | Pipeline can be defined in a `Jenkinsfile` |
| GitHub provides hosted runners | You configure Jenkins agents |
| Direct GitHub event integration | Integrates with many source-control systems and tools |

Both can automate testing, building and deployment. Using both is not mandatory. If both are enabled, avoid unintentionally running duplicate pipelines.

## 21. Current implementation and future enhancements

Current CI scope:
- Jenkins connected to the GitHub repository.
- Pipeline configured using Pipeline script from SCM.
- Python environment preparation.
- Dependency installation.
- Automated `pytest` execution.
- SCM polling for repository changes.
- Build success/failure reporting.
- Test and coverage report publishing where configured.

Possible future enhancements:
- Build the application Docker image after tests pass.
- Add image tagging and image validation.
- Push the image to Amazon ECR.
- Deploy to Amazon ECS with AWS Fargate.
- Store deployment secrets in AWS Secrets Manager.
- Add build notifications and approval gates.

These are future enhancements, not completed functionality unless implemented and verified.

## 22. Quick start

### With Docker

From the project root:

```powershell
docker compose -f jenkins/docker-compose.jenkins.yml build
docker compose -f jenkins/docker-compose.jenkins.yml up -d
```

Open `http://localhost:8083`.

### Without Docker on Windows

1. Install a Jenkins-supported Java runtime.
2. Install Git and Python.
3. Install Jenkins using the official Windows installer.
4. Open Jenkins, commonly at `http://localhost:8080`.
5. Unlock Jenkins and install required plugins.
6. Create a Pipeline job connected to the GitHub repository.
7. Use a Windows-compatible Jenkinsfile with `bat` commands, or configure a Linux agent for the existing Linux-oriented Jenkinsfile.

### Run the pipeline

1. Open the Jenkins job.
2. Select **Build Now** for a manual build.
3. For automatic builds, push a commit to the configured GitHub branch.
4. Wait for SCM polling to detect the change.
5. Review Console Output, test results and coverage reports.

## 23. Official references

- Jenkins documentation: https://www.jenkins.io/doc/
- Jenkins installation: https://www.jenkins.io/doc/book/installing/
- Jenkins Pipeline: https://www.jenkins.io/doc/book/pipeline/
- Pipeline syntax: https://www.jenkins.io/doc/book/pipeline/syntax/
- Git plugin: https://plugins.jenkins.io/git/
- Docker documentation: https://docs.docker.com/
- Docker Compose: https://docs.docker.com/compose/

---

**Maintenance:** Update this document whenever the Jenkinsfile, Docker configuration, plugin list, pipeline stages, ports or installation procedure changes.
