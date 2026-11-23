# Native Windows Jenkins CI Pipeline

## 1. Overview

This guide explains how to run the End-to-End-LLMOps-Project CI pipeline with Jenkins installed directly on Windows. Docker is not needed. Jenkins runs as a Windows service and uses `bat` commands to prepare Python, install dependencies, run tests, and publish reports.

Development happens on the branch `feature/jenkins-windows-ci`. `main` stays unchanged until the pipeline is tested and merged through a GitHub Pull Request.

**What the pipeline does:** when Jenkins detects a new commit, it checks out the code, verifies Python and Git, creates or reuses a virtual environment, installs dependencies, runs pytest, generates JUnit and coverage reports, then publishes and archives them.

**What it does not do:** this is CI only. It does not build a Docker image, push to Amazon ECR, or deploy to Amazon EKS or any cloud. Those can be added later.

```text
Push to GitHub feature branch -> Jenkins detects change -> Checkout
-> Verify Python and Git -> Create/reuse venv -> Install dependencies
-> Run pytest -> Generate JUnit and coverage reports
-> Publish and archive reports -> SUCCESS or FAILURE
```

## 2. Project files

```text
End-to-End-LLMOps-Project/
├── .github/workflows/ci.yml
├── jenkins/            (Jenkinsfile, JENKINS_WINDOWS_CI.md, JENKINS_DOCUMENTATION.md, README.md)
├── tests/              (unit, api, integration, regression, conftest.py)
├── multi_doc_chat/  evaluation/  config/
├── requirements.txt  requirements-dev.txt  pyproject.toml
├── Dockerfile  README.md  .gitignore
```

| File | Purpose |
|---|---|
| `jenkins/Jenkinsfile` | Pipeline definition |
| `requirements.txt` | Application dependencies |
| `requirements-dev.txt` | Development and test dependencies |
| `tests/conftest.py` | Shared pytest fixtures and config |
| `.gitignore` | Excludes venvs, caches, and generated reports |

The Dockerfile and GitHub Actions workflow already exist. This Jenkins job does not use the Dockerfile.

## 3. Prerequisites

Java (for Jenkins), Jenkins, Python 3.12, Git for Windows, and PowerShell or Command Prompt.

```powershell
java -version
python --version
git --version
```

Jenkins should be running at `http://localhost:8080`.

## 4. Jenkins service configuration

Check the service (PowerShell as Administrator):

```powershell
Get-Service Jenkins
sc.exe qc Jenkins
```

In this setup Jenkins runs as `LocalSystem`, with workspace `C:\ProgramData\Jenkins\.jenkins\workspace`.

**Python version:** the machine has several Pythons. In Jenkins, plain `python` returned 3.11.9, while the direct 3.12 executable returned 3.12.10. So the Jenkinsfile sets the full path:

```text
C:\Users\Lenovo\AppData\Local\Programs\Python\Python312\python.exe
```

This path is machine specific. On another machine, update `PYTHON_EXE` in the Jenkinsfile. The Jenkins service account must be able to access this Python and the project workspace.

**Verify the environment:** create a temporary Freestyle job with an **Execute Windows batch command** step:

```bat
where python
python --version
where git
git --version
"C:\Users\Lenovo\AppData\Local\Programs\Python\Python312\python.exe" --version
whoami
```

In this setup, Git worked, the direct Python 3.12 worked, and the service ran as `nt authority\system`. Keep the job for future troubleshooting.

## 5. Required plugins

| Plugin | Purpose |
|---|---|
| Pipeline | Creates and runs Pipeline jobs |
| Git, Git Client | Git repository access |
| JUnit | Shows test results |
| Credentials Binding | Provides stored credentials to builds |
| HTML Publisher | Optional dedicated HTML report link |

Check under **Manage Jenkins → Plugins → Installed plugins** and install anything missing from Available plugins. The Jenkinsfile uses the `junit` and `archiveArtifacts` steps. Archiving HTML alone does not create a dedicated report view, so use HTML Publisher if you want one.

## 6. Jenkinsfile

Script Path must be exactly `jenkins/Jenkinsfile`.

**Environment variables**

| Variable | Purpose |
|---|---|
| `PYTHON_EXE` | Full path to the Python 3.12 executable |
| `PYTHONPATH` | Adds repo root and `multi_doc_chat` to imports |
| `GROQ_API_KEY`, `GOOGLE_API_KEY` | Dummy values for tests with mocked models |
| `LLM_PROVIDER` | Google provider setting used by test config |
| `PIP_CACHE_DIR` | Keeps downloaded pip packages in the workspace |

The API keys are dummies, not real credentials. Tests that call real providers need Jenkins Credentials.

**Stages**

1. **Checkout:** `checkout scm` gets code from the repo and branch set in the job.
2. **Verify Environment:** runs Python and Git. Fails if either cannot run.
3. **Setup Python Environment:** creates `.venv` if missing (`python.exe -m venv .venv`). Later builds reuse it while it stays in the workspace.
4. **Install Dependencies:** `python -m pip install -r requirements.txt`, then `-r requirements-dev.txt`. The pip cache reuses downloaded files, but pip may still check and install on later builds.
5. **Run Tests:** `python -m pytest tests/ --verbose`, also producing JUnit XML, XML coverage, HTML coverage, and a terminal summary.

**Post actions:** `always` publishes JUnit and archives coverage and test files. `success` and `failure` print messages. `cleanup` prints a completion message. The venv and pip cache are kept for reuse.

## 7. Create the Jenkins job

1. Open `http://localhost:8080`, click **New Item**, name it `LLMOps-Windows-CI`, choose **Pipeline**, click **OK**.
2. Under Pipeline, choose **Pipeline script from SCM** and set:

| Setting | Value |
|---|---|
| SCM | Git |
| Repository URL | `https://github.com/i-am-tushaar/End-to-End-LLMOps-Project.git` |
| Credentials | None, if the repo is public |
| Branch Specifier | `*/feature/jenkins-windows-ci` |
| Script Path | `jenkins/Jenkinsfile` |

3. Click **Save**.

During development use the feature branch. Do not point this job at `main` until the pipeline is verified and merged.

## 8. SCM polling

```groovy
triggers {
    pollSCM('H/10 * * * *')
}
```

Jenkins checks the configured branch about every 10 minutes and schedules a build when it finds a relevant change. Notes:

- A build does not necessarily start right after a push.
- Only the configured branch is checked.
- After changing the trigger in the Jenkinsfile, run the job manually once so Jenkins loads it.
- For faster builds, set up a GitHub webhook later. Local Jenkins must be reachable by GitHub for that.

## 9. Run and read results

Open `LLMOps-Windows-CI`, click **Build Now**, open the new build, and select **Console Output**. Expected stages: Checkout, Verify Environment, Setup Python Environment, Install Dependencies, Run Tests. Success ends with `Finished: SUCCESS`, failure with `Finished: FAILURE`. Read the first relevant error, since later ones are often side effects.

**Generated files:** `test-results/results.xml`, `coverage.xml`, `htmlcov/index.html`.

- **JUnit:** the plugin reads `test-results/*.xml` and shows counts and failures on the job and build pages.
- **Coverage:** `coverage.xml` and `htmlcov/**` are archived. Open the HTML report from build artifacts, or configure HTML Publisher for a dedicated link.

## 10. Git workflow

All Windows Jenkins CI work stays on `feature/jenkins-windows-ci`.

```bash
git branch
git status
git add jenkins/Jenkinsfile jenkins/JENKINS_WINDOWS_CI.md .gitignore
git commit -m "ci: add native Windows Jenkins pipeline documentation"
git push origin feature/jenkins-windows-ci
```

Adjust `git add` to the files that changed.

**Before merging, confirm:** the job uses the feature branch, checkout works, Python and Git checks pass, dependencies install, tests pass, JUnit results are published, and coverage reports are archived.

**Merge:** open a Pull Request on GitHub with base `main` and compare `feature/jenkins-windows-ci`, review, merge, then:

```bash
git switch main
git pull origin main
```

Keep the feature branch until the merge is verified.

## 11. Troubleshooting

| Problem | Likely reason | Fix |
|---|---|---|
| Python not recognized | The service has a different PATH from your terminal | Verify the full Python 3.12 path and update `PYTHON_EXE`. Test it in a Jenkins job |
| Git not recognized | Git missing from the service environment | Verify the install and that `C:\Program Files\Git\cmd` is accessible |
| venv creation fails | Python inaccessible to the service, or no `venv` support | Run the direct Python executable in a Jenkins batch job and read the error |
| Slow dependency install | Large AI/ML packages | Keep the pip cache, avoid needless version changes, read install logs |
| Tests fail on API credentials | A test makes a real external call instead of a mock | Inspect the test and fixtures. Dummy keys only for mocked tests. Use Jenkins Credentials for real calls |
| No automatic build | Wrong branch, trigger, or stale Jenkinsfile | Check the branch specifier, the `pollSCM` trigger, run a manual build to load the latest Jenkinsfile, check GitHub access and the Polling Log |

## 12. Security and maintenance

- Never commit real API keys, passwords, or tokens. Use Jenkins Credentials.
- Restrict Jenkins service and workspace permissions.
- Do not expose local Jenkins to the public internet without proper security.
- Keep dependencies documented and version controlled.
- Review failed builds and reports, and keep only the build history you need.

## 13. Future scope: Docker and AWS EKS

```text
GitHub -> Jenkins CI -> Run tests -> Build Docker image
-> Push to Amazon ECR -> Deploy to Amazon EKS -> App running in Kubernetes
```

A Docker image gives a consistent Python runtime across machines, but it does not remove the machine specific Python path from this native Windows Jenkinsfile. That path can go away later by running CI tests in a standard Python Docker container.

## 14. Quick reference

```powershell
Get-Service Jenkins       # check service
Restart-Service Jenkins   # restart
python --version          # check Python
git --version             # check Git
```

```bash
git branch                                  # current branch
git push origin feature/jenkins-windows-ci  # push feature branch
```

Jenkins URL: `http://localhost:8080`

## Summary

This pipeline automates checkout, Python setup, dependency install, testing, and report publishing on native Windows. It is developed on `feature/jenkins-windows-ci` so `main` stays unchanged until it is tested and merged. Docker image creation and AWS EKS deployment are future stages, not part of this CI.