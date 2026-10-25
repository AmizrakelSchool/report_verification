import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ----------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------
# Replace with your Assignment Bot Token when ready
BOT_TOKEN = "8979111544:AAEztiVWwUItWYgWANlGDjNgj7Fe22vqAH8"
ADMIN_CHAT_ID = -1004462485960
WORD_TEMPLATE_PATH = "Assignment_Form.docx"
# ----------------------------------------------------

# Store active feedback states
AWAITING_FEEDBACK = {}

# Store blocked user IDs
BLOCKED_USERS = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in BLOCKED_USERS:
        await update.message.reply_text("🚫 **You have been blocked from using our service.**", parse_mode="Markdown")
        return

    welcome_text = (
        "👋 **Welcome to AMIZRAKEL Assignment Writing Service!**\n\n"
        "To get started, please send a message containing:\n\n"
        "1. 📸 Your Telebirr payment **screenshot**\n"
        "2. ✉️ Your working **Email Address**\n"
        "3. 🔢 Your chosen **Assignment Details or Course Code**\n\n"
        "*(Please send the photo with these details in the caption)*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command for Admin to unblock a user: /unblock <user_id>"""
    chat_id = update.message.chat_id
    if chat_id != ADMIN_CHAT_ID:
        return

    if not context.args:
        await update.message.reply_text("⚠️ **Usage:** `/unblock <USER_ID>`", parse_mode="Markdown")
        return

    try:
        target_user_id = int(context.args[0])
        if target_user_id in BLOCKED_USERS:
            BLOCKED_USERS.remove(target_user_id)
            await update.message.reply_text(f"✅ **User `{target_user_id}` has been unblocked!**", parse_mode="Markdown")

            # Notify the user
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="✅ **Your account has been unblocked.** You may now use our service again.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        else:
            await update.message.reply_text(f"ℹ️ User `{target_user_id}` is not in the blocked list.", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("⚠️ Please provide a valid numerical User ID.")


async def handle_user_submission(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    user = update.message.from_user
    if user.id in BLOCKED_USERS:
        await update.message.reply_text("🚫 **You are blocked from using our service.**", parse_mode="Markdown")
        return

    message = update.message

    if not message.photo:
        await message.reply_text(
            "⚠️ Please make sure to attach your **Telebirr payment screenshot** along"
            " with your email and assignment details!"
        )
        return

    await message.reply_text(
        "⏳ **Payment proof received!**\nYour submission is currently under"
        " review. Please wait a moment..."
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Approve Payment", callback_data=f"payapprove_{user.id}"
            ),
            InlineKeyboardButton(
                "❌ Reject Payment", callback_data=f"payreject_{user.id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🚫 Block User", callback_data=f"blockuser_{user.id}"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    caption_text = (
        f"🔔 **New Assignment Payment Submitted!**\n\n"
        f"👤 **User:** {user.first_name} (@{user.username})\n"
        f"🆔 **User ID:** `{user.id}`\n"
        f"💬 **Details/Caption:** {message.caption or 'No caption provided'}"
    )

    await context.bot.send_photo(
        chat_id=ADMIN_CHAT_ID,
        photo=message.photo[-1].file_id,
        caption=caption_text,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # STAGE 1: Payment Approval / Rejection
    if data.startswith("payapprove_"):
        target_user_id = int(data.split("_")[1])
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n✅ **Payment Status: APPROVED**",
            parse_mode="Markdown",
        )

        # Sends the Assignment_Form.docx file automatically
        if os.path.exists(WORD_TEMPLATE_PATH):
            with open(WORD_TEMPLATE_PATH, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=target_user_id,
                    document=doc_file,
                    caption=(
                        "✅ **Payment Verified!**\n\n"
                        "📌 Please download the Word document attached above, fill out all required assignment details, "
                        "and send the completed file back to this chat."
                    ),
                    parse_mode="Markdown"
                )
        else:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="✅ **Payment Verified!**\nPlease download and fill out the assignment form documen, then send it back to this chat.\nPlease change the file name to EDITED when saving it before sending.",
                parse_mode="Markdown",
            )

    elif data.startswith("payreject_"):
        target_user_id = int(data.split("_")[1])
        await query.edit_message_caption(
            caption=query.message.caption + "\n\n❌ **Payment Status: REJECTED**",
            parse_mode="Markdown",
        )
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                "❌ **Payment Verification Failed.**\nYour payment screenshot could"
                " not be verified. Please try again or contact support."
            ),
            parse_mode="Markdown",
        )

    # STAGE 2: Form Details Approval / Correction
    elif data.startswith("formapprove_"):
        target_user_id = int(data.split("_")[1])
        if query.message.caption:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n✅ **Assignment Status: APPROVED & STARTED**",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                text=query.message.text + "\n\n✅ **Assignment Status: APPROVED & STARTED**",
                parse_mode="Markdown",
            )

        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                "🚀 **Great news! Your assignment details have been verified.**\n\nYour work"
                " is now in progress! We will notify you once it's completed."
            ),
            parse_mode="Markdown",
        )

    elif data.startswith("formcorrect_"):
        target_user_id = int(data.split("_")[1])
        AWAITING_FEEDBACK[query.from_user.id] = target_user_id
        await query.message.reply_text(
            f"✍️ **Send feedback for User ID `{target_user_id}`:**\nType your"
            " correction note in this chat, and the bot will forward it directly to the user."
        )

    # BLOCK USER ACTION
    elif data.startswith("blockuser_"):
        target_user_id = int(data.split("_")[1])
        BLOCKED_USERS.add(target_user_id)

        if query.message.caption:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n🚫 **Status: USER BLOCKED**",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                text=query.message.text + "\n\n🚫 **Status: USER BLOCKED**",
                parse_mode="Markdown",
            )

        await context.bot.send_message(
            chat_id=target_user_id,
            text="🚫 **You have been blocked from using this bot.**",
            parse_mode="Markdown",
        )


async def handle_document_submission(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    user = update.message.from_user
    chat_id = update.message.chat_id

    if user.id in BLOCKED_USERS:
        await update.message.reply_text("🚫 **You are blocked from using our service.**", parse_mode="Markdown")
        return

    if chat_id != ADMIN_CHAT_ID:
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Confirm Details", callback_data=f"formapprove_{user.id}"
                ),
                InlineKeyboardButton(
                    "💬 Request Correction", callback_data=f"formcorrect_{user.id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🚫 Block User", callback_data=f"blockuser_{user.id}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        caption_text = (
            f"📄 **NEW FILLED ASSIGNMENT FILE RECEIVED**\n"
            f"👤 **User:** {user.first_name} (@{user.username})\n"
            f"🆔 **User ID:** `{user.id}`\n\n"
            f"📎 **File:** {update.message.document.file_name}"
        )

        await context.bot.send_document(
            chat_id=ADMIN_CHAT_ID,
            document=update.message.document.file_id,
            caption=caption_text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        await update.message.reply_text(
            "📥 **Document Received!**\nYour completed assignment file has been submitted to the admin for final review."
        )


async def handle_text_messages(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    user = update.message.from_user
    chat_id = update.message.chat_id

    if user.id in BLOCKED_USERS:
        await update.message.reply_text("🚫 **You are blocked from using our service.**", parse_mode="Markdown")
        return

    if chat_id == ADMIN_CHAT_ID or user.id in AWAITING_FEEDBACK:
        target_user_id = AWAITING_FEEDBACK.pop(user.id, None)
        if target_user_id:
            feedback_note = update.message.text
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    "⚠️ **Correction Needed for Your Assignment**\n\n"
                    f"The admin left the following note:\n> *\"{feedback_note}\"*\n\n"
                    "Please update your details and send the revised file back."
                ),
                parse_mode="Markdown",
            )
            await update.message.reply_text(
                f"✅ Correction note sent to user `{target_user_id}`!"
            )
            return

    if chat_id != ADMIN_CHAT_ID:
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Confirm Details", callback_data=f"formapprove_{user.id}"
                ),
                InlineKeyboardButton(
                    "💬 Request Correction", callback_data=f"formcorrect_{user.id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🚫 Block User", callback_data=f"blockuser_{user.id}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        forward_text = (
            f"📄 **NEW ASSIGNMENT DETAILS RECEIVED**\n"
            f"👤 **User:** {user.first_name} (@{user.username})\n"
            f"🆔 **User ID:** `{user.id}`\n\n"
            f"--- **SUBMITTED DETAILS** ---\n"
            f"{update.message.text}"
        )

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=forward_text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        await update.message.reply_text(
            "📥 **Details Received!**\nYour assignment details have been submitted to"
            " the admin for final review."
        )


def main():
    token = BOT_TOKEN
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("unblock", unblock_user))

    application.add_handler(
        MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_user_submission)
    )
    application.add_handler(
        MessageHandler(filters.Document.ALL & ~filters.COMMAND, handle_document_submission)
    )

    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_messages,
        )
    )

    PORT = int(os.environ.get('PORT', 10000))
    RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')

    print("🤖 Assignment Bot is up and running via Render webhook...")
    
    if RENDER_URL:
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=token,
            webhook_url=f"{RENDER_URL}/{token}"
        )
    else:
        application.run_polling()


if __name__ == "__main__":
    main()