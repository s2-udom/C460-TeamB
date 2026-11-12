// Ticketing CI/CD pipeline. Runs on the Linux EC2 agent (label ticketing-ec2).
//
// Gates, in order:  validate -> lint -> test -> repo scan -> build image -> image scan
// Only if all gates pass and DEPLOY_TO_AWS is ticked:  push to ECR -> deploy via SSM -> smoke test
// A failed smoke test rolls back to the previous image.
//
// There are no AWS keys in Jenkins. The agent's instance role supplies short-lived credentials.
// Nothing connects in to the agent: it dials out to the controller and uses SSM for the deploy.

// Runs the deploy document on the app host and waits for it to finish.
// parameters is 'action=deploy,imageUri=<ecr image>' or 'action=rollback' (comma-separated,
// no spaces: the AWS CLI rejects two space-separated entries after one --parameters).
def runDeployDocument(String instanceId, String parameters) {
    def commandId = sh(returnStdout: true, script: 'aws ssm send-command --document-name ' + env.DEPLOY_DOCUMENT +
        ' --instance-ids ' + instanceId + ' --parameters "' + parameters + '"' +
        ' --query Command.CommandId --output text').trim()
    echo "SSM command ${commandId} sent to ${instanceId}"
    def status = 'Pending'
    timeout(time: 15, unit: 'MINUTES') {
        waitUntil {
            sleep(time: 5, unit: 'SECONDS')
            try {
                status = sh(returnStdout: true, script: 'aws ssm get-command-invocation --command-id ' + commandId +
                    ' --instance-id ' + instanceId + ' --query Status --output text').trim()
            } catch (err) {
                status = 'Pending'   // the invocation can take a moment to appear
            }
            return !(status in ['Pending', 'InProgress', 'Delayed'])
        }
    }
    sh 'aws ssm get-command-invocation --command-id ' + commandId + ' --instance-id ' + instanceId +
        ' --query StandardOutputContent --output text'
    if (status != 'Success') {
        sh 'aws ssm get-command-invocation --command-id ' + commandId + ' --instance-id ' + instanceId +
            ' --query StandardErrorContent --output text || true'
        error("Deploy command finished with status ${status}")
    }
}

pipeline {
    // Run work on a separate agent so the Jenkins controller is not used as a build worker.
    agent { label 'ticketing-agent' }

    options {
        skipDefaultCheckout(true)
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 45, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        booleanParam(
            name: 'DEPLOY_TO_AWS',
            defaultValue: false,
            description: 'Push the image to ECR and deploy it to the AWS app host. Gates always run; this only controls the release.'
        )
    }

    environment {
        FRONTEND_FILE = 'app/templates/index-prototype.html'
        CI = 'true'
        // These match the names Terraform creates for the staging environment.
        AWS_DEFAULT_REGION = 'eu-west-2'
        ECR_REPOSITORY = 'ticketing-staging-app'
        APP_HOST_NAME = 'ticketing-staging-app'
        DEPLOY_DOCUMENT = 'ticketing-staging-deploy'
        SMOKE_PATH = '/readyz'
    }

    stages {
        stage('Checkout') {
            steps {
                // Remove a partial or stale workspace before fetching.
                deleteDir()
                checkout scm
            }
        }

        stage('Validate project structure') {
            steps {
                script {
                    if (!fileExists(env.FRONTEND_FILE)) {
                        error("Required frontend file was not found: ${env.FRONTEND_FILE}")
                    }
                }
                // Prints the tool versions the build actually used, so a failure can be reproduced.
                sh '''
                    set -eu
                    node --version
                    npm --version
                    docker --version
                    aws --version
                    echo "Running as: $(aws sts get-caller-identity --query Arn --output text)"
                '''
            }
        }
     
        stage('Install frontend validation dependencies') {
            steps {
                sh 'npm ci'
            }
        }

        stage('Frontend lint') {
            steps {
                sh 'npm run lint:frontend'
            }
        }

        stage('Frontend validation') {
            steps {
                sh 'npm test'
            }
        }

        stage('Backend unit and integration tests') {
            steps {
                sh '''
                    set -eu
                    docker run --rm --user "$(id -u):$(id -g)" \\
                        -e PYTHONPATH=/work \\
                        -v "$WORKSPACE:/work" \\
                        -w /work \\
                        python:3.12-slim \\
                        sh -c '
                            set -eu
                            python -m venv /tmp/ticketing-ci-venv
                            /tmp/ticketing-ci-venv/bin/pip install --no-cache-dir -q \\
                                -r requirements.txt -r requirements-dev.txt
                            mkdir -p reports
                            /tmp/ticketing-ci-venv/bin/pytest -q \\
                                --junitxml=reports/pytest.xml
                        '
                '''
            }
            post {
                always {
                    junit testResults: 'reports/pytest.xml', allowEmptyResults: false
                }
            }
        }

        stage('Trivy repository scan') {
            // Scans the source tree. The script checks the installed Trivy is the exact
            // version in ci/trivy/version.txt, so the agent and developer laptops agree.
            steps {
                sh 'bash scripts/security/run-trivy-scan.sh'
            }
        }

        stage('Build image') {
            steps {
                script {
                    def sha = sh(returnStdout: true, script: 'git rev-parse --short=8 HEAD').trim()
                    env.IMAGE_TAG = 'build-' + env.BUILD_NUMBER + '-' + sha
                    env.LOCAL_IMAGE = 'ticketing-app:' + env.IMAGE_TAG
                }
                // The app host is x86, so build for x86 whatever the agent is.
                sh 'docker build --platform linux/amd64 --label git.commit=$(git rev-parse HEAD) -t "$LOCAL_IMAGE" .'
            }
        }

        stage('Trivy image scan') {
            // Blocks the release on a CRITICAL vulnerability that has a fix available.
            steps {
                sh '''
                    set -eu
                    trivy image --exit-code 0 --severity HIGH,CRITICAL --ignore-unfixed \
                        --format table --output trivy-image-report.txt "$LOCAL_IMAGE"
                    trivy image --exit-code 1 --severity CRITICAL --ignore-unfixed "$LOCAL_IMAGE"
                '''
            }
        }

        stage('Push to ECR') {
            when {
                expression { params.DEPLOY_TO_AWS }
            }
            steps {
                script {
                    def repoUri = sh(returnStdout: true, script: 'aws ecr describe-repositories --repository-names ' +
                        env.ECR_REPOSITORY + ' --query "repositories[0].repositoryUri" --output text').trim()
                    env.IMAGE_URI = repoUri + ':' + env.IMAGE_TAG
                    sh 'aws ecr get-login-password | docker login --username AWS --password-stdin ' + repoUri.split('/')[0]
                    sh 'docker tag "$LOCAL_IMAGE" "$IMAGE_URI" && docker push "$IMAGE_URI"'
                }
            }
        }

        stage('Deploy to AWS') {
            when {
                expression { params.DEPLOY_TO_AWS }
            }
            steps {
                script {
                    // Find the host by its Name tag, so a rebuilt instance needs no pipeline change.
                    def host = sh(returnStdout: true, script: 'aws ec2 describe-instances --filters Name=tag:Name,Values=' +
                        env.APP_HOST_NAME + ' Name=instance-state-name,Values=running' +
                        ' --query "Reservations[0].Instances[0].[InstanceId,PublicIpAddress]" --output text').trim().split('\\s+')
                    if (!host[0].startsWith('i-')) {
                        error("No running EC2 instance with the Name tag ${env.APP_HOST_NAME}")
                    }
                    env.APP_INSTANCE_ID = host[0]
                    env.APP_PUBLIC_IP = host[1]
                    echo "Deploying ${env.IMAGE_URI} to ${env.APP_INSTANCE_ID} (${env.APP_PUBLIC_IP})"
                    // The host pulls the image, restarts the container and checks /healthz.
                    // If the new container does not come up it restores the previous one itself.
                    runDeployDocument(env.APP_INSTANCE_ID, 'action=deploy,imageUri=' + env.IMAGE_URI)
                }
            }
        }

        stage('Smoke test') {
            // Checked from outside the host, the way a user reaches it. /readyz includes the database.
            when {
                expression { params.DEPLOY_TO_AWS }
            }
            steps {
                retry(6) {
                    sleep(time: 5, unit: 'SECONDS')
                    sh 'curl -fsS --max-time 5 "http://$APP_PUBLIC_IP$SMOKE_PATH"'
                }
            }
            post {
                failure {
                    script {
                        echo 'Smoke test failed, rolling back to the previous image.'
                        runDeployDocument(env.APP_INSTANCE_ID, 'action=rollback')
                    }
                }
            }
        }
    }

    post {
        always {
            script {
                // Keep a small, truthful report for each Jenkins run.
                writeFile(
                    file: 'build-report.txt',
                    text: """Ticketing CI report
Result: ${currentBuild.currentResult}
Commit: ${env.GIT_COMMIT ?: 'unknown'}
Image: ${env.IMAGE_URI ?: (env.LOCAL_IMAGE ?: 'not built')}
AWS deployment requested: ${params.DEPLOY_TO_AWS}
Agent: ${env.NODE_NAME}
"""
                )
                archiveArtifacts artifacts: 'build-report.txt,trivy-image-report.txt,trivy-repository-report.txt,trivy-critical-findings.json,trivy-version.txt', allowEmptyArchive: true
            }
            // Free disk on the agent. Failures here must not fail the build.
            sh 'docker image rm "$LOCAL_IMAGE" >/dev/null 2>&1 || true; docker image prune -f >/dev/null 2>&1 || true'
        }
    }
}
