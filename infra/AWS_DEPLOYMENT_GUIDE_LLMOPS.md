# Deploying the End-to-End LLMOps RAG Application to AWS

This guide documents the deployment of the FastAPI RAG application using
**Docker, Amazon ECR, Amazon ECS on AWS Fargate, AWS CloudFormation, AWS
Secrets Manager, IAM, VPC networking, and CloudWatch Logs**.

> **Deployment model:** ECS Fargate, not EC2. AWS manages the underlying
> compute hosts. The application runs in a Docker container.
>
> **Deployment values documented here:** Region `eu-north-1`, account
> `452975373208`, ECR repository `llmopsrepolive`, ECS cluster
> `llmops-live-cluster`, ECS service `llmops-service`, task family
> `llmops-task`, container port `8080`.

## 1. Architecture overview

Deployment flow:

1.  Build the application Docker image locally.
2.  Push the image to Amazon ECR.
3.  Register an ECS task definition that specifies the image, CPU,
    memory, port, environment variables, secrets, execution role, and
    logging.
4.  ECS launches the task on AWS Fargate in a public subnet.
5.  The task receives a public IP address.
6.  A security group permits inbound TCP traffic on port `8080` from the
    configured client IP range.
7.  Users access the FastAPI app at `http://PUBLIC_IP:8080` and Swagger
    UI at `http://PUBLIC_IP:8080/docs`.

  -----------------------------------------------------------------------
  AWS service                         Role
  ----------------------------------- -----------------------------------
  CloudFormation                      Creates infrastructure from
                                      `infra/cloudformation.yml`

  ECR                                 Stores Docker images

  ECS                                 Schedules and manages the container

  Fargate                             Runs the container without managing
                                      EC2 instances

  IAM                                 Controls deployment and task
                                      permissions

  Secrets Manager                     Stores API keys

  VPC, subnet, internet gateway,      Provides networking
  route table                         

  Security Group                      Controls inbound access to port
                                      8080

  CloudWatch Logs                     Stores container logs
  -----------------------------------------------------------------------

**Fargate vs EC2:** With EC2, you manage virtual machines. With Fargate,
you provide the container image and task configuration, while AWS
manages the underlying compute. This project uses Fargate. EC2-related
resources in the template are networking resources, not an EC2
application server.

## 2. Deployment files

``` text
End-to-End-LLMOPs-Project/
├── Dockerfile
├── .dockerignore
├── .env
├── .env.example
├── requirements.txt
├── infra/
│   ├── cloudformation.yml
│   └── task-definition.json
└── multi_doc_chat/
    └── ...
```

  -----------------------------------------------------------------------
  File                                Purpose
  ----------------------------------- -----------------------------------
  `Dockerfile`                        Defines how to build the
                                      application image

  `.dockerignore`                     Excludes unnecessary files from the
                                      Docker build context

  `.env`                              Local configuration and secrets; do
                                      not commit

  `.env.example`                      Documents variable names with
                                      placeholder values

  `requirements.txt`                  Python dependencies

  `infra/cloudformation.yml`          AWS infrastructure as code

  `infra/task-definition.json`        ECS container/task runtime
                                      configuration
  -----------------------------------------------------------------------

The repository's actual YAML and JSON files are the source of truth for
exact resource declarations. This guide documents the deployed
configuration and workflow.

## 3. Application model configuration

The deployed application uses:

-   LLM: Groq, `openai/gpt-oss-20b`
-   Embeddings: Hugging Face, `sentence-transformers/all-MiniLM-L6-v2`
-   Vector store: FAISS
-   Retriever: MMR, `top_k: 10`, `fetch_k: 20`, `lambda_mult: 0.5`
-   API: FastAPI on port `8080`

Google model integrations were removed from the active `model_loader.py`
and `config.yaml`. The active model loader uses Groq for the LLM and
Hugging Face for embeddings.

### Example `.env.example`

``` dotenv
APP_NAME=End-to-End-LLMOps-Project
APP_ENV=development
DEBUG=True

LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL_NAME=openai/gpt-oss-20b

EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

VECTOR_STORE=faiss
FAISS_INDEX_PATH=faiss_index

LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=End-to-End-LLMOps-Project
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

GROQ_JUDGE_MODEL=openai/gpt-oss-120b

HOST=0.0.0.0
PORT=8080
```

The current `model_loader.py` reads the Hugging Face model name from
`config.yaml`. Keep `.env.example`, `config.yaml`, and application code
consistent if you change models.

### Secret-handling rules

-   Real keys belong in local `.env` for local development only.
-   Never commit `.env`.
-   Commit `.env.example` with placeholders only.
-   Never put API key values in the Dockerfile, task-definition JSON,
    source code, or GitHub.
-   In AWS, store the Groq and LangSmith keys in Secrets Manager and
    reference them from the ECS task definition.
-   The public Hugging Face model used here does not require an API key.

## 4. Build and test Docker locally

The Dockerfile uses Python 3.11 slim, installs dependencies, copies the
application into `/app`, and starts Uvicorn on `0.0.0.0:8080`.

Container command:

``` dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

Build:

``` cmd
docker build -t llmopsrepolive:latest .
```

Run locally:

``` cmd
docker run -d -p 8080:8080 --name llmops-test llmopsrepolive:latest
```

Open `http://localhost:8080/docs`. If Swagger UI loads, the container is
serving FastAPI locally.

Stop and remove the test container:

``` cmd
docker stop llmops-test
docker rm llmops-test
```

## 5. AWS prerequisites and CLI identity

Install Docker Desktop and AWS CLI, configure an AWS identity, and
confirm the identity:

``` cmd
aws sts get-caller-identity
aws configure get region
```

Values used in this deployment:

  Setting             Value
  ------------------- ------------------------------------------
  AWS account         `452975373208`
  Region              `eu-north-1`
  IAM CLI user        `llmops-user`
  GitHub repository   `i-am-tushaar/End-to-End-LLMOPs-Project`

For another account, substitute its account ID and actual resource
outputs. Never copy credentials from this guide.

The deployment identity needs appropriate permissions for
CloudFormation, ECR authentication and push, ECS task definition
registration and service updates, relevant EC2 network-interface
descriptions, Secrets Manager descriptions, and narrowly scoped
`iam:PassRole` for the ECS task execution role. Use least privilege. Do
not solve access-denied errors by permanently attaching
`AdministratorAccess`; identify the denied action and grant only the
necessary permission on the narrowest resource.

## 6. Step 1: Create infrastructure using CloudFormation

### `infra/cloudformation.yml`

The template used in this deployment creates/configures:

-   VPC `10.0.0.0/16`
-   Public subnet `10.0.1.0/24`
-   Internet gateway and public route
-   Security group allowing inbound TCP `8080` from `AllowedCidr`
-   ECR repository `llmopsrepolive`
-   ECS cluster `llmops-live-cluster`
-   CloudWatch log group `/ecs/llmopstdlive`
-   ECS task execution IAM role
-   GitHub OIDC provider and GitHub Actions deployment role

The ECS task execution role is configured to pull ECR images, publish
CloudWatch logs, and retrieve the configured Secrets Manager secrets.
The deployment's secret access scope was configured for `llmops/*` in
the account and region.

### Set the allowed client IP

Find the current public IP:

``` cmd
curl https://checkip.amazonaws.com
```

Use the returned IP with `/32`, for example `YOUR_PUBLIC_IP/32`. A `/32`
allows one IPv4 address. The example is not a literal IP; use the actual
output. If the client IP changes, update the security group
rule/CloudFormation parameter.

### Deploy the stack

Run from the project root (replace `YOUR_PUBLIC_IP/32`):

``` cmd
aws cloudformation deploy --template-file infra/cloudformation.yml --stack-name llmops-infrastructure --capabilities CAPABILITY_NAMED_IAM --parameter-overrides GitHubOwner=i-am-tushaar GitHubRepo=End-to-End-LLMOPs-Project AllowedCidr=YOUR_PUBLIC_IP/32 --region eu-north-1
```

What the arguments mean:

-   `--template-file`: CloudFormation YAML template.
-   `--stack-name`: stack name.
-   `--capabilities CAPABILITY_NAMED_IAM`: acknowledges creation of
    named IAM resources.
-   `GitHubOwner` and `GitHubRepo`: GitHub repository used by the OIDC
    deployment role.
-   `AllowedCidr`: source IP range permitted to reach port 8080.
-   `--region`: AWS region.

Inspect outputs:

``` cmd
aws cloudformation describe-stacks --stack-name llmops-infrastructure --region eu-north-1 --query "Stacks[0].Outputs" --output table
```

Outputs from the deployment documented here:

  ----------------------------------------------------------------------------------------------------
  Output                              Value
  ----------------------------------- ----------------------------------------------------------------
  ECS cluster                         `llmops-live-cluster`

  ECR URI                             `452975373208.dkr.ecr.eu-north-1.amazonaws.com/llmopsrepolive`

  Log group                           `/ecs/llmopstdlive`

  Public subnet                       `subnet-08e5b96cc9a34f936`

  Security group                      `sg-0958e37ea3a4e8d49`

  ECS task execution role             `llmops-infrastructure-ECSTaskExecutionRole-zNZChLJTeS9n`

  GitHub Actions role                 `llmops-infrastructure-GitHubActionsDeployRole-2BZ6az8I1m4i`
  ----------------------------------------------------------------------------------------------------

Generated resource IDs and role suffixes can differ in another account
or after stack recreation. Use actual stack outputs.

## 7. Step 2: Store API keys in Secrets Manager

Create these secrets in `eu-north-1`:

  Secret name                  Secret value
  ---------------------------- ----------------------
  `llmops/GROQ_API_KEY`        Current Groq API key
  `llmops/LANGCHAIN_API_KEY`   LangSmith API key

The current task definition uses plaintext secret values, so the Groq
secret value should be the key itself, not a JSON object. Do not put
actual key values in this guide or source control.

### Secret rotation

ECS injects a secret when a task starts. Updating a Secrets Manager
value does not change the environment of an already-running container.
After rotating a key, force a new deployment:

``` cmd
aws ecs update-service --cluster llmops-live-cluster --service llmops-service --force-new-deployment --region eu-north-1 --no-cli-pager
```

Then wait for stability and retrieve the replacement task's public IP.

## 8. Step 3: Build and push the image to ECR

Authenticate Docker:

``` cmd
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 452975373208.dkr.ecr.eu-north-1.amazonaws.com
```

Build a versioned image (the corrected model-loader image in this
deployment was tagged `v2`):

``` cmd
docker build -t llmopsrepolive:v2 .
```

Tag it for ECR:

``` cmd
docker tag llmopsrepolive:v2 452975373208.dkr.ecr.eu-north-1.amazonaws.com/llmopsrepolive:v2
```

Push it:

``` cmd
docker push 452975373208.dkr.ecr.eu-north-1.amazonaws.com/llmopsrepolive:v2
```

The documented push completed with digest:

``` text
sha256:dc66c5153cc601b44d458736910a85a1252e4de8b564b3315bacf3a83082bc51
```

A future build will have a different digest. Verify repository images:

``` cmd
aws ecr describe-images --repository-name llmopsrepolive --region eu-north-1 --query "imageDetails[*].[imageTags,imageDigest]" --output table
```

A temporary Docker `TLS handshake timeout` occurred during one push.
Retrying the same push succeeded and Docker reused layers already
uploaded. A TLS timeout alone is not evidence of an IAM permission
problem.

## 9. Step 4: Configure and register the ECS task definition

### `infra/task-definition.json`

The task definition is the runtime blueprint for the ECS task. It does
not create the VPC or ECR repository.

Deployed settings:

  Setting               Value
  --------------------- ------------------------------------------------
  Family                `llmops-task`
  Compatibility         `FARGATE`
  Network mode          `awsvpc`
  CPU                   `1024` (1 vCPU)
  Memory                `4096` MiB (4 GB)
  Container             `llmops-container`
  Container/host port   `8080`
  Image                 ECR image with a version tag
  Log group             `/ecs/llmopstdlive`
  Log stream prefix     `ecs`
  Execution role        CloudFormation-created ECS task execution role

Environment variables included production configuration such as:

``` text
APP_NAME=End-to-End-LLMOps-Project
APP_ENV=production
DEBUG=False
LLM_PROVIDER=groq
GROQ_MODEL_NAME=openai/gpt-oss-20b
EMBEDDING_PROVIDER=huggingface
VECTOR_STORE=faiss
FAISS_INDEX_PATH=faiss_index
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=End-to-End-LLMOps-Project
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
HOST=0.0.0.0
PORT=8080
```

The `secrets` array maps Secrets Manager ARNs to environment variable
names inside the container. Conceptually:

``` json
"secrets": [
  {
    "name": "GROQ_API_KEY",
    "valueFrom": "FULL_GROQ_SECRET_ARN"
  },
  {
    "name": "LANGCHAIN_API_KEY",
    "valueFrom": "FULL_LANGCHAIN_SECRET_ARN"
  }
]
```

Use the full secret ARNs from your account. Do not put secret values in
this JSON.

Before registering a release, update the `image` field to the new
version tag, for example:

``` json
"image": "452975373208.dkr.ecr.eu-north-1.amazonaws.com/llmopsrepolive:v2"
```

Validate JSON:

``` cmd
python -m json.tool infra/task-definition.json
```

Register the definition:

``` cmd
aws ecs register-task-definition --cli-input-json file://infra/task-definition.json --region eu-north-1
```

This deployment registered `llmops-task:3`. The revision number
increases with each registration; use the actual revision returned by
AWS. If the CLI displays `-- More --`, press `Q` to exit the pager.

## 10. Step 5: Update the ECS service

The service maintains the desired number of running tasks. This project
uses one Fargate task with a public IP, a public subnet, and the
application security group.

  Service setting   Value
  ----------------- -----------------------
  Cluster           `llmops-live-cluster`
  Service           `llmops-service`
  Desired count     `1`
  Launch type       `FARGATE`
  Public IP         `ENABLED`
  Load balancer     None

The service already existed, so the release was deployed by updating it
to task revision 3:

``` cmd
aws ecs update-service --cluster llmops-live-cluster --service llmops-service --task-definition llmops-task:3 --region eu-north-1 --no-cli-pager
```

For another release, substitute the new revision number returned by
`register-task-definition`.

Wait for stability:

``` cmd
aws ecs wait services-stable --cluster llmops-live-cluster --services llmops-service --region eu-north-1
```

Inspect deployments:

``` cmd
aws ecs describe-services --cluster llmops-live-cluster --services llmops-service --region eu-north-1 --query "services[0].deployments[*].[taskDefinition,status,runningCount,desiredCount,rolloutState]" --output table
```

The active revision should eventually show one running task, one desired
task, and rollout state `COMPLETED`.

If deployment remains `IN_PROGRESS`, inspect events:

``` cmd
aws ecs describe-services --cluster llmops-live-cluster --services llmops-service --region eu-north-1 --query "services[0].events[:10].[createdAt,message]" --output table
```

Do not manually stop the old healthy task while diagnosing a replacement
that has not started.

## 11. Step 6: Find the running task and public IP

A Fargate task can receive a new public IP when ECS replaces it. Always
retrieve the current IP after a deployment or task restart.

List the running task:

``` cmd
aws ecs list-tasks --cluster llmops-live-cluster --service-name llmops-service --desired-status RUNNING --region eu-north-1 --query "taskArns[0]" --output text
```

Copy the returned task ARN, then get its network interface ID:

``` cmd
aws ecs describe-tasks --cluster llmops-live-cluster --tasks TASK_ARN --region eu-north-1 --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text
```

Replace `TASK_ARN` with the actual ARN. Then get the public IP:

``` cmd
aws ec2 describe-network-interfaces --network-interface-ids ENI_ID --region eu-north-1 --query "NetworkInterfaces[0].Association.PublicIp" --output text
```

Replace `ENI_ID` with the actual interface ID.

The latest task documented in this deployment had public IP
`51.21.247.169`. This is a historical value, not a permanent endpoint. A
replacement task may receive another IP.

## 12. Step 7: Open and test the application

Open the root endpoint:

``` text
http://PUBLIC_IP:8080
```

Open FastAPI Swagger UI:

``` text
http://PUBLIC_IP:8080/docs
```

For the task documented here, the URL was:

``` text
http://51.21.247.169:8080/docs
```

Use the current IP from Section 11 if the task has since been replaced.

Test the application:

1.  Open `/docs`.
2.  Confirm Swagger UI loads.
3.  Use the document upload/index endpoint.
4.  Confirm the application reports that the document was indexed.
5.  Ask a question whose answer exists in the uploaded document.
6.  If generation fails, inspect CloudWatch logs and verify the Groq
    secret.

Successful indexing alone does not prove the LLM API key is valid. Test
both ingestion and question answering.

## 13. Step 8: CloudWatch logs

The configured log group is:

``` text
/ecs/llmopstdlive
```

In AWS Console, open CloudWatch → Logs → Log groups →
`/ecs/llmopstdlive`.

Use logs to diagnose container startup, missing environment variables,
secret retrieval, model initialization, document ingestion, retrieval,
and Groq API errors. Never log secret values.

## 14. Troubleshooting

### Docker push: TLS handshake timeout

Retry the same `docker push`. In the documented deployment, retrying
succeeded and Docker reused previously uploaded layers.

### ECS deployment remains in progress

Inspect service events and task status:

``` cmd
aws ecs describe-services --cluster llmops-live-cluster --services llmops-service --region eu-north-1 --query "services[0].events[:10].[createdAt,message]" --output table
```

``` cmd
aws ecs describe-tasks --cluster llmops-live-cluster --tasks TASK_ARN --region eu-north-1 --query "tasks[0].[lastStatus,healthStatus,taskDefinitionArn,stopReason]" --output table
```

In this deployment, revision 3 initially showed `IN_PROGRESS`; ECS then
started task `5c54b634eb49435198c541fd23c5960b`. The task reached
`RUNNING` and used `llmops-task:3`.

`healthStatus: UNKNOWN` can occur when no container health check is
configured. It is not by itself proof of failure. Check task status,
rollout, logs, and the HTTP endpoint.

### Hugging Face warnings

The first local test downloaded
`sentence-transformers/all-MiniLM-L6-v2`. Hugging Face warned that
unauthenticated requests have lower rate limits. The model loaded
successfully and produced 384-dimensional embeddings. Optional
metadata-file 404 checks did not prevent initialization.

### Google API key error

The earlier model loader selected Google embeddings. The active
configuration was changed to Hugging Face embeddings and Groq LLM, and
Google integrations were removed from the active `model_loader.py` and
`config.yaml`.

The local test then succeeded: Hugging Face returned 384-dimensional
embeddings and Groq returned HTTP 200.

### Groq API returns 401 Invalid API Key

The deployed application successfully indexed a document, but a
question-answering request failed with:

``` text
groq.AuthenticationError: 401
Invalid API Key
```

The Groq API key had recently been regenerated. The remaining action is
to update the `llmops/GROQ_API_KEY` secret with the current valid key
and force a new ECS deployment so the replacement task receives it.

``` cmd
aws ecs update-service --cluster llmops-live-cluster --service llmops-service --force-new-deployment --region eu-north-1 --no-cli-pager
```

Wait for service stability, retrieve the new public IP, and retest
question answering. Do not place the key in source code or
task-definition JSON.

### Public IP no longer works

A replacement task may receive a new IP. Retrieve the current task, ENI,
and IP using Section 11. Also verify that the task is `RUNNING`, the
security group permits TCP `8080` from your current public IP, the
application binds to `0.0.0.0:8080`, and the subnet has a route to the
internet gateway.

If your public IP changes, update the CloudFormation `AllowedCidr`
parameter/security group ingress. Keep access restricted; do not expose
port 8080 to the whole internet without considering the security
implications.

## 15. Repeatable release checklist

For each new application release, assuming infrastructure, ECR, ECS
service, and secrets already exist:

1.  Build a new image tag:

    ``` cmd
    docker build -t llmopsrepolive:v3 .
    ```

2.  Authenticate Docker to ECR:

    ``` cmd
    aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 452975373208.dkr.ecr.eu-north-1.amazonaws.com
    ```

3.  Tag the image:

    ``` cmd
    docker tag llmopsrepolive:v3 452975373208.dkr.ecr.eu-north-1.amazonaws.com/llmopsrepolive:v3
    ```

4.  Push it:

    ``` cmd
    docker push 452975373208.dkr.ecr.eu-north-1.amazonaws.com/llmopsrepolive:v3
    ```

5.  Change the `image` field in `infra/task-definition.json` to the new
    tag.

6.  Validate the JSON:

    ``` cmd
    python -m json.tool infra/task-definition.json
    ```

7.  Register a new revision:

    ``` cmd
    aws ecs register-task-definition --cli-input-json file://infra/task-definition.json --region eu-north-1
    ```

8.  Update the service using the revision returned by AWS. Example only,
    if the returned revision is 4:

    ``` cmd
    aws ecs update-service --cluster llmops-live-cluster --service llmops-service --task-definition llmops-task:4 --region eu-north-1 --no-cli-pager
    ```

9.  Wait for stability:

    ``` cmd
    aws ecs wait services-stable --cluster llmops-live-cluster --services llmops-service --region eu-north-1
    ```

10. Retrieve the new public IP using Section 11.

11. Test `http://PUBLIC_IP:8080/docs`, upload a document, and ask a
    question.

Use a new unique image tag for each release rather than relying on a
mutable `latest` tag.

## 16. Security and production considerations

This deployment exposes FastAPI directly through the Fargate task public
IP. It does not use an Application Load Balancer or a custom domain.
This is convenient for a controlled project demonstration, but a
production setup should consider:

-   Application Load Balancer and HTTPS/TLS.
-   Domain name and managed certificate.
-   Authentication and authorization for API endpoints.
-   Stable endpoint, because task public IPs can change.
-   Container health checks.
-   Monitoring, alarms, and log retention.
-   Image scanning and dependency updates.
-   Cost monitoring for Fargate, ECR storage, CloudWatch Logs, and data
    transfer.

The CloudFormation stack configured a 14-day CloudWatch log retention
period. A service desired count of one is intended to keep one task
running continuously, which incurs ongoing Fargate charges. Scale down
or delete resources when they are no longer required, while checking for
other billable resources.

## 17. Deployment completion summary

Completed in the deployment documented here:

-   Built and tested the FastAPI Docker container locally.
-   Created AWS infrastructure using CloudFormation.
-   Created the ECR repository and pushed the application image.
-   Created the ECS cluster and Fargate service.
-   Configured public subnet, public IP assignment, and security group.
-   Stored Groq and LangSmith API keys in Secrets Manager.
-   Configured ECS task CPU, memory, port, environment variables,
    secrets, execution role, and CloudWatch logging.
-   Changed model configuration to Groq for LLM and Hugging Face for
    embeddings.
-   Verified the model loader locally: Hugging Face produced
    384-dimensional embeddings and Groq returned a successful response.
-   Built and pushed Docker image `v2`.
-   Registered ECS task definition revision `llmops-task:3`.
-   Updated the ECS service to revision 3.
-   Confirmed the new Fargate task reached `RUNNING`.
-   Retrieved a public IP and opened the FastAPI application.
-   Uploaded and indexed one document through the deployed application.

**Remaining action:** Document indexing worked, but question answering
returned Groq `401 Invalid API Key`. The Groq key had recently been
regenerated. Update `llmops/GROQ_API_KEY` in Secrets Manager, force a
new ECS deployment, retrieve the replacement task's public IP, and
retest question answering.

## 18. Useful AWS Console links

-   [CloudFormation
    stacks](https://eu-north-1.console.aws.amazon.com/cloudformation/home?region=eu-north-1#/stacks)
-   [ECR
    repositories](https://eu-north-1.console.aws.amazon.com/ecr/repositories?region=eu-north-1)
-   [ECS
    clusters](https://eu-north-1.console.aws.amazon.com/ecs/v2/clusters?region=eu-north-1)
-   [Secrets
    Manager](https://eu-north-1.console.aws.amazon.com/secretsmanager/listsecrets?region=eu-north-1)
-   [CloudWatch log
    groups](https://eu-north-1.console.aws.amazon.com/cloudwatch/home?region=eu-north-1#logsV2:log-groups)
