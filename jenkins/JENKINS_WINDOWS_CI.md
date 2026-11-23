# Native Windows Jenkins CI Pipeline

## 1. Overview

This document explains how to run the End-to-End-LLMOps-Project Continuous Integration (CI) pipeline using Jenkins installed directly on a Windows PC.

This setup does **not** require Docker to run Jenkins or execute the CI pipeline. Jenkins runs as a Windows service and uses Windows batch commands (`bat`) to prepare Python, install dependencies, run tests, and publish reports.

The pipeline is being developed on the Git branch:

```text
feature/jenkins-windows-ci
```

The `main` branch is kept unchanged until the Windows CI pipeline has been tested successfully and merged through a GitHub Pull Request.

### What the pipeline does

When Jenkins detects a new commit on the configured branch, it:

1. Checks out the source code from GitHub.
2. Verifies that Python and Git are available.
3. Creates or reuses a Python virtual environment.
4. Installs application and development dependencies.
5. Runs the automated pytest suite.
6. Generates JUnit and coverage reports.
7. Publishes the reports in Jenkins and archives the generated files.

### What this pipeline does not do

This is a CI-only pipeline. It does not build a Docker image, push an image to Amazon ECR, deploy the application to Amazon EKS, or deploy the application to any cloud environment. Docker and AWS EKS deployment can be added in a later CI/CD implementation.

## 2. CI workflow

```text
Developer pushes code
        |
        v
GitHub feature branch
        |
        v
Jenkins detects the change
        |
        v
Checkout source code
        |
        v
Verify Python and Git
        |
        v
Create/reuse Python virtual environment
        |
        v
Install project dependencies
        |
        v
Run pytest test suite
        |
        v
Generate JUnit and coverage reports
        |
        v
Publish and archive reports
        |
        v
Jenkins build: SUCCESS or FAILURE
```

## 3. Project structure

The relevant project structure is:

```text
End-to-End-LLMOps-Project/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── jenkins/
│   ├── Jenkinsfile
│   ├── JENKINS_WINDOWS_CI.md
│   ├── JENKINS_DOCUMENTATION.md
│   └── README.md
│
├── tests/
│   ├── unit/
│   ├── api/
│   ├── integration/
│   ├── regression/
│   └── conftest.py
│
├── multi_doc_chat/
├── evaluation/
├── config/
│
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── Dockerfile
├── README.md
└── .gitignore
```

### Important files

| File | Purpose |
|---|---|
| `jenkins/Jenkinsfile` | Defines the executable Jenkins pipeline |
| `requirements.txt` | Contains application dependencies |
| `requirements-dev.txt` | Contains development and test dependencies |
| `tests/` | Contains automated tests |
| `tests/conftest.py` | Defines shared pytest fixtures and test configuration |
| `.gitignore` | Excludes virtual environments, caches, and generated reports from Git |

The Dockerfile and GitHub Actions workflow are existing project components. This native Windows Jenkins job does not use the Dockerfile.

## 4. Prerequisites

Install and verify the following on the Windows machine:

| Tool | Purpose |
|---|---|
| Java | Runtime required by Jenkins |
| Jenkins | Runs and manages the CI pipeline |
| Python 3.12 | Runs the project and tests |
| Git for Windows | Checks out source code from GitHub |
| PowerShell or Command Prompt | Used to administer and verify the Windows environment |

Useful verification commands:

```powershell
java -version
python --version
git --version
```

The Jenkins service must be running and accessible in a browser. In the current setup, Jenkins is available at:

```text
http://localhost:8080
```

## 5. Jenkins Windows service configuration

### 5.1 Check the service

Open PowerShell as Administrator:

```powershell
Get-Service Jenkins
```

To inspect the service configuration:

```powershell
sc.exe qc Jenkins
```

In the current setup, Jenkins runs as:

```text
LocalSystem
```

The Jenkins service workspace observed during the environment test was:

```text
C:\ProgramData\Jenkins\.jenkins\workspace
```

### 5.2 Python version selection

The machine has more than one Python installation. The default `python` command returned Python 3.11.9 in the Jenkins environment test, while the direct Python 3.12 executable returned Python 3.12.10.

For that reason, the current Jenkinsfile explicitly specifies the Python 3.12 executable:

```text
C:\Users\Lenovo\AppData\Local\Programs\Python\Python312\python.exe
```

This path is machine-specific. A developer using another Windows machine must update `PYTHON_EXE` in the Jenkinsfile to the Python 3.12 executable path on that machine.

The Jenkins service account must have permission to access the selected Python installation and project workspace. The direct Python executable was successfully tested from a Jenkins job in the current environment.

### 5.3 Verify the environment from Jenkins

A temporary Freestyle job can verify the service environment.

Add the build step **Execute Windows batch command** and run:

```bat
echo Checking Python:
where python
python --version

echo Checking Git:
where git
git --version

echo Checking Python 3.12 directly:
"C:\Users\Lenovo\AppData\Local\Programs\Python\Python312\python.exe" --version

echo Checking Jenkins account:
whoami
```

In the current environment test, Jenkins reported:

- Git was available.
- The direct Python 3.12 executable worked.
- The service process ran as `nt authority\system`.

The temporary environment-test job can be retained for future troubleshooting.

## 6. Required Jenkins plugins

The following plugins are used or recommended for this pipeline:

| Plugin | Purpose |
|---|---|
| Pipeline | Creates and runs Pipeline jobs |
| Git | Connects Jenkins jobs to Git repositories |
| Git Client | Provides Git operations used by Jenkins |
| JUnit | Displays JUnit test results |
| Credentials Binding | Makes stored credentials available to builds when needed |
| HTML Publisher | Can display HTML coverage reports in Jenkins |

Check installed plugins through **Manage Jenkins → Plugins → Installed plugins**. Install any missing plugins through the Available plugins tab.

The Jenkinsfile uses the `junit` and `archiveArtifacts` pipeline steps. The HTML Publisher plugin is useful if you later want a dedicated HTML report link on the build page; archiving HTML files alone does not create that dedicated report view.

## 7. Jenkinsfile configuration

The pipeline definition is stored at:

```text
jenkins/Jenkinsfile
```

The Jenkins job must use this exact Script Path.

### 7.1 Environment variables

The current Jenkinsfile defines:

| Variable | Purpose |
|---|---|
| `PYTHON_EXE` | Full path to the Python 3.12 executable |
| `PYTHONPATH` | Adds the repository root and `multi_doc_chat` directory to Python's import path |
| `GROQ_API_KEY` | Dummy value for tests that use mocked model components |
| `GOOGLE_API_KEY` | Dummy value for tests that use mocked model components |
| `LLM_PROVIDER` | Selects the Google provider setting used by the test configuration |
| `PIP_CACHE_DIR` | Stores downloaded pip packages in the Jenkins workspace |

The dummy API keys are not real credentials. Tests that make actual calls to external providers must be handled separately and must use securely stored Jenkins credentials.

### 7.2 Pipeline stages

#### Stage 1: Checkout

```groovy
checkout scm
```

Checks out the source code from the repository and branch configured in the Jenkins job.

#### Stage 2: Verify Environment

Checks Python and Git using Windows batch commands. This stage fails if the required executable cannot be run.

#### Stage 3: Setup Python Environment

Creates a virtual environment if it does not already exist:

```bat
python.exe -m venv .venv
```

The environment is located in the Jenkins workspace:

```text
.venv\Scripts\python.exe
```

Subsequent builds reuse the environment if it remains available in the workspace.

#### Stage 4: Install Dependencies

Installs application dependencies:

```bat
python -m pip install -r requirements.txt
```

Then installs development and test dependencies:

```bat
python -m pip install -r requirements-dev.txt
```

The pip cache is configured through `PIP_CACHE_DIR` to reduce repeated package downloads.

Note: pip may still check and install packages on subsequent builds. The cache reuses downloaded package files; it does not guarantee that dependency installation will be skipped.

#### Stage 5: Run Tests

Runs the test suite:

```bat
python -m pytest tests/ --verbose
```

The Jenkinsfile also generates JUnit XML results, an XML coverage report, an HTML coverage report, and a terminal coverage summary.

### 7.3 Post-build actions

The `post` section runs after the pipeline stages.

- `always`: Attempts to publish JUnit results and archive coverage and test files.
- `success`: Displays a success message when the pipeline succeeds.
- `failure`: Displays a failure message when the pipeline fails.
- `cleanup`: Displays a completion message.

The virtual environment and pip cache are retained for reuse.

## 8. Create the Jenkins Pipeline job

Open Jenkins:

```text
http://localhost:8080
```

Create a new job:

1. Click **New Item**.
2. Enter the job name `LLMOps-Windows-CI`.
3. Select **Pipeline**.
4. Click **OK**.

Under the Pipeline section, select **Pipeline script from SCM**.

Configure the fields:

| Setting | Value |
|---|---|
| Definition | Pipeline script from SCM |
| SCM | Git |
| Repository URL | `https://github.com/i-am-tushaar/End-to-End-LLMOps-Project.git` |
| Credentials | None, if the repository is public |
| Branch Specifier | `*/feature/jenkins-windows-ci` |
| Script Path | `jenkins/Jenkinsfile` |

Click **Save**.

Important: During development, use the feature branch. Do not configure this test job to build `main` until the new pipeline has been verified and merged.

## 9. SCM polling and automatic builds

The Jenkinsfile currently uses:

```groovy
triggers {
    pollSCM('H/10 * * * *')
}
```

This tells Jenkins to check the configured Git branch approximately every ten minutes.

When Jenkins detects a new commit, it schedules a build.

Important points:

- SCM polling does not necessarily start a build immediately after a push.
- Jenkins checks the configured branch, not every branch in the repository.
- A build is normally scheduled only when Jenkins detects a relevant source-control change.
- After changing a Jenkinsfile trigger, run the job manually once so Jenkins can load the updated pipeline definition.

For faster triggering, a GitHub webhook can be configured later. A locally hosted Jenkins instance needs to be reachable by GitHub for a webhook to reach it.

## 10. Run the pipeline

To run the first build:

1. Open `LLMOps-Windows-CI`.
2. Click **Build Now**.
3. Open the newly created build.
4. Select **Console Output**.
5. Follow each stage and inspect any errors.

The expected stages are:

```text
Checkout
Verify Environment
Setup Python Environment
Install Dependencies
Run Tests
```

A successful build should finish with:

```text
Finished: SUCCESS
```

If a stage fails, Jenkins displays:

```text
Finished: FAILURE
```

Read the first relevant error in Console Output. Later errors may simply be consequences of the first failure.

## 11. Test reports and coverage

The pipeline generates these files in the Jenkins workspace:

```text
test-results/
    results.xml

coverage.xml

htmlcov/
    index.html
    ...
```

### JUnit report

The JUnit plugin reads:

```text
test-results/*.xml
```

It displays test counts and failures on the Jenkins job and build pages.

### Coverage reports

The pipeline archives:

```text
coverage.xml
htmlcov/**
```

The HTML report can be opened from the archived build artifacts. To display it through a dedicated HTML report link on the Jenkins build page, configure the HTML Publisher plugin in the Jenkinsfile.

## 12. Git branch workflow

All new Windows Jenkins CI work is developed on:

```text
feature/jenkins-windows-ci
```

The existing `main` branch is kept unchanged during development.

### 12.1 Check the current branch

```bash
git branch
```

### 12.2 Commit the changes

```bash
git status
git add jenkins/Jenkinsfile jenkins/JENKINS_WINDOWS_CI.md .gitignore
git commit -m "ci: add native Windows Jenkins pipeline documentation"
```

Adjust the `git add` command if only some of these files have changed.

### 12.3 Push the feature branch

```bash
git push origin feature/jenkins-windows-ci
```

### 12.4 Verify the pipeline

Before merging, confirm that:

- The Jenkins job uses the feature branch.
- Checkout succeeds.
- Python and Git verification succeeds.
- Dependencies install successfully.
- Automated tests pass.
- JUnit results are published.
- Coverage reports are archived.

### 12.5 Merge through a Pull Request

After successful verification:

1. Open the GitHub repository.
2. Create a Pull Request.
3. Set the base branch to `main`.
4. Set the compare branch to `feature/jenkins-windows-ci`.
5. Review the changes.
6. Merge the Pull Request.
7. Update your local main branch:

```bash
git switch main
git pull origin main
```

Do not delete the feature branch until the merge has been verified.

## 13. Troubleshooting

### Python is not recognized

**Possible reason:** Jenkins runs as a Windows service and may have a different PATH from your interactive terminal.

**Solution:** Verify the full Python 3.12 path and update `PYTHON_EXE` in the Jenkinsfile. Test the executable from a Jenkins job.

### Git is not recognized

**Possible reason:** Git is missing from the environment visible to the Jenkins service.

**Solution:** Verify the Git installation and ensure its `cmd` directory is accessible:

```text
C:\Program Files\Git\cmd
```

### Python virtual environment creation fails

**Possible reason:** The Python installation is inaccessible to the Jenkins service or lacks the required `venv` support.

**Solution:** Run the direct Python executable from a Jenkins batch job and inspect the error.

### Dependency installation takes a long time

**Possible reason:** The project includes large AI/ML dependencies, and pip may need to download and install them.

**Solution:** Retain the pip cache, avoid unnecessarily changing dependency versions, and inspect the package installation logs.

### Tests fail because of API credentials

**Possible reason:** A test is making a real external API call instead of using a mock.

**Solution:** Inspect the test and its fixtures. Use dummy credentials only for tests that are genuinely mocked. Store real credentials in Jenkins Credentials if external API tests are intentionally required.

### Jenkins does not automatically trigger a build

Check the job's branch specifier, the `pollSCM` trigger in the Jenkinsfile, whether the latest Jenkinsfile has been loaded by a manual build, whether Jenkins can access GitHub, and the job's Polling Log if available.

## 14. Security and maintenance

- Do not commit real API keys, passwords, or access tokens.
- Use Jenkins Credentials for real secrets.
- Keep the Jenkins service and workspace permissions appropriately restricted.
- Do not expose a local Jenkins instance directly to the public internet without proper security controls.
- Keep application and development dependencies documented and version-controlled.
- Review generated test reports and failed builds.
- Retain only the build history needed for debugging and audit purposes.

## 15. Future scope: Docker and AWS EKS

The current pipeline is limited to native Windows CI.

The planned future deployment workflow is:

```text
GitHub
   |
   v
Jenkins CI
   |
   v
Run automated tests
   |
   v
Build application Docker image
   |
   v
Push image to Amazon ECR
   |
   v
Deploy image to Amazon EKS
   |
   v
Application running in Kubernetes
```

Building the application Docker image will provide a consistent Python runtime for the application across different machines. It does not automatically remove the machine-specific Python path from this native Windows Jenkinsfile. That path can later be eliminated by running CI tests in a standardized environment, such as a Python Docker container.

## 16. Quick reference commands

### Check Jenkins service

```powershell
Get-Service Jenkins
```

### Restart Jenkins

```powershell
Restart-Service Jenkins
```

### Check Python

```powershell
python --version
```

### Check Git

```powershell
git --version
```

### Check current Git branch

```bash
git branch
```

### Push feature branch

```bash
git push origin feature/jenkins-windows-ci
```

### Open Jenkins

```text
http://localhost:8080
```

## Final summary

This native Windows Jenkins CI pipeline automates source-code checkout, Python environment setup, dependency installation, automated testing, and report publishing.

It is developed independently on `feature/jenkins-windows-ci` so that the existing `main` branch remains unchanged until the new pipeline is tested and merged.

Docker image creation and AWS EKS deployment are separate future stages and are not part of this current CI implementation.
