#!/usr/bin/env bash
# Deploy a versioned registry image to staging and restore the previous healthy
# version if its health check does not succeed.
set -Eeuo pipefail

state_dir="${STATE_DIR:-/opt/ai-assisted-cicd/state}"
state_file="${state_dir}/last-successful.env"
compose_file="${COMPOSE_FILE:-compose.yaml}"
attempts=10
delay_seconds=3
target_repository="${IMAGE_REPOSITORY:?IMAGE_REPOSITORY must be set}"
target_tag="${IMAGE_TAG:?IMAGE_TAG must be set}"

mkdir -p "${state_dir}"

previous_repository=""
previous_tag=""
if [[ -f "${state_file}" ]]; then
    # This file is written only by this script and contains two shell variables.
    # shellcheck disable=SC1090
    source "${state_file}"
    previous_repository="${IMAGE_REPOSITORY:-}"
    previous_tag="${IMAGE_TAG:-}"
fi

verify_health() {
    local attempt
    for ((attempt = 1; attempt <= attempts; attempt++)); do
        if curl --fail --silent --show-error http://127.0.0.1:8000/health; then
            return 0
        fi
        echo "Health check attempt ${attempt}/${attempts} failed; retrying in ${delay_seconds} seconds."
        sleep "${delay_seconds}"
    done
    return 1
}

deploy_image() {
    local repository="$1"
    local tag="$2"

    echo "Deploying ${repository}:${tag} to staging."
    IMAGE_REPOSITORY="${repository}" IMAGE_TAG="${tag}" docker compose -f "${compose_file}" pull
    IMAGE_REPOSITORY="${repository}" IMAGE_TAG="${tag}" APP_VERSION="${tag}" \
        docker compose -f "${compose_file}" up --detach --no-build --force-recreate
    IMAGE_REPOSITORY="${repository}" IMAGE_TAG="${tag}" docker compose -f "${compose_file}" ps
}

if deploy_image "${target_repository}" "${target_tag}" && verify_health; then
    umask 077
    {
        printf 'IMAGE_REPOSITORY=%q\n' "${target_repository}"
        printf 'IMAGE_TAG=%q\n' "${target_tag}"
    } > "${state_file}"
    echo "Staging deployment successful: ${target_repository}:${target_tag}"
    exit 0
fi

echo 'New staging deployment is unhealthy.'
docker compose -f "${compose_file}" logs --no-color || true

if [[ -n "${previous_repository}" && -n "${previous_tag}" ]]; then
    echo "Rolling back to last healthy image: ${previous_repository}:${previous_tag}"
    deploy_image "${previous_repository}" "${previous_tag}"

    if verify_health; then
        echo "Rollback successful: ${previous_repository}:${previous_tag} is healthy."
    else
        echo 'Rollback failed: the previous image did not become healthy.' >&2
    fi
else
    echo 'No previous healthy image is recorded; rollback is not possible for the first deployment.' >&2
fi

# The release failed even if rollback succeeded, so Jenkins must mark it failed.
exit 1
