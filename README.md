# imgmeta-cli

A cross-platform command-line tool to **view image metadata** and create a **metadata-stripped copy** of an image.

Works on Windows Command Prompt, PowerShell, macOS Terminal, and Linux shells through Python's command-line interface.

## Features

- View image format, dimensions, color mode, frame count, file size, SHA-256, EXIF tags, GPS fields (when available), and other metadata exposed by Pillow.
- Strip EXIF and common embedded metadata by re-encoding an image.
- Process a single image or a directory; optional recursive processing.
- Keeps the original file unchanged. By default, cleaned copies use the `_clean` suffix.
- Preserves an embedded ICC color profile by default to help retain color appearance. Use `--no-icc` to remove it too.

## Supported formats

JPEG, PNG, WebP, TIFF, and BMP. Support for individual features depends on the installed Pillow codecs and the source file.

## Requirements

- Python 3.9 or newer
- Pillow (installed automatically with the package)

## Install

### Option A — install from a cloned/downloaded repository

```bash
https://github.com/Afternoon11/Image-MetaData-Remover.git
cd imgmeta-cli
python -m venv .venv
```

Activate the environment:

**Windows CMD**
```bat
.venv\Scripts\activate.bat
```

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS**
```bash
source .venv/bin/activate
```

Install the project:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

You can now run `imgmeta` from that activated environment.

### Option B — run without installing the command

From the repository folder:

```bash
python -m imgmeta view photo.jpg
python -m imgmeta clean photo.jpg
```

## Usage

### 1. View metadata

```bash
imgmeta view photo.jpg
```

Save the report as JSON:

```bash
imgmeta view photo.jpg --output report.json
```

### 2. Remove metadata

Create `photo_clean.jpg` beside the original:

```bash
imgmeta clean photo.jpg
```

Choose an output filename:

```bash
imgmeta clean photo.jpg --output cleaned.jpg
```

Choose an output directory:

```bash
imgmeta clean photo.jpg --output cleaned_images/
```

Remove ICC color profile as well:

```bash
imgmeta clean photo.jpg --no-icc
```

### 3. Batch clean a directory

Non-recursive:

```bash
imgmeta clean ./photos --output ./cleaned
```

Recursive:

```bash
imgmeta clean ./photos --recursive --output ./cleaned
```

On Windows, paths can be quoted:

```bat
imgmeta clean "C:\Users\You\Pictures" --recursive --output "C:\Users\You\Pictures\cleaned"
```

If an output file already exists, the tool refuses to overwrite it. Add `--overwrite` only when replacement is intentional.

### 4. Help and version

```bash
imgmeta --help
imgmeta view --help
imgmeta clean --help
imgmeta --version
```

## Important behavior and limitations

- **The source is not modified.** The tool writes a new output file unless you explicitly use `--overwrite`.
- Metadata removal is performed by decoding and re-encoding the image. It is not a byte-for-byte metadata deletion.
- **JPEG is lossy:** cleaning re-encodes JPEG at quality 95, so pixel data may change slightly. Keep a backup if exact image preservation matters.
- Animated WebP handling depends on Pillow's installed codec support. Verify the output before deleting originals.
- ICC profiles are retained by default because they affect color rendering, not personal identity. `--no-icc` removes them.
- The viewer reports metadata Pillow exposes. Some vendor-specific, proprietary, sidecar, filesystem, or container-level data may not be displayed.
- This tool does not guarantee that every possible metadata block is removed from every file variant. For forensic-grade sanitization, validate outputs with an independent tool such as ExifTool.
- Never rely on metadata removal as the only privacy protection before publishing sensitive images.

## Development

```bash
python -m pip install -e .
python -m imgmeta --help
```

## License

MIT. See [LICENSE](LICENSE).
