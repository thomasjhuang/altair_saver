import contextlib
from http import client
import io
import os
import socket
import subprocess
import sys
import tempfile
from typing import Any, Dict, IO, Iterator, List, Optional, Union

import altair as alt

MimeType = Union[str, bytes, dict]
Mimebundle = Dict[str, MimeType]
JSON = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONDict = Dict[str, JSON]


def internet_connected(test_url: str = "cdn.jsdelivr.net") -> bool:
    """Return True if web connection is available."""
    conn = client.HTTPConnection(test_url, timeout=5)
    try:
        conn.request("HEAD", "/")
    except socket.gaierror:
        return False
    else:
        return True
    finally:
        conn.close()


def fmt_to_mimetype(
    fmt: str,
    vegalite_version: str = alt.VEGALITE_VERSION,
    vega_version: str = alt.VEGA_VERSION,
) -> str:
    """Get a mimetype given a format string."""
    if fmt == "vega-lite":
        return "application/vnd.vegalite.v{}+json".format(
            vegalite_version.split(".")[0]
        )
    elif fmt == "vega":
        return "application/vnd.vega.v{}+json".format(vega_version.split(".")[0])
    elif fmt == "pdf":
        return "application/pdf"
    elif fmt == "html":
        return "text/html"
    elif fmt == "png":
        return "image/png"
    elif fmt == "svg":
        return "image/svg+xml"
    else:
        raise ValueError(f"Unrecognized fmt={fmt!r}")


def mimetype_to_fmt(mimetype: str) -> str:
    """Get a format string given a mimetype."""
    if mimetype.startswith("application/vnd.vegalite"):
        return "vega-lite"
    elif mimetype.startswith("application/vnd.vega"):
        return "vega"
    elif mimetype == "application/pdf":
        return "pdf"
    elif mimetype == "text/html":
        return "html"
    elif mimetype == "image/png":
        return "png"
    elif mimetype == "image/svg+xml":
        return "svg"
    else:
        raise ValueError(f"Unrecognized mimetype={mimetype!r}")


def infer_mode_from_spec(spec: JSONDict) -> str:
    """Given a spec, return the inferred mode.

    This uses the '$schema' value if present, and otherwise tries to
    infer the type based on top-level keys. If both approaches fail,
    it returns "vega-lite" by default.

    Parameters
    ----------
    spec : dict
        The vega or vega-lite specification

    Returns
    -------
    mode : str
        Either "vega" or "vega-lite"
    """
    if "$schema" in spec:
        schema = spec["$schema"]
        if not isinstance(schema, str):
            pass
        elif "/vega-lite/" in schema:
            return "vega-lite"
        elif "/vega/" in schema:
            return "vega"

    # Check several vega-only top-level properties.
    for key in ["axes", "legends", "marks", "projections", "scales", "signals"]:
        if key in spec:
            return "vega"

    return "vega-lite"


@contextlib.contextmanager
def temporary_filename(**kwargs: Any) -> Iterator[str]:
    """Create and clean-up a temporary file

    Arguments are the same as those passed to tempfile.mkstemp

    We could use tempfile.NamedTemporaryFile here, but that causes issues on
    windows (see https://bugs.python.org/issue14243).
    """
    filedescriptor, filename = tempfile.mkstemp(**kwargs)
    os.close(filedescriptor)

    try:
        yield filename
    finally:
        if os.path.exists(filename):
            os.remove(filename)


@contextlib.contextmanager
def maybe_open(fp: Union[IO, str], mode: str = "w") -> Iterator[IO]:
    """Write to string or file-like object"""
    if isinstance(fp, str):
        with open(fp, mode) as f:
            yield f
    elif isinstance(fp, io.TextIOBase) and "b" in mode:
        raise ValueError("File expected to be opened in binary mode.")
    elif isinstance(fp, io.BufferedIOBase) and "b" not in mode:
        raise ValueError("File expected to be opened in text mode")
    else:
        yield fp


def extract_format(fp: Union[IO, str]) -> str:
    """Extract the output format from a file or filename."""
    filename: Optional[str]
    if isinstance(fp, str):
        filename = fp
    else:
        filename = getattr(fp, "name", None)
    if filename is None:
        raise ValueError(f"Cannot infer format from {fp}")
    if filename.endswith(".vg.json"):
        return "vega"
    elif filename.endswith(".json"):
        return "vega-lite"
    else:
        return filename.split(".")[-1]


def check_output_with_stderr(
    cmd: Union[str, List[str]], shell: bool = False, input: Optional[bytes] = None
) -> bytes:
    """Run a command in a subprocess, printing stderr to sys.stderr.

    This is important because subprocess stderr in notebooks is printed to the
    terminal rather than the notebook.
    """
    try:
        ps = subprocess.run(
            cmd,
            shell=shell,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            input=input,
        )
    except subprocess.CalledProcessError as err:
        if err.stderr:
            sys.stderr.write(err.stderr.decode())
            sys.stderr.flush()
        raise
    else:
        if ps.stderr:
            sys.stderr.write(ps.stderr.decode())
            sys.stderr.flush()
        return ps.stdout
