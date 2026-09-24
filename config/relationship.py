# config/relationship.py
# M10 · Deterministic relationship dynamics for the chat path.
# Deltas stay inside the LLM guidance band (|delta| <= 0.04 per dimension per
# turn) so the deterministic analyzer and the LLM deep evaluator agree in scale.

# Maximum per-turn delta for any dimension (mirrors LLM guidance).
RELATIONSHIP_MAX_DELTA = 0.04

# Gratitude → trust + comfort (+ small affection).
RELATIONSHIP_GRATITUDE_WORDS = ["thank you", "thanks", "appreciate", "grateful"]
RELATIONSHIP_GRATITUDE_TRUST_BOOST = 0.020
RELATIONSHIP_GRATITUDE_COMFORT_BOOST = 0.020
RELATIONSHIP_GRATITUDE_AFFECTION_BOOST = 0.010

# Praise / recognition → trust + respect (+ small comfort).
RELATIONSHIP_PRAISE_WORDS = [
    "proud", "helped", "good listener", "great job", "amazing",
    "you're the best", "you're amazing", "you handled", "it worked",
    "the reason i", "the reason i'm",
]
RELATIONSHIP_PRAISE_TRUST_BOOST = 0.020
RELATIONSHIP_PRAISE_RESPECT_BOOST = 0.020
RELATIONSHIP_PRAISE_COMFORT_BOOST = 0.010

# Vulnerability / disclosure → comfort (+ small trust).
RELATIONSHIP_VULNERABILITY_WORDS = [
    "i feel", "i've been", "i have been", "i'm scared", "i am scared",
    "i'm worried", "i am worried", "struggling", "opening up",
    "my anxiety", "i can't", "i cannot", "honestly",
]
RELATIONSHIP_VULNERABILITY_COMFORT_BOOST = 0.020
RELATIONSHIP_VULNERABILITY_TRUST_BOOST = 0.010

# Hostility / dismissal → trust − comfort − respect.
RELATIONSHIP_HOSTILITY_WORDS = [
    "stupid", "idiot", "shut up", "annoying", "hate you",
    "useless", "i don't need you", "i dont need you", "waste of time",
]
RELATIONSHIP_HOSTILITY_TRUST_PENALTY = -0.040
RELATIONSHIP_HOSTILITY_COMFORT_PENALTY = -0.030
RELATIONSHIP_HOSTILITY_RESPECT_PENALTY = -0.030

# Affection → affection (+ small trust).
RELATIONSHIP_AFFECTION_WORDS = ["love you", "miss you", "care about you", "hug"]
RELATIONSHIP_AFFECTION_BOOST = 0.030
RELATIONSHIP_AFFECTION_TRUST_BOOST = 0.010

# Mai's reassurance / support in her own reply → comfort.
RELATIONSHIP_REASSURANCE_PHRASES = [
    "don't have to carry it alone", "i'm here", "i am here",
    "it's okay", "it's not your fault", "you don't have to",
]
RELATIONSHIP_REASSURANCE_COMFORT_BOOST = 0.010

# Continued presence → familiarity.
RELATIONSHIP_FAMILIARITY_BOOST = 0.010
