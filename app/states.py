from aiogram.fsm.state import State, StatesGroup


class CardStates(StatesGroup):
    waiting_for_main_photo = State()
    waiting_for_minor_photo_1 = State()
    waiting_for_minor_photo_2 = State()


class ConfigStates(StatesGroup):
    waiting_for_value = State()


class ExampleStates(StatesGroup):
    waiting_for_photos = State()
    waiting_for_features = State()
    waiting_for_description = State()
    waiting_for_price = State()

