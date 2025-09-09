# your_logic/api_manager.py
import alpaca_trade_api as tradeapi
import logging
import os
from dotenv import load_dotenv

class AlpacaManager:
    """
    Manages a single, shared Alpaca API instance for the application.
    Loads API keys from a .env file for security.
    """
    def __init__(self):
        # --- NEW: Load environment variables from .env file ---
        load_dotenv()
        
        self.api = None
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.secret_key = os.getenv('APCA_API_SECRET_KEY')
        self.base_url = os.getenv('APCA_BASE_URL', 'https://paper-api.alpaca.markets') # Default to paper if not set
        logging.info("AlpacaManager initialized.")

    def initialize(self):
        """Creates the Alpaca API instance."""
        if not self.api_key or not self.secret_key:
            logging.error("Alpaca API Key/Secret not found. Ensure they are set in your .env file (APCA_API_KEY_ID, APCA_API_SECRET_KEY).")
            return

        if not self.api:
            try:
                self.api = tradeapi.REST(
                    key_id=self.api_key,
                    secret_key=self.secret_key,
                    base_url=self.base_url,
                    api_version='v2'
                )
                account = self.api.get_account()
                logging.info(f"Successfully initialized Alpaca connection. Account Status: {account.status}")
            except Exception as e:
                logging.error(f"Failed to initialize Alpaca API: {e}")
                self.api = None

    def get_api(self):
        """Returns the active Alpaca API instance."""
        return self.api

    def close(self):
        """Placeholder for closing connections."""
        logging.info("Alpaca connection manager shutting down.")
        pass
