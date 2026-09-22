import sys
from pathlib import Path

# Add the project root to Python's import path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.parser import extract_resume_text
from app.scoring import calibrated_score


SAMPLE_DIR = BASE_DIR / "sample_data"


def load_resume(filename: str) -> str:
    path = SAMPLE_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Sample resume not found: {path}"
        )

    text, warning = extract_resume_text(
        path.name,
        path.read_bytes(),
    )

    if warning:
        print(
            f"Parser warning for {filename}: {warning}"
        )

    if not text.strip():
        raise ValueError(
            f"No text extracted from {filename}"
        )

    return text


def similarity_score(
    resume_a: str,
    resume_b: str,
) -> float:
    """
    Simple lexical similarity used only for the
    calibration demonstration.

    This is not an industry-standard metric.
    It is a lightweight diagnostic to show that
    similar resumes should not receive extremely
    different scores.
    """

    words_a = set(
        resume_a.lower().split()
    )

    words_b = set(
        resume_b.lower().split()
    )

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def demo_raw_scores() -> dict[str, float]:
    """
    Example raw scores representing how the scoring
    model could respond to three similar resumes.

    These values are intentionally close so that we
    can demonstrate the calibration behavior.
    """

    return {
        "resume_a.txt": 78.0,
        "resume_b.txt": 74.0,
        "resume_c.txt": 62.0,
    }


def main() -> None:
    print("=" * 60)
    print("RESUME FIT SCORER - CALIBRATION DEMONSTRATION")
    print("=" * 60)

    # ---------------------------------------------------------
    # Load three sample resumes
    # ---------------------------------------------------------

    resumes = {}

    for filename in [
        "resume_a.txt",
        "resume_b.txt",
        "resume_c.txt",
    ]:
        resumes[filename] = load_resume(filename)

    print("\nLoaded resumes:")

    for filename, text in resumes.items():
        print(
            f"  {filename}: "
            f"{len(text)} characters"
        )

    # ---------------------------------------------------------
    # Similarity diagnostics
    # ---------------------------------------------------------

    print("\nPairwise lexical similarity:")

    filenames = list(resumes.keys())

    for i in range(len(filenames)):
        for j in range(i + 1, len(filenames)):

            first = filenames[i]
            second = filenames[j]

            similarity = similarity_score(
                resumes[first],
                resumes[second],
            )

            print(
                f"  {first} vs {second}: "
                f"{similarity:.3f}"
            )

    # ---------------------------------------------------------
    # Raw model scores
    # ---------------------------------------------------------

    raw_scores = demo_raw_scores()

    print("\nRaw scores:")

    for filename, score in raw_scores.items():
        print(
            f"  {filename}: {score:.2f}"
        )

    # ---------------------------------------------------------
    # Apply calibration
    # ---------------------------------------------------------

    calibrated_scores = {}

    print("\nCalibrated scores:")

    for filename, raw_score in raw_scores.items():

        calibrated = calibrated_score(
            raw_score
        )

        calibrated_scores[filename] = calibrated

        print(
            f"  {filename}: "
            f"raw={raw_score:.2f} "
            f"-> calibrated={calibrated:.2f}"
        )

    # ---------------------------------------------------------
    # Compare A and B
    # ---------------------------------------------------------

    raw_gap = abs(
        raw_scores["resume_a.txt"]
        - raw_scores["resume_b.txt"]
    )

    calibrated_gap = abs(
        calibrated_scores["resume_a.txt"]
        - calibrated_scores["resume_b.txt"]
    )

    print("\nCalibration comparison:")

    print(
        f"  Resume A/B raw gap: "
        f"{raw_gap:.2f} points"
    )

    print(
        f"  Resume A/B calibrated gap: "
        f"{calibrated_gap:.2f} points"
    )

    # ---------------------------------------------------------
    # Assignment guardrail
    # ---------------------------------------------------------

    print("\nCalibration guardrail:")

    if calibrated_gap <= 15:
        print(
            "  PASS: similar resumes remain "
            "within the 15-point calibration guardrail."
        )
    else:
        print(
            "  REVIEW: similar resumes exceed "
            "the 15-point calibration guardrail."
        )

    print("\nNote:")
    print(
        "The 15-point threshold is a project-level "
        "calibration guardrail, not an industry standard."
    )

    print("\n" + "=" * 60)
    print("CALIBRATION DEMONSTRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()