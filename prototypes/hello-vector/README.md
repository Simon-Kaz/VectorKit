# hello-vector

Minimal prototype that connects to Vector, reads battery state, and makes it
speak. Use it to validate the full pipeline (wire-pod up, firmware flashed,
SDK authenticated) before building anything else.

## Run

```bash
# one-time: install the vendored SDK (our fork) and authenticate
pip install -e libs/vendor/wirepod-vector-python-sdk
python -m anki_vector.configure   # writes ~/.anki_vector/ creds

cd prototypes/hello-vector
python main.py
```

Expected output:

```
Connected. Battery: 4.0xV, level 3
```

and Vector says "Hello. The pipeline works."

## If it fails

- ImportError about the SDK: run `pip install -e libs/vendor/wirepod-vector-python-sdk`.
- Connection/TLS error: re-run `python -m anki_vector.configure`.
- Timeout: confirm Vector's IP matches `~/.anki_vector/sdk_config.ini`.

See `../../docs/setup-vector.md`.
