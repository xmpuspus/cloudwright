"""Tests for the HCL string escape helper used by all Terraform renderers."""

from __future__ import annotations

from cloudwright.exporter.terraform import render
from cloudwright.exporter.terraform.common import _hcl_quote
from cloudwright.spec import ArchSpec, Component

# --- Direct helper tests ----------------------------------------------------


def test_quote_wraps_simple_string_in_double_quotes():
    assert _hcl_quote("foo") == '"foo"'


def test_quote_escapes_inner_double_quote():
    # Input  : foo"bar
    # Output : "foo\"bar"
    assert _hcl_quote('foo"bar') == '"foo\\"bar"'


def test_quote_escapes_backslash_first():
    # Backslash escape must not double-escape later replacements.
    assert _hcl_quote("c:\\path") == '"c:\\\\path"'


def test_quote_escapes_newlines_and_carriage_returns():
    assert _hcl_quote("a\nb") == '"a\\nb"'
    assert _hcl_quote("a\rb") == '"a\\rb"'


def test_quote_handles_combination_of_specials():
    # Newline + quote in the same payload.
    payload = 'name = "evil"\n}\nresource "x" "y" {'
    out = _hcl_quote(payload)
    # Must not contain a raw newline or unescaped inner quote.
    assert "\n" not in out
    assert '"\n}\n' not in out
    assert out.startswith('"') and out.endswith('"')
    assert "\\n" in out and '\\"' in out


def test_quote_handles_none_as_empty_string():
    assert _hcl_quote(None) == '""'


def test_quote_coerces_non_string_input():
    # Numeric input shouldn't crash; it just gets stringified.
    assert _hcl_quote(42) == '"42"'


# --- End-to-end: malicious component label cannot inject HCL ----------------


def test_render_neutralizes_quote_injection_in_label():
    spec = ArchSpec(
        name="App",
        provider="aws",
        region="us-east-1",
        components=[
            Component(
                id="bk",
                service="s3",
                provider="aws",
                label='evil"\nresource "aws_iam_user" "owned" {}\n#',
                tier=3,
            )
        ],
    )
    hcl = render(spec)
    # The injection attempt must be inert: the rogue resource header should
    # appear only as escaped text inside a Name tag, never as a real top-level
    # resource declaration.
    assert 'resource "aws_iam_user" "owned"' not in hcl
    # And the escaped form should be present on a single tag line.
    assert '\\"' in hcl


def test_render_neutralizes_quote_injection_in_region():
    spec = ArchSpec(
        name="App",
        provider="aws",
        region='us-east-1"\n}\nresource "aws_iam_user" "owned" {}\n#',
        components=[
            Component(id="web", service="ec2", provider="aws", label="Web", tier=2),
        ],
    )
    hcl = render(spec)
    assert 'resource "aws_iam_user" "owned"' not in hcl
