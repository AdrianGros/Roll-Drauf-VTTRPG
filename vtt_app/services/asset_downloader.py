"""
Asset Downloader Service
Handles downloading assets from various sources (Game-Icons, Pixabay, AmbientCG, Kenney)
"""

import os
import requests
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote
from pathlib import Path

logger = logging.getLogger(__name__)


class AssetDownloader:
    """Download assets from various sources"""

    DOWNLOAD_DIR = "vtt_app/static/downloads"
    ICONS_DIR = "vtt_app/static/icons"
    TEXTURES_DIR = "vtt_app/static/images/textures"
    FONTS_DIR = "vtt_app/static/fonts"

    # Timeout for HTTP requests
    TIMEOUT = 30

    def __init__(self):
        """Initialize downloader"""
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)

    def download_file(self, url: str, output_path: str, timeout: int = TIMEOUT) -> bool:
        """
        Download a single file from URL

        Args:
            url: HTTP(S) URL to download
            output_path: Local path to save file
            timeout: Request timeout in seconds

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading: {url} → {output_path}")

            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()

            # Create parent directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Write file in chunks
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size = os.path.getsize(output_path)
            logger.info(f"✓ Downloaded: {os.path.basename(output_path)} ({file_size} bytes)")
            return True

        except requests.RequestException as e:
            logger.error(f"✗ Download failed: {url} - {str(e)}")
            return False
        except IOError as e:
            logger.error(f"✗ File write failed: {output_path} - {str(e)}")
            return False

    # =========================================================================
    # GAME-ICONS.NET
    # =========================================================================

    def download_game_icons(self, icon_names: List[str], category: str = "misc") -> Dict[str, bool]:
        """
        Download icons from game-icons.net

        Args:
            icon_names: List of icon names to download
            category: Category for naming (campaign, session, combat, spell, inventory, etc.)

        Returns:
            dict: {icon_name: success_bool}

        Example:
            downloader.download_game_icons(
                ["book", "scroll", "library"],
                category="campaign"
            )
        """
        results = {}
        base_url = "https://game-icons.net/icons/ffffff/000000/1x1"

        for icon_name in icon_names:
            # Try to find icon in different author collections
            authors = ["lorc", "delapouite", "john-colborne"]
            downloaded = False

            for author in authors:
                url = f"{base_url}/{author}/{icon_name.lower()}.svg"
                output_path = os.path.join(
                    self.ICONS_DIR,
                    f"icon-{category}-{icon_name.lower()}.svg"
                )

                if self.download_file(url, output_path):
                    results[icon_name] = True
                    downloaded = True
                    break

            if not downloaded:
                logger.warning(f"Could not download icon: {icon_name}")
                results[icon_name] = False

        return results

    # =========================================================================
    # PIXABAY
    # =========================================================================

    def download_pixabay_backgrounds(
        self,
        query: str,
        quantity: int = 5,
        min_width: int = 2560,
        colors: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Download background images from Pixabay

        Args:
            query: Search query (e.g., "galaxy background")
            quantity: Number of images to download
            min_width: Minimum image width
            colors: List of colors to filter by (optional)

        Returns:
            dict: {filename: success_bool}

        Example:
            downloader.download_pixabay_backgrounds(
                "galaxy background 4k",
                quantity=5,
                colors=["purple", "blue"]
            )
        """
        results = {}

        # Pixabay API endpoint (no key needed for basic searches)
        search_url = "https://pixabay.com/"

        # Note: Pixabay doesn't have a free public API for bulk downloads
        # This would need manual implementation or Pixabay API key
        logger.warning("Pixabay downloads require manual implementation or API key")
        logger.info(f"Query: {query}, Quantity: {quantity}")

        return results

    # =========================================================================
    # AMBIENTCG
    # =========================================================================

    def download_ambientcg_texture(
        self,
        texture_id: str,
        resolution: str = "1K"
    ) -> bool:
        """
        Download PBR texture from AmbientCG

        Args:
            texture_id: Texture ID (e.g., "fabric_003")
            resolution: Resolution (1K, 2K, 4K, 8K)

        Returns:
            bool: True if successful

        Example:
            downloader.download_ambientcg_texture("fabric_003", "4K")
        """
        try:
            # AmbientCG CDN structure
            url = f"https://cdn.ambientcg.com/{texture_id}_{resolution}/files/{texture_id}_{resolution}-png.zip"
            output_path = os.path.join(
                self.DOWNLOAD_DIR,
                f"{texture_id}_{resolution}.zip"
            )

            return self.download_file(url, output_path)

        except Exception as e:
            logger.error(f"AmbientCG download failed: {str(e)}")
            return False

    # =========================================================================
    # GOOGLE FONTS (WOFF2)
    # =========================================================================

    def download_google_font(
        self,
        font_name: str,
        weight: int = 400
    ) -> bool:
        """
        Download font from Google Fonts CDN

        Args:
            font_name: Font name (e.g., "Cinzel")
            weight: Font weight (400, 700, etc.)

        Returns:
            bool: True if successful

        Example:
            downloader.download_google_font("Cinzel", 400)
        """
        # Google Fonts WOFF2 URLs (from CSS API)
        font_urls = {
            "Cinzel": {
                400: "https://fonts.gstatic.com/s/cinzel/v25/jizfREFkOho6OFmT0ZtsKIHGR_2c-9drv0P0.woff2",
                700: "https://fonts.gstatic.com/s/cinzel/v25/jizvREFkOho6OFmT0ZtsKIHGR_2c-9drv7SnCwAE.woff2"
            },
            "BadScript": {
                400: "https://fonts.gstatic.com/s/badscript/v13/HLF0oB5vJNPB-8SkRmNr7WlA.woff2"
            },
            "PirataOne": {
                400: "https://fonts.gstatic.com/s/pirataone/v8/f0L10_83bPrXkJK8LFMp4gZfBg.woff2"
            }
        }

        try:
            if font_name not in font_urls or weight not in font_urls[font_name]:
                logger.warning(f"Font not found: {font_name} (weight: {weight})")
                return False

            url = font_urls[font_name][weight]
            output_filename = f"{font_name.lower()}-{weight}.woff2"
            output_path = os.path.join(self.FONTS_DIR, output_filename)

            return self.download_file(url, output_path)

        except Exception as e:
            logger.error(f"Font download failed: {str(e)}")
            return False

    # =========================================================================
    # KENNEY ASSETS (Manual download from kenney.nl)
    # =========================================================================

    def prepare_kenney_extraction_guide(self) -> Dict:
        """
        Since Kenney assets require manual download from itch.io,
        provide extraction guide

        Returns:
            dict: Instructions for Kenney asset extraction
        """
        return {
            "source": "https://kenney.nl/assets",
            "download": "Fantasy Game Assets 8.0 ZIP",
            "size_mb": "50-100",
            "extract_to": f"{self.DOWNLOAD_DIR}/kenney-assets/",
            "instructions": [
                "1. Visit https://kenney.nl/assets",
                "2. Download 'Fantasy Game Assets 8.0'",
                "3. Extract ZIP to the path above",
                "4. Run: AssetOrganizer.organize_kenney_assets()",
            ]
        }


# =========================================================================
# Convenience functions for direct use
# =========================================================================

def download_game_icons_batch(icons: List[Dict[str, str]]) -> Dict:
    """
    Convenience function to download multiple Game-Icons categories

    Args:
        icons: List of {"name": "book", "category": "campaign"}

    Returns:
        dict: Results per icon

    Example:
        download_game_icons_batch([
            {"name": "book", "category": "campaign"},
            {"name": "scroll", "category": "campaign"},
            {"name": "play", "category": "session"},
        ])
    """
    downloader = AssetDownloader()
    results = {}

    # Group by category
    by_category = {}
    for icon in icons:
        category = icon.get("category", "misc")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(icon["name"])

    # Download each category
    for category, names in by_category.items():
        results[category] = downloader.download_game_icons(names, category=category)

    return results
