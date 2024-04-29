#!/usr/bin/env python3

import asyncio
import time
from functools import partial
from typing import Dict, Any

import pyrogram
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import Message, CallbackQuery

# Import helper modules
from bot import bot, bot_cache, categories_dict, download_dict, download_dict_lock
from bot.helper.ext_utils.bot_utils import MirrorStatus, arg_parser, fetch_user_tds, fetch_user_dumps, getDownloadByGid, is_gdrive_link, new_task, sync_to_async, get_readable_time
from bot.helper.ext_utils.help_messages import CATEGORY_HELP_MESSAGE
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage, open_category_btns

async def change_category(client: pyrogram.Client, message: Message):
    """
    Change the category of a download task.

    :param client: Pyrogram client
    :param message: Received message
    """
    user_id = message.from_user.id
    text = message.text.split('\n')
    input_list = text[0].split(' ')

    arg_base = {'link': '', 
                '-id': '',
                '-index': ''}

    args = arg_parser(input_list[1:], arg_base)

    drive_id = args['-id']
    index_link = args['-index']

    if drive_id and is_gdrive_link(drive_id):
        drive_id = GoogleDriveHelper.getIdFromUrl(drive_id)

    dl = None
    if gid := args['link']:
        dl = await getDownloadByGid(gid)
        if not dl:
            await sendMessage(message, f"GID: <code>{gid}</code> Not Found.")
            return
    if reply_to := message.reply_to_message:
        async with download_dict_lock:
            dl = download_dict.get(reply_to.id, None)
        if not dl:
            await sendMessage(message, "This is not an active task!")
            return
    if not dl:
        await sendMessage(message, CATEGORY_HELP_MESSAGE)
        return
    if not await CustomFilters.sudo(client, message) and dl.message.from_user.id != user_id:
        await sendMessage(message, "This task is not for you!")
        return
    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_QUEUEDL]:
        await sendMessage(message, f'Task should be on {MirrorStatus.STATUS_DOWNLOADING} or {MirrorStatus.STATUS_PAUSED} or {MirrorStatus.STATUS_QUEUEDL}')
        return
    listener = dl.listener() if dl and hasattr(dl, 'listener') else None
    if listener and not listener.isLeech:
        if not index_link and not drive_id and categories_dict:
            drive_id, index_link, is_cancelled = await open_category_btns(message)
        if is_cancelled:
            return
        if not index_link and not drive_id:
            return await sendMessage(message, "Time out")
        msg = '<b>Task has been Updated Successfully!</b>'
        if drive_id:
            if not (folder_name := await sync_to_async(GoogleDriveHelper().getFolderData, drive_id)):
                return await sendMessage(message, "Google Drive id validation failed!!")
            if listener.drive_id and listener.drive_id == drive_id:
                msg += f'\n\n<b>Folder name</b> : {folder_name} Already selected'
            else:
                msg += f'\n\n<b
