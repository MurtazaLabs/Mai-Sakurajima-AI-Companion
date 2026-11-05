# Complete Folder Structure

> Generated Aug 8 2026 (counts refreshed Aug 9 2026 — M10–M13 additions). Every folder and file in the repository, excluding runtime artifacts: `mai_env/`, `__pycache__/`, `.pytest_cache/`.

---

## Per-Folder File Counts

| Folder | Files | Folder | Files |
|--------|-------|--------|-------|
| `.opencode/` | 160 | `api/` | 91 |
| `core/` | 56 | `tests/` | 55 (incl. behavior/) |
| `docs/` | 26 | `voice/` | 31 |
| `knowledge/` | 28 | `memory/` | 27 |
| `app/` | 18 | `config/` | 19 |
| `agency/` | 12 | `profiling/` | 7 |
| `plugins/` | 6 | `native/` | 6 |
| `prompt/` | 6 | `models/` | 5 |
| `data/` | 5 | `vector_memory/` | 5 |
| `scripts/` | 6 | `reasoning/` | 4 |
| `observability/` | 3 | `important/` | 3 |
| `execution/` | 3 | `llm/` | 3 |
| `evaluation/` | 5 | `logs/` | 2 |
| `cache/` | 2 | `temp/` | 1 |
| `gateways/` | 1 | | |

**Total:** 660 folders+files listed | **18 source packages + 2 entry points** | **42,395 source lines** (py-only, Aug 9)

---

## Complete Tree

```text
E:\Mai_ai\
    .opencode/
        skills/
            mai-ai-suite/
                reference/
                    ai-infrastructure-expert/
                    ai-product-manager/
                    character-narrative-designer/
                    data-analytics-specialist/
                    desktop-os-expert/
                    devops-engineer/
                    integration-api-ecosystem-specialist/
                    knowledge-base-builder/
                    llm-model-specialist/
                    mai-ai-systems-auditor/
                    mai-development-orchestrator/
                    memory-architecture-expert/
                    performance-engineer/
                    prompt-architect/
                    python-codebase-architect/
                    python-master-engineer/
                    reasoning-architecture-expert/
                    security-engineer/
                    ui-ux-designer/
                    voice-architecture-expert/
                CHANGELOG
                README.md
                SKILL.md
            skill-creator/
    agency/
        __init__.py
        agent.py
        dream_report.py
        dream_tasks.py
        dreaming.py
        evolution.py
        goals.py
        preference_evolution.py
        procedural.py
        registry.py
        tools.py
        world.py
    api/
        middleware/
            __init__.py
            rate_limiter.py
        static/
            css/
                animations.css
                mobile.css
                orb.css
                presence.css
                style.css
                widgets.css
                windows.css
            img/
                (20+ PNG assets)
            js/
                agency.js
                chat.js
                consciousness.js
                desktop.js
                desktop-nav.js
                graph.js
                graph3d.js
                graph-toggle.js
                inspector.js
                memory.js
                motion.js
                notifications.js
                orb.js
                os.js
                page-redirect.js
                permissions.js
                presence.js
                reasoning.js
                router.js
                search.js
                sw.js
                system.js
                tasks.js
                voice.js
                widgets.js
                windows.js
            agency.html
            chat.html
            consciousness.html
            graph.html
            index.html
            inspector.html
            manifest.json
            memory.html
            permissions.html
            presence.html
            reasoning.html
            system.html
            tasks.html
            voice.html
        __init__.py
        auth.py
        certs.py
        errors.py
        routes_agency.py
        routes_auth.py
        routes_chat.py
        routes_dashboard.py
        routes_inspector.py
        routes_knowledge.py
        routes_memory.py
        routes_permissions.py
        routes_profile.py
        routes_reasoning.py
        routes_system.py
        routes_tasks.py
        routes_voice.py
        server.py
        static_serving.py
        stream_manager.py
        ws_bridge.py
    app/
        builders/
            __init__.py
            agency.py
            cognition.py
            infrastructure.py
            knowledge.py
            memory.py
            reasoning.py
            runtime.py
            voice.py
        __init__.py
        application.py
        boot.py
        builder.py
        config_loader.py
        lifecycle.py
        metadata.py
        orchestrator.py
        validation.py
    cache/
        personality_state.json
        thought_journal.json
    config/
        ai.py
        autonomy.py
        character.py
        debug.py
        emotion.py
        executor.py
        experience.py
        llm.py
        memory.py
        needs.py
        paths.py
        personality.py
        reflection.py
        relationship.py
        runtime.py
        scheduler.py
        settings.py
        speaker.py
        voice.py
    core/
        autonomy/
            engine.py
        identity/
            character/
                volume-01-identity.md
                volume-02-speech.md
                volume-03-relationships.md
                volume-04-rule-resolution.md
            profiles/
            __init__.py
            boundaries.py
            canonical.py
            identity.py
            identity_core.py
            personality.py
            preferences.py
            profiles.py
            speech.py
            values.py
        state/
            relationships/
                User.json
            db.py
            models.py
            per_person_relationship.py
            relationship.py
            shared_state.py
        attention.py
        behavior_builder.py
        brain.py
        brain_memory.py
        brain_routing.py
        cognition.py
        cognitive_state.py
        config_manager.py
        emotion.py
        emotion_goals.py
        emotion_system.py
        event_bus.py
        event_metadata.py
        event_registry.py
        event_specs.py
        idle_behavior.py
        mai_message.py
        memory_coordinator.py
        os_kernel.py
        personality_state.py
        plugin_system.py
        post_think_hooks.py
        profile_store.py
        prompt_builder.py
        prompt_orchestrator.py
        reasoning_coordinator.py
        response_pipeline.py
        scheduler.py
        style_filter.py
        tasks.py
        tool_manager.py
        utils.py
        wake_generator.py
        write_journal.py
    data/
        certs/
            cert.pem
            key.pem
            openssl.cnf
        profiles/
            profiles.db
        vector_db/
            chroma.sqlite3
    execution/
        handlers.py
        safe_executor.py
        task_executor.py
    evaluation/
        __init__.py
        rubric.py
        runner.py
        scenarios.py
        transcript.py
    gateways/
        discord_bot.py
    knowledge/
        attention.py
        belief_engine.py
        brain_graph.py
        builder.py
        chunker.py
        cognitive_graph.py
        consolidation.py
        document_store.py
        extractor.py
        graph.py
        graph_exporter.py
        graph_manager.py
        graph_reflection.py
        indexer.py
        link_integrity.py
        memory_writer.py
        obsidian_reader.py
        obsidian_writer.py
        reasoning.py
        retriever.py
        state_dumper.py
        vault_compiler.py
        vault_janitor.py
        vault_logger.py
        vault_migrator.py
        vault_post_processor.py
        vault_schema.py
        watcher.py
    llm/
        providers/
            ollama.py
            openrouter.py
        manager.py
    logs/
        cognitive_audit/
        orchestrator/
    memory/
        consolidation.py
        decay.py
        embedding_service.py
        emotion_analyzer.py
        experience.py
        extractor.py
        graph.py
        hierarchy.py
        intelligence.py
        lifecycle.py
        manager.py
        memory.py
        node.py
        pipeline.py
        recall.py
        reflection.py
        relationship_updater.py
        router.py
        schema.py
        schema_migrator.py
        scoring.py
        search_engine.py
        state.py
        tagger.py
        vault_loader.py
        vector_lifecycle.py
        vector_store.py
    models/
        speaker/
            classifier.ckpt
            embedding_model.ckpt
            hyperparams.yaml
            label_encoder.ckpt
            mean_var_norm_emb.ckpt
    native/
        __init__.py
        hotkeys.py
        notifier.py
        startup.py
        tray.py
        watchdog.py
    observability/
        event_inspector.py
        health.py
        tracer.py
    plugins/
        calendar.py
        example_plugin.py
        news.py
        system_monitor.py
        weather.py
        web_scraper.py
    profiling/
        analyze_boot.py
        analyze_chat.py
        boot_profile.prof
        chat_profile.prof
        profile_boot.py
        profile_chat.py
        README.md
    prompt/
        __init__.py
        agent.py
        builder.py
        character.py
        context.py
        emotional.py
    reasoning/
        engine.py
        journal.py
        learning.py
        reflection.py
    scripts/
        backfill_conversations.py
        build_daemon.py
        check_vault_writers.py
        installer.iss
        run_m9_evaluation.py
        sweep_graph_junk.py
    temp/
        arch_analysis.json
    tests/
        behavior/
            __init__.py
            fixtures.py
            harness.py
            test_causal_trace.py
            test_character_behavior.py
            test_conflict_resolution.py
            test_renderer_parity.py
        conftest.py
        test_agency.py
        test_agency_advanced.py
        test_brain.py
        test_brain_graph.py
        test_config.py
        test_core.py
        test_deferred_v43.py
        test_dream_engine.py
        test_event_bus.py
        test_event_bus_fabric.py
        test_event_inspector.py
        test_event_metadata.py
        test_event_registry.py
        test_experience_context.py
        test_execution.py
        test_extractor.py
        test_greeting_first.py
        test_health.py
        test_integration.py
        test_identity_core.py
        test_knowledge.py
        test_llm.py
        test_mai_message.py
        test_memory.py
        test_needs_engine.py
        test_observability.py
        test_orchestrator.py
        test_per_person.py
        test_phase3.py
        test_preference_evolution.py
        test_profile_store.py
        test_prompt.py
        test_rate_limiter.py
        test_reasoning.py
        test_relationship_chat.py
        test_rule_resolution.py
        test_scheduler.py
        test_schema.py
        test_speaker.py
        test_thought_packet.py
        test_vad.py
        test_voice.py
        test_voice_renderer.py
        test_voice_tier3.py
        test_voice_tier4.py
    vector_memory/
        555918a3-f5d2-4169-b96f-7885a16a91aa/
            data_level0.bin
            header.bin
            length.bin
            link_lists.bin
        chroma.sqlite3
    voice/
        speaker/
            profiles/
            __init__.py
            speaker_database.py
            speaker_encoder.py
            speaker_manager.py
            speaker_profile.py
        adaptive_noise_filter.py
        audio_buffer.py
        audio_utils.py
        diarization.py
        emotion_detector.py
        events.py
        full_aec.py
        interrupt.py
        kokoro_tts.py
        metrics.py
        microphone.py
        noise_filter.py
        prosody.py
        realtime.py
        recorder.py
        renderer.py
        speaker_identifier.py
        stream_player.py
        stt.py
        utterance_segmenter.py
        vad.py
        voice_config.py
        voice_event.py
        voice_manager.py
        voice_state.py
        wake_detector.py
        wake_word.py
    AGENTS.md
    docker-compose.yml
    Dockerfile
    pytest.ini
    requirements.txt
    requirements-docker.txt
    run.py
    run_daemon.py
```

---

## Wiki Links

**Architecture summaries (reading order):**
- [[01-Architecture/01-System Overview]]
- [[01-Architecture/02-Application Boot & Lifecycle]]
- [[01-Architecture/03-Core Brain Kernel & State]]
- [[01-Architecture/04-Memory Subsystem]]
- [[01-Architecture/05-Knowledge Graph & Vault]]
- [[01-Architecture/06-Agency Reasoning LLM & Execution]]
- [[01-Architecture/07-Voice Subsystem]]
- [[01-Architecture/08-API Native & Surface]]
- [[01-Architecture/09-Events & Data Flow]]
- [[01-Architecture/10-Status & Debt]]

**Feature specs:**
- [[03-Features/Native OS Bridge Architecture]]
- [[03-Features/Discord Integration Plan]]
- [[03-Features/Event Fabric Architecture]]

**Master reference:**
- [[05-Reference/MERGED_COMPLETE Reference]]

**Project charter:**
- [[00-Overview/Project Charter]]