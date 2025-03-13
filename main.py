from pyrogram import Client, idle
from flask import Flask, jsonify, request
from database import Database
from pyrogram.types import Update
import config
import asyncio
import os
import json
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

    async def start(self):
        """Start the bot and set up necessary configurations"""
        if not self._is_running:
            await super().start()
            self._is_running = True
            me = await self.get_me()
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

    async def stop(self):
        """Stop the bot gracefully"""
        if self._is_running:
            await super().stop()
            self._is_running = False
            logger.info("Bot Stopped")

# Initialize bot as a global variable
bot = FileShareBot()

@app.route('/')
def home():
    """Basic route for health check"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "service": "AlphaShare Bot"
    })

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }), 200

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Handle incoming updates from Telegram"""
    try:
        if not request.is_json:
            logger.warning("Received non-JSON request")
            return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400

        update_data = request.get_json()
        
        # Log the incoming update (excluding sensitive data)
        logger.info(f"Received update type: {update_data.get('message', {}).get('text', 'No text')}")

        try:
            # Process the update
            update = Update.parse_obj(update_data)
            await bot.process_update(update)
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

async def start_bot():
    """Start the bot and keep it running"""
    try:
        await bot.start()
        logger.info("Bot started successfully")
        
        # If running locally, use polling
        if os.environ.get('ENVIRONMENT') == 'local':
            logger.info("Running in local environment, starting polling...")
            await idle()
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        raise

def run_flask():
    """Run the Flask application"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    try:
        # Set up event loop policy for Windows if needed
        if os.name == 'nt':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Determine the environment
        is_production = os.environ.get('ENVIRONMENT') == 'production'
        
        if is_production:
            # In production (Vercel), run only the Flask app
            logger.info("Starting in production mode (webhook)")
            run_flask()
        else:
            # In development, run both bot and Flask app
            logger.info("Starting in development mode")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(start_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}")
        raise
