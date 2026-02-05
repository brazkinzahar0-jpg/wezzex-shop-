from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Select
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

from src.bot.states import RemnashopReferral
from src.core.constants import USER_KEY
from src.core.enums import (
    ReferralAccrualStrategy,
    ReferralLevel,
    ReferralRewardStrategy,
    ReferralRewardType,
)
from src.core.utils.formatters import format_user_log as log
from src.core.utils.message_payload import MessagePayload
from src.infrastructure.database.models.dto import UserDto
from src.services.notification import NotificationService
from src.services.settings import SettingsService


@inject
async def on_enable_toggle(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    settings_service: FromDishka[SettingsService],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]

    settings = await settings_service.get()
    settings.referral.enable = not settings.referral.enable
    await settings_service.update(settings)

    logger.info(
        f"{log(user)} Successfully toggled referral system status to '{settings.referral.enable}'"
    )


@inject
async def on_level_select(
    callback: CallbackQuery,
    widget: Select[int],
    dialog_manager: DialogManager,
    selected_level: int,
    settings_service: FromDishka[SettingsService],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    logger.debug(f"{log(user)} Selected referral level '{selected_level}'")

    settings = await settings_service.get()
    settings.referral.level = ReferralLevel(selected_level)
    config: dict[ReferralLevel, int] = settings.referral.reward.config

    for lvl in ReferralLevel:
        if lvl.value <= selected_level and lvl not in config:
            prev_value = config.get(ReferralLevel(lvl.value - 1), 0)
            config[lvl] = prev_value

    settings.referral.reward.config = config
    await settings_service.update(settings)

    logger.info(f"{log(user)} Successfully updated referral level to '{selected_level}'")
    await dialog_manager.switch_to(state=RemnashopReferral.MAIN)


@inject
async def on_reward_select(
    callback: CallbackQuery,
    widget: Select[ReferralRewardType],
    dialog_manager: DialogManager,
    selected_reward: ReferralRewardType,
    settings_service: FromDishka[SettingsService],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    logger.debug(f"{log(user)} Selected referral reward '{selected_reward}'")

    settings = await settings_service.get()
    settings.referral.reward.type = selected_reward
    await settings_service.update(settings)

    logger.info(f"{log(user)} Successfully updated referral reward to '{selected_reward}'")
    await dialog_manager.switch_to(state=RemnashopReferral.MAIN)


@inject
async def on_accrual_strategy_select(
    callback: CallbackQuery,
    widget: Select[ReferralAccrualStrategy],
    dialog_manager: DialogManager,
    selected_strategy: ReferralAccrualStrategy,
    settings_service: FromDishka[SettingsService],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    logger.debug(f"{log(user)} Selected referral accrual strategy '{selected_strategy}'")

    settings = await settings_service.get()
    settings.referral.accrual_strategy = selected_strategy
    await settings_service.update(settings)

    logger.info(
        f"{log(user)} Successfully updated referral accrual strategy to '{selected_strategy}'"
    )
    await dialog_manager.switch_to(state=RemnashopReferral.MAIN)


@inject
async def on_reward_strategy_select(
    callback: CallbackQuery,
    widget: Select[ReferralRewardStrategy],
    dialog_manager: DialogManager,
    selected_strategy: ReferralRewardStrategy,
    settings_service: FromDishka[SettingsService],
) -> None:
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    logger.debug(f"{log(user)} Selected referral reward strategy '{selected_strategy}'")

    settings = await settings_service.get()
    settings.referral.reward.strategy = selected_strategy
    await settings_service.update(settings)

    logger.info(
        f"{log(user)} Successfully updated referral reward strategy to '{selected_strategy}'"
    )
    await dialog_manager.switch_to(state=RemnashopReferral.MAIN)


@inject
async def on_reward_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    notification_service: FromDishka[NotificationService],
    settings_service: FromDishka[SettingsService],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    text = message.text

    if not text:
        await notification_service.notify_user(
            user=user,
            payload=MessagePayload(i18n_key="ntf-referral-invalid-reward"),
        )
        return

    settings = await settings_service.get()
    config: dict[ReferralLevel, int] = settings.referral.reward.config

    if text.isdigit():
        value = int(text)
        config[ReferralLevel.FIRST] = value
    else:
        try:
            for pair in text.split():
                lvl_str, val_str = pair.split("=")
                lvl = ReferralLevel(int(lvl_str.strip()))
                val = int(val_str.strip())
                config[lvl] = val
        except Exception:
            await notification_service.notify_user(
                user=user,
                payload=MessagePayload(i18n_key="ntf-referral-invalid-reward"),
            )
            return

    settings.referral.reward.config = config
    await settings_service.update(settings)

    logger.info(f"{log(user)} Updated referral reward: {settings.referral.reward}")
