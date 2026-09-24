# core/prompt_builder.py
from core.identity import get_identity as _get_identity_impl
from prompt.builder import PromptBuilder as NewPromptBuilder

_builder = NewPromptBuilder()


def build_system_prompt(
    context="",
    emotion=None,
    behavior="",
    personality=None,
    relationship=None,
    recall=None,
    knowledge=None,
    graph=None,
    experiences=None,
    tool_defs=None,
    system_notes=None,
    speech_pacing=None,
    cognitive_state=None,
    identity_data=None,
    monologue_enabled=False,
):
    if emotion is None:
        emotion = {}
    kwargs = dict(
        emotion_state=emotion,
        behavior=behavior,
        memory_context=context,
        recall=recall,
        knowledge=knowledge,
        graph=graph,
        tool_defs=tool_defs,
        personality=personality,
        relationship=relationship,
        system_notes=system_notes,
        speech_pacing=speech_pacing,
        cognitive_state=cognitive_state,
        identity_data=identity_data,
        monologue_enabled=monologue_enabled,
    )
    if experiences is not None:
        kwargs["experiences"] = experiences
    return _builder.build_system(**kwargs)


def get_identity():
    return _get_identity_impl()
