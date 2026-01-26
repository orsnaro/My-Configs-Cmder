#!/bin/bash
#Discord Bot (Wizard GPTEOUS) auto run script
# 
if ! pgrep -f "bot_wizy_discord.py" > /dev/null;
then
	echo -e "discord bot wizy  was not running! ... starting wizy bot"
	export CURRENT_DATETIME=$(date +"%Y-%m-%d,%H:%M:%S")
	echo -e "#################################### \n\n\n [STARTING NEW BOT SESSION] DATE: $CURRENT_DATETIME GMT \n\n\n#################################### \n"
	echo -e "cding to project dir ~/repos/Discord_bot_ai ⌛"
	cd /home/ors/repos/Discord_bot_ai
	echo -e "OK until now ...  switching branch to production-Home-Server⌛"
	git checkout production-Home-Server
	. /home/ors/crons/cron_env_vars && echo 'ENV vars loaded in tmux bot session side' || echo 'ENV VOID DETECTED!'
	export IS_PRODUCTION=1
	echo -e "OK util now ...  doing pip install updgrade from requirements.txt"
	pip install -r requirements.txt --upgrade
	echo -e "ALL OK until beofre running the bot python app✅  starting app main process  bot_wizy_discord.py ⚡"
	exec python3 /home/ors/repos/Discord_bot_ai/main_wizard_bot.py 1
    echo -e "exited main process!  cding back to home ~ "
	cd /home/ors
else
	echo -e "bot_wizy_discord.py is already running"
fi
