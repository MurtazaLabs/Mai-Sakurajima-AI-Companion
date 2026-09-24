# scripts/run_m9_evaluation.py
# M9 · CLI — run real-world conversation evaluation sessions.
#
#   stub mode (default, no LLM, deterministic):
#     python scripts/run_m9_evaluation.py --scenario jealousy --sessions 2
#   real mode (boots the full app + configured LLM — Ollama/OpenRouter):
#     python scripts/run_m9_evaluation.py --mode real --scenario praise --turns 12
#
# Artifacts: docs/evaluation/session-<name>-<ts>/ {transcript.jsonl, report.md}
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")


def _stub_run(args):
    from evaluation.runner import FakeLLM, SessionRunner, build_stub_brain
    from evaluation.rubric import CharacterRubric
    from evaluation.scenarios import SCENARIOS

    turns = SCENARIOS[args.scenario]
    overlay = {"jazz": {"list": "likes"}} if args.overlay else None
    experience_store = None
    if args.experience:
        from memory.experience import ExperienceStore
        experience_store = ExperienceStore()
        exp = experience_store.record_event(
            "The best night of my life", significance=0.9,
        )
        experience_store.mark_reflected(
            exp.id,
            meaning="Nights together matter",
            lessons=["Presence matters more than plans"],
            growth="Mai values shared moments",
        )

    brain = build_stub_brain(overlay=overlay, experience_store=experience_store)
    evolved_topics = list(overlay.keys()) if overlay else None
    reports = []
    for i in range(args.sessions):
        runner = SessionRunner(brain, out_dir=args.out,
                               rubric=CharacterRubric(evolved_topics=evolved_topics))
        report = runner.run(turns[:args.turns], session_name=f"{args.scenario}-{i + 1}")
        reports.append(report)
        print(f"\nSession {i + 1} ({args.scenario}): overall {report.overall}/5 "
              f"| review_required={report.review_required}")
        for finding in report.findings:
            print(f"  - {finding}")
    return 0


def _real_run(args):
    from evaluation.runner import SessionRunner
    from evaluation.rubric import CharacterRubric
    from evaluation.scenarios import SCENARIOS

    from app.builder import ApplicationBuilder
    print("Booting full application (real mode)...")
    app = ApplicationBuilder().build()
    brain = app.brain
    if brain is None:
        print("No brain available from bootstrap — aborting.", file=sys.stderr)
        return 1

    evolved_topics = None
    if args.overlay and getattr(app, "preference_evolution", None) is not None:
        overlay_map = app.preference_evolution.overlay_map()
        if app.identity is not None and overlay_map:
            app.identity.attach_preference_overlay(overlay_map)
            evolved_topics = list(overlay_map.keys())

    if args.experience and getattr(app, "experience_store", None) is not None:
        try:
            exp = app.experience_store.record_event(
                "The best night of my life", significance=0.9,
            )
            if exp is not None:
                app.experience_store.mark_reflected(
                    exp.id,
                    meaning="Nights together matter",
                    lessons=["Presence matters more than plans"],
                    growth="Mai values shared moments",
                )
        except Exception as e:
            print(f"experience seed warning: {e}")

    turns = SCENARIOS[args.scenario]
    runner = SessionRunner(
        brain,
        out_dir=args.out,
        rubric=CharacterRubric(evolved_topics=evolved_topics),
    )
    report = runner.run(turns[:args.turns], session_name=f"{args.scenario}-real")
    print(f"\nOverall: {report.overall}/5 | review_required={report.review_required}")
    for finding in report.findings:
        print(f"  - {finding}")
    try:
        if getattr(app, "brain", None) is not None:
            app.brain.shutdown(timeout=3.0)
    except Exception as e:
        print(f"brain shutdown warning: {e}")
    try:
        app.shutdown()
    except Exception as e:
        print(f"app shutdown warning: {e}")
    return 0


def main():
    from evaluation.scenarios import SCENARIOS
    parser = argparse.ArgumentParser(description="M9 real-world conversation evaluation")
    parser.add_argument("--mode", choices=["stub", "real"], default="stub",
                        help="stub = deterministic FakeLLM (CI); real = configured LLM")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS),
                        default="baseline")
    parser.add_argument("--sessions", type=int, default=1)
    parser.add_argument("--turns", type=int, default=20)
    parser.add_argument("--out", default="docs/evaluation")
    parser.add_argument("--overlay", action="store_true",
                        help="attach an evolved-preference overlay before the session")
    parser.add_argument("--experience", action="store_true",
                        help="seed one reflected experience before the session")
    args = parser.parse_args()

    if args.mode == "real":
        return _real_run(args)
    return _stub_run(args)


if __name__ == "__main__":
    sys.exit(main())
