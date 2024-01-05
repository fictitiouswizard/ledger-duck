podman build -t ledger-duck-api .

run -d --name duck-ledger-api --env-file .\.env -p 8080:8080 localhost/ledger-duck-api:latest