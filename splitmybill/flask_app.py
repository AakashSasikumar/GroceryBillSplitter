import os

from flask import Flask, request

from splitmybill.interface.telegram_bot import TelegramSplitter

app = Flask(__name__)

# Initialize bot instance
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
bot = TelegramSplitter(token=TOKEN, api_key=ANTHROPIC_KEY)


@app.route("/")
def index():
    return "SplitMyBill Telegram Bot Webhook Server"

@app.route(f"/{TOKEN}", methods=["POST"])
async def telegram_webhook():
    """Handle incoming telegram webhook updates."""
    if request.headers.get("content-type") == "application/json":
        update = request.get_json()
        # Convert the JSON to a Telegram Update object
        await bot.application.process_update(update)
        return "ok"
    return "error"


if __name__ == "__main__":
    # Set the webhook URL when starting the server
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g., https://your-domain.com
    if WEBHOOK_URL:
        bot.application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

    # Run the Flask app
    app.run(host="0.0.0.0", port=8443, ssl_context=None)  # Set ssl_context if using HTTPS