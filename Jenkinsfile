pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    triggers {
        // VM1 is private, so GitHub cannot send a public webhook to it.
        // Polling makes Jenkins check GitHub for new commits every five minutes.
        pollSCM('H/5 * * * *')
    }

    environment {
        IMAGE_NAME = 'system-monitor-api'
        IMAGE_TAG = "build-${BUILD_NUMBER}"
        DOCKERHUB_REPOSITORY = 'ahmadalimalik/system-monitor-api'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    python -m pip install --upgrade pip
                    pip install -r requirements-dev.txt
                    pytest -q --junitxml=test-results.xml --cov=app --cov-report=xml:coverage.xml
                '''
                junit 'test-results.xml'
                archiveArtifacts artifacts: 'coverage.xml', fingerprint: true
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube-Local') {
                    script {
                        def scannerHome = tool 'SonarScanner'
                        sh "${scannerHome}/bin/sonar-scanner"
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build --tag ${IMAGE_NAME}:${IMAGE_TAG} .
                    docker image inspect ${IMAGE_NAME}:${IMAGE_TAG}
                '''
            }
        }

        stage('Scan Docker Image') {
            steps {
                script {
                    int scanStatus = sh(
                        returnStatus: true,
                        script: '''
                            # Keep the report visible even when Trivy returns 1 for a blocked image.
                            set +e
                            trivy image --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --no-progress --exit-code 1 --format table --output trivy-image-report.txt ${IMAGE_NAME}:${IMAGE_TAG}
                            scan_status=$?
                            set -e
                            cat trivy-image-report.txt
                            exit "$scan_status"
                        '''
                    )

                    archiveArtifacts artifacts: 'trivy-image-report.txt', fingerprint: true

                    if (scanStatus != 0) {
                        error 'Security gate failed: Trivy found HIGH or CRITICAL vulnerabilities with available fixes.'
                    }
                }
            }
        }

        stage('Push Image to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKERHUB_USERNAME',
                    passwordVariable: 'DOCKERHUB_TOKEN'
                )]) {
                    sh '''
                        echo "$DOCKERHUB_TOKEN" | docker login --username "$DOCKERHUB_USERNAME" --password-stdin
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${DOCKERHUB_REPOSITORY}:${IMAGE_TAG}
                        docker push ${DOCKERHUB_REPOSITORY}:${IMAGE_TAG}
                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to Staging') {
            steps {
                sh 'IMAGE_REPOSITORY=${DOCKERHUB_REPOSITORY} IMAGE_TAG=${IMAGE_TAG} bash ./scripts/deploy-staging.sh'
            }
        }
    }

    post {
        success {
            echo "Staging deployment succeeded: ${IMAGE_NAME}:${IMAGE_TAG}"
        }
        failure {
            echo 'Pipeline failed. Inspect the stage log and container logs before making changes.'
        }
        always {
            sh 'docker compose ps || true'
        }
    }
}
