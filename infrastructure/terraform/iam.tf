# Identity of the app host. Gives it exactly three abilities:
#   1. be managed through SSM Session Manager (no SSH needed)
#   2. read the database password secret
#   3. pull images from the app's ECR repository
data "aws_iam_policy_document" "ec2_assume" {
statement {
actions = ["sts:AssumeRole"]

principals {
type = "Service"
identifiers = ["ec2.amazonaws.com"]
}
}
}

resource "aws_iam_role" "app" {
name = "${local.name}-app-role"
assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "app_ssm" {
role = aws_iam_role.app.name
policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "app_access" {
statement {
sid = "ReadDatabaseSecret"
actions = ["secretsmanager:GetSecretValue"]
resources = [aws_db_instance.main.master_user_secret[0].secret_arn]
}

statement {
sid = "EcrLogin"
actions = ["ecr:GetAuthorizationToken"]
resources = ["*"]
}

statement {
sid = "EcrPull"
actions = [
"ecr:BatchCheckLayerAvailability",
"ecr:BatchGetImage",
"ecr:GetDownloadUrlForLayer",
]
resources = [aws_ecr_repository.app.arn]
}
}

resource "aws_iam_role_policy" "app_access" {
name = "${local.name}-app-access"
role = aws_iam_role.app.id
policy = data.aws_iam_policy_document.app_access.json
}

resource "aws_iam_instance_profile" "app" {
name = "${local.name}-app-profile"
role = aws_iam_role.app.name
}

resource "aws_iam_role" "jenkins_agent" {
name = "${local.name}-jenkins-agent-role"
assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "jenkins_agent_ssm" {
role = aws_iam_role.jenkins_agent.name
policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "jenkins_agent_access" {
statement {
sid = "EcrPushLogin"
actions = ["ecr:GetAuthorizationToken"]
resources = ["*"]
}

statement {
sid = "EcrPushRepository"
actions = [
"ecr:BatchCheckLayerAvailability",
"ecr:GetDownloadUrlForLayer",
"ecr:BatchGetImage",
"ecr:InitiateLayerUpload",
"ecr:UploadLayerPart",
"ecr:CompleteLayerUpload",
"ecr:PutImage"
]
resources = [aws_ecr_repository.app.arn]
}

statement {
sid = "SsmSendCommands"
actions = [
"ssm:SendCommand",
"ssm:GetCommandInvocation",
"ssm:DescribeInstanceInformation"
]
resources = ["*"]
}
}

resource "aws_iam_role_policy" "jenkins_agent_access" {
name = "${local.name}-jenkins-agent-access"
role = aws_iam_role.jenkins_agent.id
policy = data.aws_iam_policy_document.jenkins_agent_access.json
}

resource "aws_iam_instance_profile" "jenkins_agent" {
name = "${local.name}-jenkins-agent-profile"
role = aws_iam_role.jenkins_agent.name
}
