"""
Test Dataset Manager for RAG Evaluation
Handles creation, loading, and management of test datasets
"""

import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import logging

from .metrics import GroundTruth, RetrievalResult

logger = logging.getLogger(__name__)

@dataclass
class TestDataset:
    """Represents a test dataset for RAG evaluation"""
    name: str
    description: str
    queries: List[str]
    ground_truths: List[GroundTruth]
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'queries': selfQueries,
            'ground_truths': [asdict(gt) for gt in self.ground_truths],
            'metadata': self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestDataset':
        """Create TestDataset from dictionary"""
        ground_truths = []
        for gt_data in data.get('ground_truths', []):
            # Convert relevant_document_ids back to set
            if 'relevant_document_ids' in gt_data:
                gt_data['relevant_document_ids'] = set(gt_data['relevant_document_ids'])
            ground_truths.append(GroundTruth(**gt_data))

        return cls(
            name=data['name'],
            description=data['description'],
            queries=data['queries'],
            ground_truths=ground_truths,
            metadata=data.get('metadata', {})
        )

class TestDatasetManager:
    """Manages test datasets for RAG evaluation"""

    def __init__(self, base_directory: str = "./test_datasets"):
        self.base_directory = base_directory
        os.makedirs(base_directory, exist_ok=True)
        logger.info(f"TestDatasetManager initialized with base directory: {base_directory}")

    def save_dataset(self, dataset: TestDataset, filename: str = None) -> str:
        """
        Save a test dataset to file

        Args:
            dataset: TestDataset to save
            filename: Optional filename, defaults to {name}.json

        Returns:
            Path to saved file
        """
        if filename is None:
            # Sanitize filename
            safe_name = "".join(c for c in dataset.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_name.replace(' ', '_').lower()}.json"

        filepath = os.path.join(self.base_directory, filename)

        # Convert to dict for JSON serialization
        dataset_dict = dataset.to_dict()

        # Handle GroundTruth serialization (convert sets to lists)
        def prepare_for_json(obj):
            if isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, dict):
                return {k: prepare_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [prepare_for_json(item) for item in obj]
            else:
                return obj

        dataset_dict = prepare_for_json(dataset_dict)

        with open(filepath, 'w') as f:
            json.dump(dataset_dict, f, indent=2)

        logger.info(f"Test dataset saved to {filepath}")
        return filepath

    def load_dataset(self, filename: str) -> TestDataset:
        """
        Load a test dataset from file

        Args:
            filename: Name of the file to load

        Returns:
            TestDataset object
        """
        filepath = os.path.join(self.base_directory, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Test dataset file not found: {filepath}")

        with open(filepath, 'r') as f:
            dataset_dict = json.load(f)

        # Convert lists back to sets for relevant_document_ids
        for gt_data in dataset_dict.get('ground_truths', []):
            if 'relevant_document_ids' in gt_data:
                gt_data['relevant_document_ids'] = set(gt_data['relevant_document_ids'])

        dataset = TestDataset.from_dict(dataset_dict)
        logger.info(f"Test dataset loaded from {filepath}")
        return dataset

    def list_datasets(self) -> List[str]:
        """
        List all available test datasets

        Returns:
            List of dataset filenames
        """
        if not os.path.exists(self.base_directory):
            return []

        datasets = []
        for file in os.listdir(self.base_directory):
            if file.endswith('.json'):
                datasets.append(file)

        return sorted(datasets)

    def delete_dataset(self, filename: str) -> bool:
        """
        Delete a test dataset

        Args:
            filename: Name of the file to delete

        Returns:
            True if deleted, False if not found
        """
        filepath = os.path.join(self.base_directory, filename)

        if not os.path.exists(filepath):
            logger.warning(f"Test dataset file not found for deletion: {filepath}")
            return False

        os.remove(filepath)
        logger.info(f"Test dataset deleted: {filepath}")
        return True

    def create_bis_standards_dataset(self) -> TestDataset:
        """
        Create a sample BIS standards test dataset

        Returns:
            TestDataset with BIS standards queries
        """
        queries = [
            "What are the safety requirements for information technology equipment according to IS 13252?",
            "What is the procedure for obtaining BIS certification for electronic products?",
            "What are the testing requirements for fire extinguishers as per IS 14785?",
            "How to verify if a product complies with Indian Standards for safety?",
            "What documents are required for BIS certification application?",
            "What are the EMC testing requirements for IT equipment?",
            "How often does BIS require factory inspections for certified products?",
            "What are the marking requirements for BIS certified products?",
            "What is the difference between ISI mark and BIS certification?",
            "How to test for temperature rise in electrical appliances?"
        ]

        # Create ground truths with example relevant document IDs
        # In a real system, these would correspond to actual document IDs in your database
        ground_truths = [
            GroundTruth(
                query=queries[0],
                relevant_document_ids={"IS_13252_2016", "BIS_CERTIFICATION_GUIDE", "IT_ELECTRONICS_SAFETY"},
                expected_answer="IS 13252 specifies safety requirements for information technology equipment including protection against electric shock, energy hazards, fire prevention, and mechanical hazards."
            ),
            GroundTruth(
                query=queries[1],
                relevant_document_ids={"BIS_CERTIFICATION_PROCESS", "BIS_ACT_2016", "CERTIFICATION_GUIDE"},
                expected_answer="BIS certification process involves application submission, product testing, factory inspection, and grant of license upon compliance."
            ),
            GroundTruth(
                query=queries[2],
                relevant_document_ids={"IS_14785_2006", "FIRE_EXTINGUISHER_STANDARDS", "PORTABLE_EXTINGUISHER_TESTING"},
                expected_answer="IS 14785 specifies performance, construction, and testing requirements for portable fire extinguishers including pressure test, discharge test, and fire test."
            ),
            GroundTruth(
                query=queries[3],
                relevant_document_ids={"BIS_COMPLIANCE_MANUAL", "STANDARD_VERIFICATION_PROCESS"},
                expected_answer="To verify compliance, check for BIS standard mark, verify license details, and test samples against relevant Indian Standards."
            ),
            GroundTruth(
                query=queries[4],
                relevant_document_ids={"BIS_APPLICATION_FORM", "CERTIFICATION_DOCUMENTS_REQUIRED"},
                expected_answer="Required documents include application form, test reports from BIS-recognized labs, factory details, and product specifications."
            ),
            GroundTruth(
                query=queries[5],
                relevant_document_ids={"IS_13252_EMC_PART", "EMC_TESTING_GUIDE", "IT_EMC_REQUIREMENTS"},
                expected_answer="EMC testing for IT equipment includes emissions testing (conducted and radiated) and immunity testing as per IEC/CISPR standards adopted in IS 13252."
            ),
            GroundTruth(
                query=queries[6],
                relevant_document_ids={"BIS_SURVEILLANCE_GUIDE", "FACTORY_INSPECTION_PERIODICITY"},
                expected_answer="BIS requires periodic factory inspections, typically annually, to ensure continued conformity of certified products."
            ),
            GroundTruth(
                query=queries[7],
                relevant_document_ids={"BIS_MARKING_REQUIREMENTS", "PRODUCT_LABELING_STANDARDS"},
                expected_answer="BIS certified products must bear the standard mark along with license number, and may include additional information as per specific standards."
            ),
            GroundTruth(
                query=queries[8],
                relevant_document_ids={"ISI_MARK_VS_BIS_CERTIFICATION", "BIS_ACT_2016_EXPLAINED"},
                expected_answer="ISI mark is the certification mark issued by BIS indicating conformity to Indian Standards, while BIS certification refers to the overall process of obtaining authorization to use the mark."
            ),
            GroundTruth(
                query=queries[9],
                relevant_document_ids={"TEMPERATURE_RISE_TESTING", "ELECTRICAL_APPLIANCE_TESTING"},
                expected_answer="Temperature rise test measures the increase in temperature of windings or surfaces when the appliance operates at rated load, ensuring it stays within limits specified in the relevant standard."
            )
        ]

        dataset = TestDataset(
            name="BIS Standards Knowledge Base",
            description="Test dataset for evaluating RAG performance on BIS standards and certification knowledge",
            queries=queries,
            ground_truths=ground_truths,
            metadata={
                "domain": "BIS Standards and Certification",
                "language": "English",
                "total_queries": len(queries),
                "created_by": "BIS Compass Evaluation System"
            }
        )

        return dataset

    def create_custom_dataset_from_dict(self, data: Dict[str, Any]) -> TestDataset:
        """
        Create a TestDataset from dictionary data

        Args:
            data: Dictionary containing dataset information

        Returns:
            TestDataset object
        """
        ground_truths = []
        for gt_data in data.get('ground_truths', []):
            # Convert relevant_document_ids to set if it's a list
            if 'relevant_document_ids' in gt_data and isinstance(gt_data['relevant_document_ids'], list):
                gt_data['relevant_document_ids'] = set(gt_data['relevant_document_ids'])
            ground_truths.append(GroundTruth(**gt_data))

        return TestDataset(
            name=data.get('name', 'Custom Dataset'),
            description=data.get('description', 'Custom test dataset'),
            queries=data.get('queries', []),
            ground_truths=ground_truths,
            metadata=data.get('metadata', {})
        )

# Convenience functions
def create_sample_bis_dataset() -> TestDataset:
    """Convenience function to create a sample BIS dataset"""
    manager = TestDatasetManager()
    return manager.create_bis_standards_dataset()

def save_sample_dataset(filename: str = "bis_standards_test_dataset.json") -> str:
    """Convenience function to create and save a sample BIS dataset"""
    manager = TestDatasetManager()
    dataset = manager.create_bis_standards_dataset()
    return manager.save_dataset(dataset, filename)