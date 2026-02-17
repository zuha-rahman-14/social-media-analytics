"""
Text Manipulation Detection — BERT + Rule-Based Hybrid

Layers:
  1. Rule-Based   — clickbait, spam, hate patterns, formatting anomalies
  2. Linguistic   — TTR, sentence variance, readability (Flesch-Kincaid), URL/hashtag analysis
  3. BERT         — fine-tuned transformer for semantic manipulation detection

Fine-tuning datasets:
  - FakeNewsNet (PolitiFact + GossipCop)
  - LIAR dataset (6-class fake news benchmark)
  - PHEME (Twitter rumour detection)

Install: pip install transformers torch
Replace 'distilbert-base-uncased-finetuned-sst-2-english' with your fine-tuned model.
"""
import re
import logging
import numpy as np
from typing import Tuple, List, Dict, Optional

logger = logging.getLogger(__name__)

# ── Compiled Patterns ────────────────────────────────────────────────
CLICKBAIT = [
    r"\byou won'?t believe\b", r"\bshocking\b", r"\bmind[- ]?blow(ing)?\b",
    r"\bsecrets?\b.*\b(reveal|exposed)\b", r"\bthey don'?t want you to know\b",
    r"\bwhat happens? next\b", r"\bgoing viral\b", r"\bbreaking[\s!]*news\b",
    r"\bexclusive reveal\b", r"\b\d+ things? (that|you)\b",
]
SPAM = [
    r"\bclick here\b", r"\bfree (offer|money|gift|download|trial)\b",
    r"\bmake \$?\d+", r"\bearn (from home|online|passive)\b",
    r"\blimited time (offer|only)\b", r"\bact now\b", r"\blink in bio\b",
    r"\b(dm|whatsapp|telegram) me\b", r"\bno credit card\b",
]
HATE = [
    r"\ball \w+ are\b", r"\bthose people\b.{0,30}\b(always|never|all)\b",
    r"\bshould be (banned|removed|eliminated|killed)\b",
    r"\b(inferior|superior) (race|people|group)\b",
]
RE_EXCESS_PUNCT = re.compile(r'[!?]{3,}')
RE_ALL_CAPS = re.compile(r'\b[A-Z]{4,}\b')
RE_REPEAT = re.compile(r'(.)\1{3,}')
RE_EMOJI_CLUSTER = re.compile(
    r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF'
    r'\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]{4,}',
    re.UNICODE
)


class TextManipulationDetector:

    def __init__(self, model_name=None):
        self.bert_pipeline = None
        self.model_name = model_name or 'distilbert-base-uncased-finetuned-sst-2-english'
        self._load_bert()

    def _load_bert(self):
        try:
            from transformers import pipeline
            self.bert_pipeline = pipeline(
                'text-classification',
                model=self.model_name,
                truncation=True,
                max_length=512
            )
            logger.info(f"BERT pipeline loaded: {self.model_name}")
        except Exception as e:
            logger.warning(f"BERT not available ({e}) — rule-based fallback active.")

    def detect(self, text: str) -> Tuple[float, str, List[Dict]]:
        """
        Analyze text for manipulation signals.

        Returns:
            score   : float 0-1    (1 = highly suspicious)
            label   : str          ('Authentic', 'Suspicious', 'Likely Manipulated')
            details : List[Dict]   each: {'rule': str, 'severity': str, 'excerpt': str}
        """
        if not text or not text.strip():
            return 0.0, 'No Text', []

        details = []

        rule_score, rule_details = self._rule_checks(text)
        ling_score, ling_details = self._linguistic_analysis(text)
        details.extend(rule_details)
        details.extend(ling_details)

        if self.bert_pipeline:
            bert_score, bert_detail = self._bert_predict(text)
            final = 0.40 * bert_score + 0.35 * rule_score + 0.25 * ling_score
            if bert_detail:
                details.append(bert_detail)
        else:
            final = 0.55 * rule_score + 0.45 * ling_score

        final = float(np.clip(final, 0.0, 1.0))
        return round(final, 4), self._to_label(final), details

    # ── Rule Checks ───────────────────────────────────────────────────
    def _rule_checks(self, text: str) -> Tuple[float, List[Dict]]:
        findings, score = [], 0.0
        lower = text.lower()

        for pat in CLICKBAIT:
            m = re.search(pat, lower)
            if m:
                findings.append({'rule': 'Clickbait Language', 'severity': 'medium',
                                  'excerpt': self._excerpt(text, m.start())})
                score += 0.12

        for pat in SPAM:
            m = re.search(pat, lower)
            if m:
                findings.append({'rule': 'Spam / Promotional Pattern', 'severity': 'high',
                                  'excerpt': self._excerpt(text, m.start())})
                score += 0.18

        for pat in HATE:
            m = re.search(pat, lower)
            if m:
                findings.append({'rule': 'Generalizing / Hateful Language', 'severity': 'high',
                                  'excerpt': self._excerpt(text, m.start())})
                score += 0.20

        if RE_EXCESS_PUNCT.search(text):
            findings.append({'rule': 'Excessive Punctuation (!!!)', 'severity': 'low', 'excerpt': ''})
            score += 0.06

        caps = RE_ALL_CAPS.findall(text)
        if len(caps) >= 3:
            findings.append({'rule': f'Excessive CAPS Words ({len(caps)})', 'severity': 'medium',
                              'excerpt': ', '.join(caps[:4])})
            score += 0.09

        if RE_REPEAT.search(text):
            findings.append({'rule': 'Repeated Characters (e.g. "soooo")', 'severity': 'low', 'excerpt': ''})
            score += 0.04

        if RE_EMOJI_CLUSTER.search(text):
            findings.append({'rule': 'Emoji Cluster (4+ in a row)', 'severity': 'low', 'excerpt': ''})
            score += 0.04

        return min(score, 1.0), findings

    # ── Linguistic Analysis ───────────────────────────────────────────
    def _linguistic_analysis(self, text: str) -> Tuple[float, List[Dict]]:
        findings, score = [], 0.0
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 5]
        words = re.findall(r'\b\w+\b', text.lower())

        if not words:
            return 0.0, []

        # Type-Token Ratio
        ttr = len(set(words)) / len(words)
        if ttr < 0.35:
            findings.append({'rule': f'Low Lexical Diversity (TTR={ttr:.2f}) — repetitive/templated',
                              'severity': 'medium', 'excerpt': ''})
            score += 0.14

        # Sentence length uniformity (bot-like)
        if len(sentences) > 3:
            lengths = [len(s.split()) for s in sentences]
            var = float(np.var(lengths))
            if var < 1.5:
                findings.append({'rule': 'Suspiciously Uniform Sentence Length (possible bot/template)',
                                  'severity': 'medium', 'excerpt': ''})
                score += 0.12

        # Readability
        flesch = self._flesch(text)
        if flesch < 20:
            findings.append({'rule': f'Very Low Readability (Flesch={flesch:.0f}) — obfuscated language',
                              'severity': 'low', 'excerpt': ''})
            score += 0.07

        # URL stuffing
        urls = re.findall(r'https?://\S+', text)
        if len(urls) > 2:
            findings.append({'rule': f'Multiple URLs detected ({len(urls)})',
                              'severity': 'medium', 'excerpt': ' '.join(urls[:2])})
            score += 0.11

        # Hashtag stuffing
        tags = re.findall(r'#\w+', text)
        if len(tags) > 10:
            findings.append({'rule': f'Hashtag Stuffing ({len(tags)} hashtags)',
                              'severity': 'medium', 'excerpt': ''})
            score += 0.10

        return min(score, 1.0), findings

    # ── BERT ─────────────────────────────────────────────────────────
    def _bert_predict(self, text: str) -> Tuple[float, Optional[Dict]]:
        """
        Run BERT classification.
        Production model: fine-tuned on FakeNewsNet/LIAR/PHEME.
        Current proxy: distilbert SST-2 (negative sentiment as weak manipulation proxy).
        """
        try:
            result = self.bert_pipeline(text[:512])[0]
            if result['label'] == 'NEGATIVE':
                bert_score = result['score'] * 0.6
            else:
                bert_score = (1 - result['score']) * 0.3

            detail = None
            if bert_score > 0.38:
                detail = {
                    'rule': f"BERT Model Flag ({result['label']}, conf={result['score']:.0%})",
                    'severity': 'high' if bert_score > 0.55 else 'medium',
                    'excerpt': 'Semantic analysis detected potentially manipulative content.'
                }
            return bert_score, detail
        except Exception as e:
            logger.error(f"BERT error: {e}")
            return 0.3, None

    # ── Helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _excerpt(text, pos, window=45):
        start = max(0, pos - 10)
        end = min(len(text), pos + window)
        return f"…{text[start:end].strip()}…"

    @staticmethod
    def _flesch(text):
        sents = max(len(re.findall(r'[.!?]+', text)), 1)
        words_list = re.findall(r'\b\w+\b', text)
        words = max(len(words_list), 1)
        syllables = sum(TextManipulationDetector._syllables(w) for w in words_list)
        return 206.835 - 1.015 * (words / sents) - 84.6 * (syllables / words)

    @staticmethod
    def _syllables(word):
        count = len(re.findall(r'[aeiou]+', word.lower()))
        if word.lower().endswith('e') and count > 1:
            count -= 1
        return max(count, 1)

    @staticmethod
    def _to_label(score):
        if score < 0.35:
            return 'Authentic'
        elif score < 0.65:
            return 'Suspicious'
        return 'Likely Manipulated'
