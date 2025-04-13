import logging
import asyncio
from telegram import Update, BotCommand, InputMediaPhoto, InputFile,constants
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    Defaults,
    filters,
)
from telegram.constants import ParseMode
import io

# Import configuration, user management, and AI processing logic
import config
import user_management
import ai_processing

# --- Bot Configuration ---
logger = logging.getLogger(__name__)
defaults = Defaults(parse_mode=ParseMode.HTML, disable_web_page_preview=True)

# --- Helper Functions ---
def is_admin(user_id: int) -> bool:
    """Check if a user ID belongs to an admin."""
    return user_id in config.ADMIN_USER_IDS

# --- Command Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    user_id = user.id
    logger.info(f"User {user_id} ({user.username}) started the bot.")

    status = user_management.get_user_status(user_id)
    welcome_message = f"Welcome {user.mention_html()}!\n\n"
    welcome_message += "I can apply AI transformations to your photos.\n\n"

    if is_admin(user_id):
        welcome_message += "You are an <b>Admin</b>. Use /adminhelp for admin commands.\n"
    elif user_management.has_access(user_id):
        welcome_message += "You have <b>approved access</b>. Send me a photo to transform!\n"
    elif user_management.has_used_trial(user_id):
        welcome_message += "You have used your one-time trial. Use /request_access to ask for full access.\n"
    else:
        welcome_message += "You have a <b>one-time trial</b>. Send me a photo to try it out!\n"

    welcome_message += "\nUse /help for more info."
    await update.message.reply_html(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command."""
    user_id = update.effective_user.id
    help_text = """
<b>How to use the bot:</b>
1.  Send me a photo you want to transform.
2.  I will apply an AI filter (e.g., Anime style).

<b>Access:</b>
- New users get a one-time free trial.
- After the trial, use /request_access to ask an admin for full access.

<b>Commands:</b>
/start - Check your status and welcome message.
/help - Show this help message.
/request_access - Ask admin for full access (after trial).
/status - Check your current access status.
"""
    if is_admin(user_id):
        help_text += "\nUse /adminhelp for admin-specific commands."

    await update.message.reply_html(help_text)

async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /adminhelp command."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use admin commands.")
        return

    admin_help = """
<b>Admin Commands:</b>
/approve `user_id` - Grant full access to a user.
/block `user_id` - Revoke access for a user.
/pending - List users waiting for approval.
/status `user_id` - Check a specific user's status.
/broadcast `message` - Send a message to all approved users (Use with caution!).
/toggle_nsfw - Enable/Disable NSFW content generation (Current: {}).
/send_message `user_id` `message` - Send a custom message to a specific user.
""".format("Enabled" if ai_processing.get_nsfw_mode() else "Disabled")
    await update.message.reply_html(admin_help)


async def request_access_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /request_access command."""
    user = update.effective_user
    user_id = user.id

    if user_management.has_access(user_id):
        await update.message.reply_text("You already have approved access.")
        return
    if not user_management.has_used_trial(user_id):
         await update.message.reply_text("You can still use your free trial. Send a photo first!")
         return

    if user_management.request_access(user_id):
        await update.message.reply_text("Your request for access has been sent to the admins.")
        # Notify admins
        notification = f"❗️ Access Request: User {user.mention_html()} (ID: <code>{user_id}</code>) has requested access."
        for admin_id in config.ADMIN_USER_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=notification, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.error(f"Failed to send access request notification to admin {admin_id}: {e}")
    else:
        # This case should ideally not happen if checks above are correct, but good to handle
        await update.message.reply_text("Could not process your request. You might already have access or a pending request.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /status command (also admin version)."""
    user_id_to_check = update.effective_user.id
    requester_id = update.effective_user.id

    # Admin checking specific user
    if is_admin(requester_id) and context.args:
        try:
            user_id_to_check = int(context.args[0])
            user_info = f"Status for User ID <code>{user_id_to_check}</code>:\n"
        except (IndexError, ValueError):
            await update.message.reply_text("Usage: /status [user_id] (optional, admin only)")
            return
    # Regular user checking self
    else:
        user_info = "Your status:\n"


    status_str = user_management.get_user_status(user_id_to_check)
    await update.message.reply_html(f"{user_info}<b>{status_str}</b>")

# --- Admin Command Handlers ---

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to approve a user."""
    if not is_admin(update.effective_user.id): return

    try:
        user_id_to_approve = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /approve <user_id>")
        return

    user_management.approve_user(user_id_to_approve)
    await update.message.reply_text(f"User {user_id_to_approve} has been approved.")

    # Notify the user
    try:
        await context.bot.send_message(
            chat_id=user_id_to_approve,
            text="✅ Your access request has been approved! You can now use the bot freely."
        )
    except Exception as e:
        logger.error(f"Failed to send approval notification to user {user_id_to_approve}: {e}")

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to block (revoke approval) a user."""
    if not is_admin(update.effective_user.id): return

    try:
        user_id_to_block = int(context.args[0])
        if user_id_to_block in config.ADMIN_USER_IDS:
             await update.message.reply_text("Cannot block an admin.")
             return
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /block <user_id>")
        return

    user_management.block_user(user_id_to_block)
    await update.message.reply_text(f"User {user_id_to_block} has been blocked.")
     # Notify the user
    try:
        await context.bot.send_message(
            chat_id=user_id_to_block,
            text="❌ Your access to the bot has been revoked by an admin."
        )
    except Exception as e:
        logger.error(f"Failed to send block notification to user {user_id_to_block}: {e}")

async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list pending access requests."""
    if not is_admin(update.effective_user.id): return

    pending_ids = user_management.get_pending_requests()
    if not pending_ids:
        await update.message.reply_text("No pending access requests.")
        return

    message = "<b>Pending Approval Requests:</b>\n"
    for user_id in pending_ids:
        # Try to get user info for better display (might fail if user blocked bot etc)
        try:
            user = await context.bot.get_chat(user_id)
            message += f"- {user.mention_html()} (ID: <code>{user_id}</code>)\n"
        except Exception:
             message += f"- User ID: <code>{user_id}</code> (Could not fetch details)\n"

    await update.message.reply_html(message)


async def toggle_nsfw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to toggle NSFW mode."""
    if not is_admin(update.effective_user.id): return

    current_mode = ai_processing.get_nsfw_mode()
    ai_processing.set_nsfw_mode(not current_mode)
    new_mode_str = "ENABLED" if not current_mode else "DISABLED"
    await update.message.reply_text(f"AI NSFW Generation Mode is now {new_mode_str}.")


async def send_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to send a message to a specific user."""
    if not is_admin(update.effective_user.id): return

    try:
        target_user_id = int(context.args[0])
        message_text = update.message.text.split(None, 2)[2] # Get message after /send_message <user_id>
        if not message_text:
            raise ValueError("Message cannot be empty")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /send_message <user_id> <your_message_here>")
        return

    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"ℹ️ Message from Admin:\n\n{message_text}"
        )
        await update.message.reply_text(f"Message sent successfully to user {target_user_id}.")
        logger.info(f"Admin {update.effective_user.id} sent message to {target_user_id}")
    except Exception as e:
        logger.error(f"Failed to send message to user {target_user_id}: {e}")
        await update.message.reply_text(f"Failed to send message: {e}")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to broadcast a message to approved users."""
    if not is_admin(update.effective_user.id): return

    try:
        message_text = update.message.text.split(None, 1)[1] # Get message after /broadcast
    except IndexError:
        await update.message.reply_text("Usage: /broadcast <your_message_here>")
        return

    approved_users = [uid for uid, data in user_management.user_database.items() if data.get("approved", False)]
    if not approved_users:
        await update.message.reply_text("No approved users found to broadcast to.")
        return

    await update.message.reply_text(f"Starting broadcast to {len(approved_users)} approved users...")
    logger.info(f"Admin {update.effective_user.id} starting broadcast.")

    success_count = 0
    failure_count = 0
    for user_id in approved_users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 Broadcast Message:\n\n{message_text}"
            )
            success_count += 1
            await asyncio.sleep(0.1) # Small delay to avoid hitting rate limits aggressively
        except Exception as e:
            logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
            failure_count += 1

    await update.message.reply_text(
        f"Broadcast finished.\nSuccessfully sent: {success_count}\nFailed: {failure_count}"
    )


# --- Message Handlers ---

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming photos."""
    user = update.effective_user
    user_id = user.id

    # 1. Check Access
    if not user_management.can_use_bot(user_id):
        logger.warning(f"User {user_id} attempted photo upload without access.")
        status = user_management.get_user_status(user_id)
        if status == "Trial Used (Blocked)":
             await update.message.reply_text("You have used your free trial. Use /request_access to get full access.")
        else: # Should not happen based on can_use_bot logic, but as fallback
             await update.message.reply_text("You do not have access to use this feature currently.")
        return

    # 2. Download Photo
    photo_file = await update.message.photo[-1].get_file() # Get largest available photo
    photo_bytes_io = io.BytesIO()
    await photo_file.download_to_memory(photo_bytes_io)
    photo_bytes = photo_bytes_io.getvalue()
    photo_bytes_io.close()

    logger.info(f"User {user_id} uploaded a photo ({len(photo_bytes)} bytes).")
    processing_msg = await update.message.reply_text("⏳ Processing your photo with AI magic...")

    # 3. Process Photo (using Anime filter as default example)
    try:
        # --- Choose AI function based on logic (e.g., user input, default) ---
        # For now, default to anime filter
        result_bytes = await ai_processing.apply_anime_filter(photo_bytes)

        if result_bytes:
            # 4. Send Result
            result_file = InputFile(result_bytes, filename="result.jpg") # Or png if appropriate
            await update.message.reply_photo(
                photo=result_file,
                caption="✨ Here's your transformed image!"
            )
            await processing_msg.delete() # Remove "Processing..." message

            # 5. Update Trial Status (if applicable)
            if not user_management.has_access(user_id):
                user_management.record_trial_use(user_id)
                logger.info(f"Recorded trial use for user {user_id}.")
                # Optional: Send a follow-up message about trial ending
                await update.message.reply_text("You have now used your one-time trial. Use /request_access to get full access for future use.")

        else:
            # Handle processing failure
            await processing_msg.edit_text("❌ Sorry, something went wrong during processing. Please try again later.")
            logger.error(f"AI processing failed for user {user_id}.")

    except Exception as e:
        logger.error(f"Error in handle_photo for user {user_id}: {e}", exc_info=True)
        await processing_msg.edit_text("❌ An unexpected error occurred. Please report this if it persists.")


# --- Error Handler ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log Errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    # Optionally, notify admin about critical errors
    # if isinstance(context.error, SomeCriticalError):
    #     for admin_id in config.ADMIN_USER_IDS:
    #         await context.bot.send_message(chat_id=admin_id, text=f"🚨 Critical Error: {context.error}")


# --- Main Application Setup ---
async def post_init(application: Application):
    """Set bot commands after initialization."""
    commands = [
        BotCommand("start", "Start the bot and check status"),
        BotCommand("help", "Show help information"),
        BotCommand("request_access", "Request full access after trial"),
        BotCommand("status", "Check your access status"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands set.")

def main():
    """Start the bot."""
    logger.info("Starting bot...")
    if not config.TELEGRAM_BOT_TOKEN:
        logger.critical("TELEGRAM_BOT_TOKEN is not set. Exiting.")
        return
    if not config.ADMIN_USER_IDS:
        logger.critical("ADMIN_USER_IDS is not set. Exiting.")
        return

    # --- Load User Data ---
    # Uncomment the next line if using file persistence in user_management.py
    # user_management.load_user_data()

    # --- Setup Application ---
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .defaults(defaults)
        .post_init(post_init)
        .build()
    )

    # --- Register Handlers ---
    # General Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("request_access", request_access_command))
    application.add_handler(CommandHandler("status", status_command))

    # Admin Commands (check for admin rights within handlers)
    application.add_handler(CommandHandler("adminhelp", admin_help_command))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("block", block_command))
    application.add_handler(CommandHandler("pending", pending_command))
    application.add_handler(CommandHandler("toggle_nsfw", toggle_nsfw_command))
    application.add_handler(CommandHandler("send_message", send_message_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))


    # Message Handlers
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    # Add handlers for other message types if needed (e.g., text for clothes changing prompt)

    # Error Handler
    application.add_error_handler(error_handler)

    # --- Run the Bot ---
    logger.info("Running bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

    # --- Save User Data on Exit ---
    # Uncomment the next line if using file persistence in user_management.py
    # logger.info("Saving user data before exit...")
    # user_management.save_user_data()
    # logger.info("User data saved. Exiting.")


if __name__ == "__main__":
    # Note: If deploying on Render as a 'Web Service' expecting waitress,
    # you might need a different structure (e.g., run bot polling in a
    # separate thread and have waitress serve a minimal health check endpoint).
    # This current structure is best suited for Render's 'Background Worker'.
    main()


