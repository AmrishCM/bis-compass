"""
RAG Evaluation Runner
Orchestrates the evaluation process for RAG systems
"""

import asyncio
import time
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, asdict
import json
import logging

from .metrics import RAGEvaluator, EvaluationResult, GroundTruth, RetrievalResult, GenerationResult

logger = logging.getLogger(__name__)

@dataclass
class EvaluationConfig:
    """Configuration for evaluation run"""
    k_values: List[int] = None
    batch_size: int = 10
    save_detailed_results: bool = True
    save_summary_only: bool = False
    output_directory: str = "./evaluation_results"

    def __post_init__(self):
        if self.k_values is None:
            self.k_values = [1, 3, 5, 10]

@dataclass
class EvaluationReport:
    """Container for evaluation report"""
    config: EvaluationConfig
    start_time: float
    end_time: float
    total_time: float
    total_queries: int
    aggregated_results: Dict[str, Any]
    individual_results: List[Dict[str, Any]] = None

class RAGEvaluationRunner:
    """Main runner for RAG evaluation"""

    def __init__(self, config: EvaluationConfig = None):
        self.config = config or EvaluationConfig()
        self.evaluator = RAGEvaluator()
        self.results: List[EvaluationResult] = []

    async def run_evaluation(
        self,
        queries: List[str],
        retrieval_callable: Callable[[str], List[RetrievalResult]],
        ground_truths: List[GroundTruth],
        generation_callable: Optional[Callable[[str, List[RetrievalResult]], GenerationResult]] = None
    ) -> EvaluationReport:
        """
        Run a complete evaluation

        Args:
            queries: List of query strings
            retrieval_callable: Function that takes a query and returns retrieval results
            ground_truths: List of ground truth objects
            generation_callable: Optional function that takes query and retrieved docs and returns generation

        Returns:
            EvaluationReport with results
        """
        start_time = time.time()
        logger.info(f"Starting evaluation of {len(queries)} queries")

        # Validate inputs
        if len(queries) != len(ground_truths):
            raise ValueError("Number of queries must match number of ground truths")

        # Process in batches if specified
        all_results = []
        for i in range(0, len(queries), self.config.batch_size):
            batch_queries = queries[i:i + self.config.batch_size]
            batch_ground_truths = ground_truths[i:i + self.config.batch_size]

            logger.info(f"Processing batch {i//self.config.batch_size + 1}/{(len(queries) + self.config.batch_size - 1)//self.config.batch_size}")

            # Run evaluation for this batch
            batch_results = self.evaluator.evaluate_batch(
                batch_queries,
                retrieval_callable,
                batch_ground_truths,
                generation_callable
            )
            all_results.extend(batch_results)

            # Small delay between batches to prevent overwhelming the system
            if i + self.config.batch_size < len(queries):
                await asyncio.sleep(0.1)

        self.results = all_results
        end_time = time.time()

        # Aggregate results
        aggregated = self.evaluator.aggregate_results(all_results)

        # Create report
        report = EvaluationReport(
            config=self.config,
            start_time=start_time,
            end_time=end_time,
            total_time=end_time - start_time,
            total_queries=len(queries),
            aggregated_results=aggregated,
            individual_results=[asdict(result) for result in all_results] if self.config.save_detailed_results else None
        )

        logger.info(f"Evaluation completed in {report.total_time:.2f} seconds")
        logger.info(f"Average overall score: {aggregated.get('average_overall_score', 0):.3f}")

        return report

    def save_report(self, report: EvaluationReport, filepath: str = None):
        """
        Save evaluation report to file

        Args:
            report: EvaluationReport to save
            filepath: Optional filepath, defaults to config.output_directory
        """
        import os
        from datetime import datetime

        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs(self.config.output_directory, exist_ok=True)
            filepath = f"{self.config.output_directory}/evaluation_report_{timestamp}.json"

        # Convert report to dict for JSON serialization
        report_dict = asdict(report)

        # Handle potential serialization issues with numpy types if any
        def convert_for_json(obj):
            if isinstance(obj, (int, float, str, bool)) or obj is None:
                return obj
            elif isinstance(obj, dict):
                return {k: convert_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_for_json(item) for item in obj]
            else:
                return str(obj)

        report_dict = convert_for_json(report_dict)

        with open(filepath, 'w') as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"Evaluation report saved to {filepath}")

    def load_report(self, filepath: str) -> EvaluationReport:
        """
        Load evaluation report from file

        Args:
            filepath: Path to evaluation report JSON file

        Returns:
            EvaluationReport object
        """
        import json
        from dataclasses import asdict

        with open(filepath, 'r') as f:
            report_dict = json.load(f)

        # Convert dict back to EvaluationReport
        # This is simplified - in production you'd want proper deserialization
        report = EvaluationReport(**report_dict)
        return report

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the last evaluation run

        Returns:
            Dictionary with summary statistics
        """
        if not self.results:
            return {"error": "No evaluation results available"}

        aggregated = self.evaluator.aggregate_results(self.results)
        return {
            "total_queries": len(self.results),
            "average_overall_score": aggregated.get('average_overall_score', 0),
            "evaluation_completed": True,
            "timestamp": time.time()
        }

# Convenience function for quick evaluation
async def quick_evaluate(
    queries: List[str],
    retrieval_func: Callable[[str], List[RetrievalResult]],
    ground_truths: List[GroundTruth],
    generation_func: Optional[Callable[[str, List[RetrievalResult]], GenerationResult]] = None,
    config: EvaluationConfig = None
) -> EvaluationReport:
    """
    Quick evaluation function for simple use cases

    Args:
        queries: List of query strings
        retrieval_func: Function that retrieves documents for a query
        ground_truths: List of ground truth objects
        generation_func: Optional generation function
        config: Optional evaluation configuration

    Returns:
        EvaluationReport
    """
    runner = RAGEvaluationRunner(config)
    return await runner.run_evaluation(queries, retrieval_func, ground_truths, generation_func)