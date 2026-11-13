"""Optional coast display fields preserve the bounded document contract."""
import pytest
from vtt.mapmaker_document import InvalidDocument, normalize_document
from tests.test_mapmaker_library import document


def test_optional_coast_fields_keep_old_defaults_and_roundtrip():
    old, _ = normalize_document(document())
    assert old['layers'][0]['effects'] == {'coast': True}
    source = document()
    source['layers'][0]['effects'].update(coastColor='#AABBCC', coastWidth=0)
    clean, _ = normalize_document(source)
    assert clean['layers'][0]['effects'] == {'coast': True, 'coastColor': '#aabbcc', 'coastWidth': 0}


@pytest.mark.parametrize('key,value', [('coastWidth', True), ('coastWidth', -1), ('coastWidth', 17), ('coastWidth', '8'), ('coastWidth', None), ('coastColor', 'red'), ('coastColor', '#123'), ('coastColor', None)])
def test_coast_fields_reject_unsafe_or_ambiguous_values(key, value):
    source = document()
    source['layers'][0]['effects'][key] = value
    with pytest.raises(InvalidDocument):
        normalize_document(source)
