"""All binary_sensor entities."""

from homeassistant.helpers.entity import EntityDescription

from . import FiskerButtonEntityDescription

BUTTON_ENTITIES: list[EntityDescription] = [
    FiskerButtonEntityDescription(
        key="doors_unlock",
        name="Doors Unlock",
        translation_key="doors_unlock",
        icon="mdi:car-door-lock-open",
        command="doors_unlock",
    ),
    FiskerButtonEntityDescription(
        key="doors_lock",
        name="Doors Lock",
        translation_key="doors_lock",
        icon="mdi:car-door-lock",
        command="doors_lock",
    ),
    FiskerButtonEntityDescription(
        key="trunk_open",
        name="Trunk Open",
        translation_key="trunk_open",
        icon="mdi:car-back",
        command="trunk_open",
    ),
    FiskerButtonEntityDescription(
        key="trunk_close",
        name="Trunk Close",
        translation_key="trunk_close",
        icon="mdi:car-back",
        command="trunk_close",
    ),
    FiskerButtonEntityDescription(
        key="california_mode_on",
        name="California mode ON",
        translation_key="california_mode",
        icon="mdi:car-convertible",
        command="california_mode",
        command_data="on",
    ),
    FiskerButtonEntityDescription(
        key="california_mode_off",
        name="California mode OFF",
        translation_key="california_mode",
        icon="mdi:car-convertible",
        command="california_mode",
        command_data="off",
    ),
]
