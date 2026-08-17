"""Integration tests for the FastAPI endpoints.

Covers both input paths (JSON body and multipart upload), each main
endpoint, and invalid-input error handling.
"""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── /analyze ──────────────────────────────────────────────────────────────────

def test_analyze_json(client, musicxml):
    r = client.post("/analyze", json={"musicxml": musicxml})
    assert r.status_code == 200
    body = r.json()
    assert body["meter"] == "4/4"
    assert body["meter_family"] == "simple"
    assert isinstance(body["presets"], list) and len(body["presets"]) > 0
    assert isinstance(body["suite"], list) and len(body["suite"]) > 0


def test_analyze_multipart(client, musicxml):
    r = client.post(
        "/analyze",
        files={"file": ("melody.xml", musicxml.encode(), "text/xml")},
    )
    assert r.status_code == 200
    assert r.json()["meter"] == "4/4"


# ── /arrange ──────────────────────────────────────────────────────────────────

def test_arrange_json(client, musicxml):
    r = client.post("/arrange", json={"musicxml": musicxml})
    assert r.status_code == 200
    body = r.json()
    assert "musicxml" in body
    assert "<score-partwise" in body["musicxml"]
    assert "preset" in body
    assert "meter" in body


def test_arrange_multipart(client, musicxml):
    r = client.post(
        "/arrange",
        files={"file": ("melody.xml", musicxml.encode(), "text/xml")},
    )
    assert r.status_code == 200
    assert "<score-partwise" in r.json()["musicxml"]


def test_arrange_download_returns_binary(client, musicxml):
    r = client.post("/arrange?download=true", json={"musicxml": musicxml})
    assert r.status_code == 200
    assert "application/octet-stream" in r.headers["content-type"]
    assert len(r.content) > 0


# ── /suite ────────────────────────────────────────────────────────────────────

def test_suite_json_seeded(client, musicxml):
    r = client.post("/suite?seed=42", json={"musicxml": musicxml})
    assert r.status_code == 200
    body = r.json()
    assert "<score-partwise" in body["musicxml"]
    assert len(body["sections"]) > 1
    # Each section must carry an index, name, and tempo
    for section in body["sections"]:
        assert "index" in section
        assert "name" in section
        assert "tempo" in section


def test_suite_is_reproducible_with_seed(client, musicxml):
    r1 = client.post("/suite?seed=7", json={"musicxml": musicxml})
    r2 = client.post("/suite?seed=7", json={"musicxml": musicxml})
    assert r1.json()["sections"] == r2.json()["sections"]


# ── /merge ────────────────────────────────────────────────────────────────────

def test_merge_json(client, musicxml):
    r = client.post("/merge", json={"musicxml": musicxml})
    assert r.status_code == 200
    body = r.json()
    assert "<score-partwise" in body["musicxml"]
    assert len(body["sections"]) > 1


# ── /compress ─────────────────────────────────────────────────────────────────

def test_compress_returns_mxl_blob(client, musicxml):
    # First generate an arrangement so we have a real arranged musicxml
    arranged = client.post("/arrange", json={"musicxml": musicxml}).json()["musicxml"]
    r = client.post("/compress", json={"musicxml": arranged})
    assert r.status_code == 200
    assert "application/octet-stream" in r.headers["content-type"]
    # .mxl is a ZIP — check the magic bytes
    assert r.content[:2] == b'PK'


def test_compress_preserves_content(client, musicxml):
    import zipfile, io
    arranged = client.post("/arrange", json={"musicxml": musicxml}).json()["musicxml"]
    r = client.post("/compress", json={"musicxml": arranged})
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
        assert 'META-INF/container.xml' in names
        assert 'score.xml' in names
        inner = zf.read('score.xml').decode()
    assert "<score-partwise" in inner


# ── error cases ───────────────────────────────────────────────────────────────

def test_invalid_musicxml_content_returns_error(client):
    r = client.post("/analyze", json={"musicxml": "this is not xml"})
    assert r.status_code >= 400


def test_missing_musicxml_field_returns_422(client):
    r = client.post("/analyze", json={"wrong_field": "value"})
    assert r.status_code == 422


def test_unsupported_content_type_returns_422(client):
    r = client.post(
        "/analyze",
        content=b"raw bytes",
        headers={"content-type": "text/plain"},
    )
    assert r.status_code == 422


def test_unknown_preset_returns_400(client, musicxml):
    r = client.post("/arrange?preset=nonexistent_preset", json={"musicxml": musicxml})
    assert r.status_code == 400
