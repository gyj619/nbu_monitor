# NBU Monitor - NBU Graduate School Notification Monitor

Automatically monitor NBU graduate school notification page and send email alerts when new notifications are detected.

Target: https://graduate.nbu.edu.cn/zsgz/ssszs.htm

## Features

- Auto-fetch notification page from NBU graduate school website
- MD5 hash-based incremental change detection, no duplicates
- Email alerts via QQ SMTP with HTML formatted content
- Runs on GitHub Actions every 30 minutes (cron schedule)
- Persists notification state via pickle plus git auto-commit
- First run silently records state, no email sent

## How It Works

1. GitHub Actions cron triggers nbu.py every 30 minutes
2. Script fetches the target webpage via requests library
3. Parses HTML with BeautifulSoup, extracts notifications
4. Computes MD5 hash for each notification (title plus url)
5. Compares current hashes with saved state in nbu_state.pkl
6. New unseen hashes trigger an HTML email alert via QQ SMTP
7. Updated state is git-committed back to the repository

## Project Structure

nbu_monitor/
  nbu.py              - Main monitoring script
  nbu_state.pkl       - Persisted notification hash state
  requirements.txt    - Python dependencies
  .github/workflows/
    nbu_monitor.yml   - GitHub Actions workflow
  README.md           - This file

## Prerequisites

### 1. Get QQ Email SMTP Authorization Code

1. Log in to QQ Mail, go to Settings - Account
2. Enable POP3/SMTP service
3. Generate an authorization code (NOT your QQ password)

### 2. Configure GitHub Secrets

Go to your repo: Settings - Secrets and variables - Actions

Add a secret named EMAIL_PASS with the SMTP authorization code.

### 3. Clone the Repository

    git clone https://github.com/gyj619/nbu_monitor.git
    cd nbu_monitor
    pip install -r requirements.txt

## Custom Configuration

Edit the main() function in nbu.py:

    target_url = "https://graduate.nbu.edu.cn/zsgz/ssszs.htm"
    email_to = "your-email@example.com"

To change SMTP server, modify email_config in NBUMonitor:

    smtp_server: smtp.qq.com (default, port 587 with TLS)
    sender_email: your-sender@qq.com
    sender_password: read from env var EMAIL_PASS

## GitHub Actions Workflow

The workflow is at .github/workflows/nbu_monitor.yml:

- Schedule: runs every 30 minutes (cron: */30 * * * *)
- Manual trigger: supports workflow_dispatch
- Environment: Ubuntu latest plus Python 3.10
- Permission: contents: write (to commit state file back)

## Tech Stack

- requests - HTTP requests and web scraping
- beautifulsoup4 - HTML parsing and notification extraction
- smtplib / email - Build and send HTML-formatted emails
- hashlib - MD5 hash for change detection
- pickle - Local state persistence
- GitHub Actions - Scheduled automation and execution

## Local Testing

Linux/macOS:
    EMAIL_PASS=your_smtp_code python nbu.py

Windows (cmd):
    set EMAIL_PASS=your_smtp_code
    python nbu.py

Windows (PowerShell):
    $env:EMAIL_PASS="your_smtp_code"
    python nbu.py

First run: silently records existing notifications, no email.
Subsequent runs: detects new notifications and sends alerts.

## Notes

- EMAIL_PASS is the SMTP authorization code, not your QQ password
- The state file nbu_state.pkl is auto-managed via git
- Delete nbu_state.pkl if you change the target URL to rebuild state
- Ensure GitHub Actions has contents: write permission enabled

## License

MIT License

---

Built for learning purposes. If the NBU website structure changes, please open an issue.