#!/usr/bin/env python3
"""
Dictator of the Day - Daily email about history's most fascinating authoritarian rulers.
Calls the Anthropic API to generate content, then sends via Gmail.

Setup: See README.md
"""

import anthropic
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

# ---------------------------------------------------------------------------
# CONFIGURATION — set these as environment variables (see README)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GMAIL_ADDRESS     = os.environ["GMAIL_ADDRESS"]       # your gmail address
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"] # gmail app password (not your real password)
RECIPIENT_EMAIL   = os.environ.get("RECIPIENT_EMAIL", GMAIL_ADDRESS)  # defaults to sender


# ---------------------------------------------------------------------------
# PROMPT
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the author of a darkly witty, deeply researched daily newsletter 
called "Dictator of the Day." Your job is to write a short, engaging email about one 
authoritarian ruler — sometimes a household name, often a gloriously obscure one. 

Tone: Think of a brilliant history professor who also writes for The Onion. Sharp, 
informative, occasionally deadpan, never preachy. You're not excusing anything these 
people did — you're illuminating how strange, human, and absurd power can be.

Format your response as valid HTML for an email. Use this structure:

<h2>[RULER NAME] ([YEARS IN POWER])</h2>
<h3>[Country] — [One-line hook/subtitle]</h3>

<p><strong>The Basics:</strong> 2-3 sentences on who they were and how they came to power.</p>

<p><strong>The Signature Move:</strong> Their most famous or infamous policy, action, or personality quirk. 
This is the meaty paragraph — go deep on one specific thing rather than listing everything.</p>

<p><strong>The Absurd Detail:</strong> One specific, almost unbelievable fact that captures their 
particular flavor of delusion or grandiosity. The weirder the better.</p>

<p><strong>The Legacy:</strong> 1-2 sentences. What did they leave behind? Are they still 
celebrated somewhere? Is there a museum? A holiday?</p>

<p><em>Obscurity Rating: [X/10]</em> — where 1 is Hitler and 10 is someone only a Central Asian 
history PhD would recognize. Aim for a mix across emails — don't always do famous ones.</p>

Rules:
- Vary your picks widely: geography, era, gender, style of authoritarianism
- Prioritize specific, verifiable facts over vague claims
- Roughly 1 in 3 should be genuinely obscure (Obscurity Rating 6+)
- Don't repeat leaders (though you have no memory of past emails, just avoid the obvious ones)
- Keep the whole thing under 400 words
- Return ONLY the HTML content — no markdown, no code blocks, no preamble"""

USER_PROMPT = f"""Today is {date.today().strftime('%A, %B %d, %Y')}. 
Write today's Dictator of the Day email. Pick whoever you find most interesting today."""


# ---------------------------------------------------------------------------
# GENERATE CONTENT
# ---------------------------------------------------------------------------
def generate_email_content() -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    message = client.messages.create(
        model="claude-opus-4-6",  # Using Opus for best historical knowledge
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT}]
    )
    
    return message.content[0].text


# ---------------------------------------------------------------------------
# SEND EMAIL
# ---------------------------------------------------------------------------
def send_email(html_content: str):
    today = date.today().strftime("%B %d, %Y")
    subject = f"Dictator of the Day — {today}"
    
    # Wrap in full HTML email template
    full_html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Georgia, serif;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f5f0;
                color: #2c2c2c;
                line-height: 1.7;
            }}
            h2 {{
                color: #8b0000;
                border-bottom: 2px solid #8b0000;
                padding-bottom: 8px;
                margin-top: 0;
            }}
            h3 {{
                color: #555;
                font-style: italic;
                margin-top: -10px;
                font-weight: normal;
            }}
            p {{ margin-bottom: 16px; }}
            em {{ color: #777; font-size: 0.9em; }}
            .footer {{
                margin-top: 40px;
                padding-top: 16px;
                border-top: 1px solid #ccc;
                font-size: 0.8em;
                color: #999;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        {html_content}
        <div class="footer">
            Dictator of the Day · Unsubscribe by turning off your cron job
        </div>
    </body>
    </html>
    """
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = RECIPIENT_EMAIL
    
    msg.attach(MIMEText(full_html, "html"))
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())
    
    print(f"✓ Email sent: {subject}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Generating content...")
    content = generate_email_content()
    print("Sending email...")
    send_email(content)
    print("Done.")
