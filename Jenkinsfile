pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        IMAGE_NAME = 'system-monitor-api'
        IMAGE_TAG = "build-${BUILD_NUMBER}"
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
                    pytest -q
                '''
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

        stage('Deploy to Staging') {
            steps {
                sh '''
                    IMAGE_TAG=${IMAGE_TAG} APP_VERSION=${IMAGE_TAG} docker compose up --detach --no-build --force-recreate
                    docker compose ps
                '''
            }
        }

        stage('Verify Health') {
            steps {
                sh '''
                    for attempt in 1 2 3 4 5 6 7 8 9 10; do
                        if curl --fail --silent --show-error http://127.0.0.1:8000/health; then
                            exit 0
                        fi
                        echo "Health check attempt ${attempt}/10 failed; retrying in 3 seconds."
                        sleep 3
                    done

                    echo 'Deployment failed: the service did not become healthy.'
                    docker compose logs --no-color
                    exit 1
                '''
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
