# resume-builder

Generates tailored, two-page PDF resumes using Claude. You provide your career history once, then for each job application Claude selects the most relevant experience, writes a custom summary, and reorders your skills — all output as a draft you review and edit before the final PDF is rendered.

Available as a **CLI tool** for local use or a **web app** you can host and access from any device (iPad, phone, laptop).

## Live Instance

A hosted instance is running at **[resume.norangio.dev](https://resume.norangio.dev)**.

It's invite-only — if you'd like access, reach out to me directly for a login. Note that each resume generation makes a paid Claude API call, so I ask that you only use it for genuine job applications.

## How It Works

1. You paste a job description
2. Claude reads your career docs and produces a tailored draft — selecting the most relevant bullets, writing a targeted summary, and reordering skills by relevance
3. You review and edit the draft (this is the human-in-the-loop step)
4. The tool renders it to HTML and exports a polished two-page PDF via headless Chromium

## Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/) with access to the model you want to use (default: `claude-opus-4-6`)

**Note on API costs**: Each resume generation makes one Claude API call with your full career docs as context. With Opus, this typically costs $0.20–0.50 per run depending on how detailed your career docs are.

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/resume-builder.git
cd resume-builder

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e "."

# 4. Install Playwright browser (one-time)
playwright install chromium

# 5. Configure environment
cp .env.example .env
# Edit .env — see below
```

Open `.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...   # Your Anthropic API key
CLAUDE_MODEL=claude-opus-4-6   # Or claude-sonnet-4-6 for faster/cheaper runs

CANDIDATE_NAME=Jane Smith
CANDIDATE_EMAIL=jane@example.com
CANDIDATE_PHONE=(555) 123-4567
CANDIDATE_LOCATION=San Francisco, CA
CANDIDATE_LINKEDIN=https://linkedin.com/in/janesmith   # optional
```

Your contact info is injected directly into the resume header — it's never sent to Claude. This keeps your personal details out of the API call.

## Create Your Career Docs

The tool reads two markdown files from the `career_docs/` directory. Example templates are provided to show the expected format:

```bash
# Copy the examples as a starting point
cp career_docs/01-career-timeline.example.md career_docs/01-career-timeline.md
cp career_docs/02-skills-and-achievements.example.md career_docs/02-skills-and-achievements.md
```

Then replace the placeholder content with your own:

**`01-career-timeline.md`** — Your full career history in reverse chronological order. For each role, include company, title, dates, location, and detailed bullet points. Be thorough — include more than you'd put on a single resume. Claude will select the most relevant items for each application.

**`02-skills-and-achievements.md`** — Your technical skills, domain expertise, notable achievements, education, and certifications. This complements the timeline with cross-cutting information that doesn't belong to a single role.

These files are gitignored (they contain personal info), but the `.example.md` templates are tracked so new users can see the expected structure.

## Usage

```bash
# Full workflow: Claude tailors → you review JSON → PDF rendered
python -m resume_builder.cli --jd "paste job description here"

# Or provide job description from a file
python -m resume_builder.cli --jd-file job.txt

# Re-render from an existing JSON draft (skips Claude — useful for editing and layout iteration)
python -m resume_builder.cli --draft drafts/resume_draft_20260219_120000.json

# Output HTML only (open in browser to iterate on layout without Playwright)
python -m resume_builder.cli --jd "..." --html-only

# Specify output path
python -m resume_builder.cli --jd "..." --output ~/Desktop/resume.pdf
```

## The JSON Draft

After Claude runs, it writes a JSON file to `drafts/`. This is the human-in-the-loop step — you can:
- Rewrite or trim any bullet
- Add bullets Claude missed
- Adjust the summary
- Reorder skills categories
- Remove a role entirely

The schema is straightforward and readable in any text editor. Once you confirm, the tool reloads the edited JSON and renders the PDF.

---

## Web App

The web app provides the same workflow through a browser — no terminal required. It supports multiple users, each with their own career docs and profile, and is designed to work well on phones and tablets.

### Web App Quick Start

```bash
# 1. Complete the base setup above (clone, venv, pip install, playwright, .env)
#    For the web app, only ANTHROPIC_API_KEY is required in .env.
#    CANDIDATE_* fields are optional — each user sets their own contact info in the web UI.

# 2. Create a user account
python add_user.py yourname yourpassword

# 3. Start the server
python run_web.py
# → Running on http://0.0.0.0:8000
```

Open `http://localhost:8000` in a browser. You'll be prompted to log in, then:

1. **Profile** — enter your name, email, phone, and location (saved for all future resumes)
2. **My Docs** — paste your career timeline and skills/achievements (pre-filled with example templates on first visit)
3. **Generate** — paste a job description and hit Generate
4. **Review** — edit the summary, skills, and bullet points in a structured form
5. **Download PDF** — tap the button, get your resume

After initial setup, the typical flow is just: paste job description, generate, review, download.

### Adding More Users

```bash
python add_user.py alice alicepassword
python add_user.py bob bobpassword
```

Each user gets isolated storage for their career docs, profile, and generated drafts. Credentials are stored in `users.json` (bcrypt-hashed, gitignored).

---

## Hosting on a VPS (Access from Anywhere)

This section walks through deploying the web app on a Hetzner VPS with a real domain name and HTTPS, so you can access it from your phone, tablet, or any browser.

### What You'll Need

- A Hetzner account (~$4-5/month for the cheapest server)
- A domain name (~$10-15/year)
- About 30 minutes for initial setup

### Step 1: Buy a Domain

1. Go to [Namecheap](https://www.namecheap.com/) or [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) and search for a domain
2. Anything works — e.g., `yourlastname-tools.com`, `smithfamily.dev`, etc.
3. Purchase it (typically $10-15/year for a `.com` or `.dev`)
4. You'll configure DNS later once you have a server IP address

### Step 2: Create a Hetzner Server

1. Sign up at [Hetzner Cloud](https://www.hetzner.com/cloud/)
2. Create a new project, then click **Add Server**
3. Settings:
   - **Location**: Pick the one closest to you
   - **Image**: Ubuntu 24.04
   - **Type**: CX22 (2 vCPU, 4 GB RAM) — the cheapest option that comfortably runs Playwright
   - **SSH Key**: Add your public SSH key (or choose a root password)
4. Click **Create & Buy Now**
5. Note the server's **IP address** (e.g., `65.109.x.x`)

### Step 3: Point Your Domain at the Server

Go back to your domain registrar's DNS settings and add an **A record**:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `resume` | `65.109.x.x` (your server IP) | 300 |

This creates `resume.yourdomain.com`. You can add more subdomains later for other apps:

| Type | Name | Value |
|------|------|-------|
| A | `resume` | `65.109.x.x` |
| A | `photos` | `65.109.x.x` |
| A | `notes` | `65.109.x.x` |

DNS propagation usually takes 5-30 minutes.

### Step 4: Set Up the Server

SSH into your new server and run these commands:

```bash
ssh root@65.109.x.x

# Update system
apt update && apt upgrade -y

# Install Python and dependencies
apt install -y python3.12 python3.12-venv python3-pip git

# Install Caddy (reverse proxy that handles HTTPS automatically)
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy

# Clone your repo
cd /opt
git clone https://github.com/yourusername/resume-builder.git
cd resume-builder

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e "."
playwright install --with-deps chromium

# Configure
cp .env.example .env
nano .env   # Add your ANTHROPIC_API_KEY

# Create user accounts
python add_user.py yourname yourpassword
python add_user.py spouse spousepassword
```

### Step 5: Configure Caddy (HTTPS + Reverse Proxy)

Caddy automatically obtains and renews HTTPS certificates from Let's Encrypt.

```bash
nano /etc/caddy/Caddyfile
```

Replace the contents with:

```
resume.yourdomain.com {
    reverse_proxy localhost:8000
}
```

If you host multiple apps later, just add more blocks:

```
resume.yourdomain.com {
    reverse_proxy localhost:8000
}

other.yourdomain.com {
    reverse_proxy localhost:8001
}
```

Restart Caddy:

```bash
systemctl restart caddy
```

### Step 6: Run the App as a Service

Create a systemd service so the app starts automatically and survives reboots:

```bash
nano /etc/systemd/system/resume-builder.service
```

Paste:

```ini
[Unit]
Description=Resume Builder Web App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/resume-builder
Environment=PATH=/opt/resume-builder/.venv/bin:/usr/bin
ExecStart=/opt/resume-builder/.venv/bin/python run_web.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
systemctl enable resume-builder
systemctl start resume-builder
```

### Step 7: Verify

1. Open `https://resume.yourdomain.com` on your phone or tablet
2. You should see a login prompt — enter the credentials you created
3. Set up your profile and career docs, then try generating a resume

### Deploying New Code

Deployments use GitHub as the source of truth.

```bash
# From your local clone: push current branch, then deploy that branch
./deploy.sh

# Deploy a specific branch
./deploy.sh main

# Skip local push (useful in CI/CD where code is already on GitHub)
SKIP_PUSH=1 ./deploy.sh main
```

`./deploy.sh` SSHes to the server and runs:

```bash
bash /opt/resume-builder/deploy/server-deploy.sh main
```

### GitHub Actions Auto Deploy

`.github/workflows/deploy.yml` deploys automatically on pushes to `main` (and supports manual runs).

Required repository secrets:
- `VPS_HOST` (example: `5.78.109.38`)
- `VPS_USER` (example: `root`)
- `VPS_SSH_KEY` (private key content used by Actions)

One-time key setup:
```bash
# local machine
ssh-keygen -t ed25519 -f ~/.ssh/github-actions-hetzner -C "github-actions-deploy"

# server
cat ~/.ssh/github-actions-hetzner.pub | ssh root@5.78.109.38 'cat >> /root/.ssh/authorized_keys'
```
Then paste `~/.ssh/github-actions-hetzner` (private key) into the `VPS_SSH_KEY` secret.

### Useful Commands

```bash
# Check if the app is running
systemctl status resume-builder

# View logs
journalctl -u resume-builder -f

# Deploy latest main directly on server
bash /opt/resume-builder/deploy/server-deploy.sh main

# Add a new user
cd /opt/resume-builder && source .venv/bin/activate && python add_user.py newuser password
```

### Security Notes

- Basic Auth credentials are sent with every request — Caddy's automatic HTTPS ensures they're encrypted in transit
- The server is only accessible via HTTPS (Caddy redirects HTTP automatically)
- Your Anthropic API key lives in `.env` on the server, never exposed to browsers
- `users.json` stores bcrypt-hashed passwords, not plaintext
- For additional hardening, consider setting up [UFW firewall rules](https://www.digitalocean.com/community/tutorials/how-to-set-up-a-firewall-with-ufw-on-ubuntu) to only allow ports 22, 80, and 443

---

## Customization

**Visual style**: Edit `templates/resume.html.j2`. The template uses print-optimized CSS. Use `--html-only` to iterate quickly in your browser without running Playwright.

**Claude's selection behavior**: Edit `resume_builder/prompts/system.txt` to change how Claude picks bullets, writes summaries, or handles relevance.

**Claude model**: Set `CLAUDE_MODEL` in `.env` to use a different model (e.g. `claude-sonnet-4-6` for faster/cheaper runs).

## Project Structure

```
resume-builder/
├── career_docs/                  # Your career history (personal files gitignored)
│   ├── 01-career-timeline.example.md
│   └── 02-skills-and-achievements.example.md
├── resume_builder/
│   ├── cli.py                    # CLI entry point
│   ├── tailor.py                 # Claude API call + JSON validation
│   ├── schema.py                 # Pydantic models (resume data contract)
│   ├── renderer.py               # Jinja2 → HTML
│   ├── exporter.py               # Playwright HTML → PDF
│   ├── config.py                 # Settings from .env
│   └── prompts/
│       ├── system.txt            # Claude system prompt
│       └── user_template.txt     # User message template
├── web_app/
│   ├── app.py                    # FastAPI web app (all routes)
│   ├── auth.py                   # HTTP Basic Auth
│   ├── user_data.py              # Per-user profile and career docs
│   └── templates/                # Mobile-first HTML templates
├── templates/
│   └── resume.html.j2            # Resume HTML/CSS template
├── add_user.py                   # Helper to create web app users
├── run_web.py                    # Web app entry point (uvicorn)
├── drafts/                       # Generated JSON drafts (gitignored)
└── output/                       # Generated PDFs (gitignored)
```

## License

[MIT](LICENSE)
