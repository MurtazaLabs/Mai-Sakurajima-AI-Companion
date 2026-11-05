"""speechbrain deprecated-alias defusal (Oct 25 2026 compat shim).

``import speechbrain`` registers lazy ``DeprecatedModuleRedirect`` entries in
``sys.modules`` for the old module paths renamed in the 1.x release
(``speechbrain.pretrained``, ``speechbrain.k2_integration``, ...). Any later
``inspect`` walk over ``sys.modules`` — torch performs one per
``torch.library.impl_abstract`` call, which transformers >= 4.53 triggers via
torchvision during import — touches those ``__getattr__`` methods, which
attempt to import the external packages behind them (not installed), and the
unrelated import chain (kokoro/transformers) dies. The defusal in
voice/speaker/speaker_encoder.py replaces every placeholder with an inert
module; these tests pin that behavior with fake placeholders (cheap).
"""
import sys
import types

import pytest

from voice.speaker.speaker_encoder import _defuse_speechbrain_deprecated_redirects


class DeprecatedModuleRedirect(types.ModuleType):
    """Emulates speechbrain's LazyModule redirect: attribute access retries import."""

    def __getattr__(self, name):
        raise ImportError("Please install k2 to use k2")


_POISON_NAMES = ("speechbrain.pretrained", "speechbrain.k2_integration")


def _plant_poisons(monkeypatch):
    for name in _POISON_NAMES:
        monkeypatch.setitem(sys.modules, name, DeprecatedModuleRedirect(name))


def test_defusal_makes_placeholders_inert(monkeypatch):
    _plant_poisons(monkeypatch)
    _defuse_speechbrain_deprecated_redirects()
    for name in _POISON_NAMES:
        inert = sys.modules[name]
        assert type(inert).__name__ != "DeprecatedModuleRedirect"
        # inspect's getmodule probe must not trigger a poisoned __getattr__
        assert hasattr(inert, "__file__") is False


def test_defusal_ignores_non_speechbrain_keys(monkeypatch):
    real = types.ModuleType("speechbrain.pretrained")
    other = DeprecatedModuleRedirect("some.other.package")
    monkeypatch.setitem(sys.modules, "speechbrain.pretrained", real)
    monkeypatch.setitem(sys.modules, "some.other.package", other)
    _defuse_speechbrain_deprecated_redirects()
    assert sys.modules["speechbrain.pretrained"] is real  # plain speechbrain modules passed through
    assert sys.modules["some.other.package"] is other  # non-speechbrain poison untouched


def _sys_modules_walk_hasattr():
    """Mirror of inspect.getmodule's sys.modules loop that live-crashes on the
    speechbrain placeholders under torch.library's source lookup."""
    for module_name, module in list(sys.modules.items()):
        if module_name in ("__main__", "__builtin__", "builtins"):
            continue
        if hasattr(module, "__file__"):
            pass


def test_sys_modules_walk_survives_after_defusal(monkeypatch):
    _plant_poisons(monkeypatch)
    with pytest.raises(ImportError, match="k2"):
        _sys_modules_walk_hasattr()
    _defuse_speechbrain_deprecated_redirects()
    _sys_modules_walk_hasattr()  # inert placeholders -> walk completes


def test_real_speechbrain_placeholders_defused():
    pytest.importorskip("speechbrain")
    import speechbrain  # noqa: F401 — may register the redirects (no-op if a prior import defused them)
    _defuse_speechbrain_deprecated_redirects()
    remaining = [
        k
        for k, v in list(sys.modules.items())
        if type(v).__name__ == "DeprecatedModuleRedirect"
        and type(v).__module__ == "speechbrain.utils.importutils"
    ]
    # Contract: after defusal no speechbrain placeholder remains that a
    # sys.modules walk could trip on (order-independent by design).
    assert remaining == []
