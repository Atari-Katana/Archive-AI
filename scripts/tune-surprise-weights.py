#!/usr/bin/env python3
"""
Empirical Tuning for Surprise Score Weights
Optimize perplexity and semantic weights using grid search.
"""

import asyncio
import numpy as np
from typing import List, Tuple, Dict
from dataclasses import dataclass
import json


@dataclass
class TestCase:
    """Test case for surprise score evaluation"""
    message: str
    expected_surprise: float  # 0.0 = boring, 1.0 = very surprising
    perplexity: float
    semantic_distance: float


@dataclass
class TuningResult:
    """Result of tuning experiment"""
    perplexity_weight: float
    semantic_weight: float
    precision: float
    recall: float
    f1_score: float
    accuracy: float


class SurpriseScoreTuner:
    """
    Tunes surprise score weights empirically.

    Uses grid search to find optimal weights for:
    - perplexity (unexpectedness)
    - semantic distance (novelty)

    Current defaults: 0.6 perplexity, 0.4 semantic
    """

    def __init__(self):
        self.test_cases = self.create_test_dataset()

    def create_test_dataset(self) -> List[TestCase]:
        """
        Create test dataset with expected surprise scores.

        Categories:
        - High surprise: Novel information, unexpected turns
        - Medium surprise: Somewhat interesting
        - Low surprise: Repetitive, common phrases

        Returns:
            List of test cases
        """
        return [
            # High surprise (0.8-1.0)
            TestCase("I just discovered a new fundamental particle in physics!", 0.9, 150.0, 0.95),
            TestCase("My cat learned to speak fluent Japanese overnight.", 1.0, 200.0, 0.98),
            TestCase("Quantum teleportation experiment succeeded in my basement.", 0.95, 180.0, 0.92),

            # Medium surprise (0.4-0.7)
            TestCase("I'm learning Python programming.", 0.5, 50.0, 0.4),
            TestCase("Had a great dinner at a new restaurant.", 0.6, 60.0, 0.5),
            TestCase("Just finished reading an interesting book.", 0.55, 55.0, 0.45),

            # Low surprise (0.0-0.3)
            TestCase("Hello", 0.1, 10.0, 0.05),
            TestCase("How are you?", 0.15, 15.0, 0.1),
            TestCase("The weather is nice today.", 0.2, 20.0, 0.15),
            TestCase("Thank you", 0.1, 12.0, 0.08),

            # Edge cases
            TestCase("Repetition repetition repetition repetition", 0.05, 5.0, 0.02),
            TestCase("A completely novel combination of obscure technical terms: "
                    "quantum entanglement meets blockchain cryptography in neural networks", 0.85, 120.0, 0.88),
        ]

    def calculate_surprise_score(
        self,
        perplexity: float,
        semantic_distance: float,
        perplexity_weight: float,
        semantic_weight: float
    ) -> float:
        """
        Calculate surprise score with given weights.

        Args:
            perplexity: Perplexity score (higher = more surprising)
            semantic_distance: Semantic distance (higher = more novel)
            perplexity_weight: Weight for perplexity component
            semantic_weight: Weight for semantic component

        Returns:
            Surprise score (0.0 to 1.0)
        """
        # Normalize perplexity (assuming max ~200)
        normalized_perplexity = min(perplexity / 200.0, 1.0)

        # Semantic distance already 0-1
        normalized_semantic = semantic_distance

        # Weighted combination
        score = (perplexity_weight * normalized_perplexity +
                semantic_weight * normalized_semantic)

        return min(max(score, 0.0), 1.0)

    def evaluate_weights(
        self,
        perplexity_weight: float,
        semantic_weight: float,
        threshold: float = 0.5
    ) -> TuningResult:
        """
        Evaluate weights on test dataset.

        Args:
            perplexity_weight: Weight for perplexity
            semantic_weight: Weight for semantic distance
            threshold: Classification threshold

        Returns:
            Evaluation metrics
        """
        predictions = []
        labels = []

        for test_case in self.test_cases:
            # Calculate predicted surprise
            predicted_surprise = self.calculate_surprise_score(
                test_case.perplexity,
                test_case.semantic_distance,
                perplexity_weight,
                semantic_weight
            )

            # Binary classification: surprising or not
            predicted_label = 1 if predicted_surprise >= threshold else 0
            true_label = 1 if test_case.expected_surprise >= threshold else 0

            predictions.append(predicted_label)
            labels.append(true_label)

        # Calculate metrics
        tp = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 1)
        fp = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 0)
        tn = sum(1 for p, l in zip(predictions, labels) if p == 0 and l == 0)
        fn = sum(1 for p, l in zip(predictions, labels) if p == 0 and l == 1)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / len(predictions)

        return TuningResult(
            perplexity_weight=perplexity_weight,
            semantic_weight=semantic_weight,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy
        )

    def grid_search(
        self,
        perplexity_range: Tuple[float, float] = (0.0, 1.0),
        semantic_range: Tuple[float, float] = (0.0, 1.0),
        step: float = 0.1
    ) -> List[TuningResult]:
        """
        Perform grid search over weight space.

        Args:
            perplexity_range: (min, max) for perplexity weight
            semantic_range: (min, max) for semantic weight
            step: Grid step size

        Returns:
            List of tuning results, sorted by F1 score
        """
        results = []

        perplexity_values = np.arange(
            perplexity_range[0],
            perplexity_range[1] + step,
            step
        )
        semantic_values = np.arange(
            semantic_range[0],
            semantic_range[1] + step,
            step
        )

        total_combinations = len(perplexity_values) * len(semantic_values)
        print(f"Testing {total_combinations} weight combinations...")

        for i, perp_weight in enumerate(perplexity_values):
            for sem_weight in enumerate(semantic_values):
                # Weights should sum to approximately 1.0 (allow some flexibility)
                total_weight = perp_weight + sem_weight[1]
                if abs(total_weight - 1.0) > 0.2:
                    continue  # Skip combinations that don't sum to ~1.0

                result = self.evaluate_weights(perp_weight, sem_weight[1])
                results.append(result)

            # Progress indicator
            if i % 5 == 0:
                print(f"  Tested {i * len(semantic_values)} / {total_combinations} combinations...")

        # Sort by F1 score
        results.sort(key=lambda r: r.f1_score, reverse=True)

        return results

    def run_tuning(self, verbose: bool = True) -> TuningResult:
        """
        Run full tuning process.

        Args:
            verbose: Print detailed results

        Returns:
            Best tuning result
        """
        print("=" * 70)
        print("Surprise Score Weight Tuning")
        print("=" * 70)
        print()
        print(f"Test dataset: {len(self.test_cases)} cases")
        print()

        # Current baseline
        print("Testing current weights (0.6 perplexity, 0.4 semantic)...")
        baseline = self.evaluate_weights(0.6, 0.4)
        print(f"  Precision: {baseline.precision:.3f}")
        print(f"  Recall: {baseline.recall:.3f}")
        print(f"  F1 Score: {baseline.f1_score:.3f}")
        print(f"  Accuracy: {baseline.accuracy:.3f}")
        print()

        # Grid search
        print("Running grid search...")
        results = self.grid_search(step=0.05)

        # Top results
        print()
        print("=" * 70)
        print("Top 5 Weight Combinations:")
        print("=" * 70)
        print()

        for i, result in enumerate(results[:5], 1):
            print(f"{i}. Perplexity: {result.perplexity_weight:.2f}, "
                  f"Semantic: {result.semantic_weight:.2f}")
            print(f"   Precision: {result.precision:.3f}, "
                  f"Recall: {result.recall:.3f}, "
                  f"F1: {result.f1_score:.3f}, "
                  f"Accuracy: {result.accuracy:.3f}")
            print()

        # Best result
        best = results[0]
        print("=" * 70)
        print("Recommended Weights:")
        print("=" * 70)
        print(f"PERPLEXITY_WEIGHT = {best.perplexity_weight:.2f}")
        print(f"SEMANTIC_WEIGHT = {best.semantic_weight:.2f}")
        print()
        print(f"Expected Performance:")
        print(f"  Precision: {best.precision:.1%}")
        print(f"  Recall: {best.recall:.1%}")
        print(f"  F1 Score: {best.f1_score:.3f}")
        print(f"  Accuracy: {best.accuracy:.1%}")
        print("=" * 70)

        # Save results
        self.save_results(results[:10])

        return best

    def save_results(self, results: List[TuningResult]):
        """Save top results to file"""
        output = {
            "timestamp": "2026-01-03",
            "test_cases": len(self.test_cases),
            "results": [
                {
                    "perplexity_weight": r.perplexity_weight,
                    "semantic_weight": r.semantic_weight,
                    "precision": r.precision,
                    "recall": r.recall,
                    "f1_score": r.f1_score,
                    "accuracy": r.accuracy,
                }
                for r in results
            ]
        }

        with open("surprise_weight_tuning_results.json", "w") as f:
            json.dump(output, f, indent=2)

        print()
        print("Results saved to: surprise_weight_tuning_results.json")


def main():
    """Main entry point"""
    tuner = SurpriseScoreTuner()
    best_result = tuner.run_tuning()

    print()
    print("Update brain/config.py with these values:")
    print(f"  SURPRISE_PERPLEXITY_WEIGHT = {best_result.perplexity_weight:.2f}")
    print(f"  SURPRISE_SEMANTIC_WEIGHT = {best_result.semantic_weight:.2f}")
    print()


if __name__ == "__main__":
    main()
