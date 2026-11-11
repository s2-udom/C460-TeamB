// Local CI pipeline for the current frontend prototype.
// AWS deployment is deliberately guarded and disabled until infrastructure is ready.
pipeline {
    // Run work on a separate agent so the Jenkins controller is not used as a build worker.
    agent { label 'ticketing-agent' }

    options {
        skipDefaultCheckout(true)
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        booleanParam(
            name: 'DEPLOY_TO_AWS',
            defaultValue: false,
            description: 'Deploy the application to EC2. Keep false until EC2 and Jenkins credentials are configured.'
        )
        string(
            name: 'EC2_HOST',
            defaultValue: '',
            description: 'EC2 public DNS name or IP address used when DEPLOY_TO_AWS is true.'
        )
    }

    environment {
        FRONTEND_FILE = 'app/templates/index-prototype.html'
        CI = 'true'
    }

    stages {
        stage('Checkout') {
            steps {
                // Remove a partial or stale .git directory before fetching.
                // This keeps reused Windows agent workspaces safe to re-checkout.
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
                    if (isUnix()) {
                        sh 'node --version'
                        sh 'npm --version'
                    } else {
                        bat 'node --version'
                        bat 'npm.cmd --version'
                    }
                }
            }
        }

        stage('Install frontend validation dependencies') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'npm ci'
                    } else {
                        bat 'npm.cmd ci'
                    }
                }
            }
        }

        stage('Frontend lint') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'npm run lint:frontend'
                    } else {
                        bat 'npm.cmd run lint:frontend'
                    }
                }
            }
        }

        stage('Frontend validation') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'npm test'
                    } else {
                        bat 'npm.cmd test'
                    }
                }
            }
        }

        stage('Trivy repository scan') {
            // Trivy scans the checked-out repository. The runner verifies that the
            // exact version in ci/trivy/version.txt is installed on the agent.
            steps {
                script {
                    if (isUnix()) {
                        sh 'bash scripts/security/run-trivy-scan.sh'
                    } else {
                        // Jenkins runs as LocalSystem on the Windows agent.
                        // Expose the standard pinned installation directory to
                        // this build even when it is only in a user's PATH.
                        withEnv(['PATH+TRIVY=C:\\Tools\\Trivy']) {
                            bat 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts\\security\\run-trivy-scan.ps1'
                        }
                    }
                }
            }
        }

        stage('Deploy to EC2') {
            when {
                expression { params.DEPLOY_TO_AWS }
            }
            steps {
                script {
                    if (!params.EC2_HOST?.trim()) {
                        error('EC2_HOST is required when DEPLOY_TO_AWS is true.')
                    }
                }
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ec2-deploy-key',
                        keyFileVariable: 'EC2_KEY',
                        usernameVariable: 'EC2_USER'
                    )
                ]) {
                    script {
                        if (isUnix()) {
                            sh '''
                                set -eu
                                mkdir -p "$HOME/.ssh"
                                ssh-keyscan -H "$EC2_HOST" >> "$HOME/.ssh/known_hosts"
                                ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "mkdir -p /opt/ticketing"
                                scp -i "$EC2_KEY" -r app docker-compose.yml Dockerfile requirements.txt run.py "$EC2_USER@$EC2_HOST:/opt/ticketing/"
                                ssh -i "$EC2_KEY" "$EC2_USER@$EC2_HOST" "cd /opt/ticketing && docker compose up -d --build"
                            '''
                        } else {
                            powershell '''
                                $ErrorActionPreference = "Stop"
                                $target = "$env:EC2_USER@$env:EC2_HOST"
                                $destination = "${target}:/opt/ticketing/"

                                ssh -i "$env:EC2_KEY" -o StrictHostKeyChecking=accept-new $target "mkdir -p /opt/ticketing"
                                scp -i "$env:EC2_KEY" -o StrictHostKeyChecking=accept-new -r app docker-compose.yml Dockerfile requirements.txt run.py $destination
                                ssh -i "$env:EC2_KEY" -o StrictHostKeyChecking=accept-new $target "cd /opt/ticketing && docker compose up -d --build"
                            '''
                        }
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
                    text: """Ticketing frontend CI report
Result: ${currentBuild.currentResult}
Commit: ${env.GIT_COMMIT ?: 'unknown'}
Frontend file: ${env.FRONTEND_FILE}
AWS deployment requested: ${params.DEPLOY_TO_AWS}
"""
                )
                archiveArtifacts artifacts: 'build-report.txt,trivy-repository-report.txt,trivy-critical-findings.json,trivy-version.txt', allowEmptyArchive: true
            }
        }
    }
}
