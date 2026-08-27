import pytest

from loomi.demo import ask_context, ask_feedback
from loomi.models import Occasion, Outfit, OutfitContext, ScoredOutfit, WeatherCondition


class FakeInput:
    """Gibt nacheinander vordefinierte Antworten zurück."""

    def __init__(self, answers):
        self._answers = list(answers)

    def __call__(self, prompt=""):
        if not self._answers:
            raise AssertionError(f"Keine weiteren Eingaben vorgesehen (Prompt: {prompt!r})")
        return self._answers.pop(0)


def test_ask_context_asks_only_weather():
    fake = FakeInput(["24", "2"])
    ctx = ask_context(fake)
    assert ctx.temperature == 24.0
    assert ctx.condition is WeatherCondition.CLOUDY  # Index 2
    assert ctx.occasion is Occasion.CASUAL  # Default, wird nicht abgefragt
    assert ctx.preferred_style is None


def test_ask_context_uses_defaults_on_enter():
    fake = FakeInput(["", "rain"])
    ctx = ask_context(fake)
    assert ctx.temperature == 20.0
    assert ctx.condition is WeatherCondition.RAIN  # Wert statt Index


def test_ask_context_accepts_german_comma_and_retries():
    fake = FakeInput(["abc", "24,5", "2"])
    ctx = ask_context(fake)
    assert ctx.temperature == 24.5  # "24,5" wird akzeptiert
    assert ctx.condition is WeatherCondition.CLOUDY


def test_ask_context_retries_invalid_condition():
    fake = FakeInput(["20", "99", "sunny"])
    ctx = ask_context(fake)
    assert ctx.condition is WeatherCondition.SUNNY  # nach ungültigem Index


def test_ask_context_rejects_out_of_range_temperature():
    fake = FakeInput(["100", "-50", "8", "2"])
    ctx = ask_context(fake)
    assert ctx.temperature == 8.0
    assert ctx.condition is WeatherCondition.CLOUDY


def test_ask_context_accepts_custom_occasion():
    fake = FakeInput(["8", "2"])
    ctx = ask_context(fake, occasion=Occasion.WORK)
    assert ctx.occasion is Occasion.WORK


def make_scored() -> ScoredOutfit:
    return ScoredOutfit(outfit=Outfit(), total=0.9, components=[])


def test_ask_feedback_accepts_rating():
    fake = FakeInput(["4"])
    feedback = ask_feedback(fake, make_scored())
    assert feedback is not None
    assert feedback.rating == 4
    assert feedback.outfit == Outfit()


def test_ask_feedback_retries_invalid_rating():
    fake = FakeInput(["abc", "0", "6", "3"])
    feedback = ask_feedback(fake, make_scored())
    assert feedback is not None
    assert feedback.rating == 3


def test_ask_feedback_skip_on_enter():
    fake = FakeInput([""])
    assert ask_feedback(fake, make_scored()) is None


def test_ask_feedback_stores_context():
    fake = FakeInput(["5"])
    context = OutfitContext(12.0, WeatherCondition.RAIN, Occasion.CASUAL)
    feedback = ask_feedback(fake, make_scored(), context)
    assert feedback is not None
    assert feedback.context is context
