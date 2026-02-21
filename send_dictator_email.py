#!/usr/bin/env python3
"""
Dictator of the Day - Daily email about history's most fascinating authoritarian rulers.
Calls the Anthropic API to generate content, generates a continent map, sends via Gmail.
"""

import anthropic
import smtplib
import os
import json
import io
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import geopandas as gpd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import date

# ---------------------------------------------------------------------------
# CONFIGURATION — set these as GitHub Actions secrets
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL    = os.environ.get("RECIPIENT_EMAIL", GMAIL_ADDRESS)


# ---------------------------------------------------------------------------
# PROMPT
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are the author of a darkly witty, deeply researched daily newsletter 
called "Dictator of the Day." Your job is to write a short, engaging email about one 
authoritarian ruler — sometimes a household name, often a gloriously obscure one. 

Tone: Think of a brilliant history professor who also writes for The Onion. Sharp, 
informative, occasionally deadpan, never preachy. You're not excusing anything these 
people did — you're illuminating how strange, human, and absurd power can be.

Format your response as a JSON object with these exact keys:
{
  "ruler_name": "just the ruler's name, e.g. 'Francisco Macías Nguema'",
  "country": "exact modern country name as it appears in world geographic data (e.g. 'Equatorial Guinea', 'North Korea')",
  "continent": "one of: Africa, Asia, Europe, North America, South America, Oceania",
  "wikipedia_url": "the Wikipedia URL for this specific ruler (e.g. https://en.wikipedia.org/wiki/Francisco_Maci%C3%A1s_Nguema)",
  "html": "the full email HTML content as a string"
}

The HTML content should use this structure:

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
- Keep the HTML content under 400 words
- Return ONLY the raw JSON object — no markdown, no code blocks, no preamble"""

USER_PROMPT = f"""Today is {date.today().strftime('%A, %B %d, %Y')}. 
Write today's Dictator of the Day email. Pick whoever you find most interesting today."""


# ---------------------------------------------------------------------------
# GENERATE CONTENT
# ---------------------------------------------------------------------------
def generate_email_content() -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT}]
    )
    
    raw = message.content[0].text.strip()
    # Strip markdown code fences if Claude adds them anyway
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    
    return json.loads(raw)


# ---------------------------------------------------------------------------
# GENERATE MAP
# ---------------------------------------------------------------------------
def generate_continent_map(country_name: str, continent: str) -> bytes:
    """
    Returns PNG bytes of a continent map with the target country highlighted.
    Uses Natural Earth data bundled with geopandas.
    """
    world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))

    continent_map = {
        "North America": "North America",
        "South America": "South America",
        "Europe": "Europe",
        "Africa": "Africa",
        "Asia": "Asia",
        "Oceania": "Oceania",
    }
    gpd_continent = continent_map.get(continent, continent)

    continent_gdf = world[world["continent"] == gpd_continent].copy()

    # Match country name flexibly
    continent_gdf["_match"] = continent_gdf["name"].apply(
        lambda n: country_name.lower() in n.lower() or n.lower() in country_name.lower()
    )
    matched = continent_gdf["_match"]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_facecolor("#d6eaf8")  # Ocean blue
    fig.patch.set_facecolor("#f9f5f0")

    continent_gdf[~matched].plot(
        ax=ax, color="#c8d6c8", edgecolor="#888888", linewidth=0.5,
    )
    if matched.any():
        continent_gdf[matched].plot(
            ax=ax, color="#8b0000", edgecolor="#444444", linewidth=0.8,
        )

    ax.set_axis_off()
    plt.title(country_name, fontsize=11, color="#2c2c2c", pad=8, fontfamily="serif")
    plt.tight_layout(pad=0.5)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# SEND EMAIL
# ---------------------------------------------------------------------------
def send_email(data: dict, map_png: bytes):
    today = date.today().strftime("%B %d, %Y")
    subject = f"{data['ruler_name']} — {today}"

    html_content = data["html"]
    wikipedia_url = data.get("wikipedia_url", "")

    wiki_link = ""
    if wikipedia_url:
        wiki_link = f'<p style="margin-top: 20px;"><a href="{wikipedia_url}" style="color: #8b0000;">→ Read more on Wikipedia</a></p>'

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
            h2 {{ color: #8b0000; border-bottom: 2px solid #8b0000; padding-bottom: 8px; margin-top: 0; }}
            h3 {{ color: #555; font-style: italic; margin-top: -10px; font-weight: normal; }}
            p {{ margin-bottom: 16px; }}
            em {{ color: #777; font-size: 0.9em; }}
            .map-container {{ text-align: center; margin: 20px 0; }}
            .map-container img {{ max-width: 100%; border-radius: 6px; border: 1px solid #ccc; }}
            a {{ color: #8b0000; }}
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
        {wiki_link}
        <div class="map-container">
            <img src="cid:continent_map" alt="Map of {data.get('country', '')}" />
        </div>
        <div class="footer">
            Dictator of the Day · Powered by Claude
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = f"Dictator of the Day <{GMAIL_ADDRESS}>"
    msg["To"]      = RECIPIENT_EMAIL

    msg.attach(MIMEText(full_html, "html"))

    img = MIMEImage(map_png, _subtype="png")
    img.add_header("Content-ID", "<continent_map>")
    img.add_header("Content-Disposition", "inline", filename="map.png")
    msg.attach(img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())

    print(f"✓ Email sent: {subject}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Generating content...")
    data = generate_email_content()
    print(f"  → {data.get('country')} ({data.get('continent')})")

    print("Generating map...")
    map_png = generate_continent_map(data["country"], data["continent"])

    print("Sending email...")
    send_email(data, map_png)
    print("Done.")
