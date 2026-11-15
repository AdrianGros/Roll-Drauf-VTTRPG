# Korrektur der Image-Herkunft

Discover nannte zunächst den geerbten Labelwert `com.docker.compose.image`
(a7f79477…). Maßgeblich ist das Containerfeld `.Image`: **f5bd530568aa…**.
Der Container startete unverändert am 15.11., 10:11:12 UTC; Tag und Source-Revision
sind weiterhin `feedback-token-clipboard-20261111-4158a0c4b` und `4158a0c4b`.
Die vollständige Dateiinventur wurde in genau diesem laufenden Container erhoben.
Es gab keinen festgestellten zwischenzeitlichen Produktionswechsel.

Der Prepare-Guard hat die falsche ID vor Build und Aktivierung zurückgewiesen.
Die Reconciliation und der endgültige Releasebeleg verwenden die tatsächliche ID.
Die historische Discover-Ausgabe bleibt mit dieser expliziten Korrektur nachvollziehbar.
