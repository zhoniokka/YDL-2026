"""Generate an image of the Almaty mountains via the llm.alem.ai text-to-image API."""

import base64
import os
import sys
import urllib.request

from load_env import load_env

URL = "https://llm.alem.ai/v1/images/generations"

# Key is read from .env (IMAGE_API_KEY); never hardcoded.
load_env()
API_KEY = os.environ.get("IMAGE_API_KEY")
if not API_KEY:
    sys.exit("IMAGE_API_KEY is not set. Copy .env.example to .env and add your key.")

PROMPT = (
    "The Almaty mountains: the snow-capped peaks of the Trans-Ili Alatau "
    "rising over the city of Almaty, Kazakhstan, alpine forest in the "
    "foreground, dramatic light at sunrise, highly detailed, photorealistic"
)

OUTPUT = "almaty_mountains.png"


def main():
    payload = json_bytes({
        "model": "text-to-image",
        "prompt": PROMPT,
        "size": "1024x1024",
    })

    req = urllib.request.Request(
        URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    print("Requesting image...")
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode("utf-8")

    data = parse_json(body)
    item = data["data"][0]

    if item.get("b64_json"):
        image_bytes = base64.b64decode(item["b64_json"])
        with open(OUTPUT, "wb") as f:
            f.write(image_bytes)
        print(f"Saved image to {OUTPUT}")
    elif item.get("url"):
        url = item["url"]
        print(f"Downloading image from {url}")
        with urllib.request.urlopen(url) as img_resp:
            with open(OUTPUT, "wb") as f:
                f.write(img_resp.read())
        print(f"Saved image to {OUTPUT}")
    else:
        print("Unexpected response:", body, file=sys.stderr)
        sys.exit(1)


# --- tiny json helpers (stdlib only) ---
import json


def json_bytes(obj):
    return json.dumps(obj).encode("utf-8")


def parse_json(text):
    return json.loads(text)


if __name__ == "__main__":
    main()
