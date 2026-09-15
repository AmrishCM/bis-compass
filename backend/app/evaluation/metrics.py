"""
RAG (Retrieval-Augmented Generation) Evaluation Metrics
Implements various metrics to evaluate the performance of RAG systems
"""

import math
from typing import List, Dict, Any, Tuple, Set, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class RetrievalResult:
    """Represents a single retrieval result"""
    document_id: str
    score: float
    content: str
    metadata: Dict[str, Any] = None

@dataclass
class GroundTruth:
    """Represents ground truth for evaluation"""
    query: str
    relevant_document_ids: Set[str]
    expected_answer: Optional[str] = None

@dataclass
class GenerationResult:
    """Represents a generation result"""
    query: str
    generated_answer: str
    retrieved_documents: List[RetrievalResult]
    reference_documents: List[str] = None  # Document IDs that should support the answer

@dataclass
class EvaluationResult:
    """Container for evaluation results"""
    query: str
    retrieval_metrics: Dict[str, float]
    generation_metrics: Dict[str, float]
    overall_score: float
    details: Dict[str, Any] = None

class RAGEvaluator:
    """Main class for evaluating RAG system performance"""

    def __init__(self):
        pass

    def precision_at_k(self, retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
        """
        Calculate Precision@K
        Percentage of retrieved documents in top-k that are relevant
        """
        if k <= 0:
            return 0.0

        top_k = retrieved_ids[:k]
        if not top_k:
            return 0.0

        relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in relevant_ids)
        return relevant_in_top_k / len(top_k)

    def recall_at_k(self, retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
        """
        Calculate Recall@K
        Percentage of relevant documents that are retrieved in top-k
        """
        if not relevant_ids:
            return 0.0

        top_k = retrieved_ids[:k]
        if not top_k:
            return 0.0

        relevant_in_top_k = sum(1 for doc_id in top_k if doc_id in relevant_ids)
        return relevant_in_top_k / len(relevant_ids)

    def average_precision(self, retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
        """
        Calculate Average Precision (AP)
        Area under the precision-recall curve
        """
        if not relevant_ids:
            return 0.0

        relevant_count = 0
        precision_sum = 0.0

        for i, doc_id in enumerate(retrieved_ids, 1):
            if doc_id in relevant_ids:
                relevant_count += 1
                precision_at_i = relevant_count / i
                precision_sum += precision_at_i

        if relevant_count == 0:
            return 0.0

        return precision_sum / len(relevant_ids)

    def mean_average_precision(self, queries_results: List[Tuple[List[str], Set[str]]]) -> float:
        """
        Calculate Mean Average Precision (MAP)
        Mean of Average Precision across all queries
        """
        if not queries_results:
            return 0.0

        ap_sum = 0.0
        for retrieved_ids, relevant_ids in queries_results:
            ap_sum += self.average_precision(retrieved_ids, relevant_ids)

        return ap_sum / len(queries_results)

    def reciprocal_rank(self, retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
        """
        Calculate Reciprocal Rank
        Multiplicative inverse of the rank of the first relevant document
        """
        for i, doc_id in enumerate(retrieved_ids, 1):
            if doc_id in relevant_ids:
                return 1.0 / i
        return 0.0

    def mean_reciprocal_rank(self, queries_results: List[Tuple[List[str], Set[str]]]) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR)
        Mean of Reciprocal Rank across all queries
        """
        if not queries_results:
            return 0.0

        rr_sum = 0.0
        for retrieved_ids, relevant_ids in queries_results:
            rr_sum += self.reciprocal_rank(retrieved_ids, relevant_ids)

        return rr_sum / len(queries_results)

    def ndcg_at_k(self, retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain (NDCG)@K
        """
        if k <= 0:
            return 0.0

        # Calculate DCG@K
        dcg = 0.0
        for i, doc_id in enumerate(retrieved_ids[:k], 1):
            if doc_id in relevant_ids:
                # Using binary relevance: 1 if relevant, 0 if not
                dcg += 1.0 / math.log2(i + 1)

        # Calculate IDCG@K (ideal DCG)
        ideal_relevant_count = min(len(relevant_ids), k)
        idcg = 0.0
        for i in range(1, ideal_relevant_count + 1):
            idcg += 1.0 / math.log2(i + 1)

        if idcg == 0:
            return 0.0

        return dcg / idcg

    def mean_ndcg_at_k(self, queries_results: List[Tuple[List[str], Set[str]]], k: int) -> float:
        """
        Calculate Mean NDCG@K
        """
        if not queries_results:
            return 0.0

        ndcg_sum = 0.0
        for retrieved_ids, relevant_ids in queries_results:
            ndcg_sum += self.ndcg_at_k(retrieved_ids, relevant_ids, k)

        return ndcg_sum / len(queries_results)

    def hit_rate_at_k(self, retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
        """
        Calculate Hit Rate@K
        Percentage of queries with at least one relevant document in top-k
        """
        if not queries_results:
            return 0.0

        hit_count = 0
        for retrieved_ids, relevant_ids in queries_results:
            top_k = retrieved_ids[:k]
            if any(doc_id in relevant_ids for doc_id in top_k):
                hit_count += 1

        return hit_count / len(queries_results)

    def faithfulness_score(self, generated_answer: str, retrieved_documents: List[RetrievalResult]) -> float:
        """
        Calculate Faithfulness Score
        Measures how faithful the generated answer is to the retrieved documents
        Simple implementation: checks if key entities/concepts from answer appear in retrieved docs
        """
        if not generated_answer or not retrieved_documents:
            return 0.0

        # Simple implementation: check overlap of significant words
        answer_words = set(generated_answer.lower().split())
        # Remove common stop words (simplified)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        answer_words = answer_words - stop_words

        if not answer_words:
            return 0.0

        # Check how many answer words appear in retrieved documents
        retrieved_text = " ".join([doc.content.lower() for doc in retrieved_documents])
        retrieved_words = set(retrieved_text.split())

        common_words = answer_words & retrieved_words
        if not answer_words:
            return 0.0

        return len(common_words) / len(answer_words)

    def answer_relevance_score(self, query: str, generated_answer: str) -> float:
        """
        Calculate Answer Relevance Score
        Measures how relevant the generated answer is to the query
        Simple implementation: word overlap between query and answer
        """
        if not query or not generated_answer:
            return 0.0

        query_words = set(query.lower().split())
        answer_words = set(generated_answer.lower().split())

        # Remove stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        query_words = query_words - stop_words
        answer_words = answer_words - stop_words

        if not query_words:
            return 0.0

        common_words = query_words & answer_words
        return len(common_words) / len(query_words)

    def evaluate_retrieval(
        self,
        query: str,
        retrieved_documents: List[RetrievalResult],
        ground_truth: GroundTruth,
        k_values: List[int] = [1, 3, 5, 10]
    ) -> Dict[str, float]:
        """
        Evaluate retrieval performance for a single query
        """
        retrieved_ids = [doc.document_id for doc in retrieved_documents]
        relevant_ids = ground_truth.relevant_document_ids

        metrics = {}

        # Calculate metrics for different k values
        for k in k_values:
            metrics[f'precision@{k}'] = self.precision_at_k(retrieved_ids, relevant_ids, k)
            metrics[f'recall@{k}'] = self.recall_at_k(retrieved_ids, relevant_ids, k)
            metrics[f'ndcg@{k}'] = self.ndcg_at_k(retrieved_ids, relevant_ids, k)
            metrics[f'hit_rate@{k}'] = 1.0 if self.recall_at_k(retrieved_ids, relevant_ids, k) > 0 else 0.0

        # Calculate rank-based metrics
        metrics['map'] = self.average_precision(retrieved_ids, relevant_ids)
        metrics['mrr'] = self.reciprocal_rank(retrieved_ids, relevant_ids)

        return metrics

    def evaluate_generation(
        self,
        generation_result: GenerationResult
    ) -> Dict[str, float]:
        """
        Evaluate generation performance
        """
        metrics = {}

        # Faithfulness: how well the answer is supported by retrieved documents
        metrics['faithfulness'] = self.faithfulness_score(
            generation_result.generated_answer,
            generation_result.retrieved_documents
        )

        # Answer relevance: how well the answer addresses the query
        metrics['answer_relevance'] = self.answer_relevance_score(
            generation_result.query,
            generation_result.generated_answer
        )

        # If we have reference documents, check if answer is grounded in them
        if generation_result.reference_documents:
            # Simple check: does answer contain information from reference docs?
            # This would be more sophisticated in a real implementation
            metrics['reference_groundedness'] = 0.8  # Placeholder

        return metrics

    def evaluate_batch(
        self,
        queries: List[str],
        retrieval_function,  # Function that takes query and returns List[RetrievalResult]
        ground_truths: List[GroundTruth],
        generation_function=None  # Optional function that takes query and retrieved docs and returns generated answer
    ) -> List[EvaluationResult]:
        """
        Evaluate a batch of queries
        """
        results = []

        for i, (query, ground_truth) in enumerate(zip(queries, ground_truths)):
            logger.info(f"Evaluating query {i+1}/{len(queries)}: {query[:50]}...")

            # Get retrieval results
            retrieved_docs = retrieval_function(query)

            # Evaluate retrieval
            retrieval_metrics = self.evaluate_retrieval(query, retrieved_docs, ground_truth)

            # Evaluate generation if function provided
            generation_metrics = {}
            generated_answer = ""
            if generation_function:
                generation_result = generation_function(query, retrieved_docs)
                generated_answer = generation_result.generated_answer
                generation_metrics = self.evaluate_generation(
                    GenerationResult(
                        query=query,
                        generated_answer=generated_answer,
                        retrieved_documents=retrieved_docs
                    )
                )

            # Calculate overall score (weighted average)
            retrieval_score = sum(retrieval_metrics.values()) / len(retrieval_metrics) if retrieval_metrics else 0.0
            generation_score = sum(generation_metrics.values()) / len(generation_metrics) if generation_metrics else 0.0
            overall_score = (retrieval_score * 0.6) + (generation_score * 0.4)  # Weight retrieval higher

            results.append(EvaluationResult(
                query=query,
                retrieval_metrics=retrieval_metrics,
                generation_metrics=generation_metrics,
                overall_score=overall_score,
                details={
                    'retrieved_count': len(retrieved_docs),
                    'ground_truth_relevant_count': len(ground_truth.relevant_document_ids)
                }
            ))

        return results

    def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        Aggregate evaluation results across multiple queries
        """
        if not results:
            return {}

        aggregation = {
            'total_queries': len(results),
            'average_overall_score': sum(r.overall_score for r in results) / len(results),
            'retrieval_metrics': {},
            'generation_metrics': {}
        }

        # Aggregate retrieval metrics
        if results[0].retrieval_metrics:
            for metric_name in results[0].retrieval_metrics.keys():
                values = [r.retrieval_metrics[metric_name] for r in results if metric_name in r.retrieval_metrics]
                aggregation['retrieval_metrics'][metric_name] = {
                    'mean': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'std': math.sqrt(sum((x - sum(values)/len(values))**2 for x in values) / len(values)) if len(values) > 1 else 0.0
                }

        # Aggregate generation metrics
        if results[0].generation_metrics:
            for metric_name in results[0].generation_metrics.keys():
                values = [r.generation_metrics[metric_name] for r in results if metric_name in r.generation_metrics]
                aggregation['generation_metrics'][metric_name] = {
                    'mean': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'std': math.sqrt(sum((x - sum(values)/len(values))**2 for x in values) / len(values)) if len(values) > 1 else 0.0
                }

        return aggregation

# Convenience function for easy logger setup
def setup_evaluation_logger(level=logging.INFO):
    """Setup logging for evaluation module"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logger