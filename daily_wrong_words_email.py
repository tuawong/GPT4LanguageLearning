"""
Send a daily email digest of top pinyin and meaning error words.

Uses the exact same logic as the visualization dashboard:
- Groups by Word
- Filters by Quiz Attempts > 1 and error count >= 1
- Ranks by error percentage, then by error count
- Returns top 20 for each error type

Environment variables:
- EMAIL_SMTP_HOST: SMTP server host (e.g. smtp.gmail.com)
- EMAIL_SMTP_PORT: SMTP server port (typically 587)
- EMAIL_USER: sender username/email
- EMAIL_APP_PASSWORD: SMTP password or app password
- EMAIL_TO: recipient email (defaults to EMAIL_USER if omitted)

Usage examples:
- Dry run (print tables instead of sending email):
  python daily_wrong_words_email.py --dry-run
- Real send:
  python daily_wrong_words_email.py
- Custom top N:
  python daily_wrong_words_email.py --top-n 30 --dry-run
"""

from __future__ import annotations

import argparse
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from main.sql import load_dict
from main.visualizations import prepare_df

# Load .env from repo root
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)


DEFAULT_TOP_N = 20


def _format_word_cell(word: object) -> str:
    """Render Chinese words larger in the HTML email tables."""
    return f"<span style='font-size: 2em;'>{word}</span>"


def fetch_top_pinyin_errors(df: pd.DataFrame, top_n: int = DEFAULT_TOP_N) -> pd.DataFrame:
    """Return top pinyin error words (same logic as visualization dashboard)."""
    work = df.copy()
    
    # Group by Word, aggregate pinyin errors
    top_pinyin = work.groupby('Word').agg({
        'Num Pinyin Wrong': 'sum',
        'Quiz Attempts': 'sum',
        'Pinyin': 'first',
        'Meaning': 'first'
    }).reset_index()
    
    # Filter: only words with > 1 attempt
    top_pinyin = top_pinyin[top_pinyin['Quiz Attempts'] > 1]
    
    # Calculate error percentage
    top_pinyin['Pinyin Wrong %'] = (
        top_pinyin['Num Pinyin Wrong'] / top_pinyin['Quiz Attempts'] * 100
    ).round(1)
    
    # Filter: at least 1 wrong
    top_pinyin = top_pinyin[top_pinyin['Num Pinyin Wrong'] >= 1]
    
    # Sort by percentage desc, then by count desc
    top_pinyin = top_pinyin.sort_values(
        by=['Pinyin Wrong %', 'Num Pinyin Wrong'],
        ascending=[False, False]
    ).head(top_n)
    
    return top_pinyin[['Word', 'Pinyin', 'Meaning', 'Num Pinyin Wrong', 'Quiz Attempts', 'Pinyin Wrong %']]


def fetch_top_meaning_errors(df: pd.DataFrame, top_n: int = DEFAULT_TOP_N) -> pd.DataFrame:
    """Return top meaning error words (same logic as visualization dashboard)."""
    work = df.copy()
    
    # Group by Word, aggregate meaning errors
    top_meaning = work.groupby('Word').agg({
        'Num Meaning Wrong': 'sum',
        'Quiz Attempts': 'sum',
        'Pinyin': 'first',
        'Meaning': 'first'
    }).reset_index()
    
    # Filter: only words with > 1 attempt
    top_meaning = top_meaning[top_meaning['Quiz Attempts'] > 1]
    
    # Calculate error percentage
    top_meaning['Meaning Wrong %'] = (
        top_meaning['Num Meaning Wrong'] / top_meaning['Quiz Attempts'] * 100
    ).round(1)
    
    # Filter: at least 1 wrong
    top_meaning = top_meaning[top_meaning['Num Meaning Wrong'] >= 1]
    
    # Sort by percentage desc, then by count desc
    top_meaning = top_meaning.sort_values(
        by=['Meaning Wrong %', 'Num Meaning Wrong'],
        ascending=[False, False]
    ).head(top_n)
    
    return top_meaning[['Word', 'Pinyin', 'Meaning', 'Num Meaning Wrong', 'Quiz Attempts', 'Meaning Wrong %']]


def _build_html_body(pinyin_df: pd.DataFrame, meaning_df: pd.DataFrame) -> str:
    """Build HTML email with two error tables."""
    html_parts = ["<html><body>"]
    
    # Pinyin errors table
    html_parts.append("<h2>Top 20 Pinyin Errors</h2>")
    if pinyin_df.empty:
        html_parts.append("<p>No pinyin errors found.</p>")
    else:
        display_cols = ['Word', 'Pinyin', 'Meaning', 'Num Pinyin Wrong', 'Quiz Attempts', 'Pinyin Wrong %']
        pinyin_table = pinyin_df[display_cols].to_html(
            index=False,
            border=1,
            escape=False,
            formatters={'Word': _format_word_cell},
        )
        html_parts.append(pinyin_table)
    
    html_parts.append("<hr style='margin-top: 40px; margin-bottom: 40px;'>")
    
    # Meaning errors table
    html_parts.append("<h2>Top 20 Meaning Errors</h2>")
    if meaning_df.empty:
        html_parts.append("<p>No meaning errors found.</p>")
    else:
        display_cols = ['Word', 'Pinyin', 'Meaning', 'Num Meaning Wrong', 'Quiz Attempts', 'Meaning Wrong %']
        meaning_table = meaning_df[display_cols].to_html(
            index=False,
            border=1,
            escape=False,
            formatters={'Word': _format_word_cell},
        )
        html_parts.append(meaning_table)
    
    html_parts.append("</body></html>")
    return "".join(html_parts)


def send_email(subject: str, html_body: str) -> None:
    """Send the email using SMTP settings in environment variables."""
    smtp_host = os.getenv("EMAIL_SMTP_HOST", "").strip('"')
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587").strip('"'))
    email_user = os.getenv("EMAIL_USER", "").strip('"')
    email_password = os.getenv("EMAIL_APP_PASSWORD", "").strip('"')
    email_to = os.getenv("EMAIL_TO", email_user).strip('"')

    missing = [
        k
        for k, v in {
            "EMAIL_SMTP_HOST": smtp_host,
            "EMAIL_USER": email_user,
            "EMAIL_APP_PASSWORD": email_password,
            "EMAIL_TO": email_to,
        }.items()
        if not v
    ]
    if missing:
        raise RuntimeError(f"Missing environment variable(s): {', '.join(missing)}")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_user
    msg["To"] = email_to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(email_user, email_password)
        server.sendmail(email_user, [email_to], msg.as_string())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily top wrong words email sender")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Number of words to include (default 20)")
    parser.add_argument("--dry-run", action="store_true", help="Print output without sending email")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Load dictionary and prepare data (same as dashboard)
    df = load_dict()
    df = prepare_df(df)
    
    # Get top errors for both pinyin and meaning
    pinyin_df = fetch_top_pinyin_errors(df, top_n=args.top_n)
    meaning_df = fetch_top_meaning_errors(df, top_n=args.top_n)

    subject = "Mandarin Top Wrong Words Digest"
    html_body = _build_html_body(pinyin_df, meaning_df)

    if args.dry_run:
        print(f"Subject: {subject}\n")
        print("=" * 100)
        print("TOP 20 PINYIN ERRORS")
        print("=" * 100)
        if pinyin_df.empty:
            print("No pinyin errors found.")
        else:
            print(pinyin_df.to_string(index=False))
        print("\n" + "=" * 100)
        print("TOP 20 MEANING ERRORS")
        print("=" * 100)
        if meaning_df.empty:
            print("No meaning errors found.")
        else:
            print(meaning_df.to_string(index=False))
        return

    send_email(subject=subject, html_body=html_body)
    print(f"Email sent successfully with {len(pinyin_df)} pinyin errors and {len(meaning_df)} meaning errors.")


if __name__ == "__main__":
    main()
