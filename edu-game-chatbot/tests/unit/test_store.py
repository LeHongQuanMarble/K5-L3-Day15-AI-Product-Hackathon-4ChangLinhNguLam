"""SessionStore (Session Memory) (T05)"""

import asyncio

import pytest

from app.core.models import Message, Version
from app.core.store import SessionStore


@pytest.fixture
def st(tmp_path) -> SessionStore:
    return SessionStore(tmp_path / "sessions")


def test_create_and_get_roundtrip(st) -> None:
    s = st.create()
    s.request = "game toán"
    s.versions.append(Version(number=1, html_path="v1/index.html"))
    st.add_message(s, Message(role="user", text="hi"))
    st.save(s)
    assert st.get(s.id) == s
    assert st.exists(s.id)
    assert s.latest_version.number == 1


def test_get_missing_raises_keyerror(st) -> None:
    with pytest.raises(KeyError):
        st.get("nope")
    with pytest.raises(KeyError):
        st.get("../x")
    assert not st.exists("nope")


def test_save_is_atomic(st) -> None:
    s = st.create()
    st.save(s)
    assert not list(st.session_dir(s.id).glob("*.tmp"))
    assert (st.session_dir(s.id) / "memory.json").is_file()


def test_updated_at_increases(st) -> None:
    s = st.create()
    first = s.updated_at
    st.save(s)
    assert s.updated_at > first
    assert st.get(s.id).updated_at == s.updated_at


@pytest.mark.parametrize("name", ["../x", "a/../b", "a/b", "a\\b", "", "x\x00y", "a:b"])
def test_safe_path_rejects_traversal(st, name) -> None:
    s = st.create()
    with pytest.raises(ValueError):
        st.safe_path(s.id, name)


def test_safe_path_rejects_absolute(st, tmp_path) -> None:
    s = st.create()
    with pytest.raises(ValueError):
        st.safe_path(s.id, "/etc/passwd")
    with pytest.raises(ValueError):
        st.safe_path(s.id, str(tmp_path / "a.txt"))
    with pytest.raises(ValueError):
        st.safe_path("../evil", "a.txt")


def test_safe_path_ok(st) -> None:
    s = st.create()
    p = st.safe_path(s.id, "bai.pdf")
    assert p.parent == (st.session_dir(s.id) / "uploads").resolve()
    assert st.version_dir(s.id, 2).name == "v2"


def test_add_message_and_event(st) -> None:
    s = st.create()
    m = st.add_message(s, Message(role="bot", text="xin chào"))
    st.add_event(s, "N1", "ok", n=3)
    assert s.messages == [m]
    assert s.events[0]["node"] == "N1" and s.events[0]["n"] == 3 and "at" in s.events[0]


async def test_lock_is_per_session(st) -> None:
    a, b = st.create(), st.create()
    assert st.lock(a.id) is st.lock(a.id)
    assert st.lock(a.id) is not st.lock(b.id)
    assert isinstance(st.lock(a.id), asyncio.Lock)
