from pyrogram import Client
from flask import Flask, jsonify, request
from database import Database
import config
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

class FileShareBot(Client):
    def __init__(self):
        """Initialize the Telegram bot with API credentials and database connection."""
        super().__init__(
            name="FileShareBot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            plugins=dict(root="handlers")
        )
        self.db = Database()
        self._is_running = False
        logger.info("Bot Initialized!")

    def start(self):
        """Start the bot and connect to Telegram."""
        if not self._is_running:
            super().start()
            self._is_running = True
            me = self.get_me()
            logger.info(f"Bot Started as {me.first_name}")
            logger.info(f"Username: @{me.username}")
            logger.info("Bot is ready to handle updates!")

            # Initialize database connection
            try:
                self.db = Database()
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Database connection failed: {str(e)}")
                raise

    def stop(self):
        """Stop the bot gracefully."""
        if self._is_running:
            super().stop()
            self._is_running = False
            logger.info("Bot Stopped")

    def process_update(self, update):
        """Handle updates received via webhook."""
        try:
            self.loop.create_task(self.dispatcher.updates_handler(update))  # Process update asynchronously
            logger.info(f"Processed update: {update}")
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}")

# Initialize bot as a global variable
bot = FileShareBot()

@app.route('/')
def home():
    """Basic route for health check."""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "service": "AlphaShare Bot"
    })

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming updates from Telegram via webhook."""
    try:
        if not request.is_json:
            logger.warning("Received non-JSON request")
            return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

        update_data = request.get_json()

        # Log the incoming update (excluding sensitive data)
        logger.info(f"Received update type: {update_data.get('message', {}).get('text', 'No text')}")

        try:
            # Process the update
            bot.invoke_update(update_data)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}")
            return jsonify({
                "status": "error",
                "message": "Failed to process update",
                "error": str(e)
            }), 500

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

def run_flask():
    """Run the Flask application."""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    try:
        # Start the bot
        bot.start()

        # Run the Flask app
        run_flask()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot.stop()
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}")
        bot.stop()
        raise
