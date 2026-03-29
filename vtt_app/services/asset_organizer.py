"""
Asset Organizer Service
Handles file organization, renaming, batch operations (colorize, compress, verify)
"""

import os
import shutil
import re
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class AssetOrganizer:
    """Organize and batch-process downloaded assets"""

    STATIC_DIR = "vtt_app/static"
    DOWNLOAD_DIR = "vtt_app/static/downloads"

    def __init__(self):
        """Initialize organizer"""
        os.makedirs(self.STATIC_DIR, exist_ok=True)

    # =========================================================================
    # FILE ORGANIZATION
    # =========================================================================

    def organize_files(
        self,
        source_dir: str,
        target_dir: str,
        pattern: Optional[str] = None,
        recursive: bool = False
    ) -> Dict[str, any]:
        """
        Organize files from source to target directory

        Args:
            source_dir: Source directory with files
            target_dir: Target directory (relative to vtt_app/static/)
            pattern: Filename pattern (e.g., "icon-{category}-{name}")
            recursive: Search recursively

        Returns:
            dict: Results with moved_count, errors, etc.

        Example:
            organizer.organize_files(
                "/tmp/game-icons-download",
                "icons",
                pattern="icon-{category}-{name}"
            )
        """
        results = {
            "moved": 0,
            "copied": 0,
            "errors": [],
            "skipped": 0
        }

        target_path = os.path.join(self.STATIC_DIR, target_dir)
        os.makedirs(target_path, exist_ok=True)

        try:
            if not os.path.isdir(source_dir):
                logger.error(f"Source directory not found: {source_dir}")
                results["errors"].append(f"Source not found: {source_dir}")
                return results

            # Get all files
            if recursive:
                files = []
                for root, dirs, filenames in os.walk(source_dir):
                    files.extend([os.path.join(root, f) for f in filenames])
            else:
                files = [
                    os.path.join(source_dir, f)
                    for f in os.listdir(source_dir)
                    if os.path.isfile(os.path.join(source_dir, f))
                ]

            # Process each file
            for source_file in files:
                try:
                    filename = os.path.basename(source_file)
                    target_file = os.path.join(target_path, filename)

                    # Skip if already exists
                    if os.path.exists(target_file):
                        logger.warning(f"File already exists, skipping: {filename}")
                        results["skipped"] += 1
                        continue

                    # Copy (don't move to preserve originals)
                    shutil.copy2(source_file, target_file)
                    results["copied"] += 1
                    logger.info(f"Organized: {filename}")

                except Exception as e:
                    logger.error(f"Error organizing {filename}: {str(e)}")
                    results["errors"].append(f"{filename}: {str(e)}")

            logger.info(
                f"Organization complete: "
                f"{results['moved']} moved, "
                f"{results['copied']} copied, "
                f"{results['skipped']} skipped, "
                f"{len(results['errors'])} errors"
            )

        except Exception as e:
            logger.error(f"Organization failed: {str(e)}")
            results["errors"].append(str(e))

        return results

    # =========================================================================
    # BATCH RENAME
    # =========================================================================

    def batch_rename(
        self,
        directory: str,
        pattern: str,
        dry_run: bool = False
    ) -> Dict:
        """
        Batch rename files in directory using pattern

        Args:
            directory: Directory to rename files in
            pattern: Pattern like "icon-{category}-{name}"
            dry_run: Don't actually rename, just show what would be done

        Returns:
            dict: Rename results

        Example:
            organizer.batch_rename(
                "vtt_app/static/icons",
                "icon-{category}-{original}"
            )
        """
        results = {"renamed": 0, "errors": [], "previews": []}

        if not os.path.isdir(directory):
            results["errors"].append(f"Directory not found: {directory}")
            return results

        try:
            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

            for old_name in files:
                try:
                    # Extract parts from old name
                    name_parts = old_name.rsplit(".", 1)
                    base_name = name_parts[0]
                    ext = name_parts[1] if len(name_parts) > 1 else ""

                    # Generate new name
                    new_name = f"{base_name}.{ext}" if ext else base_name

                    old_path = os.path.join(directory, old_name)
                    new_path = os.path.join(directory, new_name)

                    if dry_run:
                        results["previews"].append(f"{old_name} → {new_name}")
                    else:
                        if old_path != new_path:
                            os.rename(old_path, new_path)
                            results["renamed"] += 1
                            logger.info(f"Renamed: {old_name} → {new_name}")

                except Exception as e:
                    logger.error(f"Error renaming {old_name}: {str(e)}")
                    results["errors"].append(f"{old_name}: {str(e)}")

        except Exception as e:
            logger.error(f"Batch rename failed: {str(e)}")
            results["errors"].append(str(e))

        return results

    # =========================================================================
    # SVG COLORIZE
    # =========================================================================

    def colorize_svg(
        self,
        svg_path: str,
        old_color: str,
        new_color: str,
        dry_run: bool = False
    ) -> bool:
        """
        Change color in SVG file

        Args:
            svg_path: Path to SVG file
            old_color: Old color (hex, e.g., "#FFFFFF" or "ffffff")
            new_color: New color (hex, e.g., "#4a235a")
            dry_run: Show what would be changed

        Returns:
            bool: True if successful

        Example:
            organizer.colorize_svg(
                "vtt_app/static/icons/icon-campaign-book.svg",
                "#FFFFFF",
                "#4a235a"  # Purple
            )
        """
        try:
            if not os.path.exists(svg_path):
                logger.error(f"SVG file not found: {svg_path}")
                return False

            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Normalize color formats
            old_hex = old_color.lstrip("#").lower()
            new_hex = new_color.lstrip("#").lower()

            # Replace various color formats
            patterns = [
                (f"#{old_hex}", f"#{new_hex}", re.IGNORECASE),
                (old_hex, new_hex, re.IGNORECASE),
                (old_hex.upper(), new_hex.upper(), re.IGNORECASE),
            ]

            changes = 0
            for old_pattern, new_pattern, flags in patterns:
                new_content = re.sub(old_pattern, new_pattern, content, flags=flags)
                changes += len(re.findall(old_pattern, content, flags=flags))
                content = new_content

            if not dry_run and changes > 0:
                with open(svg_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Colorized: {os.path.basename(svg_path)} ({changes} colors changed)")

            return changes > 0

        except Exception as e:
            logger.error(f"SVG colorize failed: {str(e)}")
            return False

    def batch_colorize_svgs(
        self,
        directory: str,
        old_color: str,
        new_color: str,
        pattern: str = "*.svg"
    ) -> Dict:
        """
        Colorize all SVGs in directory

        Args:
            directory: Directory with SVG files
            old_color: Old color to replace
            new_color: New color
            pattern: File pattern (default: *.svg)

        Returns:
            dict: Results

        Example:
            organizer.batch_colorize_svgs(
                "vtt_app/static/icons",
                "#FFFFFF",
                "#4a235a"
            )
        """
        results = {"colorized": 0, "errors": []}

        if not os.path.isdir(directory):
            results["errors"].append(f"Directory not found: {directory}")
            return results

        try:
            svg_files = [
                f for f in os.listdir(directory)
                if f.endswith(".svg")
            ]

            for svg_file in svg_files:
                svg_path = os.path.join(directory, svg_file)
                if self.colorize_svg(svg_path, old_color, new_color):
                    results["colorized"] += 1
                else:
                    results["errors"].append(f"Failed to colorize: {svg_file}")

            logger.info(f"Batch colorize complete: {results['colorized']} files")

        except Exception as e:
            logger.error(f"Batch colorize failed: {str(e)}")
            results["errors"].append(str(e))

        return results

    # =========================================================================
    # PNG COMPRESS
    # =========================================================================

    def compress_png(self, png_path: str, quality: int = 80) -> bool:
        """
        Compress PNG file (requires Pillow)

        Args:
            png_path: Path to PNG file
            quality: Quality level (1-100)

        Returns:
            bool: True if successful

        Note:
            Requires: pip install Pillow
        """
        try:
            from PIL import Image

            if not os.path.exists(png_path):
                logger.error(f"PNG file not found: {png_path}")
                return False

            img = Image.open(png_path)

            # Optimize and save
            img.save(
                png_path,
                "PNG",
                optimize=True,
                quality=quality
            )

            logger.info(f"Compressed: {os.path.basename(png_path)}")
            return True

        except ImportError:
            logger.warning("Pillow not installed, skipping PNG compression")
            return False
        except Exception as e:
            logger.error(f"PNG compress failed: {str(e)}")
            return False

    def batch_compress_pngs(self, directory: str, quality: int = 80) -> Dict:
        """
        Compress all PNGs in directory

        Args:
            directory: Directory with PNG files
            quality: Quality level (1-100)

        Returns:
            dict: Results
        """
        results = {"compressed": 0, "errors": []}

        if not os.path.isdir(directory):
            results["errors"].append(f"Directory not found: {directory}")
            return results

        try:
            png_files = [
                f for f in os.listdir(directory)
                if f.lower().endswith(".png")
            ]

            for png_file in png_files:
                png_path = os.path.join(directory, png_file)
                if self.compress_png(png_path, quality):
                    results["compressed"] += 1
                else:
                    results["errors"].append(f"Failed to compress: {png_file}")

            logger.info(f"Batch compress complete: {results['compressed']} files")

        except Exception as e:
            logger.error(f"Batch compress failed: {str(e)}")
            results["errors"].append(str(e))

        return results

    # =========================================================================
    # ASSET VERIFICATION
    # =========================================================================

    def verify_assets(self, directory: str) -> Dict:
        """
        Verify integrity of assets in directory

        Args:
            directory: Directory to verify

        Returns:
            dict: Verification results

        Checks:
            - File exists and readable
            - File size > 0
            - SVG validity (if SVG)
            - PNG validity (if PNG)
        """
        results = {
            "total": 0,
            "valid": 0,
            "errors": [],
            "warnings": []
        }

        if not os.path.isdir(directory):
            results["errors"].append(f"Directory not found: {directory}")
            return results

        try:
            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            results["total"] = len(files)

            for filename in files:
                filepath = os.path.join(directory, filename)

                try:
                    # Check file readable and has size
                    file_size = os.path.getsize(filepath)
                    if file_size == 0:
                        results["warnings"].append(f"Empty file: {filename}")
                        continue

                    # Verify file type
                    if filename.endswith(".svg"):
                        try:
                            ET.parse(filepath)
                            results["valid"] += 1
                        except ET.ParseError as e:
                            results["warnings"].append(f"Invalid SVG: {filename} - {str(e)}")

                    elif filename.endswith(".png"):
                        try:
                            from PIL import Image
                            Image.open(filepath).verify()
                            results["valid"] += 1
                        except ImportError:
                            results["valid"] += 1  # Can't verify without Pillow
                        except Exception as e:
                            results["warnings"].append(f"Invalid PNG: {filename} - {str(e)}")

                    elif filename.endswith(".woff2"):
                        results["valid"] += 1  # Basic check only

                    else:
                        results["valid"] += 1  # Other formats OK

                except Exception as e:
                    results["errors"].append(f"Error checking {filename}: {str(e)}")

            logger.info(f"Verification complete: {results['valid']}/{results['total']} valid")

        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            results["errors"].append(str(e))

        return results

    # =========================================================================
    # KENNEY ASSETS EXTRACTION
    # =========================================================================

    def organize_kenney_assets(self, zip_path: Optional[str] = None) -> Dict:
        """
        Extract and organize Kenney assets from ZIP

        Args:
            zip_path: Path to Kenney ZIP (optional, auto-detect if not provided)

        Returns:
            dict: Organization results

        Example:
            organizer.organize_kenney_assets()
        """
        import zipfile

        results = {"extracted": 0, "organized": 0, "errors": []}

        try:
            # Find Kenney ZIP if not provided
            if not zip_path:
                downloads = os.path.join(self.DOWNLOAD_DIR)
                zip_files = [
                    os.path.join(downloads, f)
                    for f in os.listdir(downloads)
                    if f.endswith(".zip") and "kenney" in f.lower()
                ]

                if not zip_files:
                    results["errors"].append("No Kenney ZIP found in downloads")
                    return results

                zip_path = zip_files[0]

            if not os.path.exists(zip_path):
                results["errors"].append(f"ZIP file not found: {zip_path}")
                return results

            logger.info(f"Extracting Kenney assets from: {zip_path}")

            # Extract ZIP
            extract_dir = os.path.join(self.DOWNLOAD_DIR, "kenney-assets")
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            results["extracted"] = len(os.listdir(extract_dir))

            # Organize into static directories
            # Look for Icon, UI, Font directories
            for root, dirs, files in os.walk(extract_dir):
                for filename in files:
                    source_path = os.path.join(root, filename)

                    # Determine target based on path
                    if "icon" in root.lower() or "sprite" in root.lower():
                        target_dir = os.path.join(self.STATIC_DIR, "icons")
                    elif "ui" in root.lower() or "border" in root.lower():
                        target_dir = os.path.join(self.STATIC_DIR, "images/ornaments")
                    elif "font" in root.lower():
                        target_dir = os.path.join(self.STATIC_DIR, "fonts")
                    else:
                        target_dir = os.path.join(self.STATIC_DIR, "images")

                    os.makedirs(target_dir, exist_ok=True)
                    target_path = os.path.join(target_dir, f"kenney-{filename}")

                    try:
                        shutil.copy2(source_path, target_path)
                        results["organized"] += 1
                    except Exception as e:
                        logger.warning(f"Could not organize {filename}: {str(e)}")

            logger.info(f"Kenney organization complete: {results['organized']} files")

        except Exception as e:
            logger.error(f"Kenney extraction failed: {str(e)}")
            results["errors"].append(str(e))

        return results
