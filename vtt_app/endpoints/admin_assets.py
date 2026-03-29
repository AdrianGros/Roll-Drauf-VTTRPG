"""
Admin Assets REST API
Endpoints for downloading, organizing, and managing assets
"""

import os
import json
import logging
from flask import Blueprint, request, jsonify, send_file
from functools import wraps
from datetime import datetime

from vtt_app.services.asset_downloader import AssetDownloader, download_game_icons_batch
from vtt_app.services.asset_organizer import AssetOrganizer

logger = logging.getLogger(__name__)

admin_assets_bp = Blueprint('admin_assets', __name__, url_prefix='/api/admin/assets')

# Global job tracker (in production, use Celery or database)
_jobs = {}


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated and admin
        # This is a placeholder - integrate with your auth system
        return f(*args, **kwargs)
    return decorated_function


# =========================================================================
# JOB MANAGEMENT
# =========================================================================

class Job:
    """Simple job tracker"""
    def __init__(self, job_id: str, task_name: str, total_items: int = 1):
        self.job_id = job_id
        self.task_name = task_name
        self.total_items = total_items
        self.processed = 0
        self.status = "queued"  # queued, running, completed, failed
        self.started_at = None
        self.completed_at = None
        self.errors = []
        self.results = {}

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "task_name": self.task_name,
            "status": self.status,
            "progress": f"{self.processed}/{self.total_items}",
            "percent": int((self.processed / max(self.total_items, 1)) * 100),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "errors": self.errors,
            "results": self.results
        }


def get_next_job_id():
    """Generate unique job ID"""
    import uuid
    return str(uuid.uuid4())[:8]


# =========================================================================
# ENDPOINTS: DOWNLOAD
# =========================================================================

@admin_assets_bp.route('/download/game-icons', methods=['POST'])
@admin_required
def download_game_icons_endpoint():
    """
    Download Game-Icons.net SVG icons

    Request body:
    {
        "icons": [
            {"name": "book", "category": "campaign"},
            {"name": "scroll", "category": "campaign"},
            ...
        ]
    }

    Returns:
    {
        "job_id": "abc123",
        "status": "queued",
        "files_queued": 32
    }
    """
    try:
        data = request.get_json() or {}
        icons = data.get("icons", [])

        if not icons:
            return jsonify({"error": "No icons provided"}), 400

        job_id = get_next_job_id()
        job = Job(job_id, "download_game_icons", len(icons))
        job.status = "running"
        job.started_at = datetime.now().isoformat()

        _jobs[job_id] = job

        logger.info(f"Starting download job {job_id} for {len(icons)} icons")

        # Start download (in production, use Celery)
        downloader = AssetDownloader()
        results = download_game_icons_batch(icons)

        job.results = results
        job.status = "completed"
        job.completed_at = datetime.now().isoformat()

        # Count successful downloads
        total_success = sum(
            sum(1 for v in cat.values() if v)
            for cat in results.values()
        )
        job.processed = total_success

        return jsonify({
            "job_id": job_id,
            "status": "completed",
            "files_downloaded": total_success,
            "results": results
        }), 200

    except Exception as e:
        logger.error(f"Download game-icons failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_assets_bp.route('/download/pixabay', methods=['POST'])
@admin_required
def download_pixabay_endpoint():
    """
    Download Pixabay galaxy backgrounds

    Request body:
    {
        "query": "galaxy background 4k",
        "quantity": 5,
        "colors": ["purple", "blue"]
    }

    Returns:
    {
        "job_id": "abc123",
        "status": "queued",
        "message": "Note: Pixabay requires manual implementation"
    }
    """
    try:
        data = request.get_json() or {}
        query = data.get("query", "galaxy background")
        quantity = data.get("quantity", 5)

        job_id = get_next_job_id()
        job = Job(job_id, "download_pixabay", quantity)

        _jobs[job_id] = job

        logger.warning(
            "Pixabay downloads require API key or manual implementation. "
            "See OPTION_B_MANUAL_DOWNLOADS.md for steps."
        )

        return jsonify({
            "job_id": job_id,
            "status": "pending_manual",
            "message": "Pixabay requires manual download or API key",
            "note": "See documentation for steps"
        }), 202

    except Exception as e:
        logger.error(f"Pixabay endpoint error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_assets_bp.route('/download/fonts', methods=['POST'])
@admin_required
def download_fonts_endpoint():
    """
    Download Google Fonts (WOFF2)

    Request body:
    {
        "fonts": [
            {"name": "Cinzel", "weights": [400, 700]},
            {"name": "BadScript", "weights": [400]},
            {"name": "PirataOne", "weights": [400]}
        ]
    }

    Returns:
    {
        "job_id": "abc123",
        "fonts_downloaded": 4,
        "status": "completed"
    }
    """
    try:
        data = request.get_json() or {}
        fonts = data.get("fonts", [])

        if not fonts:
            return jsonify({"error": "No fonts provided"}), 400

        job_id = get_next_job_id()
        total_downloads = sum(len(f.get("weights", [400])) for f in fonts)
        job = Job(job_id, "download_fonts", total_downloads)
        job.status = "running"
        job.started_at = datetime.now().isoformat()

        _jobs[job_id] = job

        downloader = AssetDownloader()
        successful = 0

        for font in fonts:
            font_name = font.get("name")
            weights = font.get("weights", [400])

            for weight in weights:
                if downloader.download_google_font(font_name, weight):
                    successful += 1
                job.processed += 1

        job.status = "completed"
        job.completed_at = datetime.now().isoformat()

        return jsonify({
            "job_id": job_id,
            "status": "completed",
            "fonts_downloaded": successful,
            "total_attempted": total_downloads
        }), 200

    except Exception as e:
        logger.error(f"Download fonts failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


# =========================================================================
# ENDPOINTS: ORGANIZE
# =========================================================================

@admin_assets_bp.route('/organize/kenney', methods=['POST'])
@admin_required
def organize_kenney_endpoint():
    """
    Extract and organize Kenney assets from ZIP

    Request body:
    {
        "zip_path": "/tmp/kenney-assets.zip"  # optional
    }

    Returns:
    {
        "status": "completed",
        "extracted": 150,
        "organized": 145,
        "errors": []
    }
    """
    try:
        data = request.get_json() or {}
        zip_path = data.get("zip_path")

        organizer = AssetOrganizer()
        results = organizer.organize_kenney_assets(zip_path)

        return jsonify({
            "status": "completed",
            **results
        }), 200

    except Exception as e:
        logger.error(f"Organize kenney failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_assets_bp.route('/organize/files', methods=['POST'])
@admin_required
def organize_files_endpoint():
    """
    Organize files from source to target directory

    Request body:
    {
        "source_dir": "/tmp/game-icons-download",
        "target_dir": "icons",
        "pattern": "icon-{category}-{name}"
    }

    Returns:
    {
        "status": "completed",
        "copied": 32,
        "errors": []
    }
    """
    try:
        data = request.get_json() or {}
        source_dir = data.get("source_dir")
        target_dir = data.get("target_dir", "images")

        if not source_dir:
            return jsonify({"error": "source_dir required"}), 400

        organizer = AssetOrganizer()
        results = organizer.organize_files(source_dir, target_dir, recursive=True)

        return jsonify({
            "status": "completed",
            **results
        }), 200

    except Exception as e:
        logger.error(f"Organize files failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


# =========================================================================
# ENDPOINTS: BATCH OPERATIONS
# =========================================================================

@admin_assets_bp.route('/batch/colorize', methods=['POST'])
@admin_required
def batch_colorize_endpoint():
    """
    Batch colorize SVG files

    Request body:
    {
        "directory": "vtt_app/static/icons",
        "old_color": "#FFFFFF",
        "new_color": "#4a235a"
    }

    Returns:
    {
        "status": "completed",
        "colorized": 32,
        "errors": []
    }
    """
    try:
        data = request.get_json() or {}
        directory = data.get("directory")
        old_color = data.get("old_color", "#FFFFFF")
        new_color = data.get("new_color", "#4a235a")

        if not directory:
            return jsonify({"error": "directory required"}), 400

        organizer = AssetOrganizer()
        results = organizer.batch_colorize_svgs(directory, old_color, new_color)

        return jsonify({
            "status": "completed",
            **results
        }), 200

    except Exception as e:
        logger.error(f"Batch colorize failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_assets_bp.route('/batch/compress', methods=['POST'])
@admin_required
def batch_compress_endpoint():
    """
    Batch compress PNG files

    Request body:
    {
        "directory": "vtt_app/static/images/textures",
        "quality": 85
    }

    Returns:
    {
        "status": "completed",
        "compressed": 5,
        "errors": []
    }
    """
    try:
        data = request.get_json() or {}
        directory = data.get("directory")
        quality = data.get("quality", 85)

        if not directory:
            return jsonify({"error": "directory required"}), 400

        organizer = AssetOrganizer()
        results = organizer.batch_compress_pngs(directory, quality)

        return jsonify({
            "status": "completed",
            **results
        }), 200

    except Exception as e:
        logger.error(f"Batch compress failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


# =========================================================================
# ENDPOINTS: LIST & MANAGE
# =========================================================================

@admin_assets_bp.route('/list', methods=['GET'])
@admin_required
def list_assets_endpoint():
    """
    List assets in a directory

    Query params:
    ?path=icons|textures|fonts|ornaments|frames

    Returns:
    {
        "directory": "vtt_app/static/icons",
        "total": 32,
        "files": [
            {
                "name": "icon-campaign-book.svg",
                "size": "2.4KB",
                "type": "svg"
            },
            ...
        ]
    }
    """
    try:
        path = request.args.get("path", "icons")

        # Map paths to directories
        paths = {
            "icons": "vtt_app/static/icons",
            "textures": "vtt_app/static/images/textures",
            "fonts": "vtt_app/static/fonts",
            "ornaments": "vtt_app/static/images/ornaments",
            "frames": "vtt_app/static/images/frames"
        }

        directory = paths.get(path)
        if not directory or not os.path.isdir(directory):
            return jsonify({"error": f"Invalid path: {path}"}), 400

        files = []
        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    size_kb = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"

                    files.append({
                        "name": filename,
                        "size": size_kb,
                        "type": filename.split(".")[-1].lower()
                    })
        except PermissionError:
            return jsonify({"error": "Permission denied"}), 403

        return jsonify({
            "directory": directory,
            "path": path,
            "total": len(files),
            "files": files
        }), 200

    except Exception as e:
        logger.error(f"List assets failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_assets_bp.route('/status/<job_id>', methods=['GET'])
def job_status_endpoint(job_id):
    """
    Get job status

    Returns:
    {
        "job_id": "abc123",
        "status": "completed",
        "progress": "32/32",
        "percent": 100,
        "started_at": "2026-03-29T...",
        "completed_at": "2026-03-29T...",
        "errors": []
    }
    """
    try:
        job = _jobs.get(job_id)

        if not job:
            return jsonify({"error": "Job not found"}), 404

        return jsonify(job.to_dict()), 200

    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@admin_assets_bp.route('/verify', methods=['POST'])
@admin_required
def verify_endpoint():
    """
    Verify asset integrity

    Request body:
    {
        "directory": "vtt_app/static/icons"
    }

    Returns:
    {
        "status": "completed",
        "total": 32,
        "valid": 31,
        "errors": [...],
        "warnings": [...]
    }
    """
    try:
        data = request.get_json() or {}
        directory = data.get("directory")

        if not directory:
            return jsonify({"error": "directory required"}), 400

        organizer = AssetOrganizer()
        results = organizer.verify_assets(directory)

        return jsonify({
            "status": "completed",
            **results
        }), 200

    except Exception as e:
        logger.error(f"Verify failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


# =========================================================================
# SUMMARY / HEALTH
# =========================================================================

@admin_assets_bp.route('/health', methods=['GET'])
def health_endpoint():
    """
    Health check for asset manager API

    Returns:
    {
        "status": "healthy",
        "version": "1.0.0",
        "features": [...]
    }
    """
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "features": [
            "download_game_icons",
            "download_fonts",
            "download_pixabay",
            "organize_kenney",
            "batch_colorize",
            "batch_compress",
            "verify_assets"
        ]
    }), 200
