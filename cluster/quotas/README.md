# Cluster-wide resource quotas

This is cluster-wide policy, not something specific to the kip project. It lives in this
repo only because there's no separate infra repo for the server yet. It applies to every
namespace sharing this node (`nsk-1-vm-y6pb`), currently kip and landing.

Apply it once by hand with the admin kubeconfig, after a fresh server setup or whenever
the arithmetic below changes:

```bash
kubectl apply -f cluster/quotas/
```

This is never applied by any project's own CI. Each project's CI only ever touches its own
`k8s/` directory.

## Why this exists

Found via a real incident: a project with no `resources.requests` set on any container ate
almost all the RAM on this VPS, and an unrelated project's pods started failing with no
indication why. The error surfaced as "node ran out of memory," not as anything pointing
at the actual cause. A `ResourceQuota` per namespace means one project's pods can never be
admitted past a hard ceiling, so a mistake in one project's manifests cannot silently start
starving another project's pods.

## The arithmetic (2026-10-10)

Node capacity (`kubectl get node -o jsonpath='...status.allocatable...'`): **1 vCPU (1000m),
~3911Mi RAM (4004892Ki)**. That is the entire budget, for every namespace combined.

Requests (what the scheduler actually reserves, and the number that really guarantees
fairness):

| Namespace | CPU requests | Memory requests |
|---|---|---|
| kip (own manifests, current) | 260m | 1750Mi |
| landing (own manifests, current) | 200m | 448Mi |
| system (ingress-nginx + coredns + metrics-server, declared) | 300m | 230Mi |
| cert-manager (11 pods, no declared requests, real but unaccounted usage) | not scheduled against, but real | not scheduled against, but real |
| **Sum of the above** | **760m / 1000m (76%)** | **2428Mi / 3911Mi (62%)** |

Quotas set here add a small buffer on top of each project's own current numbers (kip
300m/1800Mi, landing 250m/500Mi) rather than the bare figures above, so a minor bump in
either project's manifests doesn't immediately need a quota change too. Sum of quotas:
550m requests.cpu, 2300Mi requests.memory — still comfortably under the node total, leaving
roughly 450m CPU and 1600Mi memory unclaimed for system overhead and short-term slack.

Limits (the soft per-container ceiling, not a reservation) are a different story and are
being honest about it rather than hiding it: kip's own container limits already sum to
about 6 CPU and ~4.1GB of memory, and landing's to about 0.9 CPU and ~0.77GB. Added up,
that is far more than the node's real 1 CPU / 3.9GB — containers like elasticsearch, api,
and worker carry generous memory limits because they load ML models (sentence-transformers
+ torch) or run a JVM with a fixed heap, and trimming those below their actual working set
would just trade this capacity problem for OOMKills. The `limits.memory` quotas here
(kip 4200Mi, landing 850Mi) match each project's real configured sum rather than the node's
true ceiling, because a tighter cap would reject kip's and landing's own pods on every
deploy. In practice this is safe only because every service here is unlikely to hit its own
memory ceiling at the same instant as every other service — if that assumption ever stops
holding (real traffic, not a demo), the fix is to either grow the node or tighten individual
container limits further, not to raise this quota.

## If more projects join this server

Each new namespace needs its own `ResourceQuota`/`LimitRange` pair here, sized the same way:
list that project's own container requests/limits, re-run the sum against the node's real
capacity, and say plainly if it doesn't fit. As of this writing there is no spare capacity
for another project shaped like kip (ML models, a message queue, its own search index) —
only maybe 450m CPU / 1600Mi memory of real unclaimed request budget exists across the
whole node. A project with landing's footprint (a single lightweight app + a small
Postgres) could probably still fit; anything heavier needs either a bigger VPS or trimming
one of the existing projects first.

## LimitRange notes

- Every container in `k8s/production/` already declares its own `resources`, so the
  `LimitRange` defaults here are a safety net for anything added later without them, not
  the thing actually constraining current pods.
- The `max` constraint (1Gi per container in kip, 512Mi in landing) is the real guardrail:
  it rejects any single container that tries to declare a limit big enough to blow the
  whole namespace quota by itself, explicit resources or not.
- Elasticsearch is exactly the kind of heavy, heterogeneous service this matters for: its
  JVM heap (`ES_JAVA_OPTS`) is set explicitly in `k8s/production/elasticsearch.yaml` rather
  than relying on any namespace default, and sized to match its own `resources.requests`,
  not the local-dev value.
