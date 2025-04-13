# Telegram AI Media Bot

This is a Telegram bot built with `python-telegram-bot` that allows users to upload photos and apply AI transformations (like anime filters). It features robust admin controls for user access and content moderation.

Deployed on [Render](https://render.com/).

## Features

* **AI Image Transformations:**
    * Image-to-Anime / Style Filters (Example implemented)
    * (Potential for other features like clothes changing)
* **User Access Control:**
    * One-time trial use for new users.
    * Requires admin approval for continued access (`/request_access`).
    * Only approved users can use the bot beyond the trial.
* **Admin Panel:**
    * Approve (`/approve`) or block (`/block`) user access.
    * List pending requests (`/pending`).
    * Check user status (`/status [user_id]`).
    * Toggle NSFW generation mode (`/toggle_nsfw`).
    * Send custom messages to users (`/send_message`).
    * Broadcast messages to approved users (`/broadcast`).
* **Deployment:** Configured for deployment on Render (using Worker type or Web Service).

## Tech Stack

* Python 3.9+ (Specify your version, e.g., 3.11)
* `python-telegram-bot` v20+
* `Waitress` (Included, primarily if using Render Web Service type)
* `python-dotenv` (for local development)
* `Pillow`, `requests` (Example dependencies for image/API handling)

## Setup for Local Development

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd telegram-ai-media-bot
    ```
2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Create a `.env` file** in the root directory and add your environment variables:
    ```dotenv
    TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
    ADMIN_USER_IDS=YOUR_TELEGRAM_USER_ID,ANOTHER_ADMIN_ID # Comma-separated IDs
    # Add other required variables like AI_API_KEY if needed
    # AI_API_KEY=YOUR_AI_SERVICE_KEY
    LOG_LEVEL=INFO
    ```
    * Get your Telegram Bot Token from BotFather on Telegram.
    * Find your Telegram User ID using bots like `@userinfobot`.

5.  **Run the bot locally:**
    ```bash
    python bot.py
    ```

## Deployment to Render

1.  **Push your code to a GitHub repository.**
2.  **Create a new service on Render:**
    * Connect your GitHub account to Render.
    * Choose your repository.
    * Select the **Service Type**:
        * **Background Worker:** Recommended for this polling setup.
        * **Web Service:** Can also work, Render will use `waitress` if detected, but it's not strictly necessary for polling. Might be useful if you add a health check endpoint later.
    * **Environment:** Select `Python`.
    * **Region:** Choose a region.
    * **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt` (Render usually detects `requirements.txt` automatically, but explicit is good).
    * **Start Command:** `python bot.py` (For Background Worker or Web Service if `Procfile` isn't defining `web`).
    * **(Optional but Recommended) Use `render.yaml`:** Commit the `render.yaml` file to your repo. Render can use this Blueprint to configure the service automatically when you create it. Select "Blueprint" as the source when creating.
3.  **Configure Environment Variables:**
    * Go to the "Environment" section for your service on Render.
    * Add **Secret Files** or **Environment Variables** for:
        * `TELEGRAM_BOT_TOKEN`
        * `ADMIN_USER_IDS` (comma-separated list of numeric IDs)
        * `AI_API_KEY` (if needed)
        * `PYTHON_VERSION` (e.g., `3.11`) - Important for Render to use the correct Python version.
        * `LOG_LEVEL` (optional, defaults to INFO)
4.  **Deploy:** Create the service. Render will build and deploy your bot. Check the logs for any errors.
5.  **(Optional - Persistence):** If you enabled file persistence for user data:
    * Create a **Disk** in the Render dashboard.
    * Attach the disk to your service, specifying a mount path (e.g., `/app/data`).
    * Update `USER_DATA_FILE` in `user_management.py` to use this path (e.g., `USER_DATA_FILE = "/app/data/user_data.json"`). Redeploy.

## Usage

* Talk to your bot on Telegram.
* Use `/start` and `/help`.
* Send a photo to trigger the AI processing (subject to access level).
* Admins can use the `/adminhelp` command to see available admin actions.

---
