# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
"""
This module updates the userbot based on Upstream revision
"""

from os import remove, execl, path
import asyncio
import sys

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from userbot import CMD_HELP, bot, HEROKU_MEMEZ, HEROKU_APIKEY, HEROKU_APPNAME
from userbot.events import register


basedir = path.abspath(path.curdir)

async def gen_chlog(repo, diff):
    ch_log = ''
    d_form = "%d/%m/%y"
    for c in repo.iter_commits(diff):
        ch_log += f'•[{c.committed_datetime.strftime(d_form)}]: {c.summary} <{c.author}>\n'
    return ch_log

@register(outgoing=True, pattern="^.update(?: |$)(.*)")
async def upstream(ups):
    "For .update command, check if the bot is up to date, update if specified"
    await ups.edit("`Checking for updates, please wait....`")
    conf = ups.pattern_match.group(1).lower()
    off_repo = 'https://github.com/AvinashReddy3108/PaperplaneExtended.git'

    try:
        txt = "`Oops.. Updater cannot continue due to some problems occured`\n\n**LOGTRACE:**\n"
        repo = Repo(basedir)
    except NoSuchPathError as error:
        await ups.edit(f'{txt}\n`directory {error} is not found`')
        repo.__del__()
        return
    except GitCommandError as error:
        await ups.edit(f'{txt}\n`Early failure! {error}`')
        repo.__del__()
        return
    except InvalidGitRepositoryError:
        repo = Repo.init(basedir)
        origin = repo.create_remote('upstream', off_repo)
        if not origin.exists():
            await ups.edit(f'{txt}\n`The upstream remote is invalid.`')
            repo.__del__()
            return
        origin.fetch()
        repo.git.reset("--hard", "FETCH_HEAD")
        repo.create_head('master', origin.refs.master).set_tracking_branch(origin.refs.master).checkout()
    ac_br = repo.active_branch.name
    if ac_br != "master":
        await ups.edit(
            f'**[UPDATER]:**` Looks like you are using your own custom branch ({ac_br}). \
            in that case, Updater is unable to identify which branch is to be merged. \
            please checkout to the official branch`')
        return

    try:
        repo.create_remote('upstream', off_repo)
    except BaseException:
        pass

    ups_rem = repo.remote('upstream')
    ups_rem.fetch(ac_br)
    changelog = await gen_chlog(repo, f'HEAD..upstream/{ac_br}')

    if not changelog:
        await ups.edit(f'\n`Your BOT is` **up-to-date** `with` **{ac_br}**\n')
        return

    if conf != "now":
        changelog_str = f'**New UPDATE available for [{ac_br}]:\n\nCHANGELOG:**\n`{changelog}`'
        if len(changelog_str) > 4096:
            await ups.edit("`Changelog is too big, sending it as a file.`")
            file = open("output.txt", "w+")
            file.write(changelog_str)
            file.close()
            await ups.client.send_file(
                ups.chat_id,
                "output.txt",
                reply_to=ups.id,
            )
            remove("output.txt")
        else:
            await ups.edit(changelog_str)
        await ups.respond(
            "`do \".update now\" to update`")
        return

    await ups.edit('`New update found, updating...`')
    ups_rem.fetch(ac_br)
    
    if HEROKU_MEMEZ:
        if not HEROKU_APIKEY or not HEROKU_APPNAME:
            await ups.edit(f'{txt}\n`Missing Heroku credentials for updating userbot dyno.`')
            return
        else:
            import heroku3
            heroku = heroku3.from_key(HEROKU_APIKEY)
            heroku_app = None
            heroku_applications = heroku.apps()
            
            for app in heroku_applications:
                if app.name == str(HEROKU_APPNAME):
                    heroku_app = app
                    break

            heroku_git_url = heroku_app.git_url.replace("https://", f"https://api:{HEROKU_APIKEY}@")

            if "heroku" in repo.remotes:
                remote = repo.remote("heroku")
                remote.set_url(heroku_git_url)
            else:
                remote = repo.create_remote("heroku", heroku_git_url)
                
        for build in heroku_app.builds():
            if build.status == "pending":
                await ups.edit('`There seems to be an ongoing build for a previous update, please wait for it to finish.`')
                return
            else:
                await remote.push(refspec="HEAD:refs/heads/master", force=True)
                await ups.edit(f"`[HEROKU MEMEZ] Dyno build in progress for app {HEROKU_APPNAME}`\
                \nCheck build progress [here](https://dashboard.heroku.com/apps/{HEROKU_APPNAME}/activity).")
    
    await ups.edit('`Successfully Updated!\n'
                   'Bot is restarting... Wait for a while!`')
    
    await bot.disconnect()
    
    # Spin a new instance of bot
    execl(sys.executable, sys.executable, *sys.argv)


CMD_HELP.update({
    'update':
    ".update\
\nUsage: Checks if the main userbot repository has any updates and shows a changelog if so.\
\n\n.update now\
\nUsage: Updates your userbot, if there are any updates in the main userbot repository."
})
