"""3.6 - redaction before persistence: every class masked, a receipt per masked field."""

from __future__ import annotations

import pytest

from agentkeys.backends.contract import SecretValue
from agentkeys.redact import looks_like_secret, redact
from agentkeys.store.contract import RedactionReceipt
from agentkeys.store.memory import MemoryStore

GH = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"
SK = "sk-0123456789abcdefghijklmnopqrstuvwxyz"
AWS = "AKIAIOSFODNN7EXAMPLE"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl"
# assembled at runtime so no token-shaped literal is committed (push protection scans text)
SLACK = "xox" + "b-" + "0" * 10 + "-" + "notarealtoken"
PRIVATE = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----"


@pytest.mark.parametrize(
    ("text", "klass"),
    [
        (f"token={GH}", "api-key"),
        (f"key={SK}", "api-key"),
        (f"aws_key={AWS}", "api-key"),
        (f"Authorization: Bearer {JWT}", "bearer"),
        (f"authorization: jwt {JWT}", "bearer"),
        (PRIVATE, "private-key"),
        ("postgres://user:hunter2@db.example:5432/app", "connection-string"),
        (f"bearer_token={JWT}", "jwt"),
        (f"slack={SLACK}", "api-key"),
        ("GITHUB_TOKEN=" + GH, "env-assignment"),
    ],
)
def test_every_class_is_masked(text: str, klass: str) -> None:
    redaction = redact(text)
    assert "***" in redaction.text
    assert not looks_like_secret(redaction.text)
    assert klass in {receipt.class_ for receipt in redaction.receipts}


def test_the_masked_form_keeps_a_correlatable_tail() -> None:
    redaction = redact(f"token={GH}")
    assert GH[-4:] in redaction.text
    assert GH not in redaction.text


def test_redaction_is_idempotent() -> None:
    once = redact(f"a={GH} b={SK}")
    twice = redact(once.text)
    assert twice.text == once.text
    assert twice.receipts == ()


def test_receipts_count_each_masked_field() -> None:
    redaction = redact(f"one={GH}\ntwo={GH}\nthree={SK}")
    assert redaction.receipts
    assert sum(receipt.count for receipt in redaction.receipts) == 3
    assert all(receipt.field for receipt in redaction.receipts)


def test_clean_text_yields_no_receipts() -> None:
    redaction = redact("nothing sensitive here: agentkeys/dev/token")
    assert redaction.text == "nothing sensitive here: agentkeys/dev/token"
    assert redaction.receipts == ()


def test_a_secret_value_cannot_be_redacted_by_accident() -> None:
    with pytest.raises(TypeError):
        redact(SecretValue("value"))  # type: ignore[arg-type]


def test_receipts_persist_through_the_store() -> None:
    store = MemoryStore()
    store.open()
    redaction = redact(f"token={GH}")
    receipts = [
        RedactionReceipt(
            receipt_id=f"rcpt_{index}",
            subject_id="subject-1",
            field=receipt.field,
            class_=receipt.class_,
            count=receipt.count,
            redactor_version="1.0",
            created_at=1000,
        )
        for index, receipt in enumerate(redaction.receipts)
    ]
    for receipt in receipts:
        store.add_receipt(receipt)
    stored = store.list_receipts("subject-1")
    assert stored == tuple(receipts)
    assert all(GH not in entry.field for entry in stored)


def test_the_shared_detector_is_the_single_source() -> None:
    from agentkeys import config

    assert config.looks_like_secret is looks_like_secret
