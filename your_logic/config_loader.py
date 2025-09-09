# your_logic/config_loader.py
import yaml
import logging

def load_config(filepath="your_logic/stock_signals_v1.yml"):
    """
    Loads the trading strategy configuration from a YAML file.
    """
    try:
        with open(filepath, 'r') as file:
            config = yaml.safe_load(file)
        logging.info(f"Successfully loaded configuration from {filepath}")
        return config
    except FileNotFoundError:
        logging.error(f"The configuration file was not found at {filepath}")
        return None
    except Exception as e:
        logging.error(f"An error occurred while reading the config file: {e}")
        return None
