import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.captions import Cue, load_captions, parse_srt, rebase_cues, srt_text
from tools.clip_tools import StudioError, render
from tools.transcription_benchmark import word_error_rate
from tools.studio_tools import read_json


class CaptionTests(unittest.TestCase):
    def test_windows_powershell_utf8_json_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'powershell-profile.json'
            path.write_text('{"title":"Reviewed caption"}', encoding='utf-8-sig')
            self.assertEqual(read_json(path), {'title': 'Reviewed caption'})

    def test_word_error_rate_counts_insertions_deletions_and_substitutions(self):
        stats = word_error_rate('One clear voice here', 'One loud voice right here now')
        self.assertEqual(stats['reference_words'], 4)
        self.assertEqual(stats['edit_distance'], 3)
        self.assertEqual(stats['word_error_rate'], 0.75)
        self.assertEqual(word_error_rate('A b c', 'a, B!')['edit_distance'], 1)

    def test_bom_crlf_unicode_and_basic_tags(self):
        cues = parse_srt('\ufeff1\r\n00:00:01,125 --> 00:00:02,500\r\n<i>That’s</i> the room.\r\n')
        self.assertEqual(cues, [Cue(1125, 2500, 'That’s the room.')])

    def test_invalid_timing_overlap_and_control_markup(self):
        bad = ["", "1\n00:90:00,000 --> 00:91:00,000\nNo", "1\n00:00:02,000 --> 00:00:01,000\nNo",
               "1\n00:00:00,000 --> 00:00:02,000\nOne\n\n2\n00:00:01,000 --> 00:00:03,000\nTwo",
               "1\n00:00:00,000 --> 00:00:01,000\n{\\pos(0,0)}Move",
               "1\n00:00:00,000 --> 00:00:01,000\n<script>no</script>"]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(StudioError):
                parse_srt(text)

    def test_cut_clamps_rebases_and_omits_outside_cues(self):
        cues = [Cue(0, 500, 'Before'), Cue(900, 1300, 'Start'), Cue(1500, 2300, 'End'), Cue(3500, 4000, 'After')]
        actual = rebase_cues(cues, 1, 2)
        self.assertEqual(actual, [Cue(0, 300, 'Start'), Cue(500, 1000, 'End')])
        self.assertEqual(parse_srt(srt_text(actual)), actual)

    def test_network_and_timebase_are_refused(self):
        for config in ({'file': 'https://example.com/captions.srt', 'timebase': 'source'},
                       {'file': 'captions.srt', 'timebase': 'clip'}):
            with self.assertRaises(StudioError):
                load_captions(config, Path('.'), 30)

    def test_review_is_strict_and_source_duration_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'captions.srt').write_text('1\n00:00:01,000 --> 00:00:02,000\nTest\n')
            config = {'file': 'captions.srt', 'timebase': 'source', 'reviewed': 'true'}
            _, info = load_captions(config, root, 3)
            self.assertEqual(info['review_pending'], ['captions_reviewed'])
            with self.assertRaises(StudioError):
                load_captions(config, root, 1)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class CaptionExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ember-caption-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'test source.mkv'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                        'color=c=black:size=640x360:rate=30', '-f', 'lavfi', '-i',
                        'sine=frequency=440:sample_rate=48000', '-t', '3', '-c:v', 'libx264',
                        '-threads', '2', '-c:a', 'pcm_s16le', str(self.source)], check=True, capture_output=True)
        self.caption = self.root / 'reviewed captions.srt'
        self.caption.write_text('1\n00:00:00,600 --> 00:00:01,400\nCAPTION TEST\n', encoding='utf-8')
        self.data = {'source': self.source.name,
                     'captions': {'file': self.caption.name, 'timebase': 'source', 'reviewed': True},
                     'clips': [{'id': 'test', 'in_seconds': 0.5, 'out_seconds': 2,
                                'title': 'Synthetic caption test', 'context_reviewed': True, 'rights_reviewed': True}]}

    def manifest(self):
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(self.data), encoding='utf-8')
        return path

    def test_unreviewed_captions_block_render(self):
        self.data['captions']['reviewed'] = False
        with self.assertRaises(StudioError):
            render(self.manifest(), self.root / 'blocked')
        self.assertFalse((self.root / 'blocked').exists())

    def test_caption_pixels_timing_and_preserved_sources(self):
        hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.source, self.caption)]
        result = render(self.manifest(), self.root / 'out')
        self.assertTrue(result['captions']['burned_in'])
        self.assertEqual(parse_srt((self.root / 'out/test.srt').read_text()), [Cue(100, 900, 'CAPTION TEST')])
        self.assertFalse((self.root / 'out/test.ass').exists())
        def bright_pixels(time):
            data = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', str(time), '-i',
                                   str(self.root / 'out/test.mp4'), '-frames:v', '1', '-vf',
                                   'crop=820:240:90:1430', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'],
                                  check=True, capture_output=True).stdout
            return sum(r > 190 and g > 190 and b > 190 for r, g, b in zip(data[::3], data[1::3], data[2::3]))
        self.assertGreater(bright_pixels(0.4), bright_pixels(0.01) + 50)
        self.assertEqual(hashes, [hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.source, self.caption)])


if __name__ == '__main__':
    unittest.main()
