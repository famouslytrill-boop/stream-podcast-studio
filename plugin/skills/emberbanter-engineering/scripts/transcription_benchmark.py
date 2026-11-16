#!/usr/bin/env python3
"""Measure a trusted local whisper.cpp CLI against a supplied reference; no recording or uploads."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

try:
    from .studio_tools import StudioError, executable, probe, run_process
    from .captions import parse_srt
except ImportError:
    from studio_tools import StudioError, executable, probe, run_process
    from captions import parse_srt


def word_error_rate(reference: str, hypothesis: str) -> dict:
    ref, hyp = (re.findall(r"[a-z0-9]+", text.lower()) for text in (reference, hypothesis))
    if not ref:
        raise StudioError("Reference must contain English words or numbers")
    previous = list(range(len(hyp) + 1))
    for i, left in enumerate(ref, 1):
        current = [i]
        for j, right in enumerate(hyp, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return {"reference_words": len(ref), "hypothesis_words": len(hyp), "edit_distance": previous[-1],
            "word_error_rate": previous[-1] / len(ref),
            "normalization": "lowercase English alphanumeric words; punctuation ignored; no number-word conversion"}


def benchmark(args) -> dict:
    destination = Path(args.output).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise StudioError("Choose a new benchmark output folder")
    if any("://" in s or s.startswith(("\\\\", "//")) for s in
           (args.whisper_exe, args.model, args.audio, args.reference)):
        raise StudioError("Benchmark inputs must be local files")
    binary = Path(args.whisper_exe).expanduser().resolve(strict=True)
    model = Path(args.model).expanduser().resolve(strict=True)
    audio = Path(args.audio).expanduser().resolve(strict=True)
    reference = Path(args.reference).expanduser().resolve(strict=True)
    if not all(p.is_file() for p in (binary, model, audio, reference)):
        raise StudioError("Engine, model, WAV and reference must be local files")
    if audio.suffix.lower() != ".wav" or audio.stat().st_size > 64_000_000 or reference.stat().st_size > 100_000:
        raise StudioError("Use a short WAV under 64 MB and a plain reference under 100 KB")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", args.model_sha256):
        raise StudioError("Supply the model's trusted SHA256 digest")
    with model.open("rb") as model_file:
        digest = hashlib.file_digest(model_file, "sha256").hexdigest()
    if digest != args.model_sha256.lower():
        raise StudioError("Model hash does not match the supplied trusted digest")
    info = probe(audio)
    if info["duration_seconds"] > 600:
        raise StudioError("Benchmark audio must be ten minutes or shorter")
    expected = reference.read_text(encoding="utf-8-sig")
    word_error_rate(expected, "")
    source_digest = hashlib.sha256(audio.read_bytes()).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ember-transcribe-", dir=destination.parent) as tmp:
        stage = Path(tmp)
        wav, prefix = stage / "speech.wav", stage / "transcript"
        run_process([executable("ffmpeg"), "-nostdin", "-v", "error", "-n", "-i", str(audio),
                     "-map", "0:a:0", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], 60)
        started = time.perf_counter()
        process = run_process([str(binary), "-m", str(model), "-f", str(wav), "-ng", "-t", "4",
                               "-l", "en", "-osrt", "-otxt", "-of", str(prefix)], 600, cwd=binary.parent)
        elapsed = time.perf_counter() - started
        transcript = (stage / "transcript.txt").read_text(encoding="utf-8-sig")
        cues = parse_srt((stage / "transcript.srt").read_text(encoding="utf-8-sig"))
        result = {
            "speech_kind": "synthetic test fixture" if args.synthetic else "supplied local WAV",
            "audio_seconds": info["duration_seconds"], "transcription_seconds": round(elapsed, 3),
            "real_time_factor": round(elapsed / info["duration_seconds"], 4),
            "engine": binary.name, "mode": "CPU, four threads; GPU not benchmarked",
            "model_name": model.name, "model_sha256": digest, "model_digest_matched": True,
            "source_sha256": source_digest, "caption_cues": len(cues),
            "accuracy": word_error_rate(expected, transcript),
            "caption_review": "required; model text is a draft", "hardware_acceptance": "not_assessed",
            "recorded": False, "published": False,
        }
        if source_digest != hashlib.sha256(audio.read_bytes()).hexdigest():
            raise StudioError("Source changed during benchmark")
        (stage / "benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (stage / "engine.log").write_text(process.stdout + "\n" + process.stderr, encoding="utf-8")
        destination.mkdir(exist_ok=False)
        for name in ("benchmark.json", "transcript.txt", "transcript.srt", "engine.log"):
            with (stage / name).open("rb") as src, (destination / name).open("xb") as dst:
                shutil.copyfileobj(src, dst)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("whisper-exe", "model", "model-sha256", "audio", "reference", "output"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--synthetic", action="store_true", help="Label a deliberately synthesized speech fixture")
    try:
        print(json.dumps(benchmark(parser.parse_args(argv)), indent=2))
        return 0
    except (StudioError, OSError, UnicodeError, subprocess.TimeoutExpired) as error:
        print(f"Transcription benchmark stopped: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
