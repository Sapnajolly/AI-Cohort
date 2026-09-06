# Day 29 — Kubernetes / Minikube Notes

## 1. Start the cluster and load Day 28's images

```
minikube start
eval $(minikube docker-env)          # point the local docker CLI at Minikube's daemon
docker compose build                 # rebuilds coverage-chatbot-backend / -frontend inside Minikube's docker
```

Using `minikube docker-env` avoids pushing to a registry — the images
built by Day 28's `docker-compose.yml` become directly visible to the
cluster, which is why both Deployments set `imagePullPolicy: IfNotPresent`
instead of trying to pull from a remote registry.

## 2. Create the Secret (never committed to git)

```
kubectl create secret generic coverage-chatbot-secrets \
  --from-literal=OPENAI_API_KEY=your-key-here \
  --from-literal=ANTHROPIC_API_KEY=your-key-here
```

Both `backend-deployment.yaml` and `frontend-deployment.yaml` reference it
via `envFrom: secretRef: name: coverage-chatbot-secrets` — no key value
ever appears in the YAML files themselves.

## 3. Apply the manifests

```
kubectl apply -f k8s/
```

Expected:
```
deployment.apps/coverage-chatbot-backend created
service/coverage-chatbot-backend created
deployment.apps/coverage-chatbot-frontend created
service/coverage-chatbot-frontend created
```

```
kubectl get pods
NAME                                          READY   STATUS    RESTARTS
coverage-chatbot-backend-6d8f7c9b7-abcde      1/1     Running   0
coverage-chatbot-backend-6d8f7c9b7-fghij      1/1     Running   0
coverage-chatbot-frontend-7c5d4f8b6-klmno     1/1     Running   0
```

2 backend replicas come up per `backend-deployment.yaml`'s `replicas: 2`,
both passing the `/health` readiness probe before receiving traffic.

## 4. Scale to 3

```
kubectl scale deployment coverage-chatbot-backend --replicas=3
kubectl get pods -l app=coverage-chatbot-backend
```

Expected: a third `coverage-chatbot-backend-*` pod appears and moves from
`ContainerCreating` -> `Running` -> ready (readiness probe passing) within
the `initialDelaySeconds: 5` / `periodSeconds: 10` window configured in
the Deployment.

```
kubectl get deployment coverage-chatbot-backend
NAME                       READY   UP-TO-DATE   AVAILABLE
coverage-chatbot-backend   3/3     3            3
```

## 5. Rolling update

Simulated a new backend image version (e.g. after a code change + rebuild):

```
docker compose build backend
kubectl set image deployment/coverage-chatbot-backend backend=coverage-chatbot-backend:latest
kubectl rollout status deployment/coverage-chatbot-backend
```

Expected:
```
Waiting for deployment "coverage-chatbot-backend" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "coverage-chatbot-backend" rollout to finish: 2 out of 3 new replicas have been updated...
deployment "coverage-chatbot-backend" successfully rolled out
```

Because `readinessProbe` is set, Kubernetes's default rolling-update
strategy brings up new pods and waits for them to pass `/health` before
terminating old ones — so `kubectl get pods` never drops below 3 ready
backend pods during the rollout (no downtime).

Rollback (if the rollout had gone wrong):
```
kubectl rollout undo deployment/coverage-chatbot-backend
```

## 6. Access the frontend

```
minikube service coverage-chatbot-frontend
```

Opens the NodePort service (`nodePort: 30851`) in the browser, hitting
the Streamlit UI, which reaches the backend at
`http://coverage-chatbot-backend:8000` — the backend's in-cluster Service
DNS name, set via the `API_URL` env var in `frontend-deployment.yaml`.

## 7. Teardown

```
kubectl delete -f k8s/
kubectl delete secret coverage-chatbot-secrets
minikube stop
```

Expected:
```
deployment.apps "coverage-chatbot-backend" deleted
service "coverage-chatbot-backend" deleted
deployment.apps "coverage-chatbot-frontend" deleted
service "coverage-chatbot-frontend" deleted
secret "coverage-chatbot-secrets" deleted
```

`kubectl get pods` afterward returns `No resources found`, confirming a
clean teardown — no orphaned pods, services, or secrets left in the
cluster.

## Notes

- Started with 2 backend replicas per the mission spec, scaled to 3 to
  practice horizontal scaling, then rolled an image update through
  without downtime (readiness probe gates traffic to new pods).
- The Secret is created imperatively via `kubectl create secret` and is
  **not** committed anywhere in this repo — only the `envFrom`/`secretRef`
  reference to its name lives in the YAML.
