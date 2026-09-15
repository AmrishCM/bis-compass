"""
Evaluation Module for BIS Compass RAG System
Provides tools for evaluating Retrieval-Augmented Generation performance
"""

from .metrics import RAGEvaluator, EvaluationResult, GroundTruth, RetrievalResult, GenerationResult
from .runner import RAGEvaluationRunner, EvaluationConfig, EvaluationReport, quick_evaluate
from .dataset_manager import TestDatasetManager, TestDataset, create_sample_bis_dataset, save_sample_dataset

__all__ = [
    "RAGEvaluator",
    "EvaluationResult",
    "GroundTruth",
    "RetrievalResult",
    "GenerationResult",
    "RAGEvaluationRunner",
    "EvaluationConfig",
    "EvaluationReport",
    "quick_evaluate",
    "TestDatasetManager",
    "TestDataset",
    "create_sample_bis_dataset",
    "save_sample_dataset"
]