from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageSequence, ExifTags, UnidentifiedImageError

VERSION = "1.0.0"
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return f"<{len(value)} bytes>"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (tuple, list)):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    return str(value)


def inspect_image(path: Path) -> dict[str, Any]:
    with Image.open(path) as im:
        exif = im.getexif()
        named_exif = {}
        for tag_id, value in exif.items():
            name = ExifTags.TAGS.get(tag_id, str(tag_id))
            if tag_id == 34853:  # GPS IFD
                try:
                    gps = exif.get_ifd(34853)
                    named_exif["GPSInfo"] = {
                        ExifTags.GPSTAGS.get(k, str(k)): json_safe(v)
                        for k, v in gps.items()
                    }
                    continue
                except Exception:
                    pass
            named_exif[name] = json_safe(value)

        info = {}
        for key, value in im.info.items():
            if key.lower() in {"exif", "icc_profile"} and isinstance(value, bytes):
                info[key] = f"<{len(value)} bytes>"
            else:
                info[key] = json_safe(value)

        return {
            "file": str(path),
            "format": im.format,
            "mode": im.mode,
            "width": im.width,
            "height": im.height,
            "frames": getattr(im, "n_frames", 1),
            "exif": named_exif,
            "other_info": info,
            "file_size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }


def clean_image(source: Path, destination: Path, keep_icc: bool = True) -> None:
    """Re-encode image without EXIF/text/XMP metadata.

    ICC profiles are color profiles rather than identifying metadata, so they
    are retained by default to avoid changing color appearance.
    """
    with Image.open(source) as im:
        fmt = (im.format or source.suffix.lstrip(".")).upper()
        if fmt == "JPG":
            fmt = "JPEG"

        save_args: dict[str, Any] = {}
        if keep_icc and im.info.get("icc_profile"):
            save_args["icc_profile"] = im.info["icc_profile"]

        # Keep animation where Pillow supports it.
        if getattr(im, "is_animated", False):
            frames = []
            durations = []
            for frame in ImageSequence.Iterator(im):
                frames.append(frame.copy())
                durations.append(frame.info.get("duration", 100))
            save_args["save_all"] = True
            save_args["append_images"] = frames[1:]
            save_args["duration"] = durations
            save_args["loop"] = im.info.get("loop", 0)

        # JPEG quality 95 is a practical balance; re-encoding is lossy.
        if fmt == "JPEG":
            save_args.update({"quality": 95, "optimize": True})
            if im.mode not in ("RGB", "L"):
                im = im.convert("RGB")
        elif fmt == "PNG":
            save_args.update({"optimize": True})
        elif fmt == "WEBP":
            save_args.update({"quality": 95, "method": 6})
        elif fmt in ("TIFF", "BMP"):
            pass
        else:
            raise ValueError(f"Unsupported image format: {fmt}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        im.save(destination, format=fmt, **save_args)


def output_path(source: Path, out: Path | None) -> Path:
    if out is None:
        return source.with_name(f"{source.stem}_clean{source.suffix}")
    if out.exists() and out.is_dir():
        return out / f"{source.stem}_clean{source.suffix}"
    if out.suffix:
        return out
    return out / f"{source.stem}_clean{source.suffix}"


def iter_inputs(path: Path, recursive: bool):
    if path.is_file():
        yield path
    elif path.is_dir():
        iterator = path.rglob("*") if recursive else path.iterdir()
        yield from sorted(p for p in iterator if p.is_file() and p.suffix.lower() in SUPPORTED)
    else:
        raise FileNotFoundError(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="imgmeta",
        description="Inspect image metadata or create a metadata-stripped copy.",
        epilog="Examples: imgmeta view photo.jpg | imgmeta clean photo.jpg",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    view = sub.add_parser("view", help="Display metadata as readable JSON.")
    view.add_argument("input", type=Path)
    view.add_argument("--pretty", action="store_true", help="Pretty-print JSON (default).")
    view.add_argument("--output", "-o", type=Path, help="Write report to a JSON file.")

    clean = sub.add_parser("clean", help="Strip metadata and save a new image.")
    clean.add_argument("input", type=Path)
    clean.add_argument("--output", "-o", type=Path, help="Output file or directory.")
    clean.add_argument("--recursive", "-r", action="store_true", help="Process a directory recursively.")
    clean.add_argument("--no-icc", action="store_true", help="Also remove embedded ICC color profiles.")
    clean.add_argument("--overwrite", action="store_true", help="Allow replacing an existing output file.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "view":
            report = inspect_image(args.input)
            rendered = json.dumps(report, indent=2, ensure_ascii=False)
            if args.output:
                args.output.write_text(rendered + "\n", encoding="utf-8")
                print(f"Metadata report written to: {args.output}")
            else:
                print(rendered)
            return 0

        inputs = list(iter_inputs(args.input, args.recursive))
        if not inputs:
            print("No supported image files found.", file=sys.stderr)
            return 1

        failures = 0
        for source in inputs:
            try:
                dest = output_path(source, args.output)
                if dest.resolve() == source.resolve():
                    raise ValueError("Input and output paths must be different.")
                if dest.exists() and not args.overwrite:
                    raise FileExistsError(f"{dest} already exists (use --overwrite to replace it).")
                clean_image(source, dest, keep_icc=not args.no_icc)
                print(f"Cleaned: {source} -> {dest}")
            except Exception as exc:
                failures += 1
                print(f"ERROR: {source}: {exc}", file=sys.stderr)
        return 1 if failures else 0

    except (FileNotFoundError, UnidentifiedImageError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
