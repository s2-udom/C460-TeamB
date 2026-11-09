// Local CI pipeline for the current frontend prototype.
// AWS deployment is deliberately guarded and disabled until infrastructure is ready.
pipeline {
    // Run work on a separate agent so the Jenkins controller is not used as a build worker.
    agent { label 'ticketing-ci' }

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
            description: 'Reserved for a future AWS deployment. Must remain false until AWS is configured.'
        )
    }

    environment {
        FRONTEND_FILE = 'app/templates/index-prototype.html'
        CI = 'true'
    }

    stages {
        stage('Checkout') {
            steps {
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

        stage('AWS deployment guard') {
            // This fails closed if somebody requests AWS deployment before it is implemented.
            when {
                expression { params.DEPLOY_TO_AWS }
            }
            steps {
                error('AWS deployment is disabled in this local-only pipeline. Configure AWS infrastructure and credentials before enabling it.')
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
                archiveArtifacts artifacts: 'build-report.txt', allowEmptyArchive: true
            }
        }
    }
}
