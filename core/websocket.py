import random

def get_live_price(entry):
    # simulate tick movement
    return entry + random.randint(-10, 50)
