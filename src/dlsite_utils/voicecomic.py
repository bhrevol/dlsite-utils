import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Literal


def voicecomic_to_mp4(
    path: Path,
    orientation: Literal["auto", "horizontal", "vertical"] = "auto",
    force: bool = False,
) -> Path:
    try:
        import ffmpeg
    except ImportError:
        raise ImportError("voicecomic to mp4 requires ffmpeg")
    try:
        from PIL import Image
    except ImportError:
        raise ImportError("voicecomic to mp4 requires PIL")
    if not path.is_dir():
        raise ValueError("Path must be a voicecomic_v2 directory")
    output_path = path.parent / f"{path.name}.mp4"
    if not force and output_path.exists():
        raise FileExistsError(f"{output_path} already exists")
    pages = sorted(p.stem for p in path.glob("*.mp4"))
    if not pages or not all((path / f"{page}.webp").exists() for page in pages):
        raise ValueError(f"{path} does not appear to be voicecomic_v2 directory")
    with tempfile.TemporaryDirectory(prefix=path.name, dir=path.parent) as tmpdir:
        parts_dir = Path(tmpdir)
        parts: list[tuple[Path, int]] = []
        if orientation == "auto":
            with Image.open(path / f"{pages[0]}.webp") as im:
                w, h = im.size
                orientation = "horizontal" if w > h else "vertical"
        for page in pages:
            if orientation == "vertical":
                input_image = (
                    ffmpeg.input(f"{path / page}.webp", loop=1, framerate=30)
                    .filter(
                        "scale", "1080", "1920", force_original_aspect_ratio="decrease"
                    )
                    .filter(
                        "pad", "1080", "1920", "(ow-iw)/2", "(oh-ih)/2", color="black"
                    )
                )
            elif orientation == "horizontal":
                input_image = (
                    ffmpeg.input(f"{path / page}.webp", loop=1, framerate=30)
                    .filter(
                        "scale", "1920", "1080", force_original_aspect_ratio="decrease"
                    )
                    .filter(
                        "pad", "1920", "1080", "(ow-iw)/2", "(oh-ih)/2", color="black"
                    )
                )
            else:
                raise ValueError("Invalid orientation")
            audio_path = path / f"{page}.mp4"
            probe = ffmpeg.probe(str(audio_path))
            duration = 0.0
            for stream in probe.get("streams", []):
                if stream.get("codec_type") != "audio":
                    continue
                duration = max(duration, float(stream.get("duration", "0")))
            if duration <= 0:
                raise ValueError("Failed to determine audio duration for {track}")
            input_audio = ffmpeg.input(str(audio_path))
            part_path = parts_dir / f"{page}.mp4"
            output = ffmpeg.output(
                input_image,
                input_audio["a:0"],
                str(part_path),
                vcodec="libx264",
                crf=16,
                tune="stillimage",
                pix_fmt="yuv420p",
                acodec="copy",
                shortest=None,
            )
            ffmpeg.run(output.global_args("-loglevel", "fatal"))
            parts.append((part_path, math.ceil(duration * 1000)))
        ffmetadata = parts_dir / "chapters.ffmetadata"
        lines = [";FFMETADATA1"]
        offset = 0
        for i, (_, duration) in enumerate(parts, start=1):
            lines.extend(
                [
                    "[CHAPTER]",
                    "TIMEBASE=1/1000",
                    f"START={offset}",
                    f"END={offset + duration - 1}",
                    f"title=Page {i}",
                ]
            )
            offset += duration
        with open(ffmetadata, "w") as f:
            f.write(os.linesep.join(lines))
        concat_file = parts_dir / "concat.txt"
        with open(concat_file, "w") as f:
            f.write(os.linesep.join(f"file '{part}'" for part, _ in parts))
        merged = parts_dir / output_path.name
        concat = ffmpeg.input(str(concat_file), format="concat", safe=0)
        meta = ffmpeg.input(str(ffmetadata))
        out = ffmpeg.output(
            concat, meta, str(merged), c="copy", movflags="+faststart", map_metadata=1
        ).global_args("-loglevel", "fatal")
        # workaround since ffmpeg-python doesnt work with metadata files
        cmd = out.compile()
        while "-map" in cmd:
            i = cmd.index("-map")
            cmd.pop(i)
            cmd.pop(i)
        subprocess.call(cmd)
        merged.replace(output_path)
    return output_path
