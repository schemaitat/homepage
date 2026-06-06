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

Three workflows live in `.github/workflows/`:

| Workflow | Trigger | What it does |
|---|---|---|
| `pr.yml` | Pull request targeting `main` | Full build (Quarto + Hugo + Marimo), no deploy |
| `deploy.yml` | Push to `main` | Full build + rsync to server |
| `security-check.yml` | Every Monday 08:00 UTC / manual | TLS, headers, SSH hardening, open ports |

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

# 3. Open firewall ports
ufw allow 'Nginx Full' && ufw allow OpenSSH && ufw enable

# 4. TLS via Let's Encrypt
apt install -y certbot python3-certbot-nginx
certbot --nginx -d schemaitat.de --non-interactive --agree-tos -m <your-email>
# certbot installs a systemd timer for automatic renewal

# 5. Security headers — write snippet then include it in nginx.conf http block
cat > /etc/nginx/snippets/security-headers.conf <<'EOF'
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
EOF
# add inside the http { } block in /etc/nginx/nginx.conf:
#   include /etc/nginx/snippets/security-headers.conf;
# also set: server_tokens off;
nginx -t && systemctl reload nginx

# 6. Disable SSH password authentication
echo 'PasswordAuthentication no' > /etc/ssh/sshd_config.d/99-hardening.conf
sshd -t && systemctl reload ssh
```

SSH access uses the key at `~/.ssh/homepage/id_ed25519`. To connect:

```bash
just ssh
```

## Local development

```bash
just dev    # Hugo dev server with drafts
just prev   # Quarto preview
just build  # full local build (quarto render + hugo)
just gen-images [--force]  # generate AI featured images
```
