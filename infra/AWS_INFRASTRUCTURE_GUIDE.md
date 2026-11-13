# AWS Infrastructure Guide for the End-to-End LLMOps Project

> **Purpose:** This document explains the AWS infrastructure defined in
> `infra/cloudformation.yml`, why each resource exists, how
> CloudFormation creates it, how to inspect it, what may incur charges,
> and how to remove it safely.

## 1. Where this document belongs

Save this file in the project repository at:

``` text
End-to-End-LLMOPs-Project/
├── infra/
│   ├── cloudformation.yml
│   └── AWS_INFRASTRUCTURE_GUIDE.md
├── .github/
│   └── workflows/
├── main.py
├── Dockerfile
└── README.md
```

**Recommended location:** `infra/AWS_INFRASTRUCTURE_GUIDE.md`

This keeps the explanation next to the CloudFormation template it
documents. Add a link to it from the main `README.md`, for example:

``` markdown
## AWS Infrastructure

See [AWS Infrastructure Guide](infra/AWS_INFRASTRUCTURE_GUIDE.md) for the
CloudFormation resources, deployment and cleanup instructions, console checks,
and cost considerations.
```

## 2. Project deployment overview

The project uses Docker to package the application. Amazon ECR stores
the image, and Amazon ECS with AWS Fargate will eventually run it.

The CloudFormation template creates the **supporting AWS
infrastructure**. It does **not**, by itself, build the Docker image,
push the image, register the application task definition, create the ECS
service, or start a Fargate task.

The intended deployment flow is:

1.  A developer pushes code to the configured GitHub repository.
2.  GitHub Actions authenticates to AWS using GitHub's OpenID Connect
    (OIDC) identity provider.
3.  GitHub Actions assumes an IAM deployment role.
4.  The workflow builds the Docker image and pushes it to Amazon ECR.
5.  An ECS task definition describes how to run the image.
6.  An ECS service runs the task on AWS Fargate in the configured VPC
    subnet.
7.  The task writes logs to CloudWatch Logs.
8.  Users access the application through the task's public IP and the
    configured application port, once the ECS service/task has been
    created and assigned a public IP.

``` text
GitHub repository
       |
       v
GitHub Actions workflow
       |
       | OIDC authentication
       v
AWS IAM deployment role
       |
       | builds and pushes image
       v
Amazon ECR repository
       |
       | image pulled by ECS
       v
ECS task definition + ECS service
       |
       v
AWS Fargate task in public subnet
       |
       +---- CloudWatch Logs
       |
       +---- Application access on TCP port 8080
```

## 3. What CloudFormation does

AWS CloudFormation is an Infrastructure as Code (IaC) service. The file
`infra/cloudformation.yml` describes the AWS resources and their
configuration in YAML.

Instead of creating each resource manually in the AWS Console,
CloudFormation reads the template and creates the resources as one
**stack**.

In this project, the stack name is:

``` text
llmops-infrastructure
```

CloudFormation tracks the resources it creates. This makes it easier to
inspect, update, and delete the infrastructure as a group.

### Template parameters

The template uses these parameters:

  -----------------------------------------------------------------------------
  Parameter               Default / example             Purpose
  ----------------------- ----------------------------- -----------------------
  `GitHubOwner`           `i-am-tushaar`                GitHub account or
                                                        organization that owns
                                                        the repository

  `GitHubRepo`            `End-to-End-LLMOPs-Project`   Repository allowed by
                                                        the GitHub OIDC role
                                                        trust policy

  `ECRRepositoryName`     `llmopsrepolive`              Name of the ECR image
                                                        repository

  `ECSClusterName`        `llmops-live-cluster`         Name of the ECS cluster

  `AllowedCidr`           `0.0.0.0/0` in the template   IPv4 CIDR permitted to
                                                        access TCP port 8080
  -----------------------------------------------------------------------------

**Security:** Do not use `0.0.0.0/0` for an application that should only
be reachable by you. For practice, pass your current public IPv4 address
with `/32`, for example `203.0.113.10/32`. The example address is
documentation-only; use your actual current public IP. A changing
home/ISP IP may require updating the security-group rule.

## 4. Resources created by `cloudformation.yml`

The following describes the resources in the current project template.

### 4.1 VPC (Virtual Private Cloud)

**CloudFormation resource type:** `AWS::EC2::VPC`\
**Configured CIDR:** `10.0.0.0/16`\
**Name tag:** `llmops-vpc`

**What it is:** A logically isolated network in AWS.

**Why it is needed:** The ECS Fargate task needs a VPC network in which
it can receive network interfaces and communicate with other services.

**How it is created:** CloudFormation creates a VPC with the CIDR range
`10.0.0.0/16` and enables DNS support and DNS hostnames.

**Where to check:** AWS Console → VPC → Your VPCs. Select the region
`eu-north-1` (Europe/Stockholm) and find the VPC named `llmops-vpc`.

**Cost:** The VPC itself has no hourly charge. Other resources or
network services used with it may incur charges.

### 4.2 Public subnet

**CloudFormation resource type:** `AWS::EC2::Subnet`\
**Configured CIDR:** `10.0.1.0/24`

**What it is:** A smaller network range inside the VPC.

**Why it is needed:** It provides a subnet in which the Fargate task can
be launched. The template selects an Availability Zone in the selected
region and enables automatic public IPv4 assignment for instances
launched in the subnet.

**How it is created:** CloudFormation creates the subnet inside the VPC
and associates it with the route table configured by the template.

**Where to check:** AWS Console → VPC → Subnets. Find the subnet with
CIDR `10.0.1.0/24`.

**Cost:** The subnet itself has no hourly charge. Public IPv4 addresses
and data transfer can cost money when used.

### 4.3 Internet Gateway

**CloudFormation resource type:** `AWS::EC2::InternetGateway` and its
VPC attachment.

**What it is:** A VPC component that enables communication between the
VPC and the internet when routing and security rules allow it.

**Why it is needed:** A task in the public subnet may need internet
connectivity, for example to serve public requests or reach external
APIs.

**How it is created:** CloudFormation creates an Internet Gateway and
attaches it to the project VPC.

**Where to check:** AWS Console → VPC → Internet Gateways. Check that
its attachment references the project VPC.

**Cost:** The Internet Gateway itself has no hourly charge. Data
transfer and public IPv4 usage may incur charges.

### 4.4 Route table, default route, and subnet association

**CloudFormation resource types:** `AWS::EC2::RouteTable`,
`AWS::EC2::Route`, and `AWS::EC2::SubnetRouteTableAssociation`.

**What they are:** A route table contains rules that decide where
network traffic is sent.

**Why they are needed:** The public subnet needs a default route to the
Internet Gateway for internet-bound IPv4 traffic.

**How they are created:** CloudFormation creates a route table, adds a
default route (`0.0.0.0/0`) targeting the Internet Gateway, and
associates the route table with the public subnet.

**Where to check:** AWS Console → VPC → Route Tables. Select the project
route table and inspect: - **Routes:** a route for `0.0.0.0/0` with the
Internet Gateway as target. - **Subnet associations:** the project
public subnet.

**Cost:** Route tables and routes do not have a separate hourly charge.

### 4.5 Security Group

**CloudFormation resource type:** `AWS::EC2::SecurityGroup`\
**Application port:** TCP `8080`\
**Default template source range:** `0.0.0.0/0`, overridden during the
practice deployment with the user's IP `/32`.

**What it is:** A virtual firewall attached to network interfaces.

**Why it is needed:** It controls inbound and outbound network traffic
for the Fargate task.

**How it is created:** The template creates a security group in the
project VPC. It permits inbound TCP traffic on port 8080 from the
`AllowedCidr` parameter and allows outbound traffic.

**Where to check:** AWS Console → EC2 → Network & Security → Security
Groups. Open the group and inspect **Inbound rules** and **Outbound
rules**.

**Cost:** Security Groups do not have a separate hourly charge.

**Security reminder:** Keep inbound access restricted to the smallest
required CIDR range. If your public IP changes, update the rule. Port
8080 should not be exposed to the whole internet unless that is an
intentional, reviewed requirement.

### 4.6 Amazon Elastic Container Registry (ECR) repository

**CloudFormation resource type:** `AWS::ECR::Repository`\
**Repository name:** `llmopsrepolive`

**What it is:** A private registry for storing Docker/OCI container
images.

**Why it is needed:** The CI/CD workflow can push the built application
image to ECR. ECS/Fargate can then pull that image to start a container.

**How it is created:** The template creates a private ECR repository
with: - Image tag mutability set to `IMMUTABLE`. - Image scanning on
push enabled. - AES-256 encryption.

**Where to check:** AWS Console → Elastic Container Registry (ECR) →
Private registry → Repositories. Select `llmopsrepolive`.

**Cost:** ECR storage is chargeable based on image data stored. Image
scanning and data transfer may also have pricing implications depending
on usage and current AWS pricing. An empty repository generally has no
image-storage charge, but verify the current ECR pricing for the region.

**Deletion note:** A repository containing images may fail to delete
unless the images are removed or the repository is configured for force
deletion. The current template should be checked for its
`EmptyOnDelete`/force-delete behaviour before relying on stack deletion
to remove a non-empty repository.

### 4.7 Amazon ECS cluster

**CloudFormation resource type:** `AWS::ECS::Cluster`\
**Cluster name:** `llmops-live-cluster`

**What it is:** A logical grouping and management boundary for ECS tasks
and services.

**Why it is needed:** It provides the cluster in which the project's ECS
service and tasks will be managed.

**How it is created:** CloudFormation creates an ECS cluster with the
configured name.

**Where to check:** AWS Console → Elastic Container Service (ECS) →
Clusters. Open `llmops-live-cluster`.

**Cost:** An ECS cluster by itself does not incur a cluster hourly fee.
The compute capacity used by tasks (such as Fargate) and related
networking/logging can incur charges.

**Important:** Creating the cluster does not start the application. The
task definition, ECS service, and running Fargate task are separate
deployment resources and are not created by this infrastructure
template.

### 4.8 CloudWatch Logs log group

**CloudFormation resource type:** `AWS::Logs::LogGroup`\
**Log group:** `/ecs/llmopstdlive`\
**Retention:** 14 days

**What it is:** A named destination for application and container logs
in Amazon CloudWatch Logs.

**Why it is needed:** When the ECS task definition is configured to use
the `awslogs` log driver, container output can be sent to this log group
for troubleshooting and monitoring.

**How it is created:** CloudFormation creates the log group and sets
retention to 14 days.

**Where to check:** AWS Console → CloudWatch → Logs → Log groups. Find
`/ecs/llmopstdlive`.

**Cost:** CloudWatch Logs can incur charges for log ingestion, storage,
and related usage. The 14-day retention setting helps limit how long
logs are retained, but it does not make logging free.

### 4.9 ECS task execution IAM role

**CloudFormation resource type:** `AWS::IAM::Role`

**What it is:** An IAM role that the ECS/Fargate agent assumes for
actions needed to start a task.

**Why it is needed:** The task execution role lets ECS perform startup
operations such as pulling a private image from ECR and sending logs to
CloudWatch. The template also adds permission to retrieve Secrets
Manager values under the `llmops/*` secret name path.

**How it is created:** The template creates a role trusted by
`ecs-tasks.amazonaws.com`, attaches the AWS managed policy
`AmazonECSTaskExecutionRolePolicy`, and adds the `ReadLLMOpsSecrets`
inline policy.

**Where to check:** AWS Console → IAM → Roles. Find the role created by
the stack (its generated name may include the stack and logical resource
name). Inspect **Permissions** and **Trust relationships**.

**Cost:** IAM roles and policies do not have a separate charge.

**Security note:** The execution role is not the same as an application
task role. If code inside the application needs to call AWS APIs
directly, a separate task role with only the necessary permissions may
be required. Do not give the application broad permissions by default.

### 4.10 GitHub OIDC identity provider

**CloudFormation resource type:** `AWS::IAM::OIDCProvider`\
**Provider URL:** `https://token.actions.githubusercontent.com`\
**Audience/client ID:** `sts.amazonaws.com`

**What it is:** An identity provider registration that allows AWS IAM to
trust identity tokens issued by GitHub Actions.

**Why it is needed:** It allows a GitHub Actions workflow to request
temporary AWS credentials by assuming an IAM role. This avoids storing
long-lived AWS access keys as GitHub repository secrets.

**How it is created:** The template registers GitHub's OIDC issuer URL
and the `sts.amazonaws.com` audience.

**Where to check:** AWS Console → IAM → Identity providers. Find
`token.actions.githubusercontent.com`.

**Cost:** IAM OIDC identity providers do not have a separate charge.

**Important:** The OIDC provider alone does not grant access. The IAM
role's trust policy must also restrict which repository, branch, and
audience are allowed.

### 4.11 GitHub Actions deployment IAM role

**CloudFormation resource type:** `AWS::IAM::Role`\
**Role name in the template:** `GitHubActionsECSDeployRole`

**What it is:** An IAM role that a permitted GitHub Actions workflow can
assume.

**Why it is needed:** It gives the workflow AWS permissions for the
deployment tasks defined by the policy, such as authenticating to ECR,
pushing an image, and interacting with ECS/CloudFormation.

**How it is created:** The template creates a role whose trust policy
uses GitHub's OIDC provider. The subject condition is restricted to the
configured repository and the `main` branch:

``` text
repo:i-am-tushaar/End-to-End-LLMOPs-Project:ref:refs/heads/main
```

The role also receives the deployment permissions specified in the YAML
template.

**Where to check:** AWS Console → IAM → Roles →
`GitHubActionsECSDeployRole`. Inspect **Trust relationships** and
**Permissions**.

**Cost:** IAM roles and policies do not have a separate charge.

**Security note:** Keep the trust policy as narrow as possible. If the
repository or branch changes, update the trust policy intentionally. Do
not replace the restricted trust condition with a wildcard unless there
is a specific, reviewed reason.

## 5. What is not created by this template?

The current `cloudformation.yml` creates the infrastructure listed
above. It does not create these application deployment components:

  -----------------------------------------------------------------------
  Not created by this     What it does            When it is needed
  template                                        
  ----------------------- ----------------------- -----------------------
  ECS task definition     Describes the container Before ECS can run the
                          image, CPU, memory,     application
                          port mappings,          
                          environment, secrets,   
                          roles and logging       

  ECS service             Keeps the desired       To run the application
                          number of tasks running as a service
                          and manages deployments 

  Fargate task            The actual running      When a task/service is
                          container workload      started

  Application public IP   Address assigned to a   When the task is
                          running task's network  launched with public IP
                          interface when public   
                          IP assignment is        
                          enabled                 

  Application Load        Provides a managed      Optional; not used in
  Balancer                entry point and routing the current public-IP
                          to tasks                design

  Secrets Manager secrets Stores actual           Must be created
                          Gemini/Groq API key     separately unless
                          values                  another process creates
                                                  them

  Docker image            Packaged application    Built locally or by CI
                          artifact                and pushed to ECR
  -----------------------------------------------------------------------

A cluster can exist while no application is running. Likewise, an ECR
repository can exist while it contains no images.

## 6. Region and naming used in this project

The AWS region used for the practice deployment is:

``` text
Europe (Stockholm)
eu-north-1
```

The CloudFormation stack name is:

``` text
llmops-infrastructure
```

Other key names:

  Item                   Name
  ---------------------- -----------------------
  ECR repository         `llmopsrepolive`
  ECS cluster            `llmops-live-cluster`
  CloudWatch log group   `/ecs/llmopstdlive`
  Application port       `8080`
  VPC CIDR               `10.0.0.0/16`
  Public subnet CIDR     `10.0.1.0/24`

Always select `eu-north-1` in the AWS Console when checking these
resources. IAM is a global service, so IAM pages may display **Global**
rather than a regional selector.

## 7. Prerequisites before deployment

1.  AWS CLI v2 is installed.
2.  AWS CLI is configured with credentials for the intended AWS account.
3.  The IAM identity has the permissions required to create, inspect,
    update, and delete every resource in the template.
4.  The current directory is the project root, where the `infra` folder
    exists.
5.  The CloudFormation template has been validated.
6.  The `AllowedCidr` value is set to the intended trusted public IPv4
    CIDR.

Check the CLI installation:

``` cmd
aws --version
```

Check which AWS identity is active:

``` cmd
aws sts get-caller-identity --region eu-north-1
```

The identity output contains account and user/role information. Do not
publish credentials or secret access keys.

## 8. Validate the CloudFormation template

Run from the project root:

``` cmd
aws cloudformation validate-template --template-body file://infra/cloudformation.yml --region eu-north-1 --no-cli-pager
```

**What it does:** Asks CloudFormation to parse and validate the template
structure and returns the template parameters and capabilities.

**Why:** It catches template-format and basic validation problems before
a stack operation.

**What it does not do:** It does not create resources and does not
guarantee that the caller has permission to create every resource. It
also does not guarantee that every resource will succeed at runtime.

## 9. Deploy the infrastructure

For a practice deployment, replace the example CIDR below with your
current public IPv4 address followed by `/32`.

``` cmd
aws cloudformation deploy --template-file infra/cloudformation.yml --stack-name llmops-infrastructure --capabilities CAPABILITY_NAMED_IAM --parameter-overrides GitHubOwner=i-am-tushaar GitHubRepo=End-to-End-LLMOPs-Project AllowedCidr=YOUR_PUBLIC_IP/32 --region eu-north-1
```

For example, if your current public IPv4 address were `203.0.113.10`,
the parameter would be:

``` text
AllowedCidr=203.0.113.10/32
```

The address above is an example only. Do not copy it unless it is
actually your public IP.

### Explanation of the deployment command

  ---------------------------------------------------------------------------
  Part                                    Meaning
  --------------------------------------- -----------------------------------
  `aws`                                   Runs the AWS CLI

  `cloudformation`                        Selects the CloudFormation service

  `deploy`                                Creates or updates a CloudFormation
                                          stack

  `--template-file`                       Points to the local YAML template

  `infra/cloudformation.yml`              The infrastructure definition

  `--stack-name`                          Names the stack

  `llmops-infrastructure`                 The stack name used for this
                                          project

  `--capabilities CAPABILITY_NAMED_IAM`   Acknowledges that the template
                                          creates named IAM resources

  `--parameter-overrides`                 Supplies values for template
                                          parameters

  `GitHubOwner=...`                       Sets the GitHub owner

  `GitHubRepo=...`                        Sets the GitHub repository

  `AllowedCidr=...`                       Restricts inbound port 8080 to the
                                          chosen IPv4 CIDR

  `--region eu-north-1`                   Deploys in Europe (Stockholm)
  ---------------------------------------------------------------------------

A successful deployment usually ends with:

``` text
Successfully created/updated stack - llmops-infrastructure
```

**Billing note:** A successful stack deployment can create billable
resources or enable later billable usage. Check current AWS pricing and
your Billing dashboard.

## 10. Check the stack and resources

### 10.1 Check stack status

``` cmd
aws cloudformation describe-stacks --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager
```

This displays the stack status, parameters, and outputs.

A successful stack creation normally shows:

``` text
CREATE_COMPLETE
```

### 10.2 Display only stack outputs

``` cmd
aws cloudformation describe-stacks --stack-name llmops-infrastructure --query "Stacks[0].Outputs" --output table --region eu-north-1
```

This displays output values such as repository URI, cluster name, subnet
ID, security group ID, role ARNs, and log group name if those outputs
are defined in the template.

### 10.3 List resources tracked by the stack

``` cmd
aws cloudformation describe-stack-resources --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager
```

This shows the logical resource IDs, physical resource IDs, resource
types, and statuses for resources tracked by CloudFormation.

### 10.4 Check recent stack events

``` cmd
aws cloudformation describe-stack-events --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager
```

This shows the stack operation history. When troubleshooting, inspect: -
`ResourceStatus` - `ResourceType` - `LogicalResourceId` -
`ResourceStatusReason`

A `CREATE_FAILED` event usually contains the reason a resource could not
be created. Common causes include missing IAM permissions, an existing
resource with the same globally/account-scoped name, a quota, or an
invalid configuration.

### 10.5 Check selected services directly

``` cmd
aws ecr describe-repositories --region eu-north-1
```

``` cmd
aws ecs list-clusters --region eu-north-1
```

``` cmd
aws logs describe-log-groups --log-group-name-prefix /ecs/llmopstdlive --region eu-north-1
```

## 11. Where to inspect resources in the AWS Console

First select **Europe (Stockholm), `eu-north-1`** in the region selector
for regional services.

  ---------------------------------------------------------------------------------------
  Resource                AWS Console navigation  What to inspect
  ----------------------- ----------------------- ---------------------------------------
  CloudFormation stack    CloudFormation → Stacks Stack status, Resources, Outputs,
                                                  Events, Template

  VPC                     VPC → Your VPCs         VPC name and CIDR

  Subnet                  VPC → Subnets           Subnet CIDR and VPC association

  Internet Gateway        VPC → Internet Gateways Attachment to the project VPC

  Route table             VPC → Route Tables      Default route and subnet association

  Security Group          EC2 → Network &         Inbound TCP 8080 source and outbound
                          Security → Security     rules
                          Groups                  

  ECR repository          ECR → Private registry  Repository name, images, image tags
                          → Repositories          

  ECS cluster             ECS → Clusters          Cluster name and resources/services

  CloudWatch log group    CloudWatch → Logs → Log `/ecs/llmopstdlive` and retention
                          groups                  

  ECS execution role      IAM → Roles             Trust relationship and attached
                                                  policies

  GitHub OIDC provider    IAM → Identity          `token.actions.githubusercontent.com`
                          providers               

  GitHub Actions role     IAM → Roles             Trust relationship and deployment
                                                  permissions
  ---------------------------------------------------------------------------------------

**Useful habit:** CloudFormation → Stack → Resources is the best first
place to see which resources belong to this stack. The physical resource
ID links the stack entry to the resource created in the AWS service.

## 12. Which resources cost money?

AWS pricing changes and depends on region, configuration, usage, data
volume, and public IPv4 allocation. The table below is a general cost
guide, not a quote or guarantee of zero charges.

  -----------------------------------------------------------------------
  Resource                            Typical cost behaviour
  ----------------------------------- -----------------------------------
  VPC                                 No hourly VPC charge

  Subnet                              No separate hourly subnet charge

  Internet Gateway                    No hourly Internet Gateway charge;
                                      data transfer and public IPv4 may
                                      cost

  Route table and routes              No separate hourly charge

  Security Group                      No separate hourly charge

  ECR repository                      Image storage is chargeable;
                                      scanning and transfer may also have
                                      pricing implications

  ECS cluster                         No cluster-only hourly charge

  CloudWatch Logs                     Ingestion and storage can be
                                      chargeable

  IAM roles and policies              No separate charge

  IAM OIDC provider                   No separate charge

  Fargate task                        Compute and allocated storage are
                                      billed while provisioned/running
                                      according to Fargate pricing

  Public IPv4 address                 Public IPv4 usage can be charged
                                      per hour

  Application Load Balancer (if added Has hourly and
  later)                              capacity/usage-related charges

  Secrets Manager (if added later)    Secret storage and API usage can be
                                      chargeable
  -----------------------------------------------------------------------

### Important cost points

-   The current template does not start a Fargate task. Therefore it
    does not create Fargate compute charges by itself.
-   An empty ECR repository generally has no image-storage charge.
    Images pushed into it consume storage.
-   CloudWatch log storage and ingestion can cost money if logs are
    written.
-   A public subnet and Internet Gateway do not, by themselves, mean a
    Fargate task or public IP is running.
-   If an ECS service/task is created later, compute, public IPv4,
    logging, and data transfer may incur charges.
-   AWS Free Tier eligibility and offers vary by account, service, date,
    and region. Do not assume a resource is free without checking the
    current pricing page and Billing console.

Check charges in AWS Console → Billing and Cost Management → Bills /
Cost Explorer. Billing data can be delayed; absence of an immediate
charge is not proof that no usage is billable.

## 13. Delete the infrastructure when practice is finished

Because the resources were created by one CloudFormation stack, delete
the stack rather than manually deleting each resource.

Run:

``` cmd
aws cloudformation delete-stack --stack-name llmops-infrastructure --region eu-north-1
```

**What it does:** Requests deletion of the stack and the resources
CloudFormation manages.

**Why it is used:** It provides one central cleanup operation and lets
CloudFormation delete resources in dependency order.

Check whether the stack still exists:

``` cmd
aws cloudformation describe-stacks --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager
```

If the stack has been fully deleted, the CLI returns a validation error
stating that the stack does not exist. In this particular check, that
message is the expected confirmation that the stack is no longer
present.

You can also inspect deletion progress:

``` cmd
aws cloudformation describe-stack-events --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager
```

### Resources that may need separate cleanup

CloudFormation deletes only resources it manages. Check separately for
resources created outside the stack, such as: - Secrets Manager secrets
created manually. - ECR images or repositories created manually. - ECS
services, tasks, task definitions, or load balancers created outside
this stack. - Public IPv4 addresses or other networking resources
created separately. - Resources in other AWS regions.

If an ECR repository contains images and stack deletion fails because it
is not empty, remove the images or use the appropriate repository
deletion option only after confirming the repository is no longer
needed.

If an ECS service or running task was created separately, delete/scale
down the service and stop the tasks before removing supporting
networking resources.

After stack deletion, inspect CloudFormation events for `DELETE_FAILED`
resources and clean them up safely. Do not assume every resource was
removed merely because the delete command returned without printing an
error.

## 14. IAM permissions and safe practice

The IAM identity running CloudFormation needs permission to: - Validate
and inspect CloudFormation templates/stacks. - Create, tag, describe,
modify, and delete the EC2/VPC resources in the template. - Create and
delete ECR repositories. - Create and describe ECS clusters. - Create
and delete CloudWatch log groups. - Create and manage IAM roles,
policies, and OIDC identity providers. - Pass the appropriate ECS
execution role where required.

A deployment can fail even when the YAML is valid if the caller does not
have the necessary IAM permissions.

### AdministratorAccess warning

During troubleshooting, broad `AdministratorAccess` was temporarily
attached to the IAM user used for this practice. This policy grants very
broad permissions across the AWS account.

**Do not leave AdministratorAccess attached as a permanent deployment
solution.**

After practice: 1. Delete the CloudFormation stack. 2. Verify that the
stack and its resources are removed. 3. Remove the temporary
`AdministratorAccess` policy from the IAM user. 4. Use a narrowly scoped
IAM policy or deployment role for future work. 5. Prefer GitHub OIDC and
temporary role credentials for CI/CD rather than storing long-lived AWS
access keys in GitHub.

Also rotate/deactivate any AWS access key that has been exposed or
shared. Never commit `.env`, AWS secret access keys, Gemini API keys, or
Groq API keys to Git.

## 15. Recommended practice workflow

Use this sequence whenever you practise the AWS deployment:

1.  Open the project in the terminal at the repository root.
2.  Check the active AWS identity with `aws sts get-caller-identity`.
3.  Confirm the region is `eu-north-1`.
4.  Check the current public IP and set `AllowedCidr` to that IP with
    `/32`.
5.  Validate `infra/cloudformation.yml`.
6.  Deploy the CloudFormation stack.
7.  Inspect CloudFormation → Stack → Resources and verify the resources
    in their AWS service consoles.
8.  Continue with ECR image push and ECS task/service deployment only
    when ready.
9.  When finished, delete the CloudFormation stack.
10. Check for separately created resources, leftover images, logs,
    secrets, tasks, and public IP addresses.
11. Remove temporary broad IAM permissions.
12. Review AWS Billing and Cost Explorer.

## 16. Quick command reference

Run these commands from the project root in Windows CMD.

``` cmd
:: Check AWS CLI version
aws --version

:: Check the active AWS identity
aws sts get-caller-identity --region eu-north-1

:: Validate the CloudFormation template
aws cloudformation validate-template --template-body file://infra/cloudformation.yml --region eu-north-1 --no-cli-pager

:: Deploy the infrastructure (replace YOUR_PUBLIC_IP)
aws cloudformation deploy --template-file infra/cloudformation.yml --stack-name llmops-infrastructure --capabilities CAPABILITY_NAMED_IAM --parameter-overrides GitHubOwner=i-am-tushaar GitHubRepo=End-to-End-LLMOPs-Project AllowedCidr=YOUR_PUBLIC_IP/32 --region eu-north-1

:: Check stack status
aws cloudformation describe-stacks --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager

:: Show stack outputs
aws cloudformation describe-stacks --stack-name llmops-infrastructure --query "Stacks[0].Outputs" --output table --region eu-north-1

:: List stack resources
aws cloudformation describe-stack-resources --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager

:: Show stack events
aws cloudformation describe-stack-events --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager

:: Delete the stack after practice
aws cloudformation delete-stack --stack-name llmops-infrastructure --region eu-north-1

:: Confirm the stack is gone (a "stack does not exist" response means deletion completed)
aws cloudformation describe-stacks --stack-name llmops-infrastructure --region eu-north-1 --no-cli-pager
```

## 17. Final summary

-   `infra/cloudformation.yml` is the Infrastructure as Code template.
-   CloudFormation creates and tracks the supporting AWS infrastructure
    as one stack.
-   VPC, subnet, Internet Gateway, routes, and Security Group provide
    networking.
-   ECR stores the Docker image.
-   ECS provides the cluster in which tasks and services are managed.
-   CloudWatch Logs stores container logs when the task definition is
    configured to send them.
-   IAM roles and GitHub OIDC enable ECS execution and GitHub Actions
    authentication.
-   The current template does not run the application; task definition,
    ECS service, and Fargate task are separate steps.
-   Some resources are free of direct hourly charges, while ECR storage,
    CloudWatch usage, Fargate, public IPv4, and data transfer can incur
    costs.
-   Delete the CloudFormation stack when practice is finished, then
    verify that separately created resources are also removed.
-   Remove temporary AdministratorAccess permissions and protect all
    credentials and API keys.

**Always verify current AWS pricing and the actual resources in your
account before leaving anything running.**
