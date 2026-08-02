"""
Day 5/6 - Chunk unstructured policy text + structured plan rows into a
single knowledge base for retrieval.

Inputs:
  - raw_text/benefits.txt, raw_text/claims_process.txt, raw_text/enrollment.txt
  - data/plans.csv  (Day 4 structured output)

Output:
  - knowledge_base.jsonl   (one JSON chunk record per line)

Chunking:
  - RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
  - Applied PER SECTION (not across the whole file), so a section like
    "Exclusions" never gets merged into "Covered Services" or "Claims
    Process" — sections are split on "## Header" markers first, then each
    section's text is run through the splitter independently.

Every chunk record has the schema:
  {
    "id": "...",
    "text": "...",
    "source_file": "...",
    "source_type": "structured|unstructured",
    "plan_type": "...",
    "section": "coverage|exclusions|claims|enrollment",
    "ingested_at": "..."
  }
"""
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter

RAW_TEXT_DIR = Path("raw_text")
PLANS_CSV = Path("data/plans.csv")
OUTPUT_PATH = Path("knowledge_base.jsonl")

# maps a lowercased "## Header" string (or the file's default preamble
# section) to the canonical section tag required by the schema
SECTION_TAG_MAP = {
    "covered services": "coverage",
    "member cost-sharing summary": "coverage",
    "exclusions": "exclusions",
    "claims process": "claims",
    "appeals": "claims",
    "reimbursement and payment": "claims",
    "enrollment": "enrollment",
    "dependent coverage": "enrollment",
    "effective dates and termination": "enrollment",
}

# fallback section for text that appears before the first "## Header"
# (e.g. the document title block), keyed by filename stem
DEFAULT_SECTION_BY_FILE = {
    "benefits": "coverage",
    "claims_process": "claims",
    "enrollment": "enrollment",
}

NETWORK_BY_PLAN_TYPE = {
    "HMO": "regional",
    "PPO": "national",
    "EPO": "select regional",
}

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def split_into_sections(raw_text: str, default_section: str):
    """Split a document on '## Header' markers into (section_tag, text) blocks."""
    parts = re.split(r"(?m)^##\s+(.+)$", raw_text)
    # parts[0] is the preamble before the first header
    blocks = []
    preamble = parts[0].strip()
    if preamble:
        blocks.append((default_section, preamble))
    for i in range(1, len(parts), 2):
        header = parts[i].strip().lower()
        body = parts[i + 1].strip()
        tag = SECTION_TAG_MAP.get(header, default_section)
        if body:
            blocks.append((tag, body))
    return blocks


def chunk_unstructured():
    chunks = []
    for txt_path in sorted(RAW_TEXT_DIR.glob("*.txt")):
        stem = txt_path.stem
        default_section = DEFAULT_SECTION_BY_FILE.get(stem, "coverage")
        raw_text = txt_path.read_text(encoding="utf-8")

        for section_tag, section_text in split_into_sections(raw_text, default_section):
            pieces = splitter.split_text(section_text)
            for i, piece in enumerate(pieces):
                chunks.append({
                    "id": f"{stem}-{section_tag}-{i:03d}",
                    "text": piece.strip(),
                    "source_file": str(txt_path.as_posix()),
                    "source_type": "unstructured",
                    "plan_type": None,
                    "section": section_tag,
                    "ingested_at": now_iso(),
                })
    return chunks


def chunk_structured_plans():
    chunks = []
    df = pd.read_csv(PLANS_CSV)
    df = df.drop_duplicates(subset="plan_id", keep="first")

    for _, row in df.iterrows():
        plan_type = str(row["plan_type"])
        network = NETWORK_BY_PLAN_TYPE.get(plan_type, "national")
        premium = row["monthly_premium"]
        deductible = row["deductible"]
        coinsurance = row["coinsurance_pct"]

        text = (
            f"{row['plan_name']}: ${premium}/month premium, "
            f"${deductible} deductible, {coinsurance}% coinsurance, "
            f"out-of-pocket max ${row['out_of_pocket_max']}, "
            f"primary care copay ${row['copay_primary_care']}, "
            f"specialist copay ${row['copay_specialist']}, "
            f"network: {network}."
        )

        chunks.append({
            "id": f"plan-{row['plan_id']}",
            "text": text,
            "source_file": str(PLANS_CSV.as_posix()),
            "source_type": "structured",
            "plan_type": plan_type,
            "section": "coverage",
            "ingested_at": now_iso(),
        })
    return chunks


def sanity_check(chunks):
    print(f"\nTotal chunks: {len(chunks)}")
    by_section = {}
    for c in chunks:
        by_section[c["section"]] = by_section.get(c["section"], 0) + 1
    print("By section:", by_section)

    sample = random.sample(chunks, min(5, len(chunks)))
    print("\n--- 5 random chunks for manual review ---")
    for c in sample:
        print(f"\n[{c['id']}] section={c['section']} source_type={c['source_type']}")
        print(c["text"])

    # flag chunks that look like they might be cut mid-sentence:
    # doesn't end in terminal punctuation and isn't the last chunk of its section
    suspicious = [
        c for c in chunks
        if c["text"] and c["text"][-1] not in ".!?\"')"
        and c["source_type"] == "unstructured"
    ]
    print(f"\nChunks not ending on terminal punctuation (review these): {len(suspicious)}")
    for c in suspicious:
        print(f"  [{c['id']}] ...{c['text'][-80:]}")


def main():
    random.seed(7)
    chunks = chunk_unstructured() + chunk_structured_plans()

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"Wrote {len(chunks)} chunks to {OUTPUT_PATH}")
    sanity_check(chunks)


if __name__ == "__main__":
    main()
