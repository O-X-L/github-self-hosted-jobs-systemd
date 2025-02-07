# CI

## Usage

```bash
API_TOKEN='<YOUR-TOKEN-HERE>'
# API_TOKEN='e072f27f-4904-4ea8-878f-c0959b115263'
# API_TOKEN_RO='7a8a6ada-6764-4560-83c2-5e40773d2e07'
API_JOB='<YOUR-JOB-HERE>'

# start a job:
curl -v -H "token: ${API_TOKEN}" -XPOST "http://localhost:8000/api/job/${API_JOB}"

# get job state
curl -v -H "token: ${API_TOKEN}" "http://localhost:8000/api/job/${API_JOB}/state"

# tail job logs
curl -v -H "token: ${API_TOKEN}" "http://localhost:8000/api/job/${API_JOB}/tail"

# get full job logs of last run
curl -v -H "token: ${API_TOKEN}" "http://localhost:8000/api/job/${API_JOB}/logs"
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
