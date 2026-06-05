# schemaitat.de

Personal homepage built with [Hugo](https://gohugo.io) and [Quarto](https://quarto.org), served by Nginx on a Hetzner VPS.

## Stack

- **Hugo** (extended) — static site generator, theme: LoveIt
- **Quarto** — renders `.qmd` notebooks to Hugo-compatible markdown
- **Marimo** — notebooks exported as WASM and served statically
- **uv** — Python dependency management
- **Nginx** — web server
- **GitHub Actions** — CI/CD

## CI/CD

Two workflows live in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `pr.yml` | Pull request targeting `main` | Full build (Quarto + Hugo + Marimo), no deploy |
| `deploy.yml` | Push to `main` | Full build + rsync to server |

### Required GitHub secrets and variables

Configure these under **Settings → Secrets and variables → Actions**:

| Type | Name | Value |
|---|---|---|
| Secret | `DEPLOY_SSH_KEY` | Private key for SSH access to the server |
| Variable | `DEPLOY_HOST` | Server IP address |
| Variable | `DEPLOY_USER` | SSH user (e.g. `root`) |

To generate a dedicated deploy key:

```bash
bash scripts/gen_ssh_key.sh homepage-deploy generated-key
# add homepage-deploy.pub to ~/.ssh/authorized_keys on the server
# add contents of homepage-deploy to DEPLOY_SSH_KEY secret
```

## Server setup

The server runs Ubuntu 26.04. Steps executed once on a fresh machine:

```bash
# 1. Install and enable Nginx
apt update && apt install -y nginx
systemctl enable --now nginx

# 2. Point Nginx at the deploy target directory
sed -i 's|root /var/www/html;|root /usr/share/nginx/html;|' /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 3. (Optional) TLS via Let's Encrypt
apt install -y certbot python3-certbot-nginx
certbot --nginx -d schemaitat.de
```

SSH access uses the key at `~/.ssh/homepage/id_ed25519`. To connect:

```bash
just ssh
```

## Local development

```bash
# Preview Hugo site with drafts
make serve

# Preview Quarto output
make prev
```
