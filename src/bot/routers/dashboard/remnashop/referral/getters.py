from typing import Any

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from fluentogram import TranslatorRunner

from src.core.enums import (
    ReferralAccrualStrategy,
    ReferralLevel,
    ReferralRewardStrategy,
    ReferralRewardType,
)
from src.services.settings import SettingsService


@inject
async def referral_getter(
    dialog_manager: DialogManager,
    settings_service: FromDishka[SettingsService],
    **kwargs: Any,
) -> dict[str, Any]:
    settings = await settings_service.get_referral_settings()

    return {
        "is_enable": settings.enable,
        "referral_level": settings.level,
        "reward_type": settings.reward.type,
        "accrual_strategy_type": settings.accrual_strategy,
        "reward_strategy_type": settings.reward.strategy,
    }


async def level_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    return {"levels": list(ReferralLevel)}


async def reward_type_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    return {"rewards": list(ReferralRewardType)}


async def accrual_strategy_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    return {"strategys": list(ReferralAccrualStrategy)}


async def reward_strategy_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    return {"strategys": list(ReferralRewardStrategy)}


@inject
async def reward_getter(
    dialog_manager: DialogManager,
    i18n: FromDishka[TranslatorRunner],
    settings_service: FromDishka[SettingsService],
    **kwargs: Any,
) -> dict[str, Any]:
    settings = await settings_service.get_referral_settings()
    reward_config = settings.reward.config

    levels_strings = []
    max_level = settings.level.value
    for lvl, val in reward_config.items():
        if lvl.value <= max_level:
            levels_strings.append(
                i18n.get(
                    "msg-referral-reward-level",
                    level=lvl.value,
                    value=val,
                    reward_type=settings.reward.type,
                    reward_strategy_type=settings.reward.strategy,
                )
            )

    reward_string = "\n".join(levels_strings)

    return {
        "reward": reward_string,
        "reward_type": settings.reward.type,
        "reward_strategy_type": settings.reward.strategy,
    }
