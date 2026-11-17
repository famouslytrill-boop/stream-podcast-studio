"""Pure media arithmetic adapted from SONARA's source-qualified formula catalogue.

Source: famouslytrill-boop/sonara-os@1693036c4e50b6b4d15db5b4943752cac5552b6d,
lib/sonara-formula-library.cjs: media_duration_seconds, media_payload_mebibytes,
render_time_estimate_seconds. These calculations do not dispatch work or predict views.
"""
from tools.studio_tools import finite


def media_math(duration_seconds, bitrate_bits_per_second, frames_per_second=30,
               measured_frames_per_second=None, overhead_seconds=0):
    duration = finite(duration_seconds, "duration_seconds", .001, 43200)
    bitrate = finite(bitrate_bits_per_second, "bitrate_bits_per_second", 1, 1_000_000_000)
    fps = finite(frames_per_second, "frames_per_second", .001, 240)
    overhead = finite(overhead_seconds, "overhead_seconds", 0, 86400)
    frames = duration * fps
    measured = None if measured_frames_per_second is None else finite(measured_frames_per_second, "measured_frames_per_second", .001, 1_000_000)
    return {"frame_count": frames, "duration_seconds": frames / fps,
            "estimated_payload_mib": bitrate * duration / (8 * 1048576),
            "estimated_render_seconds": None if measured is None else frames / measured + overhead,
            "estimate_basis": "Supplied bitrate; excludes container overhead. Render time requires an actual comparable measured frame rate.",
            "unknown": ["estimated_render_seconds"] if measured is None else [],
            "not_a_platform_performance_or_income_prediction": True}
