import os

# Must be set before hymnarranger.api is imported — ALLOWED_HOSTS is read at
# module load time and TrustedHostMiddleware is configured with that value.
os.environ.setdefault("ALLOWED_HOSTS", "testserver,localhost,127.0.0.1")

import uuid as _uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from hymnarranger.api import app
from hymnarranger.auth.security import create_access_token, hash_password
from hymnarranger.db.models import GeneratedWork, User
from hymnarranger.db.session import get_db

# Minimal two-measure melody in C major, 4/4. Music21 can parse this without
# any additional metadata (no DOCTYPE needed for the parser we use).
SIMPLE_MUSICXML = """\
<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Melody</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>E</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>G</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>6</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
    <measure number="2">
      <note><pitch><step>B</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>G</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>E</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>half</type></note>
    </measure>
  </part>
</score-partwise>"""


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def musicxml():
    return SIMPLE_MUSICXML


# ── In-memory DB fixtures for auth / works tests ───────────────────────────────
#
# Uses SQLite with raw DDL to sidestep PostgreSQL-specific types (UUID, JSONB).
# The ORM's bind/result processors handle Python↔SQLite type coercion correctly.

_SQLITE_DDL = [
    """CREATE TABLE users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        is_verified INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        password_changed_at TEXT
    )""",
    """CREATE TABLE generated_works (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        input_params TEXT NOT NULL DEFAULT '{}',
        musicxml_content TEXT NOT NULL,
        source_abc TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE password_reset_tokens (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE email_verification_tokens (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
]

_EMAIL_TARGETS = (
    "hymnarranger.auth.routes.send_verification_email",
    "hymnarranger.auth.routes.send_password_reset_email",
    "hymnarranger.auth.routes.send_already_registered_email",
)


@pytest.fixture()
def db_engine():
    # StaticPool keeps a single underlying connection so all sessions share
    # the same in-memory database (without it each new connection is a blank DB).
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as conn:
        for stmt in _SQLITE_DDL:
            conn.execute(text(stmt))
        conn.commit()
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    _Session = sessionmaker(bind=db_engine)
    session = _Session()
    yield session
    session.close()


@pytest.fixture()
def auth_client(db_session):
    """TestClient whose get_db is wired to the in-memory SQLite session.
    Outbound email calls are patched so no Brevo API key is needed."""
    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    patches = [patch(t) for t in _EMAIL_TARGETS]
    for p in patches:
        p.start()
    yield TestClient(app)
    for p in patches:
        p.stop()
    app.dependency_overrides.pop(get_db, None)


# ── Factory fixtures ───────────────────────────────────────────────────────────

@pytest.fixture()
def make_user(db_session):
    def _factory(email="alice@example.com", password="Passw0rd!", verified=True):
        user = User(
            id=_uuid.uuid4(),
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            is_verified=verified,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _factory


@pytest.fixture()
def make_work(db_session):
    def _factory(user, title="Test Work"):
        work = GeneratedWork(
            id=_uuid.uuid4(),
            user_id=user.id,
            title=title,
            input_params={},
            musicxml_content="<score/>",
        )
        db_session.add(work)
        db_session.commit()
        db_session.refresh(work)
        return work
    return _factory


def bearer(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
