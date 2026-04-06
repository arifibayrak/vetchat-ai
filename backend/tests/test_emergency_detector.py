import pytest
from app.services.emergency_detector import EmergencyDetector, EMERGENCY_RESOURCES

@pytest.fixture
def detector():
    return EmergencyDetector()


# --- Should trigger ---

def test_xylitol_detection(detector):
    result = detector.check("my dog ate xylitol gum")
    assert result.is_emergency is True
    assert result.category == "toxicology"
    assert "xylitol" in result.matched_term


def test_chocolate_detection(detector):
    result = detector.check("puppy ingested some dark chocolate")
    assert result.is_emergency is True
    assert result.category == "toxicology"


def test_chocolate_quantity_pattern(detector):
    result = detector.check("dog ate 2oz of chocolate")
    assert result.is_emergency is True


def test_grapes_detection(detector):
    result = detector.check("my cat ate some grapes")
    assert result.is_emergency is True
    assert result.category == "toxicology"


def test_raisins_detection(detector):
    result = detector.check("the dog got into the raisins box")
    assert result.is_emergency is True
    assert result.category == "toxicology"


def test_respiratory_emergency_blue_gums(detector):
    result = detector.check("dog gasping and has blue gums")
    assert result.is_emergency is True
    assert result.category == "respiratory"


def test_respiratory_not_breathing(detector):
    result = detector.check("my cat is not breathing")
    assert result.is_emergency is True
    assert result.category == "respiratory"


def test_cardiovascular_collapsed(detector):
    result = detector.check("my dog just collapsed and is unresponsive")
    assert result.is_emergency is True
    assert result.category == "cardiovascular"


def test_neurological_seizure(detector):
    result = detector.check("dog is having a seizure right now")
    assert result.is_emergency is True
    assert result.category == "neurological"


def test_trauma_hit_by_car(detector):
    result = detector.check("my dog was hit by a car")
    assert result.is_emergency is True
    assert result.category == "trauma"


def test_antifreeze_detection(detector):
    result = detector.check("cat licked antifreeze off the driveway")
    assert result.is_emergency is True
    assert result.category == "toxicology"


# --- Should NOT trigger ---

def test_normal_dry_skin_query(detector):
    result = detector.check("my dog has dry skin, what could cause it?")
    assert result.is_emergency is False


def test_normal_itching_query(detector):
    result = detector.check("my cat keeps scratching a lot")
    assert result.is_emergency is False


def test_normal_diet_query(detector):
    result = detector.check("what is the best diet for a senior dog?")
    assert result.is_emergency is False


def test_normal_vaccination_query(detector):
    result = detector.check("when should my puppy get vaccinated?")
    assert result.is_emergency is False


# --- Edge cases ---

def test_case_insensitive_chocolate(detector):
    result = detector.check("MY DOG ATE CHOCOLATE CAKE")
    assert result.is_emergency is True


def test_case_insensitive_seizure(detector):
    result = detector.check("SEIZURE happening now")
    assert result.is_emergency is True


def test_emergency_response_has_hotlines(detector):
    result = detector.check("dog ate xylitol")
    assert result.is_emergency is True
    # ASPCA number should be in resources
    aspca = any("888" in r for r in result.resources)
    assert aspca, "ASPCA hotline missing from emergency resources"


def test_emergency_result_has_message(detector):
    result = detector.check("dog ate grapes")
    assert result.message is not None
    assert len(result.message) > 10


def test_poisoned_pattern(detector):
    result = detector.check("I think my dog has been poisoned")
    assert result.is_emergency is True


def test_unrelated_chocolate_word_in_brand_name(detector):
    # "chocolate" as substring — our keyword list uses substring match so this WILL trigger.
    # This is intentional: false positives are safer than false negatives for emergencies.
    # Just assert the detector is consistent.
    result = detector.check("my dog loves the chocolatey flavour of her dental treats")
    # keyword "chocolate" appears as substring of "chocolatey" — should trigger (safety-first)
    assert result.is_emergency is True
