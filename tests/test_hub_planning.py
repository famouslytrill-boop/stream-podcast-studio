import unittest
from hub.planning import media_math
from hub.mcp import Client
from tools.studio_tools import StudioError


class MediaMathTests(unittest.TestCase):
    def test_units_known_result_and_missing_measurement(self):
        result = media_math(10, 8388608, 30)
        self.assertEqual(result["frame_count"], 300)
        self.assertEqual(result["estimated_payload_mib"], 10)
        self.assertIsNone(result["estimated_render_seconds"])
        measured = media_math(10, 8388608, 30, 60, 2)
        self.assertEqual(measured["estimated_render_seconds"], 7)

    def test_invalid_values_and_pure_tool_without_running_hub(self):
        for kwargs in [{"duration_seconds": float("nan")}, {"frames_per_second": 0}, {"measured_frames_per_second": 0}, {"bitrate_bits_per_second": True}]:
            data = {"duration_seconds": 10, "bitrate_bits_per_second": 1000, **kwargs}
            with self.assertRaises(StudioError):
                media_math(**data)
        result = Client("missing-workspace").call("studio_media_math", {"duration_seconds": 10, "bitrate_bits_per_second": 1000})
        self.assertIsNone(result["estimated_render_seconds"])


if __name__ == "__main__":
    unittest.main()
