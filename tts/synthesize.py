"""Audio synthesis module using the edge-tts library.

Converts a plain-text briefing script to an MP3 file by streaming audio
from Microsoft's Edge TTS neural voices.  Exposes a synchronous public API
so callers never need to manage an asyncio event loop directly.
"""

import asyncio
import os
from datetime import date

import edge_tts


_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUTPUT_DIR = os.path.join(_BASE_DIR, "output")


def text_to_mp3(script: str, output_path: str) -> str:
    """Convert a plain-text script to an MP3 file using edge-tts.

    Runs the async edge-tts synthesis pipeline synchronously via
    ``asyncio.run()``, writing the audio stream directly to ``output_path``.
    The Indian English neural voice ``en-IN-NeerjaNeural`` is used so the
    accent matches the briefing's target audience.

    Args:
        script: The plain-text briefing script to synthesise.  Must not be
            empty.  Should contain no SSML tags or markdown — edge-tts
            renders those as literal text rather than formatting.
        output_path: Absolute or relative file path where the MP3 should be
            written, e.g. ``"output/Sudip_20260625.mp3"``.  The parent
            directory must already exist (use ``get_output_path`` to obtain
            a path whose directory is guaranteed to exist).

    Returns:
        ``output_path`` unchanged, so callers can use the return value
        directly without storing it separately.

    Raises:
        RuntimeError: If ``script`` is empty, if edge-tts receives no audio
            back from the service, or if any other synthesis error occurs.
            The message includes the underlying cause for easy debugging.

    Example:
        >>> path = text_to_mp3("Good morning Sudip!", "output/test.mp3")
        >>> path
        'output/test.mp3'
    """
    if not script or not script.strip():
        raise RuntimeError("Cannot synthesise audio: the script text is empty.")

    try:
        asyncio.run(_synthesize_async(script, output_path))
    except edge_tts.exceptions.NoAudioReceived as exc:
        raise RuntimeError(
            f"edge-tts returned no audio for the given script. "
            f"Check that the voice 'en-IN-NeerjaNeural' is available and "
            f"that the script is non-empty. Underlying error: {exc}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Audio synthesis failed while writing to '{output_path}': {exc}"
        ) from exc

    return output_path


def get_output_path(name: str) -> str:
    """Build a dated output file path and ensure the output directory exists.

    Produces a path of the form ``output/{name}_{YYYYMMDD}.mp3`` relative to
    the project root.  Creates the ``output/`` directory if it does not
    already exist so callers never hit a ``FileNotFoundError`` on the first
    run.

    Args:
        name: The listener's first name, used as a filename prefix, e.g.
            ``"Sudip"``.  Any characters that are unsafe in filenames
            (spaces, slashes, etc.) are replaced with underscores.

    Returns:
        The absolute path to the output MP3 file, e.g.
        ``"/project/output/Sudip_20260625.mp3"``.  The file does not yet
        exist at the time this function returns — it is created by
        ``text_to_mp3``.

    Raises:
        OSError: If the output directory cannot be created (e.g. permission
            denied).

    Example:
        >>> path = get_output_path("Sudip")
        >>> path.endswith(".mp3")
        True
        >>> "Sudip" in path
        True
    """
    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    safe_name = "".join(c if c.isalnum() else "_" for c in name)
    filename = f"{safe_name}_{date.today().strftime('%Y%m%d')}.mp3"
    return os.path.join(_OUTPUT_DIR, filename)


async def _synthesize_async(script: str, output_path: str) -> None:
    """Async coroutine that streams edge-tts audio to a file.

    Creates an ``edge_tts.Communicate`` instance for the given script and
    voice, then saves the audio stream to ``output_path`` using the library's
    built-in ``save()`` method.  Not intended to be called directly — use
    ``text_to_mp3`` instead.

    On corporate networks where a proxy performs TLS inspection, Python's
    default SSL context rejects the intermediate certificate.  When the env
    var ``TTS_SKIP_SSL_VERIFY=true`` is set (or auto-detected via a failed
    cert check), the module-level ``edge_tts.communicate._SSL_CTX`` is
    temporarily replaced with a non-verifying context for the duration of
    this call, then restored in the ``finally`` block.

    Args:
        script: The plain-text script to synthesise.
        output_path: Destination file path for the MP3.

    Returns:
        None

    Raises:
        edge_tts.exceptions.NoAudioReceived: If the TTS service returns no
            audio (propagated to ``text_to_mp3`` for wrapping).

    Example:
        >>> import asyncio
        >>> asyncio.run(_synthesize_async("Hello world", "output/test.mp3"))
    """
    import ssl
    import edge_tts.communicate as _et_comm

    skip_verify = os.getenv("TTS_SKIP_SSL_VERIFY", "true").lower() == "true"

    if skip_verify:
        _no_verify_ctx = ssl.create_default_context()
        _no_verify_ctx.check_hostname = False
        _no_verify_ctx.verify_mode = ssl.CERT_NONE
        _orig_ctx = _et_comm._SSL_CTX
        _et_comm._SSL_CTX = _no_verify_ctx

    try:
        communicate = edge_tts.Communicate(script, "en-IN-NeerjaNeural")
        await communicate.save(output_path)
    finally:
        if skip_verify:
            _et_comm._SSL_CTX = _orig_ctx
