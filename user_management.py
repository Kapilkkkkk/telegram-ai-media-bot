import logging
import json
import os
from typing import Set, Dict

logger = logging.getLogger(__name__)

# --- In-memory storage (will reset on bot restart) ---
# Structure: {user_id: {"approved": bool, "used_trial": bool}}
user_database: Dict[int, Dict[str, bool]] = {}
# Set of users who have requested access
access_requests: Set[int] = set()

# --- Persistent Storage (Optional - using JSON file) ---
USER_DATA_FILE = "user_data.json"

def load_user_data():
    """Loads user data from a JSON file."""
    global user_database, access_requests
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                data = json.load(f)
                # Convert keys back to int
                user_database = {int(k): v for k, v in data.get("user_database", {}).items()}
                access_requests = set(data.get("access_requests", []))
                logger.info(f"Loaded user data from {USER_DATA_FILE}")
        except (json.JSONDecodeError, IOError, TypeError) as e:
            logger.error(f"Error loading user data from {USER_DATA_FILE}: {e}. Starting fresh.")
            user_database = {}
            access_requests = set()
    else:
        logger.info(f"{USER_DATA_FILE} not found. Starting with empty user data.")
        user_database = {}
        access_requests = set()

def save_user_data():
    """Saves current user data to a JSON file."""
    try:
        # Convert set to list for JSON serialization
        data_to_save = {
            "user_database": user_database,
            "access_requests": list(access_requests)
        }
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        # logger.debug(f"Saved user data to {USER_DATA_FILE}") # Use debug level to avoid spamming logs
    except IOError as e:
        logger.error(f"Error saving user data to {USER_DATA_FILE}: {e}")

# Load data when the module is imported
# load_user_data() # Uncomment this line to enable file persistence

# --- Access Check Functions ---

def has_access(user_id: int) -> bool:
    """Checks if a user has approved access."""
    return user_database.get(user_id, {}).get("approved", False)

def has_used_trial(user_id: int) -> bool:
    """Checks if a user has already used their one-time trial."""
    return user_database.get(user_id, {}).get("used_trial", False)

def can_use_bot(user_id: int) -> bool:
    """Determines if a user can currently use the bot's core feature."""
    if has_access(user_id):
        return True  # Approved users always have access
    if not has_used_trial(user_id):
        return True # Haven't used trial yet
    return False # Used trial and not approved

# --- Action Functions ---

def record_trial_use(user_id: int):
    """Marks the user's trial as used."""
    if user_id not in user_database:
        user_database[user_id] = {}
    user_database[user_id]["used_trial"] = True
    user_database[user_id].setdefault("approved", False) # Ensure approved key exists
    logger.info(f"User {user_id} used their trial.")
    # save_user_data() # Uncomment for persistence

def request_access(user_id: int):
    """Records an access request from a user."""
    if not has_access(user_id): # No need to request if already approved
        access_requests.add(user_id)
        logger.info(f"User {user_id} requested access.")
        # save_user_data() # Uncomment for persistence
        return True
    return False # Already approved

def approve_user(user_id: int):
    """Approves a user and removes from requests."""
    if user_id not in user_database:
        user_database[user_id] = {}
    user_database[user_id]["approved"] = True
    user_database[user_id].setdefault("used_trial", False) # Ensure trial key exists
    access_requests.discard(user_id) # Remove from requests if present
    logger.info(f"Admin approved user {user_id}.")
    # save_user_data() # Uncomment for persistence

def block_user(user_id: int):
    """Blocks (revokes approval) for a user."""
    if user_id in user_database:
        user_database[user_id]["approved"] = False
        logger.info(f"Admin blocked user {user_id}.")
        # save_user_data() # Uncomment for persistence
    else:
        # Optionally create an entry to explicitly mark as blocked
        user_database[user_id] = {"approved": False, "used_trial": True} # Assume blocked means trial used too
        logger.info(f"Admin blocked new user {user_id}.")
        # save_user_data() # Uncomment for persistence

def get_pending_requests() -> Set[int]:
    """Returns the set of user IDs pending approval."""
    return access_requests

def get_user_status(user_id: int) -> str:
    """Gets a string representation of the user's status."""
    if user_id in config.ADMIN_USER_IDS:
        return "Admin"
    status = user_database.get(user_id, {})
    approved = status.get("approved", False)
    used_trial = status.get("used_trial", False)

    if approved:
        return "Approved"
    elif user_id in access_requests:
        return "Pending Approval"
    elif used_trial:
        return "Trial Used (Blocked)"
    else:
        return "New User (Trial Available)"
