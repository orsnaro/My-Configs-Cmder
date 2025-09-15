
#!/bin/bash
#Discord Bot (Wizard GPTEOUS) auto run script

if ! pgrep -f "bot_wizy_discord.py" > /dev/null;
then
	. /home/ors/crons/cron_env_vars && echo "Env vars loaded!" || echo "ENV VOID DETECTED!"
	echo -e "discord bot wizy  was not running! ... starting wizy bot"
	export IS_PRODUCTION='1'
	export CURRENT_DATETIME=$(date +"%Y-%m-%d,%H:%M:%S")
	cd /home/ors/repos/Discord_bot_ai
	git checkout production-Home-Server
	echo -e "#################################### \n\n\n [STARTING NEW BOT SESSION] DATE: $CURRENT_DATETIME GMT \n\n\n#################################### \n" >> ./std.log
	echo '#!/bin/bash' > ../discord_bot_runner.sh
	echo 'pip install -r requirements.txt --upgrade' > ../discord_bot_runner.sh
	echo "python3 /home/ors/repos/Discord_bot_ai/main_wizard_bot.py 2" > ../discord_bot_runner.sh
	chmod u+x ../discord_bot_runner.sh
	if ! tmux has-session -t discord_bot_runner 2>/dev/null; 
	then
		tmux new -d -s discord_bot_runner '../discord_bot_runner.sh >> ../discord_bot_shell_log.txt'
	else
	   tmux kill-session -t discord_bot_runner
	   tmux new -d -s discord_bot_runner '../discord_bot_runner.sh >> ../discord_bot_shell_log.txt'
	fi
	rm ../discord_bot_runner.sh
	cd /home/ors
fi
