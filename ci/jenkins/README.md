<!-- This guide intentionally covers the prototype/local CI phase only. -->
# Local Jenkins

This configuration runs a Jenkins controller on localhost only. It does not
mount the host Docker socket and it does not deploy to AWS.

## Start Jenkins

From the repository root:

```powershell
docker compose -f ci/jenkins/docker-compose.yml up -d
docker compose -f ci/jenkins/docker-compose.yml logs -f jenkins
```

Open <http://localhost:8081>. Retrieve the first-time administrator password
with:

```powershell
docker compose -f ci/jenkins/docker-compose.yml exec jenkins `
  cat /var/jenkins_home/secrets/initialAdminPassword
```

Use the setup wizard and install the suggested plugins. The minimum plugins
needed by this repository are listed in `plugins.txt`.

## Build agent

The controller image is intentionally not used as a build worker. Create one
local Jenkins agent named `ticketing-ci` with that exact label. The agent may
be the Windows host or a separately managed build container, but it must have:

- Git
- Node.js 22.11.0 or newer
- npm
- The pinned Trivy version documented in `../trivy/README.md`

For a Windows host, create a permanent inbound agent in Jenkins, choose the
WebSocket launch method, download the generated `agent.jar`, and run the
command Jenkins provides from a local agent directory. WebSocket avoids
requiring a public inbound port. The pipeline currently needs Node/npm for the
frontend checks and the pinned Trivy CLI for the repository security scan.

Do not mount `//var/run/docker.sock` into Jenkins. Docker image builds will be
added only after a separate, approved build-agent strategy is available.

## Create the pipeline job

Create a Pipeline job using **Pipeline script from SCM** and point it at the
repository. Select the branch you are testing and use the repository root
`Jenkinsfile`. Add Git credentials in Jenkins if the repository is private.

The current pipeline runs:

1. Checkout
2. Repository/frontend structure validation
3. `npm ci`
4. HTML, embedded CSS, and embedded JavaScript linting
5. Frontend structural validation
6. Pinned Trivy repository scanning for vulnerabilities, secrets, and supported
   misconfigurations

The Trivy stage fails if Trivy is missing, the installed version does not match
`../trivy/version.txt`, the scan cannot run, or critical findings are detected.
Jenkins archives the readable report and critical-finding JSON report with the
build.

`DEPLOY_TO_AWS` is false by default. When EC2 is ready, add an SSH Username
with private key credential with the ID `ec2-deploy-key`, set `EC2_HOST` to the
instance's public DNS name or IP, and enable `DEPLOY_TO_AWS`. The deployment
stage copies the Docker application files to `/opt/ticketing` and runs
`docker compose up -d --build` on the instance. The Jenkins agent must have
an SSH client, and Jenkins must have the Credentials Binding plugin installed.

## Stop Jenkins

```powershell
docker compose -f ci/jenkins/docker-compose.yml down
```

The named `jenkins_home` volume is retained so Jenkins configuration survives
container recreation. Remove it only when intentionally resetting Jenkins.
