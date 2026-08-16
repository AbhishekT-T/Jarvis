"""Parse the real progress out of the noisy ollama pull stderr logs."""
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_FRAME = re.compile(
    r"pulling (\w+):\s+(\d+)%\s+[^\r\n]*?\s+([\d.]+) (MB|GB)/ ([\d.]+ GB|\d+ GB)\s+([\d.]+ [KM]B/s)\s+(\S+)"
)


def latest_progress(path):
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", text)
    lines = [ln.strip() for ln in text.split("\n") if "pulling" in ln and "%" in ln]
    if not lines:
        return "(no progress frame yet)"
    last = lines[-1]
    m = re.search(
        r"pulling (\w+):\s+(\d+)%\s+([\d.]+) ([KMGT]B)/\s*([\d.]+) ([KMGT]B)\s+([\d.]+) ([KMGT]B/s)\s+(\S+)",
        last,
    )
    if m:
        digest, pct, cur, cu, tot, tu, rate, eta = m.groups()
        return (f"{pct}% | {cur} {cu} / {tot} {tu} | {rate} | ETA {eta}  (digest {digest[:12]})")
    return last[:160]


if __name__ == "__main__":
    base = r"M:\coding\Jarvis"
    for name, path in (("PRO   ", f"{base}\\pull_pro_err.log"),
                       ("VISION", f"{base}\\pull_vision_err.log")):
        print(f"{name}: {latest_progress(path)}")

