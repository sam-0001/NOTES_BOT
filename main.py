# main.py
# This version is designed for web hosting platforms like Railway.

import asyncio
import os
import uvicorn
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    DictPersistence,
)

# Local imports
import config
import handlers as h

# --- Bot and Web Server Setup ---
# Use DictPersistence for in-memory storage, as servers have ephemeral filesystems.
persistence = DictPersistence()

application = (
    Application.builder()
    .token(config.TELEGRAM_BOT_TOKEN)
    .persistence(persistence)
    .build()
)

# Create a FastAPI web server instance
app = FastAPI(docs_url=None, redoc_url=None) # Disabling docs for security

# --- Main Bot Logic ---
async def main_setup() -> None:
    """Initializes the bot and its handlers."""
    # Conversation Handler for Setup
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", h.start)],
        states={
            config.ASK_YEAR: [MessageHandler(filters.Regex(r"^(1st|2nd|3rd|4th) Year$"), h.received_year)],
            config.ASK_BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, h.received_branch)],
            config.ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, h.received_name)],
        },
        fallbacks=[CommandHandler("start", h.start)],
        persistent=False,
        name="setup_conversation"
    )

    # Add all handlers to the application
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", h.help_command))
    application.add_handler(CommandHandler("myinfo", h.myinfo_command))
    application.add_handler(CommandHandler("reset", h.reset_command))
    application.add_handler(CommandHandler("notes", h.file_selection_command))
    application.add_handler(CommandHandler("assignments", h.file_selection_command))
    application.add_handler(CallbackQueryHandler(h.button_handler))

    # Initialize the application
    await application.initialize()
    # Start the background tasks
    await application.start()

    # Set the webhook using the environment variable provided by Railway
    webhook_url = f"https://{os.getenv('RAILWAY_STATIC_URL')}/webhook"
    await application.bot.set_webhook(url=webhook_url)

# --- Webhook Endpoint ---
@app.post("/webhook")
async def webhook(request: Request) -> None:
    """Handles incoming updates from Telegram."""
    try:
        update_data = await request.json()
        update = Update.de_json(data=update_data, bot=application.bot)
        await application.process_update(update)
    except Exception as e:
        config.logger.error(f"Error processing update: {e}")

# --- Server Lifecycle ---
@app.on_event("startup")
async def on_startup():
    """Runs the bot initialization when the server starts."""
    await main_setup()

@app.on_event("shutdown")
async def on_shutdown():
    """Stops the bot gracefully when the server shuts down."""
    await application.stop()
