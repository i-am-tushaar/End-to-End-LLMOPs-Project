# Windows Jenkins CI/CD Pipeline to Amazon ECR (Short Guide)

**Project:** End to End LLMOps | **Repo:** `i-am-tushaar/End-to-End-LLMOPs-Project`

> **Public copy:** Account specific values are replaced with placeholders. Use your own values when following the steps.

| Placeholder | Meaning |
|---|---|
| `<AWS_ACCOUNT_ID>` | Your 12 digit AWS account ID |
| `<UV_PATH>` | Full path to `uv.exe` on your Jenkins machine |

## 1. What This Is

A Jenkins pipeline on native Windows that tests the app, builds its Docker image, pushes the image to Amazon ECR and checks that the image arrived.

**Scope:** It publishes the image to ECR only. It does not deploy or run the app on ECS or EKS. Deployment is a separate phase.

```text
GitHub → Jenkins (Windows) → Tests → Docker build → AWS login → Push to ECR → Verify in ECR
```

## 2. Project Details

| Item | Value |
|---|---|
| Jenkins job | `LLMOps-Windows-ECR-CICD` |
| Jenkinsfile | `jenkins/windows-cicd-ecr/Jenkinsfile` |
| Jenkins URL | `http://localhost:8080` |
| AWS region | `eu-north-1` |
| AWS CLI profile | `jenkins-eks` (the name says EKS, but this pipeline uses it for ECR) |
| ECR repository | `end-to-end-llmops` |
| ECR image URI | `<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/end-to-end-llmops` |
| Image tag | `latest` |

## 3. Before You Start

The Windows machine running Jenkins needs:

1. Jenkins running as a Windows service and Git available to it.
2. Docker Desktop running with the Linux container engine.
3. UV, a compatible Python version and AWS CLI.
4. The `jenkins-eks` AWS profile configured for the Jenkins service account.
5. IAM permissions to describe the ECR repository and push images.

**Important:** Jenkins runs as `NT AUTHORITY\SYSTEM`. Tools and credentials set up for your own Windows user are not available to SYSTEM automatically. Docker, the AWS profile, the Roles Anywhere credential process and the Docker ECR credential helper must all work for SYSTEM.

## 4. Jenkinsfile Settings

```groovy
environment {
    UV_EXE = '<UV_PATH>'
    AWS_PROFILE = 'jenkins-eks'
    AWS_REGION = 'eu-north-1'
    DOCKER_HOST = 'npipe:////./pipe/dockerDesktopLinuxEngine'
    DOCKER_IMAGE = 'end-to-end-llmops:latest'
}
```

| Variable | Purpose |
|---|---|
| `UV_EXE` | Full path to the UV executable. It is machine specific, so update it if UV moves |
| `AWS_PROFILE` | AWS CLI profile Jenkins uses |
| `AWS_REGION` | Region that holds the ECR repository |
| `DOCKER_HOST` | Docker Desktop Linux engine endpoint |
| `DOCKER_IMAGE` | Local image name and tag |

Never put AWS keys, private keys, passwords, API keys or `.env` values in the Jenkinsfile.

## 5. How Login Works

**AWS:** The `jenkins-eks` profile uses AWS IAM Roles Anywhere, so Jenkins gets temporary credentials for the role `JenkinsEKSDeploymentRole` using a certificate. No permanent keys are stored.

**Docker to ECR:** The Amazon ECR credential helper gives Docker a login token whenever it pushes, so no separate `docker login` is needed. Add this to the SYSTEM account's Docker config at `C:\Windows\System32\config\systemprofile\.docker\config.json`:

```json
{
  "credHelpers": {
    "<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com": "ecr-login"
  }
}
```

The helper itself is at `C:\Program Files\Docker\Docker\resources\bin\docker-credential-ecr-login.exe`.

Never commit credential files or private keys, and never put them in the Docker image.

## 6. The 11 Pipeline Stages

| # | Stage | What it does | Key command |
|---|---|---|---|
| 1 | Check UV and Python | Confirms Jenkins can reach UV and Python | `uv` version check |
| 2 | Run Pytest Tests | Installs locked dependencies and runs tests. Fails the build if any test fails | `uv sync --locked`, then `uv run --locked pytest tests/ -v` |
| 3 | Check Docker | Confirms the Docker CLI works | `docker --version` |
| 4 | Check Docker Engine | Confirms Jenkins can reach Docker Desktop | `docker info` |
| 5 | Build Docker Image | Builds the app image from the root `Dockerfile`, then lists it | `docker build -t "end-to-end-llmops:latest" -f Dockerfile .` |
| 6 | Check AWS CLI | Confirms AWS CLI is available | `aws --version` |
| 7 | Check AWS Authentication | Confirms the profile returns an AWS identity | `aws sts get-caller-identity --profile jenkins-eks --region eu-north-1` |
| 8 | Verify ECR Access | Confirms the repository exists and can be described | `aws ecr describe-repositories --repository-names end-to-end-llmops --region eu-north-1 --profile jenkins-eks` |
| 9 | Tag Docker Image | Adds the ECR address to the local image. It does not upload anything | `docker tag end-to-end-llmops:latest <ECR_URI>:latest` |
| 10 | Push to ECR | Uploads the image layers | `docker push <ECR_URI>:latest` |
| 11 | Verify Image in ECR | Confirms the `latest` tag exists in ECR | `aws ecr describe-images --repository-name end-to-end-llmops --image-ids imageTag=latest --region eu-north-1 --profile jenkins-eks` |

`<ECR_URI>` means `<AWS_ACCOUNT_ID>.dkr.ecr.eu-north-1.amazonaws.com/end-to-end-llmops`.

## 7. How to Run It

1. Start Docker Desktop and confirm the Linux engine is running.
2. Confirm the Jenkins Windows service is running.
3. Open `http://localhost:8080` and the job `LLMOps-Windows-ECR-CICD`.
4. Click **Build Now**, then open **Console Output**.
5. Confirm the end shows `Finished: SUCCESS`.

**After changing the Jenkinsfile:**

```cmd
git add jenkins/windows-cicd-ecr/Jenkinsfile
git commit -m "Describe the pipeline change"
git push
```

Then run the job again.

## 8. Last Recorded Run

All 11 stages passed, with 166 tests passed. The image `end-to-end-llmops:latest` appeared in ECR with status `ACTIVE`, and the Jenkins result was `SUCCESS`.

## 9. Troubleshooting

| Problem | Likely cause | What to check |
|---|---|---|
| UV not found | Wrong `UV_EXE` path or SYSTEM cannot read it | Confirm the file exists at the configured path |
| Docker command not found | Docker CLI is not visible to the Jenkins service | Confirm Docker Desktop is installed and SYSTEM can run `docker` |
| Cannot connect to Docker Engine | Docker Desktop is stopped or `DOCKER_HOST` is wrong | Start Docker Desktop, check the Linux engine and the endpoint |
| AWS authentication fails | The profile or Roles Anywhere setup is not available to SYSTEM | Test the profile as SYSTEM. Never print keys in logs |
| ECR access denied | The role lacks ECR permissions, or wrong repo or region | Check the identity, region, repo name and IAM policy |
| Docker push authentication fails | Docker cannot run the ECR helper | Check the helper file and SYSTEM `config.json`, and that the registry host matches |
| ECR verification fails | The push did not finish, or wrong repo, region or tag | Re-read the push stage output and the verify command |

## 10. Security and Maintenance

1. Keep `.env` out of Git and out of the Docker build context.
2. Restrict access to Jenkins settings, AWS credential files and the SYSTEM account.
3. Give the Jenkins IAM role only the permissions it needs.
4. Commit the UV lock file so builds use the same dependency versions.
5. Consider turning on ECR image scanning and a retention policy.
6. `latest` can be overwritten. For traceable releases, also push a unique tag such as the Git commit SHA.

## 11. Next Phase: ECS Deployment

ECR only stores the image. ECS runs it. Completing this pipeline does not deploy the app. The next phase is a separate deployment pipeline:

1. Create an ECS cluster.
2. Create a task definition that points to the ECR image.
3. Set up the task execution role and application secrets.
4. Create an ECS service.
5. Deploy and verify the running app.