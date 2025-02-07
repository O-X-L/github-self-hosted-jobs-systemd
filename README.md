# CI

## Usage

```bash
API_TOKEN='<YOUR-TOKEN-HERE>'
# API_TOKEN='e072f27f-4904-4ea8-878f-c0959b115263'
# API_TOKEN_RO='7a8a6ada-6764-4560-83c2-5e40773d2e07'
API_JOB='<YOUR-JOB-HERE>'

# start a job:
curl -v -XPOST "http://localhost:8000/api/job/${API_JOB}?token=${API_TOKEN}"

# get job state
curl -v "http://localhost:8000/api/job/${API_JOB}/state?token=${API_TOKEN}"

# tail job logs
curl -v "http://localhost:8000/api/job/${API_JOB}/tail?token=${API_TOKEN}"

# get full job logs of last run
curl -v "http://localhost:8000/api/job/${API_JOB}/logs?token=${API_TOKEN}"

# limit the max lines of logs
curl -v "http://localhost:8000/api/job/${API_JOB}/logs?token=${API_TOKEN}&lines=50"
```

----

## Setup

### API

Sudoers-Privileges

```
# file: /etc/sudoers.d/ci_api
Cmnd_Alias USER_PRIV_CIAPI = \
  /usr/bin/systemctl start <YOUR-PREFIX-HERE>-*, \
  /usr/bin/journalctl *

ci_api ALL=(ALL) NOPASSWD: USER_PRIV_CIAPI
```
