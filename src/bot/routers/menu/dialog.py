from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import (
    Button,
    CopyText,
    ListGroup,
    Row,
    Start,
    SwitchInlineQueryChosenChatButton,
    SwitchTo,
    Url,
)
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.bot.keyboards import connect_buttons
from src.bot.routers.dashboard.users.handlers import on_user_search
from src.bot.states import Dashboard, MainMenu, Subscription
from src.bot.widgets import Banner, I18nFormat, IgnoreUpdate
from src.core.constants import MIDDLEWARE_DATA_KEY, PURCHASE_PREFIX, USER_KEY
from src.core.enums import BannerName

from .getters import devices_getter, invite_about_getter, invite_getter, menu_getter
from .handlers import (
    on_device_delete,
    on_get_trial,
    on_invite,
    on_show_qr,
    on_withdraw_points,
    show_reason,
)

menu = Window(
    Banner(BannerName.MENU),
    I18nFormat("msg-main-menu"),
    Row(
        *connect_buttons,
        Button(
            text=I18nFormat("btn-menu-connect-not-available"),
            id="not_available",
            on_click=show_reason,
            when=~F["connectable"],
        ),
        when=F["has_subscription"],
    ),
    Row(
        Button(
            text=I18nFormat("btn-menu-trial"),
            id="trial",
            on_click=on_get_trial,
            when=F["trial_available"],
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-menu-devices"),
            id="devices",
            state=MainMenu.DEVICES,
            when=F["has_device_limit"],
        ),
        Start(
            text=I18nFormat("btn-menu-subscription"),
            id=f"{PURCHASE_PREFIX}subscription",
            state=Subscription.MAIN,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-menu-invite"),
            id="invite",
            on_click=on_invite,
            when=F["is_referral_enable"],
        ),
        SwitchInlineQueryChosenChatButton(
            text=I18nFormat("btn-menu-invite"),
            query=Format("{invite}"),
            allow_user_chats=True,
            allow_group_chats=True,
            allow_channel_chats=True,
            id="send",
            when=~F["is_referral_enable"],
        ),
        Url(
            text=I18nFormat("btn-menu-support"),
            id="support",
            url=Format("{support}"),
        ),
    ),
    Row(
        Start(
            text=I18nFormat("btn-menu-dashboard"),
            id="dashboard",
            state=Dashboard.MAIN,
            mode=StartMode.RESET_STACK,
            when=F[MIDDLEWARE_DATA_KEY][USER_KEY].is_privileged,
        ),
    ),
    MessageInput(func=on_user_search),
    IgnoreUpdate(),
    state=MainMenu.MAIN,
    getter=menu_getter,
)

devices = Window(
    Banner(BannerName.MENU),
    I18nFormat("msg-menu-devices"),
    Row(
        Button(
            text=I18nFormat("btn-menu-devices-empty"),
            id="devices_empty",
            when=F["devices_empty"],
        ),
    ),
    ListGroup(
        Row(
            CopyText(
                text=Format("{item[platform]} - {item[device_model]}"),
                copy_text=Format("{item[platform]} - {item[device_model]}"),
            ),
            Button(
                text=Format("❌"),
                id="delete",
                on_click=on_device_delete,
            ),
        ),
        id="devices_list",
        item_id_getter=lambda item: item["short_hwid"],
        items="devices",
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=MainMenu.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.DEVICES,
    getter=devices_getter,
)

invite = Window(
    Banner(BannerName.REFERRAL),
    I18nFormat("msg-menu-invite"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-menu-invite-about"),
            id="about",
            state=MainMenu.INVITE_ABOUT,
        ),
    ),
    Row(
        CopyText(
            text=I18nFormat("btn-menu-invite-copy"),
            copy_text=Format("{referral_link}"),
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-menu-invite-qr"),
            id="qr",
            on_click=on_show_qr,
        ),
        SwitchInlineQueryChosenChatButton(
            text=I18nFormat("btn-menu-invite-send"),
            query=Format("{invite}"),
            allow_user_chats=True,
            allow_group_chats=True,
            allow_channel_chats=True,
            id="send",
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-menu-invite-withdraw-points"),
            id="withdraw_points",
            on_click=on_withdraw_points,
            when=~F["has_points"],
        ),
        Url(
            text=I18nFormat("btn-menu-invite-withdraw-points"),
            id="withdraw_points",
            url=Format("{withdraw}"),
            when=F["has_points"],
        ),
        when=F["is_points_reward"],
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=MainMenu.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.INVITE,
    getter=invite_getter,
)

invite_about = Window(
    Banner(BannerName.REFERRAL),
    I18nFormat("msg-menu-invite-about"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=MainMenu.INVITE,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.INVITE_ABOUT,
    getter=invite_about_getter,
)

router = Dialog(
    menu,
    devices,
    invite,
    invite_about,
)
