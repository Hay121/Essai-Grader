"""
EssayGrader — Text Preprocessor Module
========================================
Handles tokenization, stop-word removal, and Indonesian stemming
for converting raw essay answers into clean term vectors.

Mathematical Context:
    This module prepares raw text for vectorization into the
    Term-Document Matrix A(m×n). Quality of preprocessing directly
    impacts the fidelity of the cosine similarity computation.

References:
    Asian, J. (2007) — "Effective Techniques for Indonesian Text Retrieval"
    Salton & Buckley (1988) — "Term-weighting in Automatic Text Retrieval"
"""

import re
import os
from typing import List, Optional

from .synonym_dict import SynonymNormalizer


class IndonesianStemmer:
    """
    Rule-based Indonesian stemmer implementing common affix removal.

    Handles prefixes: me-, mem-, men-, meng-, meny-, ber-, be-, di-, ke-, se-, per-, pe-
    Handles suffixes: -kan, -an, -i, -nya, -lah, -kah, -pun

    Reference:
        Asian, J., Williams, H.E., & Tahaghoghi, S.M.M. (2005).
        "Stemming Indonesian: A Confix-Stripping Approach."
    """

    PREFIX_RULES = [
        (r'^meny([aiueo])', r's\1'),
        (r'^mem([bfpv])',   r'\1'),
        (r'^memper',        r''),
        (r'^men([cdgjstz])', r'\1'),
        (r'^meng([ghqk])',  r'\1'),
        (r'^meng([aiueo])', r'\1'),
        (r'^menge',         r''),
        (r'^me',            r''),
        (r'^ber([aiueo])',  r'r\1'),
        (r'^bel',           r''),
        (r'^ber',           r''),
        (r'^be',            r''),
        (r'^di',            r''),
        (r'^ke',            r''),
        (r'^se',            r''),
        (r'^peny([aiueo])', r's\1'),
        (r'^pem([bfpv])',   r'\1'),
        (r'^peng([aiueo])', r'\1'),
        (r'^pen([cdgjstz])', r'\1'),
        (r'^pel',           r''),
        (r'^per',           r''),
        (r'^pe',            r''),
        (r'^ter',           r''),
    ]

    SUFFIX_RULES = [
        (r'nya$',  ''),
        (r'lah$',  ''),
        (r'kah$',  ''),
        (r'pun$',  ''),
        (r'kan$',  ''),
        (r'an$',   ''),
        (r'i$',    ''),
    ]

    def stem(self, word: str) -> str:
        """
        Stem a single Indonesian word by stripping affixes.

        Implements the Confix-Stripping approach for Indonesian morphology:
        1. Try prefix removal first, then suffix (handles confixes like
           me-...-kan, di-...-kan, ber-...-i)
        2. Fall back to suffix-only removal if no prefix matches
        3. Fall back to prefix-only if no suffix matched after prefix

        Reference:
            Asian, J. et al. (2005) "Stemming Indonesian: A Confix-Stripping Approach"

        Args:
            word: Input word (lowercase)

        Returns:
            Stemmed word root
        """
        if len(word) <= 3:
            return word

        original = word

        # Step 1: Try removing prefix first (primary Indonesian morphology)
        prefix_removed = self._remove_first_prefix(word)
        if prefix_removed != word:
            # Prefix was removed, now try suffix (min 4 chars to avoid overstemming)
            suffix_removed = self._remove_first_suffix(prefix_removed)
            if suffix_removed != prefix_removed and len(suffix_removed) >= 4:
                return suffix_removed
            # No valid suffix removal, return prefix-only result
            if len(prefix_removed) >= 3:
                return prefix_removed

        # Step 2: Fallback — try suffix removal first, then prefix
        suffix_removed = self._remove_first_suffix(word)
        if suffix_removed != word:
            prefix_removed2 = self._remove_first_prefix(suffix_removed)
            if prefix_removed2 != suffix_removed and len(prefix_removed2) >= 4:
                return prefix_removed2
            if len(suffix_removed) >= 3:
                return suffix_removed

        return original

    def _remove_first_prefix(self, word: str) -> str:
        """Remove the first matching prefix from the word."""
        for pattern, replacement in self.PREFIX_RULES:
            new_word = re.sub(pattern, replacement, word)
            if new_word != word and len(new_word) > 2:
                return new_word
        return word

    def _remove_first_suffix(self, word: str) -> str:
        """Remove the first matching suffix from the word."""
        for pattern, replacement in self.SUFFIX_RULES:
            new_word = re.sub(pattern, replacement, word)
            if new_word != word and len(new_word) > 2:
                return new_word
        return word

    def _all_prefix_removals(self, word: str) -> list:
        """Get all possible results from applying any single prefix rule."""
        results = []
        for pattern, replacement in self.PREFIX_RULES:
            new_word = re.sub(pattern, replacement, word)
            if new_word != word and len(new_word) > 2:
                results.append(new_word)
        return results

    def _all_suffix_removals(self, word: str) -> list:
        """Get all possible results from applying any single suffix rule."""
        results = []
        for pattern, replacement in self.SUFFIX_RULES:
            new_word = re.sub(pattern, replacement, word)
            if new_word != word and len(new_word) > 2:
                results.append(new_word)
        return results


class TextPreprocessor:
    """
    Full text preprocessing pipeline for Indonesian essay text.

    Pipeline:
        1. Case normalization (lowercase)
        2. Punctuation & number removal
        3. Tokenization (whitespace split)
        4. Stop-word filtering
        5. Indonesian stemming
        6. Minimum token length filtering (≥3 chars)

    Usage:
        preprocessor = TextPreprocessor()
        cleaned = preprocessor.process("Fotosintesis adalah proses pembuatan makanan")
        # → "fotosintesis proses buat makan"
    """

    # Comprehensive Indonesian stopwords
    DEFAULT_STOPWORDS = {
        'dan', 'atau', 'di', 'ke', 'dari', 'yang', 'ini', 'itu',
        'dengan', 'untuk', 'pada', 'adalah', 'juga', 'sudah',
        'akan', 'telah', 'ada', 'tidak', 'bisa', 'oleh', 'kami',
        'mereka', 'saya', 'kita', 'tersebut', 'sangat', 'lebih',
        'harus', 'masih', 'belum', 'antara', 'namun', 'tetapi',
        'bahwa', 'karena', 'dapat', 'sedang', 'saat', 'serta',
        'dalam', 'lagi', 'pun', 'lain', 'begitu', 'jika', 'bila',
        'maka', 'bagi', 'tapi', 'yaitu', 'yakni', 'atas', 'bawah',
        'nya', 'hal', 'seperti', 'secara', 'sebuah', 'suatu',
        'para', 'apa', 'siapa', 'mana', 'kapan', 'bagaimana',
        'mengapa', 'kenapa', 'setiap', 'semua', 'beberapa',
        'hanya', 'cukup', 'sering', 'pernah', 'selalu', 'hampir',
        'masing', 'sendiri', 'sama', 'sebagai', 'maupun',
        'agar', 'supaya', 'hingga', 'sampai', 'ketika', 'waktu',
        'dimana', 'kemana', 'darimana', 'sehingga', 'meskipun',
        'walaupun', 'apabila', 'oleh', 'demi', 'tentang',
        'terhadap', 'kepada', 'mengenai', 'melalui', 'selama',
        'sejak', 'sebelum', 'sesudah', 'setelah', 'antara',
        'bukan', 'tanpa', 'baik', 'makin', 'semakin', 'terlalu',
        'amat', 'paling', 'sungguh', 'agak', 'cuma',
        'dong', 'sih', 'deh', 'lho', 'kok', 'toh', 'yah', 'nah',
    }

    def __init__(self, extra_stopwords: Optional[set] = None, min_token_length: int = 3):
        """
        Initialize preprocessor.

        Args:
            extra_stopwords: Additional stop-words to include
            min_token_length: Minimum character length for valid tokens
        """
        self.stemmer = IndonesianStemmer()
        self.synonym_normalizer = SynonymNormalizer()
        self.min_token_length = min_token_length
        self.stop_words = self.DEFAULT_STOPWORDS.copy()
        if extra_stopwords:
            self.stop_words.update(extra_stopwords)

        # Compile regex patterns for performance
        self._re_urls = re.compile(r'https?://\S+|www\.\S+')
        self._re_numbers = re.compile(r'\d+')
        self._re_punctuation = re.compile(r'[^\w\s]')
        self._re_whitespace = re.compile(r'\s+')

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into individual word tokens.

        Args:
            text: Input text string

        Returns:
            List of lowercase tokens with punctuation removed
        """
        text = text.lower()
        text = self._re_urls.sub(' ', text)
        text = self._re_numbers.sub(' ', text)
        text = self._re_punctuation.sub(' ', text)
        text = self._re_whitespace.sub(' ', text).strip()
        return text.split()

    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """Filter out stop-words from token list."""
        return [t for t in tokens if t not in self.stop_words]

    def normalize_synonyms(self, tokens: List[str]) -> List[str]:
        """Replace synonyms with canonical forms for semantic matching."""
        return self.synonym_normalizer.normalize(tokens)

    def stem_tokens(self, tokens: List[str]) -> List[str]:
        """Apply Indonesian stemming to each token."""
        return [self.stemmer.stem(t) for t in tokens]

    def filter_short_tokens(self, tokens: List[str]) -> List[str]:
        """Remove tokens shorter than minimum length."""
        return [t for t in tokens if len(t) >= self.min_token_length]

    def process(self, text: str) -> str:
        """
        Full preprocessing pipeline: tokenize → filter → stem → rejoin.

        Args:
            text: Raw input text

        Returns:
            Cleaned, stemmed text string ready for TF-IDF vectorization
        """
        if not text or not text.strip():
            return ''
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords(tokens)
        tokens = self.stem_tokens(tokens)
        tokens = self.normalize_synonyms(tokens)
        tokens = self.filter_short_tokens(tokens)
        return ' '.join(tokens)

    def process_batch(self, texts: List[str]) -> List[str]:
        """Process multiple texts."""
        return [self.process(text) for text in texts]

    def get_tokens(self, text: str) -> List[str]:
        """Get final token list (for keyword analysis)."""
        if not text or not text.strip():
            return []
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords(tokens)
        tokens = self.stem_tokens(tokens)
        tokens = self.normalize_synonyms(tokens)
        tokens = self.filter_short_tokens(tokens)
        return tokens
