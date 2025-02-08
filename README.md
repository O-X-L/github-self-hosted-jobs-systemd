# CI API

This repository contains an API that can be used to act as intermediate between internal CI-Jobs and GitHub workflows/actions.

Why would be need something like that? We use it as the native [Self-hosted GitHub Runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners#self-hosted-runner-security) cannot be used in a secure manner for public repositories.

----

## Usage

```bash
API_DOMAIN='ci.oxl.at'
API_TOKEN='<YOUR-TOKEN-HERE>'
# API_TOKEN='e072f27f-4904-4ea8-878f-c0959b115263'
# API_TOKEN_RO='7a8a6ada-6764-4560-83c2-5e40773d2e07'
API_JOB='<YOUR-JOB-HERE>'

# start a job:
curl -v -XPOST "https://${API_DOMAIN}/api/job/${API_JOB}?token=${API_TOKEN}"

# get job state
curl -v "https://${API_DOMAIN}/api/job/${API_JOB}/state?token=${API_TOKEN}"

# tail job logs
curl -v "https://${API_DOMAIN}/api/job/${API_JOB}/tail?token=${API_TOKEN}"

# get full job logs of last run
curl -v "https://${API_DOMAIN}/api/job/${API_JOB}/logs?token=${API_TOKEN}"

# limit the max lines of logs
curl -v "https://${API_DOMAIN}/api/job/${API_JOB}/logs?token=${API_TOKEN}&lines=50"
```

----

## Setup

### GitHub

* Add the Read-Write Token to your repository [action-secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions) (`CI_TOKEN_RW`)
* Add workflows like seen [in the examples](https://github.com/O-X-L/github-self-hosted-jobs-systemd/tree/main/workflows)
  * To trigger jobs via the API
  * Follow jobs
    * Follow the job-logs in realtime (*tail*)
    * Default pipeline behavior
  * Execute jobs on a schedule
    * Optimal for long-running jobs (*less GitHub action run-time*)
    * Can be done without following the output in realtime
    * Fetch the logs and status after the job finished

### Job Service

The job systemd-service should use a prefix to limit the scope of the API-permissions! Example: all test-services start with `ci-test-`

You will have to configure that prefix in the `api/main.py` and the `sudoers.d` file.

These services should run as an unprivileged service-user!

You could also utilize systemd-instances to run multiple instances of one service at a time and also pass a runtime-variable to that service. Example: `ci-test-<JOB>@<COMMIT/BRANCH>`

### API

Sudoers-Privileges

```
# file: /etc/sudoers.d/ci_api
Cmnd_Alias USER_PRIV_CIAPI = \
  /usr/bin/systemctl start <YOUR-PREFIX-HERE>-*, \
  /usr/bin/journalctl *

ci_api ALL=(ALL) NOPASSWD: USER_PRIV_CIAPI
```
