# Day 9: Vector Upsert & Query Test

## Setup

- **Collection:** `coverage_kb` (ChromaDB, initialized on Day 8)
- **Embeddings source:** `embeddings.npy` (generated on Day 7)
- **Knowledge base:** `knowledge_base.jsonl` (built on Day 6)
- **Batch size:** 100 records per upsert call

## Upsert Summary

```python
import chromadb
import numpy as np
import json

client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection(name="coverage_kb")

embeddings = np.load("embeddings.npy")

chunks = []
with open("knowledge_base.jsonl") as f:
    for line in f:
            chunks.append(json.loads(line))

            BATCH_SIZE = 100
            for i in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[i:i+BATCH_SIZE]
                    collection.add(
                            ids=[c["id"] for c in batch],
                                    embeddings=embeddings[i:i+BATCH_SIZE].tolist(),
                                            documents=[c["text"] for c in batch],
                                                    metadatas=[{"plan_type": c["plan_type"], "section": c["section"], "source": c["source"]} for c in batch],
                                                        )

                                                        print("Total chunks in collection:", collection.count())
                                                        ```

                                                        **Output:** Total chunks in collection: 23

                                                        ---

                                                        ## Test Query 1 — Unfiltered

                                                        **Query:** "Is physical therapy covered under the Silver plan?"

                                                        ```python
                                                        import sentence_transformers

                                                        model = sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")
                                                        query_embedding = model.encode(["Is physical therapy covered under the Silver plan?"])

                                                        results = collection.query(
                                                            query_embeddings=query_embedding.tolist(),
                                                                n_results=5,
                                                                )
                                                                ```

                                                                ### Returned Chunks (Unfiltered)

                                                                | Rank | ID | Plan Type | Section | Distance | Relevant? |
                                                                |------|----|-----------|---------|----------|-----------|
                                                                | 1 | silver_benefits_chunk_3 | Silver | Physical Therapy | 0.18 | ✅ Yes |
                                                                | 2 | silver_benefits_chunk_7 | Silver | Specialist Visits | 0.27 | ✅ Yes |
                                                                | 3 | gold_benefits_chunk_4 | Gold | Physical Therapy | 0.31 | ⚠️ Different plan |
                                                                | 4 | silver_benefits_chunk_12 | Silver | Out-of-Pocket Max | 0.38 | ✅ Partial |
                                                                | 5 | bronze_benefits_chunk_2 | Bronze | Physical Therapy | 0.42 | ⚠️ Different plan |

                                                                ### Chunk 1 Text (Rank 1)
                                                                > "Under the Silver plan, physical therapy is covered at 80% after the deductible is met. Members are entitled to up to 30 visits per year. Prior authorization is required for visits beyond the initial 6."

                                                                ### Chunk 2 Text (Rank 2)
                                                                > "Silver plan members may be referred to in-network physical therapists by their primary care physician. Co-pay is $40 per specialist visit after deductible."

                                                                ### Chunk 3 Text (Rank 3)
                                                                > "Gold plan members receive physical therapy coverage at 90% after deductible, with 60 visits per year allowed. Prior authorization required after 10 visits."

                                                                ### Chunk 4 Text (Rank 4)
                                                                > "The Silver plan has an out-of-pocket maximum of $7,000 per individual and $14,000 per family per plan year. All in-network covered services apply toward this maximum."

                                                                ### Chunk 5 Text (Rank 5)
                                                                > "Bronze plan physical therapy coverage begins after the deductible is met (50% coinsurance). Limited to 20 visits per year."

                                                                **Analysis:**
                                                                - Ranks 1, 2, 4 are Silver-plan-specific and directly relevant ✅
                                                                - Ranks 3, 5 are physical therapy results but from Gold and Bronze plans ⚠️
                                                                - The unfiltered query returns mixed-plan results — metadata filtering is needed for precision

                                                                ---

                                                                ## Test Query 2 — Filtered by plan_type: Silver

                                                                ```python
                                                                filtered_results = collection.query(
                                                                    query_embeddings=query_embedding.tolist(),
                                                                        n_results=5,
                                                                            where={"plan_type": "Silver"},
                                                                            )
                                                                            ```

                                                                            ### Returned Chunks (Filtered — Silver only)

                                                                            | Rank | ID | Plan Type | Section | Distance | Relevant? |
                                                                            |------|----|-----------|---------|----------|-----------|
                                                                            | 1 | silver_benefits_chunk_3 | Silver | Physical Therapy | 0.18 | ✅ Yes |
                                                                            | 2 | silver_benefits_chunk_7 | Silver | Specialist Visits | 0.27 | ✅ Yes |
                                                                            | 3 | silver_benefits_chunk_12 | Silver | Out-of-Pocket Max | 0.38 | ✅ Partial |
                                                                            | 4 | silver_benefits_chunk_1 | Silver | Preventive Care | 0.44 | ✅ Partial |
                                                                            | 5 | silver_benefits_chunk_9 | Silver | Deductible | 0.51 | ✅ Partial |

                                                                            **Analysis:**
                                                                            - All 5 results are Silver-plan-specific ✅
                                                                            - Top 2 directly address physical therapy coverage ✅
                                                                            - Ranks 3–5 provide supporting context (deductible, OOP max) relevant to understanding full coverage ✅
                                                                            - Metadata filter successfully scopes retrieval to one plan ✅

                                                                            ---

                                                                            ## Comparison: Filtered vs Unfiltered

                                                                            | | Unfiltered | Filtered (Silver) |
                                                                            |--|------------|-------------------|
                                                                            | Silver-plan results | 3 / 5 | 5 / 5 |
                                                                            | Direct PT coverage hits | 1 | 2 |
                                                                            | Cross-plan noise | 2 chunks | 0 |

                                                                            **Conclusion:** Metadata filtering significantly improves precision for plan-specific queries. For a RAG pipeline, filtering by `plan_type` should be applied whenever the query targets a specific plan.

                                                                            ---

                                                                            ## Retrieval Misses

                                                                            - The unfiltered query surfaced Gold and Bronze plan chunks due to semantic similarity of physical therapy text across plans
                                                                            - No critical Silver-plan chunks were missing from filtered results
                                                                            - The `silver_benefits_chunk_3` (primary PT chunk) ranked #1 in both queries — embedding quality is good

                                                                            ---

                                                                            ## collection.count() Verification

                                                                            ```
                                                                            collection.count() → 23
                                                                            len(chunks) → 23
                                                                            ✅ Index size matches chunk count
                                                                            ```
