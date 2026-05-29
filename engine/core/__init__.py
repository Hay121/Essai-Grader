"""
EssayGrader — Core Module Init
"""

from .preprocessor import TextPreprocessor
from .vectorizer import EssayVectorizer
from .evaluator import EssayEvaluator
from .contradiction_detector import ContradictionDetector

__all__ = ['TextPreprocessor', 'EssayVectorizer', 'EssayEvaluator', 'ContradictionDetector']
