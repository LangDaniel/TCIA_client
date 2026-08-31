# TCIA Client

[![Tests](https://github.com/LangDaniel/TCIA_client/actions/workflows/tests.yml/badge.svg)](https://github.com/LangDaniel/TCIA_client/actions/workflows/tests.yml)

A minimal Python client for the [REST API](https://nbia.cancerimagingarchive.net/nbia-api/services/v4/) of [The Cancer Imaging Archive (TCIA)](https://www.cancerimagingarchive.net/): query collection/series/patient metadata as JSON, and download image series as zip archives.

## Installation

With [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Or with pip:

```bash
pip install .
```

The client's only runtime dependency is [`requests`](https://pypi.org/project/requests/).

## Quick start

```python
from TCIAClient import TCIAClient

base_url = 'https://nbia.cancerimagingarchive.net/nbia-api/services/v4/'
client = TCIAClient(base_url)
```

### Querying metadata

`get_json` calls a TCIA API endpoint and returns the parsed JSON response. Any endpoint-specific parameters are passed as a dict.

```python
collections = client.get_json('getCollectionValues')
# [{'Collection': '4D-Lung'}, {'Collection': 'A091105'}, ...]

series = client.get_json('getSeries', {'Collection': 'Lung-PET-CT-Dx'})
# [{'SeriesInstanceUID': '1.3.6.1...', 'Modality': 'CT', ...}, ...]

patients = client.get_json('getPatientStudy', {'Collection': 'Lung-PET-CT-Dx'})
# [{'PatientID': 'Lung_Dx-A0001', 'PatientSex': 'M', ...}, ...]
```

The results are plain lists of dicts, so they drop straight into a `pandas.DataFrame` if you want to work with them as tables:

```python
import pandas as pd

series_df = pd.DataFrame(client.get_json('getSeries', {'Collection': 'Lung-PET-CT-Dx'}))
```

See the [TCIA REST API](https://nbia.cancerimagingarchive.net/nbia-api/services/v4/) for the full list of available endpoints and their parameters.

### Downloading an image series

`get_image` downloads a series by its `SeriesInstanceUID`, optionally unzipping the result and/or removing the archive afterwards.

```python
series_uid = series[0]['SeriesInstanceUID']

client.get_image(
    series_instance_uid=series_uid,
    local_path='downloads/series.zip',
    unzip=True,
    remove_zip=True,
)
```

## Development notes

- API responses are consumed as-is (`get_json`) — the client does no schema validation, so unexpected fields from the API pass straight through.
- `get_image` creates the parent directory of `local_path` for you; it does not currently overwrite an existing directory (see [tests/test_tcia_client.py](tests/test_tcia_client.py) for the documented behavior).
