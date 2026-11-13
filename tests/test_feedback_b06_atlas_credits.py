import base64
import io
import json
from pathlib import Path
import pytest
from PIL import Image
from vtt import atlas_domain as domain
from tests.test_mapmaker_library import document
from tests.test_atlas import png


def test_full_reviewed_raster_credit_collection_fits_atlas_bundle_and_png():
    assets=Path(__file__).resolve().parents[1]/'vtt/static/mapmaker/assets'
    credits='\n\n'.join(json.loads((assets/row['manifest']).read_text()).get('exportCredit','') for row in json.loads((assets/'packs.json').read_text())['packs'])
    assert 20000 < len(credits) < domain.MAX_CREDITS
    result=domain.bundle({'document':document(),'png':png(),'credits':credits})
    assert result['credits']==credits
    with Image.open(io.BytesIO(base64.b64decode(result['png'].split(',')[1]))) as image:
        image.load();assert image.info['Credits']==credits
    with pytest.raises(domain.AtlasError):domain.bundle({'document':document(),'png':png(),'credits':'x'*(domain.MAX_CREDITS+1)})
