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

requirements_path = path.join(path.dirname(path.dirname(path.dirname(__file__))), 'requirements.txt')

async def gen_chlog(repo, diff):
    ch_log = ''
    d_form = "%d/%m/%y"
    for c in repo.iter_commits(diff):
        ch_log += f'•[{c.committed_datetime.strftime(d_form)}]: {c.summary} <{c.author}>\n'
    return ch_log

async def update_requirements():
    reqs_path = str(requirements_path)
    try:
        process = await asyncio.create_subprocess_shell(
            ' '.join([sys.executable, "-m", "pip", "install", "-r", reqs_path]),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode
    except Exception:
        return

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
        delta_patch = origin.fetch()
        repo.git.reset("--hard", "FETCH_HEAD")
        repo.create_head('master', origin.refs.master).set_tracking_branch(origin.refs.master).checkout()
        patch_commits = repo.iter_commits(f"HEAD..{delta_patch[0].ref.name}")
        old_commit = repo.head.commit
        for diff_added in old_commit.diff('FETCH_HEAD').iter_change_type('M'):
            if "requirements.txt" in diff_added.b_path:
                await ups.edit(f'`Updating PIP requirements, please wait.`')
                update_pip = await update_requirements()
                if update_pip == 0:
                    await ups.edit(f'`Successfully updated the pip packages.`')
                else:
                    await ups.edit(f'`Please update the requirements manually.`')
                    break
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
            heroku_applications = heroku.apps()
            heroku_app = HEROKU_APPNAME
            heroku_git_url = heroku_app.git_url.replace("https://", f"https://api:{HEROKU_APIKEY}@")
            
            # Herkoku Dyno - Simply git pull the code in the dyno.
            if "heroku" in repo.remotes:
                remote = repo.remote("heroku")
                remote.set_url(heroku_git_url)
            else:
                remote = repo.create_remote("heroku", heroku_git_url)
                
    await remote.push(refspec="HEAD:refs/heads/master")
    
    await ups.edit('`Successfully Updated!\n'
                   'Bot is restarting... Wait for a second!`')
    
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
