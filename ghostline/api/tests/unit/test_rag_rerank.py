from collections import namedtuple

from app.services.rag import RAGService


def test_rag_rerank_prefers_diverse_sources_when_scores_close(monkeypatch):
    monkeypatch.setenv("GHOSTLINE_RAG_RERANK", "true")

    Row = namedtuple("Row", ["id", "content", "chunk_index", "word_count", "source_reference", "source_material_id", "filename", "similarity"])
    # Three very similar rows from file A, one slightly less similar row from file B
    rows = [
        Row("1", "alpha beta gamma", 0, 3, None, "sm1", "a.txt", 0.90),
        Row("2", "alpha beta gamma delta", 1, 4, None, "sm1", "a.txt", 0.89),
        Row("3", "alpha beta gamma epsilon", 2, 4, None, "sm1", "a.txt", 0.88),
        Row("4", "alpha beta", 0, 2, None, "sm2", "b.txt", 0.87),
    ]

    svc = RAGService()
    selected = svc._rerank_and_select_rows(query="alpha beta gamma", rows=rows, top_k=2)

    filenames = [r.filename for r in selected]
    # Expect we keep at least one chunk from b.txt in the top 2 for coverage
    assert "b.txt" in filenames


