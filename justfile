dev:
    hugo server --buildDrafts --port 1313

prev:
    quarto preview

build:
    quarto render && hugo

gen-images *args:
    uv run python scripts/gen_preview_images.py {{args}}

ssh:
    ssh -i ~/.ssh/homepage/id_ed25519 -o PasswordAuthentication=no -o StrictHostKeyChecking=accept-new root@46.224.145.228
