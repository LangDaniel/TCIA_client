import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest
import requests

from tcia_client import TCIAClient


BASE_URL = "https://example.com/services/v4/TCIA/query"


@pytest.fixture
def client():
    return TCIAClient(BASE_URL)


class TestInit:
    def test_appends_trailing_slash(self):
        client = TCIAClient(BASE_URL)
        assert client.base_url == BASE_URL + "/"

    def test_keeps_existing_trailing_slash(self):
        client = TCIAClient(BASE_URL + "/")
        assert client.base_url == BASE_URL + "/"


class TestGetJson:
    def test_builds_url_and_returns_json(self, client):
        response = MagicMock()
        response.json.return_value = {"ok": True}

        with patch("tcia_client.requests.get", return_value=response) as mock_get:
            result = client.get_json("getCollectionValues")

        assert result == {"ok": True}
        args, kwargs = mock_get.call_args
        assert args[0] == BASE_URL + "/getCollectionValues"
        assert kwargs["params"]["format"] == "json"

    def test_adds_format_json_to_existing_params(self, client):
        response = MagicMock()
        response.json.return_value = []

        with patch("tcia_client.requests.get", return_value=response) as mock_get:
            client.get_json("getSeries", params={"Collection": "TCGA-LUAD"})

        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {"Collection": "TCGA-LUAD", "format": "json"}


class TestGetImage:
    @staticmethod
    def _zip_bytes(filename="scan.dcm", content=b"dicom-bytes"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(filename, content)
        return buf.getvalue()

    @staticmethod
    def _mock_streaming_response(payload: bytes):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.iter_content.return_value = [
            payload[i:i + 4] for i in range(0, len(payload), 4)
        ]
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        return response

    def test_downloads_file_and_creates_parent_dir(self, client, tmp_path):
        payload = b"raw-image-bytes"
        response = self._mock_streaming_response(payload)
        target = tmp_path / "downloads" / "image.zip"

        with patch("tcia_client.requests.get", return_value=response) as mock_get:
            result = client.get_image("1.2.3", target, unzip=False, remove_zip=False)

        assert result is True
        assert target.read_bytes() == payload
        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {"SeriesInstanceUID": "1.2.3"}
        assert kwargs["stream"] is True

    def test_unzip_extracts_and_keeps_zip_by_default(self, client, tmp_path):
        payload = self._zip_bytes()
        response = self._mock_streaming_response(payload)
        target = tmp_path / "downloads" / "image.zip"

        with patch("tcia_client.requests.get", return_value=response):
            client.get_image("1.2.3", target, unzip=True, remove_zip=False)

        assert target.exists()
        assert (target.parent / "scan.dcm").read_bytes() == b"dicom-bytes"

    def test_unzip_with_remove_zip_deletes_archive(self, client, tmp_path):
        payload = self._zip_bytes()
        response = self._mock_streaming_response(payload)
        target = tmp_path / "downloads" / "image.zip"

        with patch("tcia_client.requests.get", return_value=response):
            client.get_image("1.2.3", target, unzip=True, remove_zip=True)

        assert not target.exists()
        assert (target.parent / "scan.dcm").read_bytes() == b"dicom-bytes"

    def test_raises_for_http_error(self, client, tmp_path):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("boom")
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        target = tmp_path / "downloads" / "image.zip"

        with patch("tcia_client.requests.get", return_value=response):
            with pytest.raises(requests.HTTPError):
                client.get_image("1.2.3", target, unzip=False, remove_zip=False)

    def test_fails_when_destination_dir_already_exists(self, client, tmp_path):
        # Characterizes a real bug in TCIAClient.get_image(): it calls
        # Path.mkdir(parents=True) without exist_ok=True, so any call whose
        # target directory already exists (e.g. tmp_path itself, or a second
        # download into the same folder) raises instead of succeeding.
        response = self._mock_streaming_response(b"data")
        target = tmp_path / "image.zip"

        with patch("tcia_client.requests.get", return_value=response):
            with pytest.raises(FileExistsError):
                client.get_image("1.2.3", target, unzip=False, remove_zip=False)
