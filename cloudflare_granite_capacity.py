"""Conservative Workers AI Granite capacity lane calculation."""
from decimal import Decimal, ROUND_FLOOR

FREE_NEURONS_PER_DAY = Decimal("10000")
INPUT_NEURONS_PER_M = Decimal("1542")
OUTPUT_NEURONS_PER_M = Decimal("10158")
MIN_PROMPT_TOKENS = Decimal("1024")
OUTPUT_RATIO_MAX = Decimal("0.2")
PREFLIGHT_MAX_OUTPUT = Decimal("1")
CONCISE_MAX_OUTPUT = Decimal("102")


def granite_concise_lane_tpd():
    """Single-pass concise lane: >=1024 input tokens, <=102 output tokens."""
    i = MIN_PROMPT_TOKENS
    o = CONCISE_MAX_OUTPUT
    useful = i + o
    neurons = INPUT_NEURONS_PER_M * i + OUTPUT_NEURONS_PER_M * o
    neurons_per_m_useful = neurons / useful
    tpd = (FREE_NEURONS_PER_DAY * Decimal(1_000_000) /
           neurons_per_m_useful).to_integral_value(rounding=ROUND_FLOOR)
    return {
        "certified_tokens_per_day": int(tpd),
        "worst_neurons_per_million_useful": str(neurons_per_m_useful),
        "min_prompt_tokens": int(i),
        "max_output_tokens": int(o),
        "input_passes": 1,
    }


def granite_ratio_lane_tpd():
    """Worst case: two input passes, main output <=20%, preflight <=1 output token."""
    i = MIN_PROMPT_TOKENS
    r = OUTPUT_RATIO_MAX
    useful = i * (Decimal(1) + r)
    neurons = (Decimal(2) * INPUT_NEURONS_PER_M * i +
               OUTPUT_NEURONS_PER_M * (i * r + PREFLIGHT_MAX_OUTPUT))
    neurons_per_m_useful = neurons / useful
    tpd = (FREE_NEURONS_PER_DAY * Decimal(1_000_000) /
           neurons_per_m_useful).to_integral_value(rounding=ROUND_FLOOR)
    return {
        "certified_tokens_per_day": int(tpd),
        "worst_neurons_per_million_useful": str(neurons_per_m_useful),
        "min_prompt_tokens": int(i),
        "max_output_ratio": str(r),
        "preflight_input_passes": 1,
        "main_input_passes": 1,
        "preflight_max_output_tokens": int(PREFLIGHT_MAX_OUTPUT),
    }
