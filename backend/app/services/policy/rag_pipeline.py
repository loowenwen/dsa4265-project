from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
import torch
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

LOGGER = logging.getLogger(__name__)

REQUIRED_CHUNK_FIELDS = {
    "chunk_id",
    "section_header",
    "category",
    "loan_type",
    "title",
    "text",
    "keywords",
}

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_GENERATOR_MODEL = "Qwen/Qwen2.5-3B-Instruct"
DEFAULT_PERSIST_DIR = "chroma_underwriting_policy_db"
DEFAULT_COLLECTION_NAME = "underwriting_policy_rag_collection"
DEFAULT_CHUNK_PATH = Path(__file__).resolve().with_name("chunk_already.json")

EXAMPLE_POLICY_QUERIES = [
    "What does the policy say about LTV ratios for residential mortgage loans?",
    "How should rental housing applicants be underwritten?",
    "When should an application be escalated to manual review?",
    "What are the valuation requirements for mortgage collateral?",
    "How are borrowers' debt serviceability ratios assessed?",
    "What standards apply to applicants under other housing status?",
]


@dataclass(slots=True)
class PolicyRAGConfig:
    chunk_path: str | Path = DEFAULT_CHUNK_PATH
    persist_dir: str | Path = DEFAULT_PERSIST_DIR
    collection_name: str = DEFAULT_COLLECTION_NAME
    embedding_model_name: str = DEFAULT_EMBEDDING_MODEL
    reranker_model_name: str = DEFAULT_RERANKER_MODEL
    generator_model_name: str = DEFAULT_GENERATOR_MODEL
    generation_max_new_tokens: int = 350
    generation_temperature: float = 0.0
    generation_top_p: float = 0.95
    fast_agent_mode: bool = False
    force_fallback_retrievers: bool = False
    disable_reranker: bool = False
    disable_generator: bool = False
    default_top_k: int = 3
    default_semantic_k: int = 10
    default_keyword_k: int = 10

    @classmethod
    def fast_agent(
        cls,
        chunk_path: str | Path = DEFAULT_CHUNK_PATH,
        persist_dir: str | Path = DEFAULT_PERSIST_DIR,
        collection_name: str = DEFAULT_COLLECTION_NAME,
    ) -> "PolicyRAGConfig":
        """Preset tuned for low-latency agent retrieval over a small policy corpus."""
        return cls(
            chunk_path=chunk_path,
            persist_dir=persist_dir,
            collection_name=collection_name,
            fast_agent_mode=True,
            force_fallback_retrievers=True,
            disable_reranker=True,
            disable_generator=True,
            default_top_k=2,
            default_semantic_k=4,
            default_keyword_k=4,
        )


@dataclass(slots=True)
class Document:
    """Lightweight replacement for a LangChain Document."""

    page_content: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class BM25Index:
    bm25: Any
    documents: list[Document]
    tokenized_corpus: list[list[str]]


@dataclass(slots=True)
class GeneratorBundle:
    model_name: str
    tokenizer: Any
    model: Any
    device: str


@dataclass(slots=True)
class LocalVectorDB:
    """Persisted dense index with a Chroma-like interface for similarity search."""

    collection_name: str
    persist_dir: Path
    documents: list[Document]
    ids: list[str]
    embeddings_matrix: Any
    embedding_model: Any

    def similarity_search_with_relevance_scores(
        self,
        query: str,
        k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        query_vector = self.embedding_model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=False,
            show_progress_bar=False,
        )[0]

        ranked: list[tuple[Document, float]] = []
        for index, doc_vector in enumerate(self.embeddings_matrix):
            doc = self.documents[index]
            if passes_filters(doc, filter):
                ranked.append((doc, float(_vector_dot(doc_vector, query_vector))))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked[:k]

    def persist(self) -> None:
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        embeddings_path = self.persist_dir / f"{self.collection_name}_embeddings.json"
        docs_path = self.persist_dir / f"{self.collection_name}_documents.json"

        embeddings_path.write_text(json.dumps(self.embeddings_matrix, ensure_ascii=False) + "\n", encoding="utf-8")
        docs_payload = [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in self.documents
        ]
        docs_path.write_text(json.dumps(docs_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@dataclass(slots=True)
class TfidfEmbeddingModel:
    """Dense-retrieval fallback that avoids torch/sentence-transformers."""

    model_name: str = "tfidf-fallback"
    idf: dict[str, float] | None = None

    def fit(self, texts: list[str]) -> "TfidfEmbeddingModel":
        document_count = len(texts)
        doc_frequency: dict[str, int] = {}
        for text in texts:
            unique_terms = set(self._tokenize(text))
            for term in unique_terms:
                doc_frequency[term] = doc_frequency.get(term, 0) + 1

        self.idf = {
            term: 1.0 + __import__("math").log((1 + document_count) / (1 + frequency))
            for term, frequency in doc_frequency.items()
        }
        return self

    def encode(
        self,
        texts: list[str],
        normalize_embeddings: bool = True,
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
    ) -> Any:
        if self.idf is None:
            raise ValueError("The TF-IDF embedding model must be fitted before encode() is called.")

        vectors = [self._encode_one(text, normalize_embeddings=normalize_embeddings) for text in texts]
        return vectors

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({"idf": self.idf}, ensure_ascii=False) + "\n", encoding="utf-8")

    def load(self, path: Path) -> "TfidfEmbeddingModel":
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.idf = {str(key): float(value) for key, value in payload["idf"].items()}
        return self

    def _tokenize(self, text: str) -> list[str]:
        base_tokens = tokenize_for_bm25(text)
        bigrams = [f"{base_tokens[index]}_{base_tokens[index + 1]}" for index in range(len(base_tokens) - 1)]
        return base_tokens + bigrams

    def _encode_one(self, text: str, normalize_embeddings: bool) -> dict[str, float]:
        import math

        tf_counts: dict[str, int] = {}
        for token in self._tokenize(text):
            if token not in self.idf:
                continue
            tf_counts[token] = tf_counts.get(token, 0) + 1

        weighted = {token: count * self.idf[token] for token, count in tf_counts.items()}
        if not normalize_embeddings or not weighted:
            return weighted

        norm = math.sqrt(sum(value * value for value in weighted.values()))
        if norm == 0:
            return weighted
        return {token: value / norm for token, value in weighted.items()}


@dataclass(slots=True)
class SimpleBM25Okapi:
    """Pure-Python BM25 implementation used when rank_bm25/numpy are unavailable."""

    tokenized_corpus: list[list[str]]
    k1: float = 1.5
    b: float = 0.75
    doc_count: int = 0
    doc_lengths: list[int] | None = None
    avgdl: float = 0.0
    term_frequencies: list[dict[str, int]] | None = None
    idf: dict[str, float] | None = None

    def __post_init__(self) -> None:
        import math

        self.doc_count = len(self.tokenized_corpus)
        self.doc_lengths = [len(doc) for doc in self.tokenized_corpus]
        self.avgdl = sum(self.doc_lengths) / self.doc_count if self.doc_count else 0.0

        self.term_frequencies: list[dict[str, int]] = []
        document_frequency: dict[str, int] = {}
        for doc in self.tokenized_corpus:
            tf: dict[str, int] = {}
            for token in doc:
                tf[token] = tf.get(token, 0) + 1
            self.term_frequencies.append(tf)
            for token in tf:
                document_frequency[token] = document_frequency.get(token, 0) + 1

        self.idf = {
            token: math.log(1 + (self.doc_count - freq + 0.5) / (freq + 0.5))
            for token, freq in document_frequency.items()
        }

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        scores: list[float] = []
        for index, tf in enumerate(self.term_frequencies):
            score = 0.0
            doc_length = self.doc_lengths[index]
            norm = self.k1 * (1 - self.b + self.b * doc_length / self.avgdl) if self.avgdl else self.k1
            for token in query_tokens:
                frequency = tf.get(token, 0)
                if frequency == 0:
                    continue
                idf = self.idf.get(token, 0.0)
                numerator = frequency * (self.k1 + 1)
                denominator = frequency + norm
                score += idf * (numerator / denominator)
            scores.append(score)
        return scores


def _normalize_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _coerce_vectors(vectors: Any) -> list[Any]:
    coerced: list[Any] = []
    for vector in vectors:
        if hasattr(vector, "tolist"):
            coerced.append(vector.tolist())
        else:
            coerced.append(vector)
    return coerced


def _vector_dot(left: Any, right: Any) -> float:
    if isinstance(left, dict) and isinstance(right, dict):
        shared = set(left).intersection(right)
        return sum(float(left[key]) * float(right[key]) for key in shared)

    if hasattr(left, "tolist"):
        left = left.tolist()
    if hasattr(right, "tolist"):
        right = right.tolist()

    return sum(float(a) * float(b) for a, b in zip(left, right))


def load_chunks(path: str | Path) -> list[dict[str, Any]]:
    """Load chunk records from JSON and skip malformed entries with warnings."""
    chunk_path = Path(path)
    if not chunk_path.exists():
        raise FileNotFoundError(f"Chunk file not found: {chunk_path}")

    raw_data = json.loads(chunk_path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, list):
        raise ValueError(f"Expected a JSON list in {chunk_path}, got {type(raw_data).__name__}")

    valid_records: list[dict[str, Any]] = []
    for index, record in enumerate(raw_data, start=1):
        if not isinstance(record, dict):
            LOGGER.warning("Skipping non-dict record at index %s", index)
            continue
        if validate_chunk_record(record):
            valid_records.append(record)
        else:
            record_id = record.get("chunk_id", f"index_{index}")
            LOGGER.warning("Skipping invalid chunk record: %s", record_id)

    if not valid_records:
        raise ValueError(f"No valid chunk records found in {chunk_path}")

    return valid_records


def validate_chunk_record(record: dict[str, Any]) -> bool:
    """Return True when a chunk record matches the expected policy schema."""
    missing = REQUIRED_CHUNK_FIELDS - record.keys()
    if missing:
        return False

    for field in REQUIRED_CHUNK_FIELDS - {"keywords"}:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            return False

    keywords = record.get("keywords")
    if not isinstance(keywords, list) or not keywords:
        return False
    if any(not isinstance(keyword, str) or not keyword.strip() for keyword in keywords):
        return False

    return True


def to_langchain_documents(records: list[dict[str, Any]]) -> list[Document]:
    """
    Convert policy chunk records into lightweight Document objects.

    The function name is kept for compatibility with downstream agent expectations.
    """
    documents: list[Document] = []
    for record in records:
        if not validate_chunk_record(record):
            LOGGER.warning("Skipping invalid record during Document conversion: %s", record.get("chunk_id"))
            continue
        metadata = {key: value for key, value in record.items() if key != "text"}
        documents.append(Document(page_content=record["text"], metadata=metadata))

    if not documents:
        raise ValueError("No valid documents could be created from the chunk records.")

    return documents


def get_embedding_model(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    prefer_fallback: bool = False,
) -> Any:
    """Load the sentence-transformer embedder used for dense retrieval."""
    if prefer_fallback:
        return TfidfEmbeddingModel(model_name="tfidf-fallback")

    try:
        import torch
        from sentence_transformers import SentenceTransformer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        return SentenceTransformer(model_name, device=device)
    except Exception as exc:
        LOGGER.warning(
            "Sentence-transformer embeddings unavailable, using TF-IDF fallback dense retriever: %s",
            exc,
        )
        return TfidfEmbeddingModel(model_name="tfidf-fallback")


def _vector_store_paths(persist_dir: str | Path, collection_name: str) -> tuple[Path, Path, Path]:
    base_dir = Path(persist_dir)
    return (
        base_dir / f"{collection_name}_embeddings.json",
        base_dir / f"{collection_name}_documents.json",
        base_dir / f"{collection_name}_embedding_model.json",
    )


def _load_local_vectordb(
    persist_dir: str | Path,
    collection_name: str,
    embedding_model: Any,
) -> LocalVectorDB | None:
    embeddings_path, docs_path, model_path = _vector_store_paths(persist_dir, collection_name)
    if not embeddings_path.exists() or not docs_path.exists():
        return None

    if hasattr(embedding_model, "load") and model_path.exists():
        embedding_model.load(model_path)

    embeddings_matrix = json.loads(embeddings_path.read_text(encoding="utf-8"))
    docs_payload = json.loads(docs_path.read_text(encoding="utf-8"))
    documents = [
        Document(page_content=item["page_content"], metadata=item["metadata"])
        for item in docs_payload
    ]
    ids = [doc.metadata["chunk_id"] for doc in documents]

    return LocalVectorDB(
        collection_name=collection_name,
        persist_dir=Path(persist_dir),
        documents=documents,
        ids=ids,
        embeddings_matrix=embeddings_matrix,
        embedding_model=embedding_model,
    )


def build_or_load_vectordb(
    documents: list[Document],
    persist_dir: str | Path,
    collection_name: str,
    rebuild: bool = False,
    embeddings: Any | None = None,
) -> LocalVectorDB:
    """
    Build or load a persisted dense vector index.

    This keeps the original function contract while avoiding the LangChain/Chroma
    runtime path that is broken in the current macOS environment.
    """
    persist_path = Path(persist_dir)
    if embeddings is None:
        embeddings = get_embedding_model()

    if rebuild and persist_path.exists():
        shutil.rmtree(persist_path)

    if not rebuild:
        existing = _load_local_vectordb(persist_dir, collection_name, embeddings)
        if existing is not None:
            return existing

    if not documents:
        raise ValueError("Cannot build a vector database without documents.")

    text_batch = [doc.page_content for doc in documents]
    if hasattr(embeddings, "fit"):
        embeddings.fit(text_batch)
    embeddings_matrix = embeddings.encode(
        text_batch,
        normalize_embeddings=True,
        convert_to_numpy=False,
        show_progress_bar=False,
    )

    vectordb = LocalVectorDB(
        collection_name=collection_name,
        persist_dir=persist_path,
        documents=documents,
        ids=[doc.metadata["chunk_id"] for doc in documents],
        embeddings_matrix=_coerce_vectors(embeddings_matrix),
        embedding_model=embeddings,
    )
    vectordb.persist()
    _, _, model_path = _vector_store_paths(persist_dir, collection_name)
    if hasattr(embeddings, "save"):
        embeddings.save(model_path)
    return vectordb


def tokenize_for_bm25(text: str) -> list[str]:
    """Lowercase, strip punctuation, and split on whitespace for BM25."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [token for token in text.split() if token]


def build_bm25_index(documents: list[Document], prefer_fallback: bool = False) -> BM25Index:
    """Build a sparse BM25 index over policy chunk text."""
    tokenized_corpus = [tokenize_for_bm25(doc.page_content) for doc in documents]
    if prefer_fallback:
        return BM25Index(bm25=SimpleBM25Okapi(tokenized_corpus), documents=documents, tokenized_corpus=tokenized_corpus)

    try:
        from rank_bm25 import BM25Okapi

        bm25 = BM25Okapi(tokenized_corpus)
    except Exception as exc:
        LOGGER.warning("rank_bm25 unavailable, using pure-Python BM25 fallback: %s", exc)
        bm25 = SimpleBM25Okapi(tokenized_corpus)
    return BM25Index(bm25=bm25, documents=documents, tokenized_corpus=tokenized_corpus)


def passes_filters(doc: Document, filters: dict[str, Any] | None = None) -> bool:
    """Apply optional exact-match metadata filters."""
    if not filters:
        return True

    metadata = doc.metadata or {}
    for field, expected in filters.items():
        if expected in (None, "", "Any"):
            continue

        actual = metadata.get(field)
        if actual is None:
            return False

        if isinstance(actual, list):
            actual_values = {_normalize_string(item) for item in actual}
            if isinstance(expected, (list, tuple, set)):
                expected_values = {_normalize_string(item) for item in expected}
                if not actual_values.intersection(expected_values):
                    return False
            else:
                if _normalize_string(expected) not in actual_values:
                    return False
            continue

        if isinstance(expected, (list, tuple, set)):
            expected_values = {_normalize_string(item) for item in expected}
            if _normalize_string(actual) not in expected_values:
                return False
        else:
            if _normalize_string(actual) != _normalize_string(expected):
                return False

    return True


def bm25_retrieve(
    query: str,
    documents: list[Document],
    bm25: BM25Index | Any,
    top_k: int = 10,
    filters: dict[str, Any] | None = None,
) -> list[tuple[Document, float]]:
    """Run sparse retrieval and return the matching documents with BM25 scores."""
    bm25_engine = bm25.bm25 if isinstance(bm25, BM25Index) else bm25
    mapped_documents = bm25.documents if isinstance(bm25, BM25Index) else documents

    tokenized_query = tokenize_for_bm25(query)
    if not tokenized_query:
        return []

    scores = bm25_engine.get_scores(tokenized_query)
    ranked: list[tuple[Document, float]] = []
    for index, score in enumerate(scores):
        doc = mapped_documents[index]
        if passes_filters(doc, filters):
            ranked.append((doc, float(score)))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:top_k]


def _dense_retrieve(
    query: str,
    vectordb: LocalVectorDB,
    top_k: int = 10,
    filters: dict[str, Any] | None = None,
) -> list[tuple[Document, float]]:
    return vectordb.similarity_search_with_relevance_scores(query, k=top_k, filter=filters)


def hybrid_retrieve(
    query: str,
    vectordb: LocalVectorDB,
    bm25: BM25Index | Any,
    documents: list[Document],
    top_k: int = 6,
    semantic_k: int = 10,
    keyword_k: int = 10,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Combine dense and sparse retrieval with transparent score tracking."""
    semantic_results = _dense_retrieve(query, vectordb, top_k=semantic_k, filters=filters)
    keyword_results = bm25_retrieve(query, documents, bm25, top_k=keyword_k, filters=filters)

    combined: dict[str, dict[str, Any]] = {}

    for rank, (doc, score) in enumerate(semantic_results, start=1):
        chunk_id = doc.metadata["chunk_id"]
        combined.setdefault(
            chunk_id,
            {
                "doc": doc,
                "dense_score": 0.0,
                "dense_rank": None,
                "sparse_score": None,
                "sparse_score_normalized": 0.0,
                "sparse_rank": None,
                "hybrid_score": 0.0,
            },
        )
        combined[chunk_id]["dense_score"] = float(score)
        combined[chunk_id]["dense_rank"] = rank
        combined[chunk_id]["hybrid_score"] += float(score)

    if keyword_results:
        bm25_scores = [score for _, score in keyword_results]
        score_min = min(bm25_scores)
        score_max = max(bm25_scores)
        denominator = (score_max - score_min) if score_max != score_min else 1.0

        for rank, (doc, raw_score) in enumerate(keyword_results, start=1):
            chunk_id = doc.metadata["chunk_id"]
            normalized = (raw_score - score_min) / denominator
            combined.setdefault(
                chunk_id,
                {
                    "doc": doc,
                    "dense_score": 0.0,
                    "dense_rank": None,
                    "sparse_score": None,
                    "sparse_score_normalized": 0.0,
                    "sparse_rank": None,
                    "hybrid_score": 0.0,
                },
            )
            combined[chunk_id]["sparse_score"] = float(raw_score)
            combined[chunk_id]["sparse_score_normalized"] = float(normalized)
            combined[chunk_id]["sparse_rank"] = rank
            combined[chunk_id]["hybrid_score"] += float(normalized)

    ranked = sorted(
        combined.values(),
        key=lambda item: (
            item["hybrid_score"],
            item["dense_score"],
            item["sparse_score_normalized"],
        ),
        reverse=True,
    )
    return ranked[:top_k]


def get_reranker(model_name: str = DEFAULT_RERANKER_MODEL) -> Any:
    """Load the cross-encoder used to rerank a small candidate set."""
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)


def rerank_documents(
    query: str,
    docs: list[Document] | list[dict[str, Any]],
    reranker: Any,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Rerank retrieved candidates and keep hybrid scores available."""
    prepared: list[dict[str, Any]] = []
    for item in docs:
        if isinstance(item, dict):
            if "doc" not in item:
                raise ValueError("Rerank input dictionaries must contain a 'doc' key.")
            prepared.append(dict(item))
        else:
            prepared.append({"doc": item})

    if not prepared:
        return []

    pairs = [(query, item["doc"].page_content) for item in prepared]
    scores = reranker.predict(pairs)

    reranked: list[dict[str, Any]] = []
    for item, score in zip(prepared, scores):
        record = dict(item)
        record["rerank_score"] = float(score)
        reranked.append(record)

    reranked.sort(key=lambda item: item["rerank_score"], reverse=True)
    return reranked[:top_k]


def build_context(retrieved_docs: list[dict[str, Any]]) -> str:
    """Build a grounded generation context using policy metadata fields."""
    sections: list[str] = []
    for index, item in enumerate(retrieved_docs, start=1):
        doc = item["doc"]
        metadata = doc.metadata
        keywords = metadata.get("keywords", [])

        score_parts = []
        if item.get("hybrid_score") is not None:
            score_parts.append(f"hybrid={item['hybrid_score']:.4f}")
        if item.get("rerank_score") is not None:
            score_parts.append(f"rerank={item['rerank_score']:.4f}")
        score_text = ", ".join(score_parts) if score_parts else "n/a"

        sections.append(
            "\n".join(
                [
                    f"[Source {index}]",
                    f"Chunk ID: {metadata.get('chunk_id', 'unknown')}",
                    f"Title: {metadata.get('title', 'Untitled')}",
                    f"Section: {metadata.get('section_header', 'Unknown')}",
                    f"Category: {metadata.get('category', 'Unknown')}",
                    f"Loan Type: {metadata.get('loan_type', 'Unknown')}",
                    f"Keywords: {', '.join(keywords)}" if isinstance(keywords, list) else f"Keywords: {keywords}",
                    f"Score: {score_text}",
                    "Text:",
                    doc.page_content,
                ]
            )
        )

    return "\n\n".join(sections)


def load_generator(model_name: str = DEFAULT_GENERATOR_MODEL) -> GeneratorBundle:
    """Load the generator model used for policy question answering."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    if torch.cuda.is_available():
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        device = "cuda"
    else:
        model = AutoModelForCausalLM.from_pretrained(model_name)
        model.to("cpu")
        device = "cpu"

    model.eval()
    return GeneratorBundle(model_name=model_name, tokenizer=tokenizer, model=model, device=device)


def _fallback_answer(query: str, retrieved_docs: list[dict[str, Any]]) -> str:
    """Grounded fallback used when the generator cannot be loaded."""
    if not retrieved_docs:
        return (
            "I could not find enough retrieved policy context to answer this question. "
            "Try a broader query or relax the metadata filters."
        )

    top_sources = retrieved_docs[:2]
    bullets: list[str] = []
    cited_ids: list[str] = []
    for item in top_sources:
        doc = item["doc"]
        cited_ids.append(doc.metadata.get("chunk_id", "unknown"))
        sentences = re.split(r"(?<=[.!?])\s+", doc.page_content.strip())
        bullets.append(f"- {sentences[0]} [{doc.metadata.get('chunk_id', 'unknown')}]")
        if len(sentences) > 1 and len(doc.page_content) < 450:
            bullets.append(f"- {sentences[1]} [{doc.metadata.get('chunk_id', 'unknown')}]")

    return (
        "The answer below is a grounded fallback because the configured generation model was not available.\n\n"
        f"Question: {query}\n\n"
        "Relevant policy statements:\n"
        + "\n".join(bullets)
        + "\n\nSources: "
        + ", ".join(dict.fromkeys(cited_ids))
    )


def generate_answer(
    query: str,
    retrieved_docs: list[dict[str, Any]],
    generator: GeneratorBundle,
    max_new_tokens: int = 350,
    temperature: float = 0.0,
    top_p: float = 0.95,
) -> str:
    """Generate a grounded answer using only the retrieved policy context."""
    import torch

    if not retrieved_docs:
        return (
            "I could not find enough retrieved policy context to answer this question. "
            "Try a broader query or relax the metadata filters."
        )

    context = build_context(retrieved_docs)
    system_prompt = (
        "You are an underwriting policy assistant. Use only the retrieved policy context. "
        "Answer the user's question clearly and accurately. If the answer is not fully supported "
        "by the retrieved context, say what is missing. Do not invent rules. Cite supporting "
        "chunk IDs in square brackets when possible."
    )
    user_prompt = (
        f"User question:\n{query}\n\n"
        f"Retrieved policy context:\n{context}\n\n"
        "Instructions:\n"
        "- Use only the retrieved context.\n"
        "- Keep the answer concise, policy-focused, and explicit about conditions or limitations.\n"
        "- If rules differ by loan type or category, state that clearly.\n"
        "- If the context is insufficient, say so instead of guessing.\n"
        "- Include chunk IDs as citations, such as [policy_006].\n"
        "- End with a short 'Sources:' line listing the most relevant chunk IDs."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    prompt = generator.tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    model_inputs = generator.tokenizer(prompt, return_tensors="pt")

    target_device = next(generator.model.parameters()).device
    model_inputs = {key: value.to(target_device) for key, value in model_inputs.items()}

    generation_kwargs: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "pad_token_id": generator.tokenizer.pad_token_id,
        "eos_token_id": generator.tokenizer.eos_token_id,
        "top_p": top_p,
        "do_sample": temperature > 0,
    }
    if temperature > 0:
        generation_kwargs["temperature"] = temperature

    with torch.no_grad():
        output_tokens = generator.model.generate(**model_inputs, **generation_kwargs)

    prompt_length = model_inputs["input_ids"].shape[-1]
    generated_tokens = output_tokens[0][prompt_length:]
    answer = generator.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    return answer


def serialize_retrieval_result(item: dict[str, Any]) -> dict[str, Any]:
    """Convert an internal retrieval result into a JSON-friendly dictionary."""
    doc = item["doc"]
    metadata = dict(doc.metadata)
    return {
        "chunk_id": metadata.get("chunk_id"),
        "section_header": metadata.get("section_header"),
        "category": metadata.get("category"),
        "loan_type": metadata.get("loan_type"),
        "title": metadata.get("title"),
        "keywords": metadata.get("keywords", []),
        "text": doc.page_content,
        "dense_score": item.get("dense_score"),
        "dense_rank": item.get("dense_rank"),
        "sparse_score": item.get("sparse_score"),
        "sparse_score_normalized": item.get("sparse_score_normalized"),
        "sparse_rank": item.get("sparse_rank"),
        "hybrid_score": item.get("hybrid_score"),
        "rerank_score": item.get("rerank_score"),
    }


class PolicyRAGPipeline:
    """Reusable RAG pipeline for underwriting and lending policy QA."""

    def __init__(self, config: PolicyRAGConfig | None = None) -> None:
        self.config = config or PolicyRAGConfig()
        self.records: list[dict[str, Any]] = []
        self.documents: list[Document] = []
        self.embeddings: Any | None = None
        self.vectordb: LocalVectorDB | None = None
        self.bm25_index: BM25Index | None = None
        self.reranker: Any | None = None
        self.generator: GeneratorBundle | None = None

    def load_documents(self) -> list[Document]:
        self.records = load_chunks(self.config.chunk_path)
        self.documents = to_langchain_documents(self.records)
        return self.documents

    def build_indexes(self, rebuild: bool = False) -> "PolicyRAGPipeline":
        if not self.documents:
            self.load_documents()

        self.embeddings = self.embeddings or get_embedding_model(
            self.config.embedding_model_name,
            prefer_fallback=(self.config.fast_agent_mode or self.config.force_fallback_retrievers),
        )
        self.vectordb = build_or_load_vectordb(
            documents=self.documents,
            persist_dir=self.config.persist_dir,
            collection_name=self.config.collection_name,
            rebuild=rebuild,
            embeddings=self.embeddings,
        )
        self.bm25_index = build_bm25_index(
            self.documents,
            prefer_fallback=(self.config.fast_agent_mode or self.config.force_fallback_retrievers),
        )
        return self

    def ensure_reranker(self) -> Any:
        if self.reranker is None:
            self.reranker = get_reranker(self.config.reranker_model_name)
        return self.reranker

    def ensure_generator(self) -> GeneratorBundle:
        if self.generator is None:
            self.generator = load_generator(self.config.generator_model_name)
        return self.generator

    def available_filter_values(self) -> dict[str, list[str]]:
        if not self.records:
            self.load_documents()

        return {
            "category": sorted({record["category"] for record in self.records}),
            "loan_type": sorted({record["loan_type"] for record in self.records}),
            "section_header": sorted({record["section_header"] for record in self.records}),
        }

    def answer_policy_query(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int | None = None,
        semantic_k: int | None = None,
        keyword_k: int | None = None,
        rerank_k: int | None = None,
        include_generation: bool | None = None,
    ) -> dict[str, Any]:
        if not query or not query.strip():
            raise ValueError("Query must be a non-empty string.")

        if self.vectordb is None or self.bm25_index is None:
            self.build_indexes(rebuild=False)

        resolved_top_k = top_k or self.config.default_top_k
        resolved_semantic_k = semantic_k or self.config.default_semantic_k
        resolved_keyword_k = keyword_k or self.config.default_keyword_k
        should_rerank = not (self.config.fast_agent_mode or self.config.disable_reranker)
        should_generate = (
            include_generation
            if include_generation is not None
            else not (self.config.fast_agent_mode or self.config.disable_generator)
        )

        rerank_top_k = rerank_k or (max(resolved_top_k, 5) if should_rerank else resolved_top_k)
        hybrid_candidates = hybrid_retrieve(
            query=query,
            vectordb=self.vectordb,
            bm25=self.bm25_index,
            documents=self.documents,
            top_k=rerank_top_k,
            semantic_k=resolved_semantic_k,
            keyword_k=resolved_keyword_k,
            filters=filters,
        )

        if should_rerank:
            try:
                reranker = self.ensure_reranker()
                reranked = rerank_documents(query, hybrid_candidates, reranker, top_k=resolved_top_k)
            except Exception as exc:
                LOGGER.warning("Reranker unavailable, falling back to hybrid ordering: %s", exc)
                reranked = hybrid_candidates[:resolved_top_k]
                for item in reranked:
                    item["rerank_score"] = item.get("hybrid_score")
        else:
            reranked = hybrid_candidates[:resolved_top_k]
            for item in reranked:
                item["rerank_score"] = item.get("hybrid_score")

        final_answer = ""
        if should_generate:
            try:
                generator = self.ensure_generator()
                final_answer = generate_answer(
                    query=query,
                    retrieved_docs=reranked,
                    generator=generator,
                    max_new_tokens=self.config.generation_max_new_tokens,
                    temperature=self.config.generation_temperature,
                    top_p=self.config.generation_top_p,
                )
            except Exception as exc:
                LOGGER.warning("Generator unavailable, using grounded fallback answer: %s", exc)
                final_answer = _fallback_answer(query, reranked)
        elif self.config.fast_agent_mode:
            final_answer = _fallback_answer(query, reranked)

        return {
            "query": query,
            "applied_filters": filters or {},
            "retrieved_docs": [serialize_retrieval_result(item) for item in hybrid_candidates],
            "reranked_docs": [serialize_retrieval_result(item) for item in reranked],
            "final_answer": final_answer,
            "context": build_context(reranked) if reranked else "",
            "debug": {
                "chunk_source": str(self.config.chunk_path),
                "persist_dir": str(self.config.persist_dir),
                "collection_name": self.config.collection_name,
                "embedding_model": "tfidf-fallback" if (self.config.fast_agent_mode or self.config.force_fallback_retrievers) else self.config.embedding_model_name,
                "reranker_model": None if not should_rerank else self.config.reranker_model_name,
                "generator_model": self.config.generator_model_name if should_generate else None,
                "semantic_k": resolved_semantic_k,
                "keyword_k": resolved_keyword_k,
                "top_k": resolved_top_k,
                "fast_agent_mode": self.config.fast_agent_mode,
            },
        }


def answer_policy_query(
    query: str,
    filters: dict[str, Any] | None = None,
    top_k: int | None = None,
    pipeline: PolicyRAGPipeline | None = None,
    rebuild: bool = False,
    chunk_path: str | Path = DEFAULT_CHUNK_PATH,
    fast_agent_mode: bool = False,
) -> dict[str, Any]:
    """Convenience function for downstream agents."""
    config = PolicyRAGConfig.fast_agent(chunk_path=chunk_path) if fast_agent_mode else PolicyRAGConfig(chunk_path=chunk_path)
    active_pipeline = pipeline or PolicyRAGPipeline(config)
    if active_pipeline.vectordb is None or active_pipeline.bm25_index is None:
        active_pipeline.build_indexes(rebuild=rebuild)
    return active_pipeline.answer_policy_query(
        query=query,
        filters=filters,
        top_k=top_k,
        include_generation=(False if fast_agent_mode else None),
    )


@lru_cache(maxsize=8)
def get_cached_agent_pipeline(
    chunk_path: str = str(DEFAULT_CHUNK_PATH),
    persist_dir: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    fast_agent_mode: bool = True,
) -> PolicyRAGPipeline:
    """Return a warm, reusable pipeline instance for downstream agent tools."""
    config = (
        PolicyRAGConfig.fast_agent(
            chunk_path=chunk_path,
            persist_dir=persist_dir,
            collection_name=collection_name,
        )
        if fast_agent_mode
        else PolicyRAGConfig(
            chunk_path=chunk_path,
            persist_dir=persist_dir,
            collection_name=collection_name,
        )
    )
    pipeline = PolicyRAGPipeline(config)
    pipeline.build_indexes(rebuild=False)
    return pipeline


def answer_policy_query_fast(
    query: str,
    filters: dict[str, Any] | None = None,
    top_k: int = 2,
    semantic_k: int = 4,
    keyword_k: int = 4,
    chunk_path: str | Path = DEFAULT_CHUNK_PATH,
    persist_dir: str | Path = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> dict[str, Any]:
    """Low-latency agent helper that keeps a cached pipeline and skips heavy model stages."""
    pipeline = get_cached_agent_pipeline(
        chunk_path=str(chunk_path),
        persist_dir=str(persist_dir),
        collection_name=collection_name,
        fast_agent_mode=True,
    )
    return pipeline.answer_policy_query(
        query=query,
        filters=filters,
        top_k=top_k,
        semantic_k=semantic_k,
        keyword_k=keyword_k,
        include_generation=False,
    )


def _build_filters_from_args(args: argparse.Namespace) -> dict[str, str]:
    filters: dict[str, str] = {}
    for field in ("category", "loan_type", "section_header"):
        value = getattr(args, field)
        if value:
            filters[field] = value
    return filters


def main() -> int:
    parser = argparse.ArgumentParser(description="Run underwriting policy RAG over chunk_already.json")
    parser.add_argument(
        "--chunk-path",
        default=str(DEFAULT_CHUNK_PATH),
        help="Path to the parsed policy chunk JSON.",
    )
    parser.add_argument(
        "--persist-dir",
        default=DEFAULT_PERSIST_DIR,
        help="Directory used to persist the dense vector index.",
    )
    parser.add_argument(
        "--collection-name",
        default=DEFAULT_COLLECTION_NAME,
        help="Dense index collection name for underwriting policy retrieval.",
    )
    parser.add_argument("--query", required=True, help="User question to answer.")
    parser.add_argument("--category", help="Optional exact-match category filter.")
    parser.add_argument("--loan-type", dest="loan_type", help="Optional exact-match loan_type filter.")
    parser.add_argument("--section-header", dest="section_header", help="Optional exact-match section_header filter.")
    parser.add_argument("--top-k", type=int, help="Number of reranked chunks to keep.")
    parser.add_argument("--semantic-k", type=int, help="Number of dense retrieval candidates.")
    parser.add_argument("--keyword-k", type=int, help="Number of BM25 retrieval candidates.")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the dense vector index from scratch.")
    parser.add_argument(
        "--fast-agent",
        action="store_true",
        help="Use the low-latency agent preset: fallback retrievers, no reranker, no local generator.",
    )
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Skip the generation model and return retrieval output only.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    config = (
        PolicyRAGConfig.fast_agent(
            chunk_path=args.chunk_path,
            persist_dir=args.persist_dir,
            collection_name=args.collection_name,
        )
        if args.fast_agent
        else PolicyRAGConfig(
            chunk_path=args.chunk_path,
            persist_dir=args.persist_dir,
            collection_name=args.collection_name,
        )
    )
    pipeline = PolicyRAGPipeline(config)
    pipeline.build_indexes(rebuild=args.rebuild)

    result = pipeline.answer_policy_query(
        query=args.query,
        filters=_build_filters_from_args(args),
        top_k=args.top_k,
        semantic_k=args.semantic_k,
        keyword_k=args.keyword_k,
        include_generation=(False if (args.retrieval_only or args.fast_agent) else None),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
