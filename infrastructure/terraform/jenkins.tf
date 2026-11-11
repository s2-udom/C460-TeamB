# What the Jenkins build agent (an EC2 instance with an IAM role) is allowed to do.
# It can push images to the app's ECR repository and run ONE fixed deploy document on the app host.
# It cannot run arbitrary commands, touch the database, or change any other AWS resource.
# There are no access keys anywhere: the agent gets short-lived credentials from its instance role.
#
# This attaches an inline policy to the role you already created for the agent instance.
# Set it in terraform.tfvars:  jenkins_agent_role_name = "<name of that role>"

variable "jenkins_agent_role_name" {
  description = "Name of the existing IAM role attached to the Jenkins agent EC2 instance."
  type        = string
}

variable "jenkins_agent_secret_parameter" {
  description = "SSM Parameter Store name (SecureString) holding the Jenkins agent secret."
  type        = string
  default     = "/ticketing/jenkins/agent-secret"
}

data "aws_caller_identity" "current" {}

resource "aws_ssm_document" "deploy" {
  name            = "${local.name}-deploy"
  document_type   = "Command"
  document_format = "YAML"
  content         = file("${path.module}/ssm/deploy.yaml")
}

data "aws_iam_policy_document" "jenkins_agent" {
  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "EcrPushToAppRepository"
    actions = [
      "ecr:DescribeRepositories",
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:UploadLayerPart",
      "ecr:CompleteLayerUpload",
      "ecr:PutImage",
    ]
    resources = [aws_ecr_repository.app.arn]
  }

  # SendCommand is only allowed for this one document on this one instance.
  statement {
    sid     = "RunDeployDocumentOnAppHost"
    actions = ["ssm:SendCommand"]
    resources = [
      aws_ssm_document.deploy.arn,
      aws_instance.app.arn,
    ]
  }

  statement {
    sid = "ReadCommandResults"
    actions = [
      "ssm:GetCommandInvocation",
      "ssm:ListCommandInvocations",
      "ssm:ListCommands",
    ]
    resources = ["*"]
  }

  # Read-only lookups so the pipeline finds the host by its Name tag instead of a hard-coded ID.
  statement {
    sid = "FindTheAppHost"
    actions = [
      "ec2:DescribeInstances",
      "ssm:DescribeInstanceInformation",
    ]
    resources = ["*"]
  }

  # Lets the agent service fetch its own connection secret at start-up.
  statement {
    sid     = "ReadAgentSecret"
    actions = ["ssm:GetParameter"]
    resources = [
      "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter${var.jenkins_agent_secret_parameter}",
    ]
  }
}

resource "aws_iam_role_policy" "jenkins_agent" {
  name   = "${local.name}-jenkins-agent"
  role   = var.jenkins_agent_role_name
  policy = data.aws_iam_policy_document.jenkins_agent.json
}

output "deploy_document_name" {
  description = "SSM document the pipeline runs on the app host."
  value       = aws_ssm_document.deploy.name
}
