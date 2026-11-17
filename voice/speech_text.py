"""Text that must never reach a TTS engine.

Two classes of noise, both of which a speech model will happily pronounce:

- **Emoji** — cosmetic in chat, spoken garbage in audio.
- **Roleplay stage directions** — local models emit them. Spark-X2.5 opens
  turns with ``(with a warm smile)``; Kokoro/ElevenLabs read it out loud.
  Only roleplay-style asides are stripped (parenthetical groups with no
  sentence structure of their own), so ordinary prose parentheses survive.

Kept in one place because both backends need it; applied in the TTS layer
only, so chat transcripts keep whatever the model wrote.

Not handled: ``*sighs*``. An asterisk pair is equally likely to be emphasis
(``*very*``) as an action, and nothing measured has emitted one yet.
"""
import re

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\u20E3]+"
)

# A parenthetical aside: short, and carrying no sentence punctuation of its own.
# "(with a warm smile)" and "(smiling)" go; "(which, as I said, took a while)"
# stays, because that is a sentence someone might actually mean.
_ASIDE_RE = re.compile(r"\s*\(([^(),.?!:;]{1,60})\)(?=\s|$)")


def sanitize(text) -> str:
    """Strip emoji and roleplay asides, then collapse whitespace."""
    text = _EMOJI_RE.sub("", str(text))
    text = _ASIDE_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()
