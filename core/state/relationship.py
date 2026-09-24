# core/state/relationship.py
import uuid
import time
import math
import logging
import json
import re
from typing import Dict

from config.settings import Settings

# NOTE: Adjust import path for your actual models
from core.state.models import RelationshipValues

logger = logging.getLogger("Mai.RelationshipEngine")

_BASE_DIMS = ("trust", "comfort", "respect", "affection", "familiarity")


def _deterministic_deltas(user_message: str, mai_response: str = "") -> Dict[str, float]:
    """Lexicon-driven relationship deltas for a single exchange.

    Mirrors the LLM deep evaluator's guidance band (|delta| <= 0.04 per
    dimension per turn). Cheap, deterministic, no LLM and no database —
    safe to run on every chat-path turn.
    """
    user = str(user_message or "").lower()
    reply = str(mai_response or "").lower()
    deltas = {"trust": 0.0, "comfort": 0.0, "respect": 0.0,
              "affection": 0.0, "familiarity": 0.0}

    def has_any(text, phrases):
        return any(p in text for p in phrases)

    if has_any(user, Settings.RELATIONSHIP_GRATITUDE_WORDS):
        deltas["trust"] += Settings.RELATIONSHIP_GRATITUDE_TRUST_BOOST
        deltas["comfort"] += Settings.RELATIONSHIP_GRATITUDE_COMFORT_BOOST
        deltas["affection"] += Settings.RELATIONSHIP_GRATITUDE_AFFECTION_BOOST

    if has_any(user, Settings.RELATIONSHIP_PRAISE_WORDS):
        deltas["trust"] += Settings.RELATIONSHIP_PRAISE_TRUST_BOOST
        deltas["respect"] += Settings.RELATIONSHIP_PRAISE_RESPECT_BOOST
        deltas["comfort"] += Settings.RELATIONSHIP_PRAISE_COMFORT_BOOST

    if has_any(user, Settings.RELATIONSHIP_VULNERABILITY_WORDS):
        deltas["comfort"] += Settings.RELATIONSHIP_VULNERABILITY_COMFORT_BOOST
        deltas["trust"] += Settings.RELATIONSHIP_VULNERABILITY_TRUST_BOOST

    if has_any(user, Settings.RELATIONSHIP_HOSTILITY_WORDS):
        deltas["trust"] += Settings.RELATIONSHIP_HOSTILITY_TRUST_PENALTY
        deltas["comfort"] += Settings.RELATIONSHIP_HOSTILITY_COMFORT_PENALTY
        deltas["respect"] += Settings.RELATIONSHIP_HOSTILITY_RESPECT_PENALTY

    if has_any(user, Settings.RELATIONSHIP_AFFECTION_WORDS):
        deltas["affection"] += Settings.RELATIONSHIP_AFFECTION_BOOST
        deltas["trust"] += Settings.RELATIONSHIP_AFFECTION_TRUST_BOOST

    if has_any(reply, Settings.RELATIONSHIP_REASSURANCE_PHRASES):
        deltas["comfort"] += Settings.RELATIONSHIP_REASSURANCE_COMFORT_BOOST

    if user:
        deltas["familiarity"] += Settings.RELATIONSHIP_FAMILIARITY_BOOST

    clamp = Settings.RELATIONSHIP_MAX_DELTA
    for k in deltas:
        deltas[k] = max(-clamp, min(clamp, deltas[k]))
    return deltas

class RelationshipEngineV2:
    def __init__(self, state, llm=None):
        """
        Injected with the SharedState instance and the LLM Engine.
        """
        self.state = state
        self.llm = llm  # 🧠 Injected so the engine can run its own deep evaluations
        
        # 30 days half-life for relationship decay
        self.decay_halflife_seconds = 30 * 24 * 3600  

    # ==================================================
    # 🧠 DEEP EVALUATION PIPELINE (Moved from Memory)
    # ==================================================
    def analyze_and_log_interaction(self, user_message: str, mai_response: str, weight: float = 1.0):
        """
        Evaluates psychological/social metrics using the deep LLM configuration
        and safely logs transaction metrics into the relationship database.
        """
        if not self.llm:
            logger.warning("No LLM assigned to RelationshipEngine. Skipping deep evaluation.")
            return

        prompt = f"""
        You are the subconscious emotional evaluation engine for Mai, an AI companion.
        Analyze the following exchange between the User and Mai to determine its impact on their relationship.
        
        User: "{user_message}"
        Mai: "{mai_response}"
        
        Provide your assessment in strict, raw JSON format. Do not wrap it in markdown block quotes or text.
        
        Target JSON Format:
        {{
            "event_type": "short_snake_case_reason",
            "description": "A 1-sentence summary of the psychological dynamic.",
            "impacts": {{
                "trust": 0.0, 
                "comfort": 0.0, 
                "respect": 0.0, 
                "affection": 0.0
            }}
        }}
        
        Rules:
        1. Keep impact values small (between -0.04 and 0.04). Most routine interactions are 0.0.
        2. Increase trust/comfort if the user is supportive, polite, or opening up.
        3. Decrease metrics if the user is hostile, insulting, or dismissive.
        """

        try:
            # Execute the prompt against the LLM
            if hasattr(self.llm, "generate"):
                raw_output = self.llm.generate(
                     "Relationship Evaluation Engine",
                      prompt
                    )
            else:
                raw_output = self.llm.generate_with_tools(prompt, "System Evaluation Context")

            if not raw_output:
                return

            data = self._extract_json(raw_output)
            
            if isinstance(data, dict):
                # ✅ Calls its OWN method directly now
                self.log_interaction_evidence(
                    event_type=data.get("event_type", "routine_dialogue"),
                    description=data.get("description", "Standard conversation log."),
                    impacts=data.get("impacts", {}),
                    weight=weight
                )
                logger.info("Logged deep metric updates for: '%s'", data.get('event_type'))
                
        except Exception as e:
            logger.error("Failed parsing metrics in Relationship Evaluator: %s", e)

    # ==================================================
    # 🧭 DETERMINISTIC CHAT-PATH ANALYSIS (M10)
    # ==================================================
    def analyze_turn(self, user_message: str, mai_response: str = "",
                     weight: float = 1.0) -> Dict[str, float]:
        """Deterministic relationship update for a chat-path turn.

        No LLM, no database — runs on every think() exchange so trust /
        comfort / respect / affection evolve on the primary conversation
        path (API, web, kernel alike). Deltas mirror the LLM evaluator's
        guidance band and are clamped per dimension.
        """
        deltas = _deterministic_deltas(user_message, mai_response)
        if weight != 1.0:
            try:
                weight = max(0.0, min(1.0, float(weight)))
                deltas = {k: v * weight for k, v in deltas.items()}
            except (TypeError, ValueError):
                pass
        self.apply_deltas(deltas)
        return deltas

    def apply_deltas(self, deltas: Dict[str, float], save: bool = True):
        """Write relationship deltas into SharedState, clamped to [0, 1].

        Handles pydantic RelationshipValues (app), plain attribute objects
        (stubs/tests), and plain dicts without crashing.
        """
        if not self.state or not deltas:
            return
        try:
            with self.state.lock:
                current = self.state.relationship_scores
                if current is None:
                    return
                if hasattr(current, "model_dump"):
                    raw = current.model_dump()
                elif isinstance(current, dict):
                    raw = dict(current)
                else:
                    raw = {k: getattr(current, k, None) for k in _BASE_DIMS}
                values = {}
                for dim in _BASE_DIMS:
                    try:
                        base = float(raw.get(dim, 0.5))
                    except (TypeError, ValueError):
                        base = 0.5
                    delta = float(deltas.get(dim, 0.0) or 0.0)
                    values[dim] = max(0.0, min(1.0, base + delta))
                self._write_scores(values)
        except Exception as e:
            logger.warning("Relationship apply_deltas failed: %s", e)
            return
        if save:
            saver = getattr(self.state, "save_state_to_disk", None)
            if callable(saver):
                try:
                    saver()
                except Exception as e:
                    logger.debug("Relationship save skipped: %s", e)

    def _write_scores(self, values: Dict[str, float]):
        current = self.state.relationship_scores
        if hasattr(current, "model_dump"):
            try:
                self.state.relationship_scores = RelationshipValues(**values)
                return
            except Exception as e:
                logger.warning("RelationshipValues write failed: %s", e)
        if isinstance(current, dict):
            self.state.relationship_scores = {**current, **values}
            return
        for dim, val in values.items():
            try:
                setattr(current, dim, val)
            except Exception:
                pass

    # ==================================================
    # 🗄️ DATABASE & MATH (Your existing code)
    # ==================================================
    def log_interaction_evidence(self, event_type: str, description: str, impacts: Dict[str, float], weight: float = 1.0):
        """
        Logs an interaction event into the SQLite database primitive and triggers a score recalculation.
        """
        evidence_id = f"ev_{uuid.uuid4().hex[:8]}"
        timestamp = time.time()

        try:
            self.state.db.log_evidence(
                ev_id=evidence_id,
                ts=timestamp,
                ev_type=event_type,
                desc=description,
                impacts=impacts,
                weight=weight
            )
            
            self.recalculate_derived_scores()
            
        except Exception as e:
            logger.error("Failed to process relationship transaction: %s", str(e))

    def recalculate_derived_scores(self):
        """
        Computes effective relationship scores by parsing the SQLite transaction history.
        Applies exponential recency decay to older records.
        """
        now = time.time()
        
        raw_evidence = self.state.db.get_all_evidence()
        
        base_scores = {"trust": 0.5, "comfort": 0.5, "respect": 0.5, "affection": 0.3, "familiarity": 0.1}
        totals = {k: v for k, v in base_scores.items()}
        weights = {k: 1.0 for k in base_scores.keys()}
        
        for ev in raw_evidence:
            elapsed = now - ev["timestamp"]
            
            decay_factor = math.exp(-0.693 * (elapsed / self.decay_halflife_seconds))
            effective_weight = ev["weight"] * decay_factor
            
            # Note: Ensure ev["dimension_impacts"] matches what your DB returns. 
            # In your log_interaction_evidence you pass it as "impacts", so make sure SQLite returns it as "dimension_impacts".
            for dim, impact in ev.get("dimension_impacts", {}).items():
                if dim in totals:
                    totals[dim] += impact * effective_weight
                    weights[dim] += effective_weight

        updated_dict = {}
        for dim in base_scores.keys():
            normalized_val = totals[dim] / (weights[dim] if weights[dim] > 0 else 1.0)
            updated_dict[dim] = max(0.0, min(1.0, normalized_val))
            
        updated_dict["familiarity"] = max(0.0, min(1.0, updated_dict["familiarity"] + (0.001 * len(raw_evidence))))
        
        with self.state.lock:
            self.state.relationship_scores = RelationshipValues(**updated_dict)
            self.state.save_state_to_disk()
            
        logger.info("🔄 Relationship scores updated. Current Trust: %.2f | Comfort: %.2f", updated_dict['trust'], updated_dict['comfort'])

    # ==================================================
    # 🛠️ UTILITIES
    # ==================================================
    def _extract_json(self, text: str) -> dict:
        """Safely clean markdown artifacts and parse raw JSON text fields from LLM."""
        if not text:
            return {}
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0).strip())
                except json.JSONDecodeError:
                    pass
            return {}