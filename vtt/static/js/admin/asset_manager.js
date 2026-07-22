/**
 * Asset Manager Frontend
 * Handles UI interaction and API calls for asset management
 */

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const tabName = this.dataset.tab;
        switchTab(tabName);
    });
});

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName).classList.add('active');

    // Update button states
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });
}

// =========================================================================
// DOWNLOAD FUNCTIONS
// =========================================================================

function updateDownloadForm() {
    const type = document.getElementById('download-type').value;

    document.getElementById('game-icons-form').style.display = 'none';
    document.getElementById('fonts-form').style.display = 'none';
    document.getElementById('pixabay-form').style.display = 'none';

    if (type === 'game-icons') {
        document.getElementById('game-icons-form').style.display = 'block';
    } else if (type === 'fonts') {
        document.getElementById('fonts-form').style.display = 'block';
    } else if (type === 'pixabay') {
        document.getElementById('pixabay-form').style.display = 'block';
    }
}

function downloadGameIcons() {
    const iconsJson = document.getElementById('icons-json').value;

    try {
        const icons = JSON.parse(iconsJson);

        if (!Array.isArray(icons) || icons.length === 0) {
            showMessage('download-message', 'Please provide valid icon list', 'error');
            return;
        }

        showProgress('download');
        const url = '/api/admin/assets/download/game-icons';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ icons })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showMessage('download-message', `Error: ${data.error}`, 'error');
            } else {
                const count = data.files_downloaded || 0;
                showMessage('download-message',
                    `✓ Downloaded ${count} icons successfully!`,
                    'success'
                );
                updateProgress('download', 100);
            }
        })
        .catch(error => {
            showMessage('download-message', `Error: ${error.message}`, 'error');
        })
        .finally(() => hideProgress('download', 2000));

    } catch (e) {
        showMessage('download-message', `Invalid JSON: ${e.message}`, 'error');
    }
}

function downloadFonts() {
    const fontsJson = document.getElementById('fonts-json').value;

    try {
        const fonts = JSON.parse(fontsJson);

        if (!Array.isArray(fonts) || fonts.length === 0) {
            showMessage('download-message', 'Please provide valid fonts list', 'error');
            return;
        }

        showProgress('download');
        const url = '/api/admin/assets/download/fonts';

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ fonts })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showMessage('download-message', `Error: ${data.error}`, 'error');
            } else {
                const count = data.fonts_downloaded || 0;
                showMessage('download-message',
                    `✓ Downloaded ${count} font files successfully!`,
                    'success'
                );
                updateProgress('download', 100);
            }
        })
        .catch(error => {
            showMessage('download-message', `Error: ${error.message}`, 'error');
        })
        .finally(() => hideProgress('download', 2000));

    } catch (e) {
        showMessage('download-message', `Invalid JSON: ${e.message}`, 'error');
    }
}

function downloadPixabay() {
    const query = document.getElementById('pixabay-query').value;
    const quantity = document.getElementById('pixabay-quantity').value;

    showMessage('download-message',
        'ℹ️ Pixabay downloads require manual implementation. See OPTION_B_MANUAL_DOWNLOADS.md for steps.',
        'info'
    );
}

// =========================================================================
// ORGANIZE FUNCTIONS
// =========================================================================

function updateOrganizeForm() {
    const type = document.getElementById('organize-type').value;
    document.getElementById('kenney-form').style.display = 'none';
    document.getElementById('files-form').style.display = 'none';

    if (type === 'kenney') {
        document.getElementById('kenney-form').style.display = 'block';
    } else {
        document.getElementById('files-form').style.display = 'block';
    }
}

function organizeKenney() {
    const zipPath = document.getElementById('kenney-zip-path').value || null;

    const url = '/api/admin/assets/organize/kenney';

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zip_path: zipPath })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showMessage('organize-message', `Error: ${data.error}`, 'error');
        } else {
            showMessage('organize-message',
                `✓ Organized ${data.organized} Kenney assets!`,
                'success'
            );
        }
    })
    .catch(error => {
        showMessage('organize-message', `Error: ${error.message}`, 'error');
    });
}

function organizeFiles() {
    const sourceDir = document.getElementById('source-dir').value;
    const targetDir = document.getElementById('target-dir').value;

    if (!sourceDir) {
        showMessage('organize-message', 'Please specify source directory', 'error');
        return;
    }

    const url = '/api/admin/assets/organize/files';

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_dir: sourceDir, target_dir: targetDir })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showMessage('organize-message', `Error: ${data.error}`, 'error');
        } else {
            showMessage('organize-message',
                `✓ Copied ${data.copied} files to ${targetDir}!`,
                'success'
            );
        }
    })
    .catch(error => {
        showMessage('organize-message', `Error: ${error.message}`, 'error');
    });
}

// =========================================================================
// BATCH OPERATIONS
// =========================================================================

function updateBatchForm() {
    const type = document.getElementById('batch-type').value;
    document.getElementById('colorize-form').style.display = 'none';
    document.getElementById('compress-form').style.display = 'none';

    if (type === 'colorize') {
        document.getElementById('colorize-form').style.display = 'block';
    } else {
        document.getElementById('compress-form').style.display = 'block';
    }
}

function batchColorize() {
    const directory = document.getElementById('colorize-dir').value;
    const oldColor = document.getElementById('old-color-hex').value;
    const newColor = document.getElementById('new-color-hex').value;

    const url = '/api/admin/assets/batch/colorize';

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            directory,
            old_color: oldColor,
            new_color: newColor
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showMessage('batch-message', `Error: ${data.error}`, 'error');
        } else {
            showMessage('batch-message',
                `✓ Colorized ${data.colorized} SVG files!`,
                'success'
            );
        }
    })
    .catch(error => {
        showMessage('batch-message', `Error: ${error.message}`, 'error');
    });
}

function batchCompress() {
    const directory = document.getElementById('compress-dir').value;
    const quality = document.getElementById('quality-slider').value;

    const url = '/api/admin/assets/batch/compress';

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directory, quality: parseInt(quality) })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showMessage('batch-message', `Error: ${data.error}`, 'error');
        } else {
            showMessage('batch-message',
                `✓ Compressed ${data.compressed} PNG files!`,
                'success'
            );
        }
    })
    .catch(error => {
        showMessage('batch-message', `Error: ${error.message}`, 'error');
    });
}

function updateQualityValue() {
    const value = document.getElementById('quality-slider').value;
    document.getElementById('quality-value').textContent = value;
}

// =========================================================================
// BROWSE ASSETS
// =========================================================================

function listAssets() {
    const path = document.getElementById('browse-dir').value;
    const url = `/api/admin/assets/list?path=${path}`;

    fetch(url)
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showMessage('browse-message', `Error: ${data.error}`, 'error');
            return;
        }

        const container = document.getElementById('asset-list-container');
        container.innerHTML = '';

        if (!data.files || data.files.length === 0) {
            showMessage('browse-message', 'No assets found in this directory', 'info');
            return;
        }

        data.files.forEach(file => {
            const card = document.createElement('div');
            card.className = 'asset-card';

            let preview = '';
            if (file.type === 'svg') {
                preview = `<img src="${data.directory}/${file.name}" alt="${file.name}" style="max-width:100%;">`;
            } else if (file.type === 'png') {
                preview = `<img src="${data.directory}/${file.name}" alt="${file.name}" style="max-width:100%;">`;
            } else if (file.type === 'woff2') {
                preview = '<div style="font-size:40px;">🔤</div>';
            } else {
                preview = '<div style="font-size:40px;">📄</div>';
            }

            card.innerHTML = `
                <div class="asset-icon">${preview}</div>
                <div class="asset-name">${file.name}</div>
                <div class="asset-size">${file.size}</div>
            `;

            container.appendChild(card);
        });

        showMessage('browse-message',
            `Showing ${data.files.length} assets from ${path}`,
            'info'
        );
    })
    .catch(error => {
        showMessage('browse-message', `Error: ${error.message}`, 'error');
    });
}

// =========================================================================
// VERIFY ASSETS
// =========================================================================

function verifyAssets() {
    const directory = document.getElementById('verify-dir').value;
    const url = '/api/admin/assets/verify';

    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directory })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showMessage('verify-message', `Error: ${data.error}`, 'error');
        } else {
            const valid = data.valid || 0;
            const total = data.total || 0;
            const errors = data.errors ? data.errors.length : 0;

            let message = `✓ Verified ${valid}/${total} assets`;
            const type = errors === 0 ? 'success' : 'warning';

            if (errors > 0) {
                message += ` (${errors} errors found)`;
            }

            showMessage('verify-message', message, type);
        }
    })
    .catch(error => {
        showMessage('verify-message', `Error: ${error.message}`, 'error');
    });
}

// =========================================================================
// UI HELPERS
// =========================================================================

function showProgress(prefix) {
    document.getElementById(`${prefix}-progress`).style.display = 'block';
    updateProgress(prefix, 0);
}

function hideProgress(prefix, delay = 0) {
    setTimeout(() => {
        document.getElementById(`${prefix}-progress`).style.display = 'none';
    }, delay);
}

function updateProgress(prefix, percent) {
    const fill = document.getElementById(`${prefix}-progress-fill`);
    fill.style.width = percent + '%';
    fill.textContent = percent + '%';
}

function showMessage(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `status-message ${type}`;
    element.style.display = 'block';
}

// Color picker sync
document.addEventListener('DOMContentLoaded', () => {
    const oldColor = document.getElementById('old-color');
    const oldColorHex = document.getElementById('old-color-hex');
    const newColor = document.getElementById('new-color');
    const newColorHex = document.getElementById('new-color-hex');

    if (oldColor && oldColorHex) {
        oldColor.addEventListener('change', (e) => {
            oldColorHex.value = e.target.value.toUpperCase();
        });
        oldColorHex.addEventListener('change', (e) => {
            oldColor.value = e.target.value;
        });
    }

    if (newColor && newColorHex) {
        newColor.addEventListener('change', (e) => {
            newColorHex.value = e.target.value.toUpperCase();
        });
        newColorHex.addEventListener('change', (e) => {
            newColor.value = e.target.value;
        });
    }

    // Load first asset list
    listAssets();

    // Set default organize form
    updateOrganizeForm();
    updateDownloadForm();
    updateBatchForm();
});
