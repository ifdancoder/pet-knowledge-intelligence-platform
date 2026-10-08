# Production deployment: knowledge.ifdancoder.ru

These manifests deploy to the shared k3s server that already runs ifdancoder.ru, as a second site on knowledge.ifdancoder.ru, in the `kip` namespace. They are a separate, self-contained set from the local-dev manifests in `k8s/` (GPU-based, no Ingress) and are never mixed with them.

## One-time manual setup

Everything `.github/workflows/deploy.yml` cannot do by itself, done once before the first push-triggered deploy.

1. Install a GitHub Actions self-hosted runner directly on the server, registered to this repo (Settings -> Actions -> Runners -> New self-hosted runner gives the exact `config.sh` command and token). Install it as a service (`./svc.sh install && ./svc.sh start`) so it survives reboots and keeps picking up jobs.
2. Make sure the runner's own user can run `docker`, `kubectl`, and `k3s ctr images import` non-interactively: either it is root, has passwordless `sudo`, is in the `docker` group, or has a working `~/.kube/config` copied from `/etc/rancher/k3s/k3s.yaml`.
3. Check the cert-manager issuer name already configured on the cluster: `kubectl get clusterissuers`. If it is not `letsencrypt-prod`, edit the `cert-manager.io/cluster-issuer` annotation in `ingress.yaml` to match before the first apply.
4. Add a DNS `A` record for `knowledge.ifdancoder.ru` pointing at the server's public IP (the same IP `ifdancoder.ru` already resolves to).
5. In the GitHub repo, add under Settings -> Secrets and variables -> Actions -> Secrets: `JWT_SECRET` (e.g. `openssl rand -hex 32`), `POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD`, `S3_SECRET_KEY`, and optionally `ANTHROPIC_API_KEY`, `SENTRY_DSN`.
6. Push to `main`. Once `CI` passes, `Deploy` runs automatically on the runner. Watch it with `kubectl get pods -n kip -w` on the server, or `gh run watch` locally.
7. Pull the Ollama model once (it persists in its `PersistentVolumeClaim`, no need to repeat on later deploys):
   ```bash
   kubectl exec -n kip ollama-0 -- ollama pull smollm2:135m
   ```

## Verification

- `kubectl get pods -n kip`: all workloads `Running`, `api`/`worker`/`frontend` each `1/1 Ready`.
- `curl -s https://knowledge.ifdancoder.ru/api/health` returns `{"status":"ok"}`.
- Open `https://knowledge.ifdancoder.ru/` in a browser: register, verify (the dev-mode verification token is in the api pod's logs: `kubectl logs -n kip deployment/api`), log in, create a workspace, upload a markdown file, search it, chat with it.
- `kubectl top pods -n kip` after a few minutes of normal use, to check actual memory/CPU against the budget in the design doc.
- The existing ifdancoder.ru site stays reachable and unaffected throughout.

## Updating

Every push to `main` that passes CI redeploys automatically: new images are built on the server, the `kip-secrets` Secret is recreated from the current GitHub Actions secrets, `k8s/production/` is reapplied, and the three app Deployments are restarted so they pick up the freshly built `:latest` images (`kubectl apply` alone would not do this, since the image tag string in the manifests never changes).
