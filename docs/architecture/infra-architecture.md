# Memosphere Architecture Design

## MVP Architecture Summary

**Chosen MVP Stack:**

- **Authentication**: Amazon Cognito (Free Tier: 50,000 MAUs)
- **Compute**: Kubernetes on EC2 (Manual scaling, cost-effective)
- **Database**: Amazon RDS PostgreSQL (Free Tier: 750 hrs/month on db.t4g.micro)
- **Storage**: Amazon S3 (Free Tier: 5GB)
- **Caching**: Amazon ElastiCache Redis (Optional for MVP)
- **CI/CD**: GitHub Actions + Amazon ECR (Self-hosted runners, zero SaaS cost), EC2-hosted GitHub Runner
- **API Gateway**: NGINX on Kubernetes on EC2 (Free, full control, future-proof)

**Key Benefits:**

- Cost-optimized using AWS Free Tier
- Scalable foundation for future growth
- Full control over infrastructure
- Easy migration path to enterprise solutions

---

## Architecture Comparison

| Option            | Cost (MVP) | Complexity  | Scalability   | Future-Proof | Best For                |
| ----------------- | ---------- | ----------- | ------------- | ------------ | ----------------------- |
| Serverless        | ✅ Lowest  | ✅ Minimal  | ✅ Auto       | ⚠️ Limited   | Solo devs, MVPs         |
| Kubernetes on EC2 | ⚠️ Low–Med | ⚠️ Moderate | ✅ Manual     | ✅ Flexible  | Devs wanting control    |
| Amazon EKS        | ❌ High    | ❌ Complex  | ✅ Enterprise | ✅ Very High | Teams, production scale |

-> Chose Kubernetes on EC2 because it is cheap and future-proof

# Database

# AWS Database Solutions Comparison (2025)

| Solution            | Use Case (Workload Type)                                        | Performance                                                   | Scalability & Architecture                                            | Management                                                   | **Estimated Relative Cost**                                                                                                     |
| ------------------- | --------------------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| **Amazon Aurora**   | **Mission-Critical OLTP**, High-Volume Transactions             | ✅ Extremely High (Up to 5x faster than standard open-source) | ✅ Cloud-Native Auto-Scaling Storage (Up to 128TB), Serverless option | ✅ Very Low (Self-healing, fully managed)                    | **High** (Premium performance, consumption-based)                                                                               |
| **Amazon RDS**      | **General Purpose OLTP**, Standard Web/App Backend              | ✅ Good/Consistent (Engine & Instance Dependent)              | ⚠️ Provisioned Scaling (Vertical & Read Replicas), Up to 64TB storage | ✅ Low (Managed patching, backups, Multi-AZ failover)        | **Low–Medium** — Free Tier covers 750 hrs/month on `db.t4g.micro`, which is **preferred** for better performance and efficiency |
| **Amazon Redshift** | **Data Warehousing/OLAP**, Large-Scale Analytics                | ✅ Very High for Analytical Queries (MPP, Columnar)           | ✅ Cluster Scaling (Node-based), Petabyte scale, Serverless option    | ⚠️ Medium (Need to optimize queries/clusters)                | **Variable (Lo–High)** — Serverless can be cost-efficient; clusters are expensive if always-on                                  |
| **RDBMS on EC2**    | **Full Control**, Specialized Licensing, Unique OS/Engine Needs | ❌ Highly Variable (Dependent on manual setup/tuning)         | ❌ Fully Manual (You manage all clustering, replication, and storage) | ❌ High (You manage OS, patching, security, backups, and HA) | **Lo–Med** (Lowest AWS charges, but **Highest TCO** due to manual labor and maintenance)                                        |

## Authentication Solution

**✅ Chosen: Amazon Cognito with OAuth2 Social Login**

### Key Features

- **Free Tier**: Up to 50,000 monthly active users (MAUs)
- **Scalability**: Fully managed, auto-scales with user base
- **Security**: Offloads password management, supports MFA, adaptive auth, and device tracking

### Supported Providers

- **Built-in**: Google, Facebook, Apple, Amazon
- **Custom**: LinkedIn, X (Twitter) via OpenID Connect or OAuth2
- **Hosted UI**: Optional, simplifies login flow without building custom screens

### MVP Recommendations

- Start with OAuth2 login only (Google, Apple, Facebook)
- Add password-based login later if needed — Cognito supports both
- Avoid SMS-based MFA initially to prevent hidden costs
- Use default Cognito email verification — it's free and secure

# API Gateway Options Comparison (MVP + Future-Proofing)

| Solution               | Cost Model                          | Scalability          | Management Overhead         | Features & Extensibility      | Best For                        |
| ---------------------- | ----------------------------------- | -------------------- | --------------------------- | ----------------------------- | ------------------------------- |
| **NGINX on EC2/K8s**   | ✅ Free (open-source) + EC2 cost    | ✅ High (Kubernetes) | ❌ High (self-managed)      | ✅ Full control, caching, TLS | ✅ Cost-effective, future-proof |
| **Amazon API Gateway** | ❌ Pay-per-request (~$3.50/million) | ✅ Auto-scaled       | ✅ None (fully managed)     | ⚠️ Limited customization      | ⚠️ MVPs, low-traffic apps       |
| **Kong Gateway (OSS)** | ✅ Free (self-hosted)               | ✅ High              | ⚠️ Medium (infra + plugins) | ✅ Plugin-rich, extensible    | Hybrid cloud, microservices     |
| **Envoy + Istio**      | ❌ High (complex mesh)              | ✅ Very High         | ❌ Very High (complex ops)  | ✅ Advanced routing, security | Enterprise-scale service mesh   |
| **Traefik**            | ✅ Free (lightweight)               | ✅ Good              | ⚠️ Medium (simple setup)    | ✅ Dynamic config, TLS        | Lightweight container apps      |

---

## ✅ MVP Recommendation

> Use **NGINX on EC2 with Kubernetes** for your API gateway:

- No per-request billing
- Full control over routing, headers, TLS, and caching
- Scales with your Kubernetes cluster
- Future-proof and extensible

Amazon API Gateway is easier to start with, but costs can grow quickly and customization is limited.

# 🚀 CI/CD Strategy for MVP Deployment

This CI/CD pipeline is designed to be **cost-effective**, **secure**, and **scalable**, using open-source tools and free-tier cloud services. It automates building, storing, and deploying containerized applications to a Kubernetes cluster hosted on EC2.

---

## 🧱 Architecture Overview

| Component          | Tool/Service                 | Role                                      |
| ------------------ | ---------------------------- | ----------------------------------------- |
| Source Control     | GitHub                       | Hosts application code and triggers CI/CD |
| CI/CD Engine       | GitHub Actions (self-hosted) | Automates build/test/deploy workflows     |
| Build Agent        | EC2-hosted GitHub Runner     | Executes CI jobs without billing minutes  |
| Container Registry | Amazon ECR                   | Stores private Docker images              |
| Deployment Target  | Kubernetes on EC2            | Hosts application workloads               |
| Secrets Management | GitHub Secrets / SOPS        | Secures credentials and tokens            |

---

## 🔄 CI/CD Workflow Steps

1. **Code Push to GitHub**
   - Developer pushes code to main or feature branch

2. **GitHub Actions Trigger**
   - Workflow starts on push or pull request
   - Runs on self-hosted runner (EC2) to avoid GitHub billing

3. **Build Docker Image**
   - Uses multi-stage Dockerfile to minimize image size
   - Tags image with commit SHA or `latest`

4. **Push to Amazon ECR**
   - Authenticates using IAM credentials
   - Stores image in private ECR repository (same region as EC2)

5. **Deploy to Kubernetes**
   - Uses `kubectl` or Helm to apply updated manifests
   - Optionally uses rolling updates or blue/green strategy

6. **Monitor & Rollback**
   - Logs and metrics via Prometheus/Grafana (optional)
   - Rollback via GitHub Actions or manual `kubectl`

---

## 💸 Cost Optimization

| Resource           | Strategy                  | Notes                                         |
| ------------------ | ------------------------- | --------------------------------------------- |
| GitHub Actions     | Self-hosted runner on EC2 | Unlimited minutes, no SaaS cost               |
| Amazon ECR         | Free tier (500 MB/month)  | Delete old images to stay lean                |
| EC2 Data Transfer  | Same-region ECR + GitHub  | Avoid cross-region and large outbound traffic |
| Kubernetes Cluster | EC2-based, no EKS billing | Manual scaling and updates                    |

---

## 🔐 Security Best Practices

- Use **private ECR repositories**
- Store secrets in **GitHub Secrets** or encrypted with **SOPS**
- Restrict IAM permissions to **least privilege**
- Scan images with **Trivy** or **Snyk** before deployment

---

## ✅ MVP Summary

> This CI/CD setup is ideal for MVPs:
>
> - Fully automated
> - Zero SaaS cost
> - Secure and private
> - Scales with your EC2 and Kubernetes footprint

# Message Queue (Job Dispatch)

**Current**: Redis Streams with consumer groups (`memosphere_messaging.RedisStreamsBroker`), used for `jobs:generate-questions`. Chosen for MVP because it's already-running infra (zero new service). The `Broker` Protocol is the seam — application code (workers, services) never touches Redis directly, so swapping the transport is contained to one new class.

**Known gap (found 2026-07-11)**: dev Redis runs without AOF, and `docker compose down -v` wipes the named volume — a stuck/pending job can be lost outright. Also, `consume_once` never redelivered pending entries despite the module's docstring promising it; `reclaim_stale()` (XAUTOCLAIM-based) plus a `generation_job_completions` idempotency table now cover automatic retry without double-counting quiz progress. This closes the _automatic-retry_ gap; it does not by itself fix the _volume-gets-deleted_ durability gap below.

**Options for production durability** (evaluated 2026-07-11, undecided):

| Option                                 | Cost                                                                                                      | Dev/Prod Parity                                                                                        | Notes                                                                                                                             |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| Self-hosted Redis + AOF                | ~$0–2/mo marginal                                                                                         | Same code path everywhere                                                                              | Cheapest, but ops burden (backups, HA, the `down -v` footgun) stays in-house                                                      |
| AWS SQS                                | ~$0/mo at low volume; ~$40/mo per 100M requests, ~$120/mo per 100M actual jobs (3 requests/job lifecycle) | New `SQSBroker` needed — dev (Redis) and prod (SQS) diverge unless dev also runs SQS (e.g. LocalStack) | Cheapest managed option; fully durable; built-in DLQ/redrive replaces `reclaim_stale()`                                           |
| AWS MemoryDB for Redis                 | ~$44/mo single node (no HA); ~$630+/mo real Multi-AZ cluster                                              | Same `RedisStreamsBroker` code everywhere — only the connection target changes                         | Most expensive; purpose-built for durability (not just cache+AOF)                                                                 |
| ElastiCache for Redis (persistence on) | ~$12/mo smallest node                                                                                     | Same code path                                                                                         | Cache product with AOF bolted on, not a durable-by-design primary store                                                           |
| RabbitMQ (self-hosted)                 | ~$0–2/mo marginal                                                                                         | Same-broker parity if kept everywhere                                                                  | Ruled out: a _third_ stateful service to operate with no existing foothold (team already runs Redis, already has AWS via Cognito) |

AWS is already in the stack (Cognito for auth), which favors SQS or MemoryDB over introducing a wholly new vendor. **No decision made yet** — revisit before this queue needs to carry production volume.

# AI/ML Services

**Primary Choice: Mistral Large API**

- Handles all LLM tasks (question generation, summarization)
- Can perform text preprocessing (key phrases, entities, syntax analysis)
- Single API for all AI needs
- Cost-effective for MVP

**Future: Amazon Comprehend** (only if needed)

- For high-volume text preprocessing
- When you need faster, specialized NLP tasks
- Custom model training requirements
