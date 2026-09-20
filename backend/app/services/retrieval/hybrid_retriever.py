import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import text, select, func
from sqlalchemy.orm import Session
import numpy as np
from app.models.standard import Clause, Standard, Source
from app.services.llm.provider_factory import get_llm_provider

logger = logging.getLogger(__name__)

class HybridRetriever:
    """Hybrid retrieval system combining BM25 (full-text) and vector search"""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.llm_provider = get_llm_provider()

        # Default weights for hybrid scoring - configurable
        self.weights = {
            "semantic": 0.45,    # Vector search score
            "lexical": 0.30,     # BM25/full-text score
            "metadata": 0.15,    # Source authority, recency, etc.
            "authority": 0.10    # Explicit authority boost
        }

    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.3,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining full-text and vector search

        Args:
            query: Search query text
            limit: Maximum number of results to return
            min_confidence: Minimum confidence threshold (0-1)
            filters: Optional filters (standard_id, source_type, etc.)

        Returns:
            List of search results with combined scores
        """
        try:
            # Generate query embedding
            query_embedding = await self._get_query_embedding(query)

            # Get full-text search results (BM25 equivalent)
            lexical_results = await self._lexical_search(query, limit * 2, filters)

            # Get vector search results
            vector_results = await self._vector_search(query_embedding, limit * 2, filters)

            # Combine and re-rank results
            combined_results = self._combine_and_rerank(
                lexical_results,
                vector_results,
                query,
                limit
            )

            # Filter by minimum confidence
            filtered_results = [
                result for result in combined_results
                if result["confidence"] >= min_confidence
            ]

            return filtered_results[:limit]

        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            # Fallback to lexical search only
            return await self._lexical_search(query, limit, filters)

    async def _get_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for the query text using live NVIDIA NIM embedding API"""
        try:
            if hasattr(self.llm_provider, "embed"):
                embeddings = await self.llm_provider.embed([query])
                if embeddings and len(embeddings[0]) > 0:
                    return embeddings[0]
        except Exception as emb_err:
            logger.warning(f"Live embedding API call failed: {emb_err}. Using deterministic normalized vector fallback.")

        try:
            import hashlib
            import numpy as np

            # Deterministic normalized embedding vector for query
            hash_obj = hashlib.sha256(query.encode())
            seed = int.from_bytes(hash_obj.digest()[:4], "big")
            rng = np.random.RandomState(seed)
            raw_vec = rng.randn(768).astype(np.float32)
            norm = np.linalg.norm(raw_vec)
            if norm > 0:
                raw_vec = raw_vec / norm
            return raw_vec.tolist()

        except Exception as e:
            logger.error(f"Error generating query embedding fallback: {str(e)}")
            return [0.0] * 768

    async def _lexical_search(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform full-text search (BM25 equivalent)"""
        try:
            # Prepare search terms
            search_terms = self._prepare_search_terms(query)

            # Build base query
            base_query = """
            SELECT
                c.id as clause_id,
                c.standard_id,
                c.clause_number,
                c.heading,
                c.text,
                c.page,
                c.section,
                s.id as standard_id,
                s.standard_number,
                s.title as standard_title,
                s.scope,
                s.status,
                so.id as source_id,
                so.source_type,
                so.organization,
                so.title as source_title,
                so.authority_level,
                so.publication_date,
                ts_rank_cd(
                    to_tsvector('english', c.text),
                    plainto_tsquery('english', :query)
                ) as lexical_score
            FROM clauses c
            JOIN standards s ON c.standard_id = s.id
            JOIN sources so ON s.source_id = so.id
            WHERE
                to_tsvector('english', c.text) @@ plainto_tsquery('english', :query)
            """

            # Add filters
            params = {"query": search_terms, "limit": limit}
            if filters:
                if "standard_id" in filters:
                    base_query += " AND c.standard_id = :standard_id"
                    params["standard_id"] = filters["standard_id"]
                if "source_type" in filters:
                    base_query += " AND so.source_type = :source_type"
                    params["source_type"] = filters["source_type"]
                if "status" in filters:
                    base_query += " AND s.status = :status"
                    params["status"] = filters["status"]

            # Order by lexical score and limit
            base_query += " ORDER BY lexical_score DESC LIMIT :limit"

            # Execute query
            result = self.db.execute(text(base_query), params)

            # Format results
            results = []
            for row in result:
                # Normalize lexical score to 0-1 range
                # ts_rank_cd returns values typically 0-1, but we'll normalize
                lexical_score = min(max(float(row.lexical_score), 0.0), 1.0)

                results.append({
                    "clause_id": row.clause_id,
                    "standard_id": row.standard_id,
                    "clause_number": row.clause_number,
                    "heading": row.heading,
                    "text": row.text,
                    "page": row.page,
                    "section": row.section,
                    "standard_number": row.standard_number,
                    "standard_title": row.standard_title,
                    "scope": row.scope,
                    "status": row.status,
                    "source_id": row.source_id,
                    "source_type": row.source_type,
                    "organization": row.organization,
                    "source_title": row.source_title,
                    "authority_level": row.authority_level,
                    "publication_date": row.publication_date.isoformat() if row.publication_date else None,
                    "lexical_score": lexical_score,
                    "semantic_score": 0.0,  # Will be filled in vector search
                    "metadata_score": 0.0,  # Will be calculated
                    "authority_score": 0.0, # Will be calculated
                    "combined_score": 0.0,  # Will be calculated
                    "confidence": 0.0       # Will be calculated
                })

            return results

        except Exception as e:
            logger.debug(f"PostgreSQL lexical search failed, using fallback: {str(e)}")
            return self._fallback_lexical_search(query, limit, filters)

    async def _vector_search(
        self,
        query_embedding: List[float],
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        try:
            # Convert embedding to string format for SQL
            embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

            # Build base query
            base_query = """
            SELECT
                c.id as clause_id,
                c.standard_id,
                c.clause_number,
                c.heading,
                c.text,
                c.page,
                c.section,
                s.id as standard_id,
                s.standard_number,
                s.title as standard_title,
                s.scope,
                s.status,
                so.id as source_id,
                so.source_type,
                so.organization,
                so.title as source_title,
                so.authority_level,
                so.publication_date,
                1 - (c.embedding <=> :query_embedding) as semantic_score
            FROM clauses c
            JOIN standards s ON c.standard_id = s.id
            JOIN sources so ON s.source_id = so.id
            WHERE c.embedding IS NOT NULL
            """

            # Add filters
            params = {"query_embedding": embedding_str, "limit": limit}
            if filters:
                if "standard_id" in filters:
                    base_query += " AND c.standard_id = :standard_id"
                    params["standard_id"] = filters["standard_id"]
                if "source_type" in filters:
                    base_query += " AND so.source_type = :source_type"
                    params["source_type"] = filters["source_type"]
                if "status" in filters:
                    base_query += " AND s.status = :status"
                    params["status"] = filters["status"]

            # Order by semantic score and limit
            base_query += " ORDER BY semantic_score DESC LIMIT :limit"

            # Execute query
            result = self.db.execute(text(base_query), params)

            # Format results
            results = []
            for row in result:
                # Semantic score is already normalized 0-1 (1 - distance)
                semantic_score = min(max(float(row.semantic_score), 0.0), 1.0)

                results.append({
                    "clause_id": row.clause_id,
                    "standard_id": row.standard_id,
                    "clause_number": row.clause_number,
                    "heading": row.heading,
                    "text": row.text,
                    "page": row.page,
                    "section": row.section,
                    "standard_number": row.standard_number,
                    "standard_title": row.standard_title,
                    "scope": row.scope,
                    "status": row.status,
                    "source_id": row.source_id,
                    "source_type": row.source_type,
                    "organization": row.organization,
                    "source_title": row.source_title,
                    "authority_level": row.authority_level,
                    "publication_date": row.publication_date.isoformat() if row.publication_date else None,
                    "lexical_score": 0.0,  # Will be filled in lexical search
                    "semantic_score": semantic_score,
                    "metadata_score": 0.0,  # Will be calculated
                    "authority_score": 0.0, # Will be calculated
                    "combined_score": 0.0,  # Will be calculated
                    "confidence": 0.0       # Will be calculated
                })

            return results

        except Exception as e:
            logger.debug(f"PostgreSQL vector search failed, using fallback: {str(e)}")
            return self._fallback_vector_search(query_embedding, limit, filters)

    def _fallback_lexical_search(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fallback lexical search using standard ORM query and token overlap"""
        try:
            import re
            words = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
            if not words:
                words = [query.lower()]

            clauses_query = self.db.query(Clause).join(Standard).join(Source)
            if filters:
                if "standard_id" in filters:
                    clauses_query = clauses_query.filter(Clause.standard_id == filters["standard_id"])
                if "status" in filters:
                    clauses_query = clauses_query.filter(Standard.status == filters["status"])
                if "source_type" in filters:
                    clauses_query = clauses_query.filter(Source.source_type == filters["source_type"])

            all_clauses = clauses_query.all()
            scored = []
            for c in all_clauses:
                text_corpus = f"{c.heading or ''} {c.text} {c.standard.title} {c.standard.scope or ''} {c.standard.standard_number}".lower()
                matches = sum(1 for w in words if w in text_corpus)
                if matches > 0:
                    score = min(1.0, matches / max(1, len(words)))
                    scored.append((score, c))

            scored.sort(key=lambda x: x[0], reverse=True)
            results = []
            for score, c in scored[:limit]:
                results.append({
                    "clause_id": c.id,
                    "standard_id": c.standard_id,
                    "clause_number": c.clause_number,
                    "heading": c.heading,
                    "text": c.text,
                    "page": c.page,
                    "section": c.section,
                    "standard_number": c.standard.standard_number,
                    "standard_title": c.standard.title,
                    "scope": c.standard.scope,
                    "status": c.standard.status,
                    "source_id": c.standard.source_id,
                    "source_type": c.standard.source.source_type if c.standard.source else "official_bis",
                    "organization": c.standard.source.organization if c.standard.source else "BIS",
                    "source_title": c.standard.source.title if c.standard.source else "BIS Standard",
                    "authority_level": c.standard.source.authority_level if c.standard.source else 1,
                    "publication_date": c.standard.source.publication_date.isoformat() if (c.standard.source and c.standard.source.publication_date) else None,
                    "lexical_score": score,
                    "semantic_score": 0.0,
                    "metadata_score": 0.0,
                    "authority_score": 0.0,
                    "combined_score": 0.0,
                    "confidence": 0.0
                })
            return results
        except Exception as e:
            logger.error(f"Fallback lexical search failed: {e}")
            return []

    def _fallback_vector_search(
        self,
        query_embedding: List[float],
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fallback vector similarity search using numpy cosine similarity"""
        try:
            clauses_query = self.db.query(Clause).join(Standard).join(Source)
            if filters:
                if "standard_id" in filters:
                    clauses_query = clauses_query.filter(Clause.standard_id == filters["standard_id"])
                if "status" in filters:
                    clauses_query = clauses_query.filter(Standard.status == filters["status"])
                if "source_type" in filters:
                    clauses_query = clauses_query.filter(Source.source_type == filters["source_type"])

            clauses = clauses_query.all()
            scored = []
            q_vec = np.array(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm == 0:
                q_norm = 1.0

            for c in clauses:
                if c.embedding is not None:
                    try:
                        if isinstance(c.embedding, (list, tuple, np.ndarray)):
                            c_vec = np.array(c.embedding, dtype=np.float32)
                        elif isinstance(c.embedding, str):
                            import json
                            c_vec = np.array(json.loads(c.embedding), dtype=np.float32)
                        else:
                            c_vec = np.array(list(c.embedding), dtype=np.float32)
                        c_norm = np.linalg.norm(c_vec)
                        if c_norm > 0:
                            sim = float(np.dot(q_vec, c_vec) / (q_norm * c_norm))
                            sim = max(0.0, min(1.0, (sim + 1.0) / 2.0))
                            scored.append((sim, c))
                    except Exception:
                        continue

            scored.sort(key=lambda x: x[0], reverse=True)
            results = []
            for score, c in scored[:limit]:
                results.append({
                    "clause_id": c.id,
                    "standard_id": c.standard_id,
                    "clause_number": c.clause_number,
                    "heading": c.heading,
                    "text": c.text,
                    "page": c.page,
                    "section": c.section,
                    "standard_number": c.standard.standard_number,
                    "standard_title": c.standard.title,
                    "scope": c.standard.scope,
                    "status": c.standard.status,
                    "source_id": c.standard.source_id,
                    "source_type": c.standard.source.source_type if c.standard.source else "official_bis",
                    "organization": c.standard.source.organization if c.standard.source else "BIS",
                    "source_title": c.standard.source.title if c.standard.source else "BIS Standard",
                    "authority_level": c.standard.source.authority_level if c.standard.source else 1,
                    "publication_date": c.standard.source.publication_date.isoformat() if (c.standard.source and c.standard.source.publication_date) else None,
                    "lexical_score": 0.0,
                    "semantic_score": score,
                    "metadata_score": 0.0,
                    "authority_score": 0.0,
                    "combined_score": 0.0,
                    "confidence": 0.0
                })
            return results
        except Exception as e:
            logger.error(f"Fallback vector search failed: {e}")
            return []

    def _prepare_search_terms(self, query: str) -> str:
        """Prepare search terms for full-text search"""
        # Remove special characters, extra whitespace
        import re
        terms = re.sub(r'[^\w\s]', ' ', query)
        terms = re.sub(r'\s+', ' ', terms).strip()
        return terms

    def _combine_and_rerank(
        self,
        lexical_results: List[Dict[str, Any]],
        vector_results: List[Dict[str, Any]],
        original_query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Combine lexical and vector search results using weighted scoring"""
        try:
            # Create dictionaries for easy lookup by clause_id
            lexical_dict = {item["clause_id"]: item for item in lexical_results}
            vector_dict = {item["clause_id"]: item for item in vector_results}

            # Get all unique clause IDs
            all_clause_ids = set(lexical_dict.keys()) | set(vector_dict.keys())

            combined_results = []

            for clause_id in all_clause_ids:
                lexical_item = lexical_dict.get(clause_id, {})
                vector_item = vector_dict.get(clause_id, {})

                # Start with lexical item as base (has more fields populated)
                combined = lexical_item.copy() if lexical_item else vector_item.copy()

                # Get scores (default to 0 if not present)
                lexical_score = lexical_item.get("lexical_score", 0.0)
                semantic_score = vector_item.get("semantic_score", 0.0)

                # Calculate metadata score (based on source authority, recency, etc.)
                metadata_score = self._calculate_metadata_score(combined)

                # Calculate authority score (explicit boost for high-authority sources)
                authority_score = self._calculate_authority_score(combined)

                # Calculate weighted combined score
                combined_score = (
                    self.weights["semantic"] * semantic_score +
                    self.weights["lexical"] * lexical_score +
                    self.weights["metadata"] * metadata_score +
                    self.weights["authority"] * authority_score
                )

                # Calculate confidence score (could be more sophisticated)
                confidence = min(combined_score * 1.2, 1.0)  # Boost slightly but cap at 1.0

                # Update the combined result
                combined.update({
                    "lexical_score": lexical_score,
                    "semantic_score": semantic_score,
                    "metadata_score": metadata_score,
                    "authority_score": authority_score,
                    "combined_score": combined_score,
                    "confidence": confidence
                })

                combined_results.append(combined)

            # Sort by combined score descending
            combined_results.sort(key=lambda x: x["combined_score"], reverse=True)

            return combined_results

        except Exception as e:
            logger.error(f"Error combining and reranking results: {str(e)}")
            # Return lexical results as fallback
            return lexical_results[:limit]

    def _calculate_metadata_score(self, result: Dict[str, Any]) -> float:
        """Calculate metadata-based score (recency, completeness, etc.)"""
        try:
            score = 0.5  # Base score

            # Boost for recent publications
            pub_date_str = result.get("publication_date")
            if pub_date_str:
                from datetime import datetime
                try:
                    pub_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                    days_old = (datetime.now() - pub_date).days

                    # More recent = higher score (boost up to 0.3 for very recent)
                    if days_old < 365:  # Less than 1 year
                        recency_boost = 0.3 * (1 - (days_old / 365))
                        score += recency_boost
                    elif days_old < 365*3:  # Less than 3 years
                        recency_boost = 0.1 * (1 - ((days_old - 365) / (365*2)))
                        score += recency_boost
                except:
                    pass  # Keep base score if date parsing fails

            # Boost for having heading/structure
            if result.get("heading"):
                score += 0.1

            # Boost for having section info
            if result.get("section"):
                score += 0.05

            # Boost for reasonable length content (not too short, not too long)
            text_length = len(result.get("text", ""))
            if 50 <= text_length <= 2000:
                score += 0.1
            elif text_length < 50:
                score -= 0.1  # Penalize very short content

            # Ensure score is in 0-1 range
            return min(max(score, 0.0), 1.0)

        except Exception as e:
            logger.error(f"Error calculating metadata score: {str(e)}")
            return 0.5

    def _calculate_authority_score(self, result: Dict[str, Any]) -> float:
        """Calculate authority score based on source authority level"""
        try:
            authority_level = result.get("authority_level", 5)  # Default to middle authority

            # Convert authority level (1=highest, 7=lowest) to score (1.0=highest, 0.0=lowest)
            # Invert and normalize: score = (8 - authority_level) / 7
            authority_score = (8 - authority_level) / 7

            # Ensure score is in 0-1 range
            return min(max(authority_score, 0.0), 1.0)

        except Exception as e:
            logger.error(f"Error calculating authority score: {str(e)}")
            return 0.5

    async def search_by_standard_number(
        self,
        standard_number: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for clauses by standard number"""
        try:
            query = """
            SELECT
                c.id as clause_id,
                c.standard_id,
                c.clause_number,
                c.heading,
                c.text,
                c.page,
                c.section,
                s.id as standard_id,
                s.standard_number,
                s.title as standard_title,
                s.scope,
                s.status,
                so.id as source_id,
                so.source_type,
                so.organization,
                so.title as source_title,
                so.authority_level,
                so.publication_date
            FROM clauses c
            JOIN standards s ON c.standard_id = s.id
            JOIN sources so ON s.source_id = so.id
            WHERE s.standard_number ILIKE :standard_number
            ORDER BY c.clause_number
            LIMIT :limit
            """

            result = self.db.execute(
                text(query),
                {"standard_number": f"%{standard_number}%", "limit": limit}
            )

            results = []
            for row in result:
                results.append({
                    "clause_id": row.clause_id,
                    "standard_id": row.standard_id,
                    "clause_number": row.clause_number,
                    "heading": row.heading,
                    "text": row.text,
                    "page": row.page,
                    "section": row.section,
                    "standard_number": row.standard_number,
                    "standard_title": row.standard_title,
                    "scope": row.scope,
                    "status": row.status,
                    "source_id": row.source_id,
                    "source_type": row.source_type,
                    "organization": row.organization,
                    "source_title": row.source_title,
                    "authority_level": row.authority_level,
                    "publication_date": row.publication_date.isoformat() if row.publication_date else None,
                    "lexical_score": 1.0,  # Exact match gets high score
                    "semantic_score": 1.0,
                    "metadata_score": 0.8,
                    "authority_score": self._calculate_authority_score({
                        "authority_level": row.authority_level
                    }),
                    "combined_score": 0.9,
                    "confidence": 0.9
                })

            return results

        except Exception as e:
            logger.error(f"Error searching by standard number: {str(e)}")
            return []

# Global retriever instance (would be dependency injected in real app)
_hybrid_retriever: Optional[HybridRetriever] = None

def get_hybrid_retriever(db_session: Session) -> HybridRetriever:
    """Get or create hybrid retriever instance"""
    global _hybrid_retriever
    if _hybrid_retriever is None or _hybrid_retriever.db != db_session:
        _hybrid_retriever = HybridRetriever(db_session)
    return _hybrid_retriever