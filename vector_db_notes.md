# Vector Database Comparison & Decision

## Overview

Vector databases store high-dimensional embeddings and enable fast similarity search. Below is a comparison of the major options evaluated for this program.

---

## Comparison Table

| Feature | Chroma | Pinecone | FAISS | Weaviate | Milvus |
|---|---|---|---|---|---|
| **Hosting** | Local / self-hosted | Fully managed cloud | Local / self-hosted | Self-hosted or cloud | Self-hosted or cloud |
| **Cost** | Free | Free tier (serverless), paid at scale | Free (library) | Free OSS, paid cloud | Free OSS, paid cloud |
| **Setup complexity** | Very low (`pip install chromadb`) | Low (API key + index creation) | Medium (manual indexing code) | Medium (Docker or cloud) | High (distributed setup) |
| **Persistence** | Local disk (SQLite + files) | Cloud (fully managed) | In-memory (manual save/load) | Local or cloud | Local or cloud |
| **Indexing algorithm** | HNSW | HNSW (managed) | IVF + HNSW | HNSW | IVF, HNSW, FLAT |
| **Python client** | `chromadb` | `pinecone` | `faiss` | `weaviate-client` | `pymilvus` |
| **Metadata filtering** | Yes | Yes | Limited | Yes | Yes |
| **Multi-tenancy / namespaces** | Collections | Namespaces | None native | Multi-tenancy | Partitions |
| **Access control (enterprise)** | Basic (app-level) | RBAC via Pinecone Control | None native | OIDC/RBAC | RBAC + LDAP |
| **Best for** | Local dev, prototypes | Serverless production | Research / offline | Production w/ rich schema | Large-scale production |

---

## Indexing Algorithms (High Level)

**HNSW (Hierarchical Navigable Small World):** Graph-based index. Builds a multi-layer proximity graph so searches hop between layers for fast approximate nearest-neighbor retrieval. Great balance of speed and recall; used by Chroma and Pinecone under the hood.

**IVF (Inverted File Index):** Partitions the vector space into clusters (Voronoi cells). At search time, only the nearest clusters are scanned. More memory-efficient at large scale but requires a training step. Used by FAISS and Milvus.

---

## Enterprise Access Control Considerations

For enterprise workloads, access control is critical — especially in healthcare/insurance contexts where documents may contain PHI or confidential plan data.

- **Pinecone** provides project-level API keys and supports namespace-level isolation, with RBAC available on enterprise plans. This allows different teams or clients to be scoped to separate namespaces without sharing data.
- **Weaviate and Milvus** support OIDC-based authentication and role-based access control, making them suitable for multi-tenant enterprise deployments where fine-grained permissions per collection/user are required.
- **Chroma** handles access control at the application layer — the developer is responsible for enforcing who can query which collection. This is fine for single-tenant local or internal tools but requires additional infrastructure (e.g., an auth proxy) for multi-tenant enterprise use.

For a production enterprise deployment with strict access-control requirements, Pinecone (managed) or Weaviate (self-hosted with OIDC) would be preferable over Chroma.

---

## Decision: Chroma for This Program

For this cohort project, **Chroma** is the recommended choice going forward. It installs with a single `pip install chromadb`, requires no account or API key, persists data locally with zero configuration, and integrates cleanly with Python — making it ideal for rapid prototyping and learning. The `coverage_kb` collection we create locally mirrors what a production vector DB would hold, letting us focus on the RAG pipeline logic rather than infrastructure. Once the system needs to scale beyond a single machine or serve multiple users with access control requirements, migrating to Pinecone serverless or Weaviate would be a natural next step, but for the scope of this program, Chroma's simplicity and zero cost make it the right tool.

---

## Collection Setup (Chroma)

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection(name="coverage_kb")
print(f"Collection '{collection.name}' ready. Count: {collection.count()}")
```

Collection name: `coverage_kb`

## Pinecone Index (for comparison)

Created a free serverless index on Pinecone (us-east-1, dimension=384, metric=cosine) named `coverage-kb` for comparison purposes. Left empty — Chroma is used for all subsequent days.
