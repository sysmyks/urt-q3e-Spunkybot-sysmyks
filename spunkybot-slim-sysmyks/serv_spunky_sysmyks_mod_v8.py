#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Spunky Bot - An automated game server bot
http://github.com/spunkybot/spunkybot
Author: Alexander Kress

This program is released under the MIT License. See LICENSE for more details.

## About ##
Spunky Bot is a lightweight game server administration bot and RCON tool,
inspired by the eb2k9 bot by Shawn Haggard.
The purpose of Spunky Bot is to administrate an Urban Terror 4.1 / 4.2 / 4.3
server and provide statistics data for players.
²
## Configuration ##
Modify the UrT server config as follows:
 * seta g_logsync "1"
 * seta g_loghits "1"
 * seta g_friendlyfire "2"
Modify the files '/conf/settings.conf' and '/conf/rules.conf'
Run the bot: python spunky.py
"""

__version__ = '1.13.0'


### IMPORTS
import wget
import os
import re
import sys
import json
import time
import sqlite3
import math
import glob
import textwrap
import logging
import random
import subprocess
import ConfigParser
import logging.handlers
import codecs
from Queue import Queue
from threading import Thread
from threading import RLock
import lib.pygeoip as pygeoip
import lib.schedule as schedule
from lib.pyquake3 import PyQuake3
from datetime import datetime
import time as ntime

# Get an instance of a logger
logger = logging.getLogger('spunkybot')
logger.setLevel(logging.DEBUG)
logger.propagate = False




# Bot player number
BOT_PLAYER_NUM = 1022

# RCON Delay in seconds, recommended range: 0.18 - 0.33
RCON_DELAY = 0.2

COMMANDS = {'help': {'desc': 'display all available commands', 'syntax': '^7Usage: ^9!help', 'level': 0, 'short': 'h'},
            'register': {'desc': 'register yourself as a basic user', 'syntax': '^7Usage: ^9!register', 'level': 0},
            # user commands, level 1
            'regtest': {'desc': 'display current user status', 'syntax': '^7Usage: ^9!regtest', 'level': 1},
            'spec': {'desc': 'move yourself to spectator', 'syntax': '^7Usage: ^9!spec or !sp', 'level': 20, 'short': 'sp'},
            'play': {'desc': 'move yourself to spectator', 'syntax': '^7Usage: ^9!play or !pl', 'level': 20, 'short': 'pl'},
            'goto': {'desc': 'Goto to a specific jump', 'syntax': '^7Usage: ^9!goto', 'level': 20},
            'glist': {'desc': 'Displays maps saved locations', 'syntax': '^7Usage: ^9!glist', 'level': 20},
            'time': {'desc': 'display the current server time', 'syntax': '^7Usage: ^9!time', 'level': 20},
            'ready': {'desc': 'start timer mod', 'syntax': '^7Usage: ^9!ready or !r', 'level': 20, 'short': 'r'},
            'regainstamina': {'desc': 'active regainstamina', 'syntax': '^7Usage: ^9!regainstamina or !rgs', 'level': 20, 'short': 'rgs'},
            'allowgoto': {'desc': 'active your goto', 'syntax': '^7Usage: ^9!allowgoto or !alg', 'level': 20, 'short': 'alg'},
            'topruns': {'desc': 'display 3 records runs', 'syntax': '^7Usage: ^9!topruns',  'level': 20, 'short': 'tr'},
            'transl': {'desc': 'translate into all languages', 'syntax': '^7Usage: ^9!transl <lang> <text>', 'level': 20},
            'maps': {'desc': 'display all available maps', 'syntax': '^7Usage: ^9!maps', 'level': 20},
            'votecycle': {'desc': 'Vote on cycling to the next map', 'syntax': '^7Usage: ^9!votecyclemap or !vc', 'level': 20, 'short': 'vc'},
            'votemap': {'desc': 'Callvote on changing current map', 'syntax': '^7Usage: ^9!votemap <mapname> or !vm',  'level': 20, 'short': 'vm'},
            'nextmap': {'desc': 'display the next map in rotation', 'syntax': '^7Usage: ^9!nextmap', 'level': 20},
            'votenextmap': {'desc': 'Callvote on setting next map', 'syntax': '^7Usage: ^9!votenextmap <mapname> or !vn',  'level': 20, 'short': 'vn'},
            'drop': {'desc': 'drop your stuff', 'syntax': '^7Usage: ^9!drop or !dr',  'level': 20, 'short': 'dr'},
            'mapinfo': {'desc': 'map info', 'syntax': '^7Usage: ^9!mapinfo',  'level': 20},
            'top': {'desc': 'display your records', 'syntax': '^7Usage: ^9!top',  'level': 20},
            'noclip': {'desc': 'noclip', 'syntax': '^7Usage: ^9!noclip or !n',  'level': 20, 'short': 'n'},
            'msgadmin': {'desc': 'send a message to the admin', 'syntax': '^7Usage: ^9!msgadmin <text>', 'level': 20},
            
            
            # moderator commands, level 20
            
            'sendmessage': {'desc': 'sendmessage specifique player', 'syntax': '^7Usage: ^9!sendmessage', 'level': 40},
            'delmessage': {'desc': 'delmessage specifique player', 'syntax': '^7Usage: ^9!delmessage', 'level': 40},
            'g_stamina': {'desc': 'g_stamina 1 or 2', 'syntax': '^7Usage: ^9!g_stamina', 'level': 40},
            'g_walljump': {'desc': 'g_walljump', 'syntax': '^7Usage: ^9!g_walljump', 'level': 40},
            'admintest': {'desc': 'display current admin status', 'syntax': '^7Usage: ^9!admintest', 'level': 40},
            'country': {'desc': 'get the country of a player', 'syntax': '^7Usage: ^9!country ^7<name>', 'level': 40},
            'lastmaps': {'desc': 'list the last played maps', 'syntax': '^7Usage: ^9!lastmaps', 'level': 40},
            'lastvote': {'desc': 'display information about the last called vote', 'syntax': '^7Usage: ^9!lastvote', 'level': 40},
            'leveltest': {'desc': 'get the admin level for a given player or myself', 'syntax': '^7Usage: ^9!leveltest ^7[<name>]', 'level': 40, 'short': 'lt'},
            'list': {'desc': 'list all connected players', 'syntax': '^7Usage: ^9!list', 'level': 40},
            'locate': {'desc': 'display geolocation info of a player', 'syntax': '^7Usage: ^9!locate ^7<name>', 'level': 40, 'short': 'lc'},
            'mute': {'desc': 'mute or un-mute a player', 'syntax': '^7Usage: ^9!mute ^7<name> [<duration>]', 'level': 40},
            'nextmap': {'desc': 'display the next map in rotation', 'syntax': '^7Usage: ^9!nextmap', 'level': 40},
            'poke': {'desc': 'notify a player that he needs to move', 'syntax': '^7Usage: ^9!poke ^7<name>', 'level': 40},
            'seen': {'desc': 'display when a player was last seen', 'syntax': '^7Usage: ^9!seen ^7<name>', 'level': 40},
            'warn': {'desc': 'warn player', 'syntax': '^7Usage: ^9!warn ^7<name> [<reason>]', 'level': 40, 'short': 'w'},
            'warninfo': {'desc': 'display how many warnings a player has', 'syntax': '^7Usage: ^9!warninfo ^7<name>', 'level': 40, 'short': 'wi'},
            'warnremove': {'desc': "remove a player's last warning", 'syntax': '^7Usage: ^9!warnremove ^7<name>', 'level': 40, 'short': 'wr'},
            'warns': {'desc': 'list the warnings', 'syntax': '^7Usage: ^9!warns', 'level': 40},
            'warntest': {'desc': 'test a warning', 'syntax': '^7Usage: ^9!warntest ^7<warning>', 'level': 40},
            'delgoto': {'desc': 'delete goto point', 'syntax': '^7Usage: ^9!delgoto ^7<goto_name>', 'level': 40},
            'setgoto': {'desc': 'set goto point', 'syntax': '^7Usage: ^9!setgoto <jump name>', 'level': 40},
            'setmapinfo': {'desc': 'set info for a map', 'syntax': '^7Usage: ^9!setmapinfo <mapname> <difficulty> <num_jumps> <author(s)>', 'level': 40},
            'delmapinfo': {'desc': 'del info for a map', 'syntax': '^7Usage: ^9!delmapinfo <mapname>', 'level': 40},
            'delmap': {'desc': 'Delete a map from mapcycle', 'syntax': '^7Usage: ^9!delmap <mapname>', 'level': 40},
            'download': {'desc': 'download', 'syntax': '^7Usage: ^9!download <map>', 'level': 40},
            

            # admin commands, level 40
            'admins': {'desc': 'list all the online admins', 'syntax': '^7Usage: ^9!admins', 'level': 40},
            'afk': {'desc': 'force a player to spec, because he is away from keyboard', 'syntax': '^7Usage: ^9!afk ^7<name>', 'level': 40},
            'aliases': {'desc': 'list the aliases of a player', 'syntax': '^7Usage: ^9!aliases ^7<name>', 'level': 40, 'short': 'alias'},
            'bigtext': {'desc': 'display big message on screen', 'syntax': '^7Usage: ^9!bigtext ^7<text>', 'level': 40},
            'exit': {'desc': 'display last disconnected player', 'syntax': '^7Usage: ^9!exit', 'level': 40},
            'find': {'desc': 'display the slot number of a player', 'syntax': '^7Usage: ^9!find ^7<name>', 'level': 40},
            'force': {'desc': 'force a player to the given team', 'syntax': '^7Usage: ^9!force ^7<name> <blue/red/spec> [<lock>]', 'level': 40},
            'kick': {'desc': 'kick a player', 'syntax': '^7Usage: ^9!kick ^7<name> <reason>', 'level': 40, 'short': 'k'},
            'nuke': {'desc': 'nuke a player', 'syntax': '^7Usage: ^9!nuke ^7<name>', 'level': 40},
            'regulars': {'desc': 'display the regular players online', 'syntax': '^7Usage: ^9!regulars', 'level': 40, 'short': 'regs'},
            'say': {'desc': 'say a message to all players', 'syntax': '^7Usage: ^9!say ^7<text>', 'level': 40, 'short': '!!'},
            'tell': {'desc': 'tell a message to a specific player', 'syntax': '^7Usage: ^9!tell ^7<name> <text>', 'level': 40},
            'tempban': {'desc': 'ban a player temporary for the given period of 1 sec to 3 days', 'syntax': '^7Usage: ^9!tempban ^7<name> <duration> [<reason>]', 'level': 40, 'short': 'tb'},
            'warnclear': {'desc': 'clear the player warnings', 'syntax': '^7Usage: ^9!warnclear ^7<name>', 'level': 40, 'short': 'wc'},
            
            # fulladmin commands, level 60
            'ban': {'desc': 'ban a player for several days', 'syntax': '^7Usage: ^9!ban ^7<name> <reason>', 'level': 60, 'short': 'b'},
            'baninfo': {'desc': 'display active bans of a player', 'syntax': '^7Usage: ^9!baninfo ^7<name>', 'level': 60, 'short': 'bi'},
            'ci': {'desc': 'kick player with connection interrupt', 'syntax': '^7Usage: ^9!ci ^7<name>', 'level': 60},
            'ping': {'desc': 'display the ping of a player', 'syntax': '^7Usage: ^9!ping ^7<name>', 'level': 60},
            'id': {'desc': 'show the IP, guid and authname of a player', 'syntax': '^7Usage: ^9!id ^7<name>', 'level': 60},
            'rain': {'desc': 'enables or disables rain', 'syntax': '^7Usage: ^9!rain ^7<on/off>', 'level': 60},
            'scream': {'desc': 'scream a message in different colors to all players', 'syntax': '^7Usage: ^9!scream ^7<text>', 'level': 60},
            'slap': {'desc': 'slap a player (a number of times)', 'syntax': '^7Usage: ^9!slap ^7<name> [<amount>]', 'level': 60},
            'status': {'desc': 'report the status of the bot', 'syntax': '^7Usage: ^9!status', 'level': 60},
            'version': {'desc': 'display the version of the bot', 'syntax': '^7Usage: ^9!version', 'level': 60},
            'veto': {'desc': 'stop voting process', 'syntax': '^7Usage: ^9!veto', 'level': 60},
            
            # senioradmin commands, level 80
            'banall': {'desc': 'ban all players matching pattern', 'syntax': '^7Usage: ^9!banall ^7<pattern> [<reason>]', 'level': 80, 'short': 'ball'},
            'banlist': {'desc': 'display the last active 10 bans', 'syntax': '^7Usage: ^9!banlist', 'level': 80},
            'bots': {'desc': 'enables or disables bot support', 'syntax': '^7Usage: ^9!bots ^7<on/off>', 'level': 80},
            'cyclemap': {'desc': 'cycle to the next map', 'syntax': '^7Usage: ^9!cyclemap', 'level': 80},
            'exec': {'desc': 'execute given config file', 'syntax': '^7Usage: ^9!exec ^7<filename>', 'level': 80},
            'gear': {'desc': 'set allowed weapons', 'syntax': '^7Usage: ^9!gear ^7<default/all/knife/pistol/shotgun/sniper/magnum/mac>', 'level': 80},
            'instagib': {'desc': 'set Instagib mode', 'syntax': '^7Usage: ^9!instagib ^7<on/off>', 'level': 80},
            'kickall': {'desc': 'kick all players matching pattern', 'syntax': '^7Usage: ^9!kickall ^7<pattern> [<reason>]', 'level': 80, 'short': 'kall'},
            'kill': {'desc': 'kill a player', 'syntax': '^7Usage: ^9!kill ^7<name>', 'level': 80},
            'clear': {'desc': 'clear all player warnings', 'syntax': '^7Usage: ^9!clear', 'level': 80, 'short': 'kiss'},
            'lastadmin': {'desc': 'display the last disconnected admin', 'syntax': '^7Usage: ^9!lastadmin', 'level': 80},
            'lastbans': {'desc': 'list the last 4 bans', 'syntax': '^7Usage: ^9!lastbans', 'level': 80, 'short': 'bans'},
            'lookup': {'desc': 'search for a player in the database', 'syntax': '^7Usage: ^9!lookup ^7<name>', 'level': 80, 'short': 'l'},
            'makereg': {'desc': 'make a player a regular (Level 2) user', 'syntax': '^7Usage: ^9!makereg ^7<name>', 'level': 80, 'short': 'mr'},
            'map': {'desc': 'load given map', 'syntax': '^7Usage: ^9!map ^7<ut4_name>', 'level': 80},
            'mapcycle': {'desc': 'list the map rotation', 'syntax': '^7Usage: ^9!mapcycle', 'level': 80},
            'maprestart': {'desc': 'restart the map', 'syntax': '^7Usage: ^9!maprestart', 'level': 80, 'short': 'restart'},
            'moon': {'desc': 'activate low gravity mode (Moon mode)', 'syntax': '^7Usage: ^9!moon ^7<on/off>', 'level': 80, 'short': 'lowgravity'},
            'permban': {'desc': 'ban a player permanent', 'syntax': '^7Usage: ^9!permban ^7<name> <reason>', 'level': 80, 'short': 'pb'},
            'putgroup': {'desc': 'add a client to a group', 'syntax': '^7Usage: ^9!putgroup ^7<name> <group>', 'level': 80},
            'rebuild': {'desc': 'sync up all available maps', 'syntax': '^7Usage: ^9!rebuild', 'level': 80},
            'setgravity': {'desc': 'set the gravity (default: 800)', 'syntax': '^7Usage: ^9!setgravity ^7<value>', 'level': 80},
            'setnextmap': {'desc': 'set the next map', 'syntax': '^7Usage: ^9!setnextmap ^7<ut4_name>', 'level': 80},
            'swapteams': {'desc': 'swap the current teams', 'syntax': '^7Usage: ^9!swapteams', 'level': 80},
            'unban': {'desc': 'unban a player from the database', 'syntax': '^7Usage: ^9!unban ^7<@ID>', 'level': 80},
            'unreg': {'desc': 'remove a player from the regular group', 'syntax': '^7Usage: ^9!unreg ^7<name>', 'level': 80},
            
            # superadmin commands, level 90
            'bomb': {'desc': 'change gametype to Bomb', 'syntax': '^7Usage: ^9!bomb', 'level': 90},
            'ctf': {'desc': 'change gametype to Capture the Flag', 'syntax': '^7Usage: ^9!ctf', 'level': 90},
            'ffa': {'desc': 'change gametype to Free For All', 'syntax': '^7Usage: ^9!ffa', 'level': 90},
            'gametype': {'desc': 'set game type', 'syntax': '^7Usage: ^9!gametype ^7<bomb/ctf/ffa/tdm/ts>', 'level': 90},
            'gungame': {'desc': 'change gametype to Gun Game', 'syntax': '^7Usage: ^9!gungame', 'level': 90},
            'jump': {'desc': 'change gametype to Jump', 'syntax': '^7Usage: ^9!jump', 'level': 90},
            'lms': {'desc': 'change gametype to Last Man Standing', 'syntax': '^7Usage: ^9!lms', 'level': 90},
            'tdm': {'desc': 'change gametype to Team Deathmatch', 'syntax': '^7Usage: ^9!tdm', 'level': 90},
            'ts': {'desc': 'change gametype to Team Survivor', 'syntax': '^7Usage: ^9!ts', 'level': 90},
            'ungroup': {'desc': 'remove admin level from a player', 'syntax': '^7Usage: ^9!ungroup ^7<name>', 'level': 90},
            'password': {'desc': 'set private server password', 'syntax': '^7Usage: ^9!password ^7[<password>]', 'level': 90},
            'reload': {'desc': 'reload map', 'syntax': '^7Usage: ^9!reload', 'level': 90},
            'cvarmap': {'desc': 'Set cvar for the current map', 'syntax': '^7!cvarmap <^8cvar^7> <^8value^7>', 'level': 90}}

REASONS = {'obj': 'go for objective',
           'camp': 'stop camping',
           'spam': 'do not spam, shut-up!',
           'lang': 'bad language',
           'racism': 'racism is not tolerated',
           'ping': 'fix your ping',
           'afk': 'away from keyboard',
           'tk': 'stop team killing',
           'sk': 'stop spawn killing',
           'spec': 'spectator too long on full server',
           'score': 'score too low for this server',
           'ci': 'connection interrupted',
           '999': 'connection interrupted',
           'whiner': 'stop complaining all the time',
           'skill': 'skill too low for this server',
           'name': 'do not use offensive names',
           'wh': 'wallhack',
           'insult': 'stop insulting',
           'autojoin': 'use auto-join',
           'abuse': 'stop abusing others',
           'teams': 'keep the teams even'}


### CLASS Log Parser ###
class LogParser(object):
    """
    log file parser
    """
    def __init__(self):
        """
        create a new instance of LogParser
        """
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        #sysmyks topruns
        self.jump_times = {}  # Stores the current times of each player
        self.records_file = os.path.join(self.base_path, 'mod', 'jump_records.json')
        self.json_path = os.path.join(self.base_path, 'mod', 'goto')
        self.mapinfo = os.path.join(self.base_path, 'mod', 'mapinfo.json')
        self.load_records()
        self.mapcycleway = CONFIG.get('server', 'mapcycle')
        self.custom_cvars_path = os.path.join(HOME, 'mod/map_cvars')
        if not os.path.exists(self.custom_cvars_path):
            os.makedirs(self.custom_cvars_path)
        # hit zone support for UrT > 4.2.013
        self.hit_points = {0: "HEAD", 1: "HEAD", 2: "HELMET", 3: "TORSO", 4: "VEST", 5: "LEFT_ARM", 6: "RIGHT_ARM",
                           7: "GROIN", 8: "BUTT", 9: "LEFT_UPPER_LEG", 10: "RIGHT_UPPER_LEG", 11: "LEFT_LOWER_LEG",
                           12: "RIGHT_LOWER_LEG", 13: "LEFT_FOOT", 14: "RIGHT_FOOT"}
        self.hit_item = {1: "UT_MOD_KNIFE", 2: "UT_MOD_BERETTA", 3: "UT_MOD_DEAGLE", 4: "UT_MOD_SPAS", 5: "UT_MOD_MP5K",
                         6: "UT_MOD_UMP45", 8: "UT_MOD_LR300", 9: "UT_MOD_G36", 10: "UT_MOD_PSG1", 14: "UT_MOD_SR8",
                         15: "UT_MOD_AK103", 17: "UT_MOD_NEGEV", 19: "UT_MOD_M4", 20: "UT_MOD_GLOCK", 21: "UT_MOD_COLT1911",
                         22: "UT_MOD_MAC11", 23: "UT_MOD_BLED"}
        self.death_cause = {1: "MOD_WATER", 3: "MOD_LAVA", 5: "UT_MOD_TELEFRAG", 6: "MOD_FALLING", 7: "UT_MOD_SUICIDE",
                            9: "MOD_TRIGGER_HURT", 10: "MOD_CHANGE_TEAM", 12: "UT_MOD_KNIFE", 13: "UT_MOD_KNIFE_THROWN",
                            14: "UT_MOD_BERETTA", 15: "UT_MOD_DEAGLE", 16: "UT_MOD_SPAS", 17: "UT_MOD_UMP45", 18: "UT_MOD_MP5K",
                            19: "UT_MOD_LR300", 20: "UT_MOD_G36", 21: "UT_MOD_PSG1", 22: "UT_MOD_HK69", 23: "UT_MOD_BLED",
                            24: "UT_MOD_KICKED", 25: "UT_MOD_HEGRENADE", 28: "UT_MOD_SR8", 30: "UT_MOD_AK103",
                            31: "UT_MOD_SPLODED", 32: "UT_MOD_SLAPPED", 33: "UT_MOD_SMITED", 34: "UT_MOD_BOMBED",
                            35: "UT_MOD_NUKED", 36: "UT_MOD_NEGEV", 37: "UT_MOD_HK69_HIT", 38: "UT_MOD_M4",
                            39: "UT_MOD_GLOCK", 40: "UT_MOD_COLT1911", 41: "UT_MOD_MAC11"}

        # RCON commands for the different admin roles
        self.user_cmds = []
        self.mod_cmds = []
        self.admin_cmds = []
        self.fulladmin_cmds = []
        self.senioradmin_cmds = []
        self.superadmin_cmds = []
        # dictionary of shortcut commands
        self.shortcut_cmd = {}

        for key, value in COMMANDS.iteritems():
            if 'short' in value:
                self.shortcut_cmd[value['short']] = key
            if value['level'] == 20:
                self.mod_cmds.append(key)
                self.admin_cmds.append(key)
                self.fulladmin_cmds.append(key)
                self.senioradmin_cmds.append(key)
                self.superadmin_cmds.append(key)
            elif value['level'] == 40:
                self.admin_cmds.append(key)
                self.fulladmin_cmds.append(key)
                self.senioradmin_cmds.append(key)
                self.superadmin_cmds.append(key)
            elif value['level'] == 60:
                self.fulladmin_cmds.append(key)
                self.senioradmin_cmds.append(key)
                self.superadmin_cmds.append(key)
            elif value['level'] == 80:
                self.senioradmin_cmds.append(key)
                self.superadmin_cmds.append(key)
            elif value['level'] >= 90:
                self.superadmin_cmds.append(key)
            else:
                self.user_cmds.append(key)
                self.mod_cmds.append(key)
                self.admin_cmds.append(key)
                self.fulladmin_cmds.append(key)
                self.senioradmin_cmds.append(key)
                self.superadmin_cmds.append(key)

        # alphabetic sort of the commands
        self.user_cmds.sort()
        self.mod_cmds.sort()
        self.admin_cmds.sort()
        self.fulladmin_cmds.sort()
        self.senioradmin_cmds.sort()
        self.superadmin_cmds.sort()

        logger.info("Starting logging      : OK")
        games_log = CONFIG.get('server', 'log_file')

        self.ffa_lms_gametype = False
        self.ctf_gametype = False
        self.ts_gametype = False
        self.tdm_gametype = False
        self.bomb_gametype = False
        self.freeze_gametype = False
        self.ts_do_team_balance = False
        self.allow_cmd_teams = True
        self.urt_modversion = None
        self.game = None
        self.players_lock = RLock()
        self.firstblood = False
        self.firstnadekill = False
        self.firstknifekill = False
        self.firstteamkill = False
        self.last_disconnected_player = None
        self.last_admin = None
        self.allow_nextmap_vote = True
        self.failed_vote_timer = 0
        self.last_vote = ''
        self.default_gear = ''

        # enable/disable autokick for team killing
        self.tk_autokick = CONFIG.getboolean('bot', 'teamkill_autokick') if CONFIG.has_option('bot', 'teamkill_autokick') else True
        self.allow_tk_bots = CONFIG.getboolean('bot', 'allow_teamkill_bots') if CONFIG.has_option('bot', 'allow_teamkill_bots') else False
        # enable/disable autokick of players with low score
        self.noob_autokick = CONFIG.getboolean('bot', 'noob_autokick') if CONFIG.has_option('bot', 'noob_autokick') else False
        self.spawnkill_autokick = CONFIG.getboolean('bot', 'spawnkill_autokick') if CONFIG.has_option('bot', 'spawnkill_autokick') else False
        self.kill_spawnkiller = CONFIG.getboolean('bot', 'instant_kill_spawnkiller') if CONFIG.has_option('bot', 'instant_kill_spawnkiller') else False
        self.spawnkill_warn_time = CONFIG.getint('bot', 'spawnkill_warn_time') if CONFIG.has_option('bot', 'spawnkill_warn_time') else 3
        self.admin_immunity = CONFIG.getint('bot', 'admin_immunity') if CONFIG.has_option('bot', 'admin_immunity') else 40
        # set the maximum allowed ping
        self.max_ping = CONFIG.getint('bot', 'max_ping') if CONFIG.has_option('bot', 'max_ping') else 200
        # kick spectator on full server
        self.num_kick_specs = CONFIG.getint('bot', 'kick_spec_full_server') if CONFIG.has_option('bot', 'kick_spec_full_server') else 10
        # set task frequency
        self.task_frequency = CONFIG.getint('bot', 'task_frequency') if CONFIG.has_option('bot', 'task_frequency') else 60
        self.warn_expiration = CONFIG.getint('bot', 'warn_expiration') if CONFIG.has_option('bot', 'warn_expiration') else 240
        self.bad_words_autokick = CONFIG.getint('bot', 'bad_words_autokick') if CONFIG.has_option('bot', 'bad_words_autokick') else 0
        # enable/disable message 'Player connected from...'
        self.show_country_on_connect = CONFIG.getboolean('bot', 'show_country_on_connect') if CONFIG.has_option('bot', 'show_country_on_connect') else True
        # enable/disable message 'Firstblood / first nade kill...'
        self.show_first_kill_msg = CONFIG.getboolean('bot', 'show_first_kill') if CONFIG.has_option('bot', 'show_first_kill') else True
        self.show_hit_stats_msg = CONFIG.getboolean('bot', 'show_hit_stats_respawn') if CONFIG.has_option('bot', 'show_hit_stats_respawn') else True
        self.show_multikill_msg = CONFIG.getboolean('bot', 'show_multi_kill') if CONFIG.has_option('bot', 'show_multi_kill') else True
        # set teams autobalancer
        self.teams_autobalancer = CONFIG.getboolean('bot', 'autobalancer') if CONFIG.has_option('bot', 'autobalancer') else False
        self.allow_cmd_teams_round_end = CONFIG.getboolean('bot', 'allow_teams_round_end') if CONFIG.has_option('bot', 'allow_teams_round_end') else False
        self.limit_nextmap_votes = CONFIG.getboolean('bot', 'limit_nextmap_votes') if CONFIG.has_option('bot', 'limit_nextmap_votes') else False
        self.vote_delay = CONFIG.getint('bot', 'vote_delay') if CONFIG.has_option('bot', 'vote_delay') else 0
        self.spam_bomb_planted_msg = CONFIG.getboolean('bot', 'spam_bomb_planted') if CONFIG.has_option('bot', 'spam_bomb_planted') else False
        self.kill_survived_opponents = CONFIG.getboolean('bot', 'kill_survived_opponents') if CONFIG.has_option('bot', 'kill_survived_opponents') else False
        self.spam_knife_kills_msg = CONFIG.getboolean('bot', 'spam_knife_kills') if CONFIG.has_option('bot', 'spam_knife_kills') else False
        self.spam_nade_kills_msg = CONFIG.getboolean('bot', 'spam_nade_kills') if CONFIG.has_option('bot', 'spam_nade_kills') else False
        self.spam_headshot_hits_msg = CONFIG.getboolean('bot', 'spam_headshot_hits') if CONFIG.has_option('bot', 'spam_headshot_hits') else False
        self.reset_headshot_hits_mapcycle = CONFIG.getboolean('bot', 'reset_headshot_hits_mapcycle') if CONFIG.has_option('bot', 'reset_headshot_hits_mapcycle') else True
        self.reset_kill_spree_mapcycle = CONFIG.getboolean('bot', 'reset_kill_spree_mapcycle') if CONFIG.has_option('bot', 'reset_kill_spree_mapcycle') else True
        ban_duration = CONFIG.getint('bot', 'ban_duration') if CONFIG.has_option('bot', 'ban_duration') else 7
        self.ban_duration = ban_duration if ban_duration > 0 else 1
        # support for low gravity server
        self.support_lowgravity = CONFIG.getboolean('lowgrav', 'support_lowgravity') if CONFIG.has_option('lowgrav', 'support_lowgravity') else False
        self.gravity = CONFIG.getint('lowgrav', 'gravity') if CONFIG.has_option('lowgrav', 'gravity') else 800
        self.explode_time = "40"
        # log that the configuration file has been loaded
        logger.info("Configuration loaded  : OK")
        # enable/disable option to get Head Admin by checking existence of head admin in database
        curs.execute("SELECT COUNT(*) FROM `xlrstats` WHERE `admin_role` = 100")
        self.iamgod = True if int(curs.fetchone()[0]) < 1 else False
        logger.info("Connecting to Database: OK")
        logger.debug("Cmd !iamgod available : %s", self.iamgod)
        self.uptime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        # Rotating Messages and Rules
        if CONFIG.has_option('rules', 'show_rules') and CONFIG.getboolean('rules', 'show_rules'):
            self.output_rules = CONFIG.get('rules', 'display') if CONFIG.has_option('rules', 'display') else "chat"
            rules_frequency = CONFIG.getint('rules', 'rules_frequency') if CONFIG.has_option('rules', 'rules_frequency') else 90
            self.rules_file = os.path.join(HOME, 'conf', 'rules.conf')
            self.rules_frequency = rules_frequency if rules_frequency > 0 else 10
            if os.path.isfile(self.rules_file):
                self.thread_rotate()
                logger.info("Load rotating messages: OK")
            else:
                logger.error("ERROR: Rotating messages will be ignored, file '%s' has not been found", self.rules_file)
        # Parse Game log file
        try:
            # open game log file
            self.log_file = open(games_log, 'r')
        except IOError:
            logger.error("ERROR: The Gamelog file '%s' has not been found", games_log)
            logger.error("*** Aborting Spunky Bot ***")
        else:
            # go to the end of the file
            self.log_file.seek(0, 2)
            # start parsing the games logfile
            logger.info("Parsing Gamelog file  : %s", games_log)
            self.read_log()

    def thread_rotate(self):
        """
        Thread process for starting method rotate_messages
        """
        processor = Thread(target=self.rotating_messages)
        processor.setDaemon(True)
        processor.start()

    def rotating_messages(self):
        """
        display rotating messages and rules
        """
        # initial wait
        time.sleep(30)
        while 1:
            with open(self.rules_file, 'r') as filehandle:
                rotation_msg = filehandle.readlines()
            if not rotation_msg:
                break
            for line in rotation_msg:
                # display rule
                with self.players_lock:
                    if "@admins" in line:
                        self.game.rcon_say(self.get_admins_online())
                    elif "@admincount" in line:
                        self.game.rcon_say(self.get_admin_count())
                    elif "@nextmap" in line:
                        self.game.rcon_say(self.get_nextmap())
                    elif "@time" in line:
                        self.game.rcon_say("^7Time: %s" % time.strftime("%H:%M", time.localtime(time.time())))
                    elif "@bigtext" in line:
                        self.game.rcon_bigtext("^7%s" % line.split('@bigtext')[-1].strip())
                    else:
                        if self.output_rules == 'chat':
                            self.game.rcon_say("^9%s" % line.strip())
                        elif self.output_rules == 'bigtext':
                            self.game.rcon_bigtext("^9%s" % line.strip())
                        else:
                            self.game.send_rcon("^9%s" % line.strip())
                # wait for given delay in the config file
                time.sleep(self.rules_frequency)

    def find_game_start(self):
        """
        find InitGame start
        """
        seek_amount = 768
        # search within the specified range for the InitGame message
        start_pos = self.log_file.tell() - seek_amount
        end_pos = start_pos + seek_amount
        try:
            self.log_file.seek(start_pos)
        except IOError:
            logger.error("ERROR: The games.log file is empty, ignoring game type and start")
            # go to the end of the file
            self.log_file.seek(0, 2)
            game_start = True
        else:
            game_start = False
        while not game_start:
            while self.log_file:
                line = self.log_file.readline()
                tmp = line.split()
                if len(tmp) > 1 and tmp[1] == "InitGame:":
                    game_start = True
                    if 'g_modversion\\4.3' in line:
                        self.hit_item.update({23: "UT_MOD_FRF1", 24: "UT_MOD_BENELLI", 25: "UT_MOD_P90",
                                              26: "UT_MOD_MAGNUM", 29: "UT_MOD_KICKED", 30: "UT_MOD_KNIFE_THROWN"})
                        self.death_cause.update({42: "UT_MOD_FRF1", 43: "UT_MOD_BENELLI", 44: "UT_MOD_P90", 45: "UT_MOD_MAGNUM",
                                                 46: "UT_MOD_TOD50", 47: "UT_MOD_FLAG", 48: "UT_MOD_GOOMBA"})
                        self.urt_modversion = 43
                        logger.info("Game modversion       : 4.3")
                    elif 'g_modversion\\4.2' in line:
                        self.hit_item.update({23: "UT_MOD_BLED", 24: "UT_MOD_KICKED", 25: "UT_MOD_KNIFE_THROWN"})
                        self.death_cause.update({42: "UT_MOD_FLAG", 43: "UT_MOD_GOOMBA"})
                        self.urt_modversion = 42
                        logger.info("Game modversion       : 4.2")
                    elif 'g_modversion\\4.1' in line:
                        # hit zone support for UrT 4.1
                        self.hit_points = {0: "HEAD", 1: "HELMET", 2: "TORSO", 3: "KEVLAR", 4: "ARMS", 5: "LEGS", 6: "BODY"}
                        self.hit_item.update({21: "UT_MOD_KICKED", 22: "UT_MOD_KNIFE_THROWN"})
                        self.death_cause.update({33: "UT_MOD_BOMBED", 34: "UT_MOD_NUKED", 35: "UT_MOD_NEGEV",
                                                 39: "UT_MOD_FLAG", 40: "UT_MOD_GOOMBA"})
                        self.urt_modversion = 41
                        logger.info("Game modversion       : 4.1")

                    if 'g_gametype\\0\\' in line or 'g_gametype\\1\\' in line or 'g_gametype\\9\\' in line or 'g_gametype\\11\\' in line:
                        # disable teamkill event and some commands for FFA (0), LMS (1), Jump (9), Gun (11)
                        self.ffa_lms_gametype = True
                    elif 'g_gametype\\7\\' in line:
                        self.ctf_gametype = True
                    elif 'g_gametype\\4\\' in line or 'g_gametype\\5\\' in line:
                        self.ts_gametype = True
                    elif 'g_gametype\\3\\' in line:
                        self.tdm_gametype = True
                    elif 'g_gametype\\8\\' in line:
                        self.bomb_gametype = True
                    elif 'g_gametype\\10\\' in line:
                        self.freeze_gametype = True

                    # get default g_gear value
                    self.default_gear = line.split('g_gear\\')[-1].split('\\')[0] if 'g_gear\\' in line else "%s" % '' if self.urt_modversion > 41 else '0'

                if self.log_file.tell() > end_pos:
                    break
                elif not line:
                    break
            if self.log_file.tell() < seek_amount:
                self.log_file.seek(0, 0)
            else:
                cur_pos = start_pos - seek_amount
                end_pos = start_pos
                start_pos = cur_pos
                start_pos = max(start_pos, 0)
                self.log_file.seek(start_pos)

    def read_log(self):
        """
        read the logfile
        """
        if self.task_frequency > 0:
            # schedule the task
            if self.task_frequency < 10:
                # avoid flooding with too less delay
                schedule.every(10).seconds.do(self.taskmanager)
            else:
                schedule.every(self.task_frequency).seconds.do(self.taskmanager)
        # schedule the task
        schedule.every(2).hours.do(self.remove_expired_db_entries)

        self.find_game_start()

        # create instance of Game
        self.game = Game(self.urt_modversion)

        self.log_file.seek(0, 2)
        while self.log_file:
            schedule.run_pending()
            line = self.log_file.readline()
            if line:
                self.parse_line(line)
            else:
                if not self.game.live:
                    self.game.go_live()
                time.sleep(.125)

    def remove_expired_db_entries(self):
        """
        delete expired ban points
        """
        # remove expired ban_points
        curs.execute("DELETE FROM `ban_points` WHERE `expires` < '{}'".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        conn.commit()

    def taskmanager(self):
        """
        - check warnings and kick players with too many warnings
        - check for spectators and set warning
        - check for players with low score and set warning
        """
        try:
            with self.players_lock:
                # get number of connected players
                counter = self.game.get_number_players()

                # check amount of warnings and kick player if needed
                for player in self.game.players.itervalues():
                    player_num = player.get_player_num()
                    if player_num == BOT_PLAYER_NUM:
                        continue
                    player_name = player.get_name()
                    player_admin_role = player.get_admin_role()

                    # clear expired warnings
                    if self.warn_expiration > 0 and player.get_warning() > 0 and player.get_last_warn_time() and player.get_last_warn_time() + self.warn_expiration < time.time():
                        player.clear_warning()

                    # kick player with 3 or more warnings, Admins will never get kicked
                    if player.get_warning() > 2 and player_admin_role < 40:
                        if 'spectator' in player.get_last_warn_msg():
                            kick_msg = reason = "spectator too long on full server"
                        elif 'ping' in player.get_last_warn_msg():
                            kick_msg = "ping too high for this server ^7[^4%s^7]" % player.get_ping_value()
                            reason = "fix your ping"
                        elif 'score' in player.get_last_warn_msg():
                            kick_msg = reason = "score too low for this server"
                        elif 'team killing' in player.get_last_warn_msg():
                            kick_msg = reason = "team killing over limit"
                            player.add_ban_point('auto-kick for team killing', 600)
                        else:
                            kick_msg = reason = "too many warnings"
                        self.game.rcon_say("^9%s ^7was kicked, %s" % (player_name, kick_msg))
                        self.game.kick_player(player_num, reason=reason)
                        continue

                    # check for spectators and set warning
                    if self.num_kick_specs > 0 and player_admin_role < 20:
                        # ignore player with name prefix GTV-
                        if 'GTV-' in player_name:
                            continue
                        # if player is spectator on full server, inform player and increase warn counter
                        # GTV or Moderator or higher levels will not get the warning
                        elif counter > self.num_kick_specs and player.get_team() == 3 and player.get_time_joined() < (time.time() - 30):
                            player.add_warning(warning='spectator too long on full server', timer=False)
                            logger.debug("%s is spectator too long on full server", player_name)
                            warnmsg = "^8WARNING ^7[^7%d^7]: You are spectator too long on full server" % player.get_warning()
                            self.game.rcon_tell(player_num, warnmsg, False)
                        # reset spec warning
                        else:
                            player.clear_specific_warning('spectator too long on full server')

                    # check for players with low score and set warning
                    if self.noob_autokick and player_admin_role < 2 and player.get_ip_address() != '0.0.0.0':
                        kills = player.get_kills()
                        deaths = player.get_deaths()
                        ratio = round(float(kills) / float(deaths), 2) if deaths > 0 else 1.0
                        # if player ratio is too low, inform player and increase warn counter
                        # Regulars or higher levels will not get the warning
                        if kills > 0 and ratio < 0.33:
                            player.add_warning(warning='score too low for this server', timer=False)
                            logger.debug("Score of %s is too low, ratio: %s", player_name, ratio)
                            warnmsg = "^8WARNING ^7[^7%d^7]: Your score is too low for this server" % player.get_warning()
                            self.game.rcon_tell(player_num, warnmsg, False)
                        else:
                            player.clear_specific_warning('score too low for this server')

                    # warn player with 3 warnings, Admins will never get the alert warning
                    if player.get_warning() == 3 and player_admin_role < 40:
                        self.game.rcon_say("^8ALERT: ^9%s ^7auto-kick from warnings if not cleared" % player_name)

                # check for player with high ping
                self.check_player_ping()

        except Exception as err:
            logger.error(err, exc_info=True)

    def check_player_ping(self):
        
        if self.max_ping > 0:
            # rcon update status
            self.game.quake.rcon_update()
            for player in self.game.quake.players or []:
                # if ping is too high, increase warn counter, Admins or higher levels will not get the warning
                try:
                    ping_value = player.ping
                    gameplayer = self.game.players[player.num]
                except KeyError:
                    continue
                else:
                    if self.max_ping < ping_value < 999 and gameplayer.get_admin_role() < self.admin_immunity:
                        gameplayer.add_high_ping(ping_value)
                        self.game.rcon_tell(player.num, "^8WARNING ^7[^7%d^7]: Your ping is too high [^4%d^7]. ^7The maximum allowed ping is %d." % (gameplayer.get_warning(), ping_value, self.max_ping), False)
                    else:
                        gameplayer.clear_specific_warning('fix your ping')
    
    #sysmyks topruns
    def save_map_info(self, map_name, author, jumps, difficulty):
        """Save map info to the mapinfo.json file"""
        if os.path.exists(self.mapinfo):
            try:
                with open(self.mapinfo, 'r') as f:
                    maps_data = json.load(f)
            except json.JSONDecodeError:
                maps_data = {}
        else:
            maps_data = {}
            
        maps_data[map_name] = {
            "author": author,
            "jumps": jumps,
            "difficulty": [difficulty, ""]  # Format expected by !mapinfo
        }
    
        try:
            with open(self.mapinfo, 'w') as f:
                json.dump(maps_data, f, indent=4)
            return True
        except Exception as e:
            logger.error("Error saving map info: %s", e)
            return False
    
    def delete_map_info(self, map_name):
        """Delete map info from the mapinfo.json file"""
        if os.path.exists(self.mapinfo):
            try:
                with open(self.mapinfo, "r") as file:
                    maps_data = json.load(file)
                    
                if map_name in maps_data:
                    del maps_data[map_name]
                    
                    with open(self.mapinfo, "w") as file:
                        json.dump(maps_data, file, indent=4, sort_keys=True)
                    return True
                else:
                    return False
                    
            except Exception as e:
                logger.error("Error deleting map info: %s", str(e))
                return False
        else:
            logger.error("mapinfo.json not found")
            return False
    
    def delete_position_from_json(self, sar, jump_name):
        """
        Delete a position from the JSON file for the current map
        """
        current_map = self.get_current_map()
        if not current_map:
            self.tell_say_message(sar, "^8Unable to retrieve current map.")
            return

        map_json_file = os.path.join(self.json_path, "{}.json".format(current_map))
        
        if not os.path.exists(map_json_file):
            self.tell_say_message(sar, "^8No positions file found for map: {}".format(current_map))
            return

        try:
            with open(map_json_file, 'r') as file:
                map_data = json.load(file)
                
            if jump_name in map_data:
                del map_data[jump_name]
                with open(map_json_file, 'w') as file:
                    json.dump(map_data, file, indent=4)
                self.tell_say_message(sar, "^9Position '{}' successfully deleted.".format(jump_name))
            else:
                self.tell_say_message(sar, "^8No position found with name: {}".format(jump_name))
                
        except Exception as e:
            self.tell_say_message(sar, "^8Error deleting position: {}".format(e))


    def get_jump_records(self, map_name):
        if os.path.exists(self.records_file):
            try:
                with open(self.records_file, "r") as file:
                    records_data = json.load(file)
                return records_data.get(map_name, {})
            except json.JSONDecodeError:
                logger.error("Error decoding {}".format(self.records_file))
                return {}
        else:
            logger.error("{} not found".format(self.records_file))
            return {}
    
    def load_records(self):
        """Loads records from the JSON file and verifies data validity."""
        if os.path.exists(self.records_file):
            try:
                with open(self.records_file, 'r') as f:
                    self.jump_records = json.load(f)
                    
                    # Verify data to avoid accidental duplicates
                    for map_name, players in self.jump_records.items():
                        for player, ways in players.items():
                            # Convert all "way" keys to strings to avoid errors
                            self.jump_records[map_name][player] = {str(k): v for k, v in ways.items()}
                    
            except (json.JSONDecodeError, IOError):
                self.jump_records = {}
                logger.warning("Invalid or missing JSON file, initializing empty.")
        else:
            self.jump_records = {}


    def save_records(self):
        """
        Saves records without duplicates to the JSON file with proper error handling
        """
        try:
            # Check if directory exists
            records_dir = os.path.dirname(self.records_file)
            if not os.path.exists(records_dir):
                os.makedirs(records_dir)
                logger.info("Creating directory for records: %s", records_dir)
            
            # Save data to a temporary file first
            temp_file = self.records_file + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.jump_records, f, indent=4, sort_keys=True)
            
            # Instead of os.replace (Python 3 only), use os.rename for Python 2.7
            # First delete the target file if it exists
            if os.path.exists(self.records_file):
                os.remove(self.records_file)
            os.rename(temp_file, self.records_file)
            
            logger.debug("Records saved successfully to %s", self.records_file)
            return True
        except Exception as e:
            logger.error("Error saving records: %s", str(e), exc_info=True)
            return False
        
    

      

   
    
        # Add these new methods
    def save_map_cvar(self, map_name, cvar, value):
        """Save custom cvar for a specific map"""
        map_file = os.path.join(self.custom_cvars_path, "%s.cfg" % map_name)
        try:
            # Read existing cvars
            cvars = {}
            if os.path.exists(map_file):
                with open(map_file, 'r') as f:
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=')
                            cvars[k.strip()] = v.strip()
            
            # Add or update cvar
            cvars[cvar] = value
            
            # Save back to file
            with open(map_file, 'w') as f:
                for k, v in cvars.items():
                    f.write("%s=%s\n" % (k, v))
            return True
        except Exception as e:
            logger.error("Error saving map cvar: %s" % e)
            return False

    def load_map_cvars(self, map_name):
        """Load and apply custom cvars for a map"""
        map_file = os.path.join(self.custom_cvars_path, "%s.cfg" % map_name)
        if os.path.exists(map_file):
            try:
                with open(map_file, 'r') as f:
                    for line in f:
                        if '=' in line:
                            cvar, value = line.strip().split('=')
                            self.game.send_rcon('%s %s' % (cvar, value))
                logger.info("Applied custom cvars for map: %s" % map_name)
                return True
            except Exception as e:
                logger.error("Error loading map cvars: %s" % e)
        return False
    
    def add_pending_message(self, sar, recipient_name, message):
        """
        Add a message that will be delivered when the player connects
        """
        # First search among connected players
        found, victim, msg = self.player_found(recipient_name)
        recipient_info = None
        
        if found:
            # Player found online
            recipient_info = {
                'id': victim.get_player_id(),
                'name': victim.get_name(),
                'guid': victim.get_guid(),
                'ip': victim.get_ip_address()
            }
        else:
            # Player not connected, search in the database
            try:
                # Search with partial name match
                curs.execute("SELECT `id`, `name`, `guid`, `ip_address` FROM `player` WHERE `name` LIKE '%{}%' ORDER BY `time_joined` DESC LIMIT 1".format(recipient_name))
                result = curs.fetchone()
                
                if result:
                    recipient_info = {
                        'id': result[0],
                        'name': result[1],
                        'guid': result[2],
                        'ip': result[3] if result[3] else 'unknown'
                    }
                    self.game.rcon_tell(sar['player_num'], "^7Player ^9{} ^7found in database.".format(recipient_info['name']))
                else:
                    self.game.rcon_tell(sar['player_num'], "^7Player not found: {}".format(recipient_name))
                    return
            except Exception as e:
                logger.error("Error searching player in database: %s", e)
                self.game.rcon_tell(sar['player_num'], "^8Error searching player: {}".format(e))
                return
        
        # Create the message
        sender_name = self.game.players[sar['player_num']].get_name()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        
        # Load existing messages
        pending_messages = {}
        messages_file = os.path.join(self.base_path, 'mod', "pending_messages.json")
        
        if os.path.exists(messages_file):
            try:
                with open(messages_file, 'r') as file:
                    pending_messages = json.load(file)
            except json.JSONDecodeError:
                pending_messages = {}
        
        # Find the player ID
        recipient_key = None
        for key in pending_messages:
            if (pending_messages[key]['guid'] == recipient_info['guid'] or 
                pending_messages[key]['name'].lower() == recipient_info['name'].lower()):
                recipient_key = key
                break
        
        # Create a new entry if the player doesn't exist in the file
        if not recipient_key:
            recipient_key = str(recipient_info['id'])
            pending_messages[recipient_key] = {
                'guid': recipient_info['guid'],
                'name': recipient_info['name'], 
                'ip': recipient_info['ip'],
                'messages': []
            }
        
        # Add the message
        pending_messages[recipient_key]['messages'].append({
            'sender': sender_name,
            'message': message,
            'timestamp': timestamp
        })
        
        # Save to JSON file
        try:
            with open(messages_file, 'w') as file:
                json.dump(pending_messages, file, indent=4)
            self.game.rcon_tell(sar['player_num'], "^7Message for ^9{} ^7saved. It will be delivered on next connection.".format(recipient_info['name']))
        except Exception as e:
            self.game.rcon_tell(sar['player_num'], "^8Error saving message: {}".format(e))

    def delete_pending_messages(self, sar, recipient_name):
        """
        Delete all pending messages for a player
        """
        # First, try to find the player among those connected
        found, victim, msg = self.player_found(recipient_name)
        recipient_info = None
        
        if found:
            recipient_info = {
                'id': victim.get_player_id(),
                'name': victim.get_name(),
                'guid': victim.get_guid()
            }
        else:
            # Player not connected, search in the database
            try:
                curs.execute("SELECT `id`, `name`, `guid` FROM `player` WHERE `name` LIKE '%{}%' ORDER BY `time_joined` DESC LIMIT 1".format(recipient_name))
                result = curs.fetchone()
                
                if result:
                    recipient_info = {
                        'id': result[0],
                        'name': result[1],
                        'guid': result[2]
                    }
                    self.game.rcon_tell(sar['player_num'], "^7Player ^9{} ^7found in database.".format(recipient_info['name']))
            except Exception as e:
                logger.error("Error searching player in database: %s", e)
        
        # Load existing messages
        messages_file = os.path.join(self.base_path, 'mod', "pending_messages.json")
        if not os.path.exists(messages_file):
            self.game.rcon_tell(sar['player_num'], "^7No pending messages")
            return
        
        try:
            with open(messages_file, 'r') as file:
                pending_messages = json.load(file)
        except json.JSONDecodeError:
            pending_messages = {}
        
        # Find the player ID
        recipient_key = None
        for key in pending_messages:
            if recipient_info and (pending_messages[key]['guid'] == recipient_info['guid']):
                recipient_key = key
                break
            elif pending_messages[key]['name'].lower() == recipient_name.lower():
                recipient_key = key
                break
        
        if recipient_key:
            player_name = pending_messages[recipient_key]['name']
            del pending_messages[recipient_key]
            # Save the updated file
            try:
                with open(messages_file, 'w') as file:
                    json.dump(pending_messages, file, indent=4)
                self.game.rcon_tell(sar['player_num'], "^7All pending messages for ^9{} ^7have been deleted.".format(player_name))
            except Exception as e:
                self.game.rcon_tell(sar['player_num'], "^8Error deleting messages: {}".format(e))
        else:
            self.game.rcon_tell(sar['player_num'], "^7No pending messages found for player {}".format(recipient_name))

    def check_pending_messages(self, player):
        """
        Check and deliver pending messages for the player
        """
        messages_file = os.path.join(self.base_path, 'mod', "pending_messages.json")
        if not os.path.exists(messages_file):
            return
        
        try:
            with open(messages_file, 'r') as file:
                pending_messages = json.load(file)
        except json.JSONDecodeError:
            return
        
        # Check if player has messages
        player_guid = player.get_guid()
        player_name = player.get_name()
        player_id = str(player.get_player_id())
        
        # Look for the player by guid, name or ID
        recipient_key = None
        for key in pending_messages:
            if (pending_messages[key]['guid'] == player_guid or 
                pending_messages[key]['name'].lower() == player_name.lower() or
                key == player_id):
                recipient_key = key
                break
        
        if recipient_key:
            messages = pending_messages[recipient_key]['messages']
            if messages:
                # Send an initial message to notify the player
                self.game.rcon_tell(player.get_player_num(), "^9You have {} pending message(s):".format(len(messages)))
                
                # Send each message
                for msg in messages:
                    time_obj = datetime.strptime(msg['timestamp'], "%Y-%m-%d %H:%M:%S")
                    time_format = time_obj.strftime("%d-%m %H:%M")
                    self.game.rcon_tell(player.get_player_num(), "^7[^9{}^7] from ^9{}: ^7{}".format(time_format, msg['sender'], msg['message']))
                
                # Delete messages now that they've been delivered
                del pending_messages[recipient_key]
                
                # Save the updated file
                with open(messages_file, 'w') as file:
                    json.dump(pending_messages, file, indent=4)
    
    def parse_line(self, string):
        """
        parse the logfile and search for specific action
        """
        line = string[7:]
        tmp = line.split(":", 1)
        line = tmp[1].strip() if len(tmp) > 1 else tmp[0].strip()
        option = {'InitGame': self.new_game, 'Warmup': self.handle_warmup, 'InitRound': self.handle_initround,
                  'Exit': self.handle_exit, 'say': self.handle_say, 'sayteam': self.handle_say, 'saytell': self.handle_saytell,
                  'ClientUserinfo': self.handle_userinfo, 'ClientUserinfoChanged': self.handle_userinfo_changed,
                  'ClientBegin': self.handle_begin, 'ClientDisconnect': self.handle_disconnect,
                  'SurvivorWinner': self.handle_teams_ts_mode, 'Kill': self.handle_kill, 'Hit': self.handle_hit,
                  'Freeze': self.handle_freeze, 'ThawOutFinished': self.handle_thawout, 'ClientSpawn': self.handle_spawn,
                  'Flag': self.handle_flag, 'FlagCaptureTime': self.handle_flagcapturetime,
                  'VotePassed': self.handle_vote_passed, 'VoteFailed': self.handle_vote_failed, 'Callvote': self.handle_callvote,
                  'ClientJumpRunStarted' : self.handle_jump_run_started, 'ClientJumpRunCanceled' : self.handle_jump_run_canceled, 
                  'ClientJumpRunStopped' : self.handle_jump_run_stopped}
        try:
            action = tmp[0].strip()
            if action in option:
                option[action](line)
            elif 'Bomb' in action:
                self.handle_bomb(line)
            elif 'Pop' in action:
                self.handle_bomb_exploded()
        except (IndexError, KeyError):
            pass
        except Exception as err:
            logger.error(err, exc_info=True)

    def explode_line(self, line):
        """
        explode line
        """
        arr = line.lstrip().lstrip('\\').split('\\')
        key = True
        key_val = None
        values = {}
        for item in arr:
            if key:
                key_val = item
                key = False
            else:
                values[key_val.rstrip()] = item.rstrip()
                key_val = None
                key = True
        return values

    def handle_vote_passed(self, line):
        """
        handle vote passed
        """
        # nextmap vote
        if "g_nextmap" in line:
            self.game.next_mapname = line.split("g_nextmap")[-1].strip('"').strip()
            self.game.rcon_say("^7Vote to set next map to '%s' ^9passed" % self.game.next_mapname)
            self.allow_nextmap_vote = False
        # cyclemap vote
        elif "cyclemap" in line:
            self.game.rcon_say("^7Vote to cycle map ^9passed")
        # kick vote
        elif "clientkickreason" in line:
            self.game.rcon_say("^7Vote to kick %s ^9passed" % self.game.players[int(line.split('"clientkickreason "')[-1].strip('"'))].get_name())

    def handle_vote_failed(self, line):
        """
        handle vote failed
        """
        # nextmap vote
        if "g_nextmap" in line:
            self.game.rcon_say("^7Vote to set next map to '%s' ^8failed" % line.split("g_nextmap")[-1].strip('"').strip())
            if self.vote_delay:
                self.failed_vote_timer = time.time() + self.vote_delay
        # cyclemap vote
        elif "cyclemap" in line:
            self.game.rcon_say("^7Vote to cycle map ^8failed")
        # kick vote
        elif "clientkickreason" in line:
            self.game.rcon_say("^7Vote to kick %s ^8failed" % self.game.players[int(line.split('"clientkickreason "')[-1].strip('"'))].get_name())

    def handle_callvote(self, line):
        """
        handle callvote
        """
        if "g_nextmap" in line:
            self.last_vote = "nextmap"
        elif "cyclemap" in line:
            self.last_vote = "cyclemap"
        elif "clientkickreason" in line:
            self.last_vote = "kick"

        spam_msg = True
        now = time.time()
        if "g_nextmap" in line and self.limit_nextmap_votes and not self.allow_nextmap_vote:
            self.game.send_rcon('veto')
            self.game.rcon_say("^7Voting for Next Map is disabled until the end of this map")
            spam_msg = False
        if "map" in line and self.failed_vote_timer > now:
            remaining_time = int(self.failed_vote_timer - now)
            self.game.send_rcon('veto')
            self.game.rcon_say("^7Map voting is disabled for ^9%d ^7seconds" % remaining_time)
        if spam_msg:
            self.game.rcon_bigtext("^7Press ^9F1 ^7or ^8F2 ^7to vote!")
            if self.game.get_last_maps() and ('"g_nextmap' in line or '"map' in line):
                self.game.rcon_say("^7Last Maps: ^7%s" % ", ".join(self.game.get_last_maps()))

    def new_game(self, line):
        """
        set-up a new game
        """
        self.ffa_lms_gametype = True if ('g_gametype\\0\\' in line or 'g_gametype\\1\\' in line or 'g_gametype\\9\\' in line or 'g_gametype\\11\\' in line) else False
        self.ctf_gametype = True if 'g_gametype\\7\\' in line else False
        self.ts_gametype = True if ('g_gametype\\4\\' in line or 'g_gametype\\5\\' in line) else False
        self.tdm_gametype = True if 'g_gametype\\3\\' in line else False
        self.bomb_gametype = True if 'g_gametype\\8\\' in line else False
        self.freeze_gametype = True if 'g_gametype\\10\\' in line else False
        logger.debug("InitGame: Starting game...")
        self.game.rcon_clear()
        # reset the player stats
        self.stats_reset()

        # set the current map
        self.game.set_current_map()
        # load all available maps
        self.game.set_all_maps()

        # support for low gravity server
        if self.support_lowgravity:
            self.game.send_rcon("set g_gravity %d" % self.gravity)

        # detonation timer
        if self.bomb_gametype:
            # bomb detonation timer
            detonation_timer = self.game.get_cvar('g_bombexplodetime')
            self.explode_time = detonation_timer or "40"

        # reset list of player who left server
        self.last_disconnected_player = None

        # allow nextmap votes
        self.allow_nextmap_vote = True
        self.failed_vote_timer = 0
        # Load cvars specific to the new map
        current_map = self.get_current_map()
        if current_map:
            self.load_map_cvars(current_map)
        

    def handle_spawn(self, line):
        """
        handle client spawn
        """
        player_num = int(line)
        player = self.game.players[player_num]
        player_name = player.get_name()
        with self.players_lock:
            self.game.players[player_num].set_alive(True)
            if player.get_welcome_msg():  
                self.game.send_rcon("spoof %s regainstamina" % (player_name))
                # Load map-specific cvars only on player's first spawn
                if self.game.get_number_players() <= 1:
                    self.game.send_rcon("timelimit 0")
                    
                
    
    def handle_flagcapturetime(self, line):
        """
        handle flag capture time
        """
        tmp = line.split(": ", 1)
        player_num = int(tmp[0])
        action = tmp[1]
        if action.isdigit():
            cap_time = round(float(action) / 1000, 2)
            logger.debug("Player %d captured the flag in %s seconds", player_num, cap_time)
            with self.players_lock:
                self.game.players[player_num].set_flag_capture_time(cap_time)

    def handle_warmup(self, line):
        """
        handle warmup
        """
        logger.debug("Warmup... %s", line)
        self.allow_cmd_teams = True
        

    def handle_initround(self, _):
        """
        handle Init Round
        """
        logger.debug("InitRound: Round started...")
        if self.ctf_gametype:
            with self.players_lock:
                for player in self.game.players.itervalues():
                    player.reset_flag_stats()
        elif self.ts_gametype or self.bomb_gametype or self.freeze_gametype:
            if self.allow_cmd_teams_round_end:
                self.allow_cmd_teams = False

    def handle_exit(self, line):
        """
        handle Exit of a match, show Awards, store user score in database and reset statistics
        """
        logger.debug("Exit: %s", line)
        self.handle_awards()
        self.allow_cmd_teams = True
        self.stats_reset(store_score=True)
        

    def stats_reset(self, store_score=False):
        """
        store user score in database if needed and reset the player statistics
        """
        with self.players_lock:
            for player in self.game.players.itervalues():
                if store_score:
                    # store score in database
                    player.save_info()
                # reset player statistics
                player.reset(self.reset_headshot_hits_mapcycle, self.reset_kill_spree_mapcycle)
                # reset team lock
                player.set_team_lock(None)

        # set first kill trigger
        if self.show_first_kill_msg and not self.ffa_lms_gametype:
            self.firstblood = True
            self.firstnadekill = True
            self.firstknifekill = True
            self.firstteamkill = True
        else:
            self.firstblood = False
            self.firstnadekill = False
            self.firstknifekill = False
            self.firstteamkill = False

    def handle_userinfo(self, line):
        """
        handle player user information, auto-kick known cheater ports or guids
        """
        with self.players_lock:
            player_num = int(line[:2].strip())
            line = line[2:].lstrip("\\").lstrip()
            values = self.explode_line(line)
            challenge = 'challenge' in values
            name = values['name'] if 'name' in values else "UnnamedPlayer"
            ip_port = values['ip'] if 'ip' in values else "0.0.0.0:0"
            auth = values['authl'] if 'authl' in values else ""
            if 'cl_guid' in values:
                guid = values['cl_guid']
            elif 'skill' in values:
                # bot connecting
                guid = "BOT%d" % player_num
            else:
                guid = "None"
                self.kick_player_reason(reason="Player with invalid GUID kicked", player_num=player_num)

            try:
                ip_address = ip_port.split(":")[0].strip()
                port = ip_port.split(":")[1].strip()
            except IndexError:
                ip_address = ip_port.strip()
                port = "27960"

            # convert loopback/localhost address
            if ip_address in ('loopback', 'localhost'):
                ip_address = '127.0.0.1'

            if player_num not in self.game.players:
                player = Player(player_num, ip_address, guid, name, auth)
                self.game.add_player(player)
                # kick banned player
                if player.get_ban_id():
                    self.kick_player_reason("^7%s ^8banned ^7(ID @%s): %s" % (player.get_name(), player.get_ban_id(), player.get_ban_msg()), player_num)
                else:
                    if self.show_country_on_connect and player.get_country():
                        self.game.rcon_say("^7%s ^7connected from %s" % (player.get_name(), player.get_country()))

            if self.game.players[player_num].get_guid() != guid:
                self.game.players[player_num].set_guid(guid)

            if self.game.players[player_num].get_authname() != auth:
                self.game.players[player_num].set_authname(auth)

            # kick player with hax guid 'kemfew'
            if "KEMFEW" in guid.upper():
                self.kick_player_reason("Cheater GUID detected for %s -> Player kicked" % name, player_num)
            if "WORLD" in guid.upper() or "UNKNOWN" in guid.upper():
                self.kick_player_reason("Invalid GUID detected for %s -> Player kicked" % name, player_num)

            if challenge:
                logger.debug("ClientUserinfo: Player %d %s is challenging the server and has the guid %s", player_num, self.game.players[player_num].get_name(), guid)
                # kick player with hax port 1337
                invalid_port_range = ["1337"]
                if port in invalid_port_range:
                    self.kick_player_reason("Cheater Port detected for %s -> Player kicked" % name, player_num)
                if self.last_disconnected_player and self.last_disconnected_player.get_guid() == self.game.players[player_num].get_guid():
                    self.last_disconnected_player = None

    def kick_player_reason(self, reason, player_num):
        """
        kick player for specific reason
        """
        if self.urt_modversion > 41:
            self.game.send_rcon('kick %d "%s"' % (player_num, reason))
        else:
            self.game.send_rcon("kick %d" % player_num)
            self.game.send_rcon(reason)

    def handle_userinfo_changed(self, line):
        """
        handle player changes
        """
        with self.players_lock:
            player_num = int(line[:2].strip())
            player = self.game.players[player_num]
            line = line[2:].lstrip("\\")
            try:
                values = self.explode_line(line)
                team_num = int(values['t'])
                player.set_team(team_num)
                name = values['n']
            except KeyError:
                team_num = 3
                player.set_team(team_num)
                name = self.game.players[player_num].get_name()

            # set new name, if player changed name
            if self.game.players[player_num].get_name() != name:
                self.game.players[player_num].set_name(name)

            # move locked player to the defined team, if player tries to change teams
            team_lock = self.game.players[player_num].get_team_lock()
            if team_lock and Player.teams[team_num] != team_lock:
                self.game.rcon_forceteam(player_num, team_lock)
                self.game.rcon_tell(player_num, "^7You are forced to: ^7%s" % team_lock)
            logger.debug("ClientUserinfoChanged: Player %d %s joined team %s", player_num, name, Player.teams[team_num])

    def handle_begin(self, line):
        """
        handle player entering game
        """
        with self.players_lock:
            player_num = int(line)
            player = self.game.players[player_num]
            player_name = player.get_name()
            player_id = player.get_player_id()
            self.game.set_current_map()
            
            # Welcome message for registered players
            if player.get_registered_user() and player.get_welcome_msg():
                self.game.rcon_say("^7Everyone welcome back ^7%s^7, player number ^7#%s^7, to this server" % (player_name, player_id))
                self.game.rcon_tell(player_num, "^7[^9Authed^7] Welcome back %s, you are ^9%s^7, last visit %s, you played %s times" % (player_name, player.roles[player.get_admin_role()], player.get_last_visit(), player.get_num_played()), False)
                # disable welcome message for next rounds
                player.disable_welcome_msg()
            elif not player.get_registered_user() and not player.get_first_time() and player.get_welcome_msg():
                self.game.rcon_tell(player_num, "^7Welcome back %s, you are player ^7#%s^7. ^7Type ^9!register ^7in chat to register and watch all commands" % (player_name, player_id))
                player.disable_welcome_msg()
            elif player.get_first_time() and player.get_welcome_msg():
                self.game.rcon_tell(player_num, "^7Welcome %s, this must be your first visit, you are player ^7#%s^7. ^7Type ^9!help ^7in chat for help" % (player_name, player_id))
                player.disable_welcome_msg()
            
            # Vérifier si le joueur a des messages en attente
            self.check_pending_messages(player)
            
            logger.debug("ClientBegin: Player %d %s has entered the game", player_num, player_name)
        
        
    
    def handle_disconnect(self, line):
        """
        handle player disconnect
        """
        with self.players_lock:
            player_num = int(line)
            player = self.game.players[player_num]
            player_name = player.get_name()
            player.save_info()
            player.reset()
            self.last_disconnected_player = player
            if player.get_admin_role() >= 40:
                self.last_admin = player
            del self.game.players[player_num]
            for player in self.game.players.itervalues():
                player.clear_tk(player_num)
                player.clear_grudged_player(player_num)
            logger.debug("ClientDisconnect: Player %d %s has left the game", player_num, player_name)
            
            if self.game.get_number_players() <= 0:
                self.game.send_rcon("timelimit 30")    
                
    #sysmyks topruns
    def handle_jump_run_started(self, line):
        """
        handle jump_run_started
        """
        player_id, way = map(int, line.split('- way: '))
        self.jump_times[player_id] = {'start_time': datetime.now(), 'way': way}
        player_num = self.game.players[player_id].get_player_num()
        logger.info('Jump run started for player {0} on way {1}.'.format(player_id, way))


    def handle_jump_run_canceled(self, line):
        """
        handle jump_run_canceled
        """
        player_id, way = map(int, line.split('- way: '))
        if player_id in self.jump_times:
            del self.jump_times[player_id]
            player_name = self.get_player_name(player_id)
            logger.info('Jump run canceled for player {0} on way {1}.'.format(player_id, way))



    def handle_jump_run_stopped(self, line):
        """
        handle_jump_run_stopped with improved error handling and logging
        """
        try:
            # Parse log line
            logger.debug("Jump run stopped raw line: %s", line)
            parts = line.split('- way: ')
            if len(parts) < 2:
                logger.error('Invalid line format for jump_run_stopped: %s', line)
                return

            way_time = parts[1].split(' - time: ')
            if len(way_time) != 2:
                logger.error('Invalid time format: %s', parts[1])
                return

            player_id = int(parts[0])
            way = str(way_time[0])  # Convert directly to string to avoid errors
            time_ms = int(way_time[1])

            # Check if player had started a run
            if player_id not in self.jump_times:
                logger.warning("Received finished run without a started run for player %d", player_id)
                return

            # Get player information
            player_name = self.get_player_name(player_id)
            current_map = self.get_current_map()
            
            logger.info("Recording run: Player=%s, Map=%s, Way=%s, Time=%d ms", 
                        player_name, current_map, way, time_ms)

            # Check if structure already exists for this map
            if current_map not in self.jump_records:
                self.jump_records[current_map] = {}
                logger.debug("New map entry created: %s", current_map)

            # Check if player already has records on this map
            if player_name not in self.jump_records[current_map]:
                self.jump_records[current_map][player_name] = {}
                logger.debug("New player entry created: %s", player_name)

            # Check if this is a new record or an improvement
            is_new_record = way not in self.jump_records[current_map][player_name] 
            is_better_time = (is_new_record or time_ms < self.jump_records[current_map][player_name][way])
            
            # Update record if better
            if is_better_time:
                self.jump_records[current_map][player_name][way] = time_ms
                self.save_records()
                
                # Format and display new record message
                minutes = time_ms // 60000
                seconds = (time_ms % 60000) // 1000
                milliseconds = time_ms % 1000
                
                message = "^9New record! ^7{} ^9Way {}: ^7{}m {}s {}ms".format(
                    player_name, way, minutes, seconds, milliseconds
                )
                player_num = self.game.players[player_id].get_player_num()
                self.game.rcon_say(message)
                
                logger.info("New record for %s on %s (way %s): %d ms", 
                            player_name, current_map, way, time_ms)
            
            # Cleanup
            del self.jump_times[player_id]
            
        except Exception as e:
            logger.error("Error in handle_jump_run_stopped: %s", str(e), exc_info=True)

    def get_player_name(self, player_id):
        if player_id in self.game.players:
            return self.game.players[player_id].get_name()
        else:
            return 'Unknown_{}'.format(player_id)
    
    def handle_hit(self, line):
        """
        handle all kind of hits
        """
        with self.players_lock:
            info = line.split(":", 1)[0].split()
            hitter_id = int(info[1])
            victim_id = int(info[0])
            hitter = self.game.players[hitter_id]
            hitter_name = hitter.get_name()
            hitpoint = int(info[2])
            hit_item = int(info[3])
            # increase summary of all hits
            hitter.set_all_hits()

            zones = {'TORSO': 'body', 'VEST': 'body', 'KEVLAR': 'body', 'BUTT': 'body', 'GROIN': 'body',
                     'LEGS': 'legs', 'LEFT_UPPER_LEG': 'legs', 'RIGHT_UPPER_LEG': 'legs',
                     'LEFT_LOWER_LEG': 'legs', 'RIGHT_LOWER_LEG': 'legs', 'LEFT_FOOT': 'legs', 'RIGHT_FOOT': 'legs',
                     'ARMS': 'arms', 'LEFT_ARM': 'arms', 'RIGHT_ARM': 'arms'}

            if hitpoint in self.hit_points:
                if self.hit_points[hitpoint] in ('HEAD', 'HELMET'):
                    hitter.headshot()
                    hitter_hs_count = hitter.get_headshots()
                    hs_msg = {5: 'watch out!',
                              10: 'awesome!',
                              15: 'unbelievable!',
                              20: '^8MANIAC!',
                              25: '^9AIMBOT?',
                              30: 'stop that',
                              35: 'stop that ^5NOW',
                              40: '^6OMG ^7stop it',
                              45: 'no mercy',
                              50: '^9HEAD RIPPER'}
                    if self.spam_headshot_hits_msg and hitter_hs_count in hs_msg:
                        self.game.rcon_bigtext("^7%s: ^9%d ^7HeadShots, %s" % (hitter_name, hitter_hs_count, hs_msg[hitter_hs_count]))
                    hs_plural = "headshots" if hitter_hs_count > 1 else "headshot"
                    percentage = int(round(float(hitter_hs_count) / float(hitter.get_all_hits()), 2) * 100)
                    self.game.send_rcon("^7%s has ^9%d ^7%s (%d percent)" % (hitter_name, hitter_hs_count, hs_plural, percentage))
                elif self.hit_points[hitpoint] in zones:
                    hitter.set_hitzones(zones[self.hit_points[hitpoint]])
                logger.debug("Player %d %s hit %d %s in the %s with %s", hitter_id, hitter_name, victim_id, self.game.players[victim_id].get_name(), self.hit_points[hitpoint], self.hit_item[hit_item])

    def handle_kill(self, line):
        """
        handle kills
        """
        with self.players_lock:
            
            parts = line.split(":", 1)
            info = parts[0].split()
            k_name = parts[1].split()[0]
            killer_id = int(info[0])
            victim_id = int(info[1])
            death_cause = self.death_cause[int(info[2])]
            victim = self.game.players[victim_id]
            victim.set_alive(False)

            if k_name == "<non-client>":
                # killed by World
                killer_id = BOT_PLAYER_NUM
            killer = self.game.players[killer_id]

            killer_name = killer.get_name()
            victim_name = victim.get_name()
            tk_event = False

            # teamkill event - disabled for FFA, LMS, Jump, for all other game modes team kills are counted and punished
            if not self.ffa_lms_gametype:
                if victim.get_team() == killer.get_team() and victim.get_team() != 3 and victim_id != killer_id and death_cause != "UT_MOD_BOMBED":
                    tk_event = True
                    # first teamkill message
                    if self.firstteamkill:
                        self.game.rcon_bigtext("^8First Team Kill: ^7%s killed by ^8%s" % (victim_name, killer_name))
                        self.firstteamkill = False
                    # increase team kill counter for killer and kick for too many team kills
                    killer.team_kill()
                    # increase team death counter for victim
                    victim.team_death()
                    # check if bot or human player got killed
                    human = False if self.allow_tk_bots and victim.get_ip_address() == '0.0.0.0' else True
                    # Regular and higher will not get punished
                    if killer.get_admin_role() < 2 and self.tk_autokick and killer.get_ip_address() != '0.0.0.0' and human:
                        # list of players of TK victim
                        killer.add_tk_victims(victim_id)
                        # list of players who killed victim
                        if killer_id not in victim.get_grudged_player():
                            victim.add_killed_me(killer_id)
                            self.game.rcon_tell(victim_id, "^7Type ^7!fp ^7to forgive ^7%s" % killer_name)
                        self.game.rcon_tell(killer_id, "^7Do not attack teammates, you ^8killed ^7%s" % victim_name)
                        if len(killer.get_tk_victim_names()) > 3:
                            killer.ban(duration=600, reason='team killing over limit', admin='bot')
                            self.game.rcon_say("^7%s ^7banned for ^810 minutes ^7for team killing over limit" % killer_name)
                            self.game.kick_player(killer_id, reason='team killing over limit')
                        else:
                            killer.add_warning('stop team killing')
                            self.game.rcon_tell(killer_id, "^8WARNING ^7[^7%d^7]: ^7For team killing you will get kicked" % killer.get_warning(), False)
                            if killer.get_warning() == 3 and killer.get_admin_role() < self.admin_immunity:
                                self.game.rcon_say("^8ALERT: ^9%s ^7auto-kick from warnings if not forgiven. Type ^7!forgive %s ^7to forgive" % (killer_name, killer_id))

            suicide_reason = ['UT_MOD_SUICIDE', 'MOD_FALLING', 'MOD_WATER', 'MOD_LAVA', 'MOD_TRIGGER_HURT',
                              'UT_MOD_SPLODED', 'UT_MOD_SLAPPED', 'UT_MOD_SMITED']
            suicide_weapon = ['UT_MOD_HEGRENADE', 'UT_MOD_HK69', 'UT_MOD_NUKED', 'UT_MOD_BOMBED']
            # suicide counter
            if death_cause in suicide_reason or (killer_id == victim_id and death_cause in suicide_weapon):
                victim.suicide()
                victim.die()
                logger.debug("Player %d %s committed suicide with %s", victim_id, victim_name, death_cause)
            # kill counter
            elif not tk_event and int(info[2]) != 10:  # 10: MOD_CHANGE_TEAM
                if killer.get_losing_streak() >= 5:
                    self.game.rcon_say("^7You are back in business ^7%s" % killer_name)
                killer.kill()

                # spawn killing - warn/kick or instant kill
                if (self.spawnkill_autokick or self.kill_spawnkiller) and self.spawnkill_warn_time and killer.get_admin_role() < self.admin_immunity:
                    # Spawn Protection time between players deaths in seconds to issue a warning
                    if victim.get_respawn_time() + self.spawnkill_warn_time > time.time():
                        if killer.get_ip_address() != '0.0.0.0':
                            if self.kill_spawnkiller and self.urt_modversion > 41:
                                self.game.send_rcon("smite %d" % killer_id)
                                self.game.rcon_say("^7%s killed for Spawn Killing" % killer_name)
                            if self.spawnkill_autokick:
                                killer.add_warning("stop spawn killing")
                                self.kick_high_warns(killer, 'stop spawn killing', 'Spawn Camping and Spawn Killing are not allowed')
                        else:
                            self.game.send_rcon("smite %d" % killer_id)

                # multi kill message
                if self.show_multikill_msg:
                    if killer.get_monsterkill() == 2:
                        self.game.rcon_say("^7%s: ^9Double Kill!" % killer_name)
                    elif killer.get_monsterkill() == 3:
                        self.game.rcon_say("^7%s: ^8Multi Kill!" % killer_name)
                    elif killer.get_monsterkill() == 4:
                        self.game.rcon_say("^7%s: ^8MONSTER KILL!!" % killer_name)

                # first kill message
                if self.firstblood:
                    self.game.rcon_bigtext("^8FIRST BLOOD: ^7%s killed by ^8%s" % (victim_name, killer_name))
                    self.firstblood = False
                    if death_cause == 'UT_MOD_HEGRENADE':
                        self.firstnadekill = False
                    if death_cause == 'UT_MOD_KNIFE' or death_cause == 'UT_MOD_KNIFE_THROWN':
                        self.firstknifekill = False
                elif self.firstnadekill and death_cause == 'UT_MOD_HEGRENADE':
                    self.game.rcon_bigtext("^7%s: ^7first HE grenade kill" % killer_name)
                    self.firstnadekill = False
                elif self.firstknifekill and (death_cause in ('UT_MOD_KNIFE', 'UT_MOD_KNIFE_THROWN')):
                    self.game.rcon_bigtext("^7%s: ^7first knife kill" % killer_name)
                    self.firstknifekill = False

                # bomb mode
                if self.bomb_gametype:
                    # bomb carrier killed
                    if victim.get_bombholder():
                        killer.kill_bomb_carrier()
                    # killed with bomb
                    if death_cause == 'UT_MOD_BOMBED':
                        killer.kills_with_bomb()

                event_series_msg = {5: 'go on!',
                                    10: 'beware!',
                                    15: 'eat that!',
                                    20: 'got pwned!',
                                    25: 'impressive!',
                                    30: 'dominating!'}

                # HE grenade kill
                if death_cause == 'UT_MOD_HEGRENADE':
                    killer.set_he_kill()
                    he_kill_count = killer.get_he_kills()
                    if self.spam_nade_kills_msg and he_kill_count in event_series_msg:
                        self.game.rcon_bigtext("^7%s: ^9%d ^7HE grenade kills, %s" % (killer_name, he_kill_count, event_series_msg[he_kill_count]))

                # Knife kill
                if "UT_MOD_KNIFE" in death_cause or "UT_MOD_KNIFE_THROWN" in death_cause:
                    killer.set_knife_kill()
                    knife_kill_count = killer.get_knife_kills()
                    if self.spam_knife_kills_msg and knife_kill_count in event_series_msg:
                        self.game.rcon_bigtext("^7%s: ^9%d ^7knife kills, %s" % (killer_name, knife_kill_count, event_series_msg[knife_kill_count]))

                # killing spree counter
                killer_color = "^8" if (killer.get_team() == 1) else "^4"
                killer_killing_streak = killer.get_killing_streak()
                kill_streak_msg = {5: "is on a killing spree (^85 ^7kills in a row)",
                                   10: "is on a rampage (^810 ^7kills in a row)",
                                   15: "is unstoppable (^815 ^7kills in a row)",
                                   20: "is godlike (^820 ^7kills in a row)"}
                if killer_killing_streak in kill_streak_msg and killer_id != BOT_PLAYER_NUM:
                    self.game.rcon_say("%s%s ^7%s" % (killer_color, killer_name, kill_streak_msg[killer_killing_streak]))

                victim_color = "^8" if (victim.get_team() == 1) else "^4"
                if victim.get_killing_streak() >= 20 and killer_name != victim_name and killer_id != BOT_PLAYER_NUM:
                    self.game.rcon_say("%s%s's ^7godlike (^8%s ^7kills) was ended by %s%s!" % (victim_color, victim_name, victim.get_killing_streak(), killer_color, killer_name))
                elif victim.get_killing_streak() >= 15 and killer_name != victim_name and killer_id != BOT_PLAYER_NUM:
                    self.game.rcon_say("%s%s's ^7unstoppable (^8%s ^7kills) was ended by %s%s!" % (victim_color, victim_name, victim.get_killing_streak(), killer_color, killer_name))
                elif victim.get_killing_streak() >= 10 and killer_name != victim_name and killer_id != BOT_PLAYER_NUM:
                    self.game.rcon_say("%s%s's ^7rampage (^8%s ^7kills) was ended by %s%s!" % (victim_color, victim_name, victim.get_killing_streak(), killer_color, killer_name))
                elif victim.get_killing_streak() >= 5 and killer_name != victim_name and killer_id != BOT_PLAYER_NUM:
                    self.game.rcon_say("%s%s's ^7killing spree (^8%s ^7kills) was ended by %s%s!" % (victim_color, victim_name, victim.get_killing_streak(), killer_color, killer_name))

                # death counter
                victim.die()
                if victim.get_losing_streak() == 5:
                    self.game.rcon_say("^7Keep it up ^7%s^7, it will come eventually" % victim_name)

                if self.show_hit_stats_msg:
                    self.game.rcon_tell(victim_id, "^8HIT Stats: ^7HS: ^9%s ^7BODY: ^9%s ^7ARMS: ^9%s ^7LEGS: ^9%s ^7TOTAL: ^9%s" % (victim.get_headshots(), victim.get_hitzones('body'), victim.get_hitzones('arms'), victim.get_hitzones('legs'), victim.get_all_hits()))
                logger.debug("Player %d %s killed %d %s with %s", killer_id, killer_name, victim_id, victim_name, death_cause)

    def player_found(self, user):
        """
        return True and instance of player or False and message text
        """
        victim = None
        name_list = []
        append = name_list.append
        for player in self.game.players.itervalues():
            player_num = player.get_player_num()
            if player_num == BOT_PLAYER_NUM:
                continue
            player_name = player.get_name()
            player_authname = player.get_authname()
            player_id = "@%d" % player.get_player_id()
            if user.upper() == player_name.upper() or user == str(player_num) or user == player_id or user.lower() == player_authname:
                victim = player
                name_list = ["^7%s [^9%d^7]" % (player_name, player_num)]
                break
            elif user.upper() in player_name.upper():
                victim = player
                append("^7%s [^9%d^7]" % (player_name, player_num))
        if not name_list:
            if user.startswith('@'):
                ret_val = self.offline_player(user)
            else:
                ret_val = False, None, "^7No players found matching %s" % user
        elif len(name_list) > 1:
            ret_val = False, None, "^7Players matching %s: ^7%s" % (user, ', '.join(name_list))
        else:
            ret_val = True, victim, "^7Found player matching %s: ^7%s" % (user, name_list[-1])
        return ret_val

    def offline_player(self, user_id):
        """
        return True and instance of player or False and message text
        """
        player_id = user_id.lstrip('@')
        if player_id.isdigit() and int(player_id) > 1:
            curs.execute("SELECT `guid`,`name`,`ip_address` FROM `player` WHERE `id` = {}".format(int(player_id)))
            result = curs.fetchone()
            if result:
                victim = Player(player_num=1023, ip_address=str(result[2]), guid=str(result[0]), name=str(result[1]))
                victim.define_offline_player(player_id=int(player_id))
                ret_val = True, victim, None
            else:
                ret_val = False, None, "^7No Player found"
        else:
            ret_val = False, None, "^7No Player found"
        return ret_val

    def map_found(self, map_name):
        """
        return True and map name or False and message text
        """
        map_list = []
        append = map_list.append
        for maps in self.game.get_all_maps():
            if map_name.lower() == maps or ('ut4_%s' % map_name.lower()) == maps:
                append(maps)
                break
            elif map_name.lower() in maps:
                append(maps)
        if not map_list:
            ret_val = False, None, "^7Map not found"
        elif len(map_list) > 1:
            ret_val = False, None, "^7Maps matching %s: ^7%s" % (map_name, ', '.join(map_list))
        else:
            ret_val = True, map_list[0], None
        return ret_val

    def handle_saytell(self, line):
        """
        handle saytell commands
        """
        tmp = line.strip()
        try:
            new = "%s%s" % (tmp[0], ''.join(tmp[1:]))
            self.handle_say(new)
        except IndexError:
            pass

    def clean_cmd_list(self, cmd_list):
        """
        remove commands which are not available in current game type or modversion
        """
        disabled_cmds = []
        clean_list = list(cmd_list)
        if self.ffa_lms_gametype or self.ts_gametype or self.tdm_gametype:
            disabled_cmds = ['bombstats', 'ctfstats', 'freezestats']
        elif self.bomb_gametype:
            disabled_cmds = ['ctfstats', 'freezestats']
        elif self.ctf_gametype:
            disabled_cmds = ['bombstats', 'freezestats']
        elif self.freeze_gametype:
            disabled_cmds = ['bombstats', 'ctfstats']

        if self.urt_modversion == 41:
            disabled_cmds += ['kill', 'instagib']
        elif self.urt_modversion == 42:
            disabled_cmds += ['instagib']

        for item in disabled_cmds:
            try:
                clean_list.remove(item)
            except ValueError:
                pass
        return clean_list
    
    def get_position_from_json(self, jump_name):
        current_map = self.get_current_map()
        if not current_map:
            self.tell_say_message("^8Unable to retrieve current map.")
            return None

        map_json_file = os.path.join(self.json_path, "{}.json".format(current_map))
        
        if not os.path.exists(map_json_file):
            self.tell_say_message("^8JSON file not found for map: {}".format(current_map))
            return None

        try:
            with open(map_json_file, 'r') as file:
                map_data = json.load(file)
            return map_data.get(jump_name, None)  # Renvoie la position associée au "jump_name"
        except json.JSONDecodeError:
            self.tell_say_message("^8Error reading JSON file.")
            return None
    
    def save_position_to_json(self, sar, jump_name, player_name, position):
        current_map = self.get_current_map()  # Get the current map
        if not current_map:
            self.tell_say_message(sar, "^8Unable to retrieve current map.")
            return

        # Path to the JSON file for the current map
        map_json_file = os.path.join(self.json_path, "{}.json".format(current_map))

        # Load existing JSON data, or create an empty dictionary if the file doesn't exist
        if os.path.exists(map_json_file):
            try:
                with open(map_json_file, 'r') as file:
                    map_data = json.load(file)
            except json.JSONDecodeError:
                map_data = {}
        else:
            map_data = {}

        # If a position is already registered for the "jump_name", don't add it again
        if jump_name in map_data:
            self.tell_say_message(sar, "^8Position already exists for this jump.")
            return

        # Add the position to the dictionary
        map_data[jump_name] = position

        # Save the new positions to the JSON file
        try:
            with open(map_json_file, 'w') as file:
                json.dump(map_data, file, indent=4)
            self.tell_say_message(sar, "^9Position saved for jump: {}".format(jump_name))
        except IOError as e:
            self.tell_say_message(sar, "^8Error saving position to file: {}".format(e))


    # mapinfo fonction
    def get_map_info(self, map_name):
        if os.path.exists(self.mapinfo):
            try:
                with open(self.mapinfo, "r") as file:
                    maps_data = json.load(file)
                return maps_data.get(map_name, None)
            except json.JSONDecodeError:
                logger.error("Error decoding .json")
                return None
        else:
            logger.error(".json not found")
            return None

    def get_current_map(self):
        return self.game.get_cvar('mapname')

    def handle_say(self, line):
        """
        handle say commands
        """
        poke_options = ['Go', 'Wake up', '*poke*', 'Attention', 'Get up', 'Move out']

        bad_words = ['fuck', 'ass', 'bastard', 'retard', 'slut', 'bitch', 'whore', 'cunt', 'pussy', 'dick', 'cock', 'sucker',
                     'fick', 'arsch', 'nutte', 'schlampe', 'hure', 'fotze', 'penis', 'wichser', 'nazi', 'hitler',
                     'putain', 'merde', 'chienne', 'batard', 'jihad', 'nigger',
                     'kurwa', 'suka', 'dupa', 'dupek', 'puta', 'maricon']

        with self.players_lock:
            line = line.strip()
            try:
                divider = line.split(": ", 1)
                number = divider[0].split(" ", 1)[0]
                name_saycmd = divider[0].split(" ", 1)[1]
                cmd = divider[1].split()[0]
                sar = {'player_num': int(number), 'command': cmd}
            except IndexError:
                sar = {'player_num': BOT_PLAYER_NUM, 'command': ''}
            except ValueError:
                sar = {'player_num': 0, 'command': str(line.split(": ", 1)).split(" ", 1)[0]}

            # when haunting player and entering command, the haunted player is the caller, therefore ignore command
            if self.game.players[sar['player_num']].get_name() != name_saycmd:
                sar = {'player_num': BOT_PLAYER_NUM, 'command': ''}

            if sar['command'] == '!mapstats':
                self.game.rcon_tell(sar['player_num'], "^9%d ^7kills - ^9%d ^7deaths" % (self.game.players[sar['player_num']].get_kills(), self.game.players[sar['player_num']].get_deaths()))
                self.game.rcon_tell(sar['player_num'], "^9%d ^7kills in a row - ^9%d ^7teamkills" % (self.game.players[sar['player_num']].get_killing_streak(), self.game.players[sar['player_num']].get_team_kill_count()))
                self.game.rcon_tell(sar['player_num'], "^9%d ^7total hits - ^9%d ^7headshots" % (self.game.players[sar['player_num']].get_all_hits(), self.game.players[sar['player_num']].get_headshots()))
                self.game.rcon_tell(sar['player_num'], "^9%d ^7HE grenade kills" % self.game.players[sar['player_num']].get_he_kills())
                if self.ctf_gametype:
                    if self.urt_modversion > 41:
                        self.game.rcon_tell(sar['player_num'], "^7flags captured: ^9%d ^7- flags returned: ^9%d ^7- fastest cap: ^9%s ^7sec" % (self.game.players[sar['player_num']].get_flags_captured(), self.game.players[sar['player_num']].get_flags_returned(), self.game.players[sar['player_num']].get_flag_capture_time()))
                    else:
                        self.game.rcon_tell(sar['player_num'], "^7flags captured: ^9%d ^7- flags returned: ^9%d" % (self.game.players[sar['player_num']].get_flags_captured(), self.game.players[sar['player_num']].get_flags_returned()))
                elif self.bomb_gametype:
                    self.game.rcon_tell(sar['player_num'], "^7planted: ^9%d ^7- defused: ^9%d" % (self.game.players[sar['player_num']].get_planted_bomb(), self.game.players[sar['player_num']].get_defused_bomb()))
                    self.game.rcon_tell(sar['player_num'], "^7bomb carrier killed: ^9%d ^7- enemies bombed: ^9%d" % (self.game.players[sar['player_num']].get_bomb_carrier_kills(), self.game.players[sar['player_num']].get_kills_with_bomb()))
                elif self.freeze_gametype:
                    self.game.rcon_tell(sar['player_num'], "^7freeze: ^9%d ^7- thaw out: ^9%d" % (self.game.players[sar['player_num']].get_freeze(), self.game.players[sar['player_num']].get_thawout()))

            elif sar['command'] in ('!help', '!h'):
                if line.split(sar['command'])[1]:
                    cmd = line.split(sar['command'])[1].strip()
                    if cmd in COMMANDS:
                        if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS[cmd]['level']:
                            self.game.rcon_tell(sar['player_num'], "%s ^7- %s" % (COMMANDS[cmd]['syntax'], COMMANDS[cmd]['desc']))
                    elif cmd in self.shortcut_cmd:
                        if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS[self.shortcut_cmd[cmd]]['level']:
                            self.game.rcon_tell(sar['player_num'], "%s ^7- %s" % (COMMANDS[self.shortcut_cmd[cmd]]['syntax'], COMMANDS[self.shortcut_cmd[cmd]]['desc']))
                    else:
                        if cmd not in self.superadmin_cmds:
                            self.game.rcon_tell(sar['player_num'], "^7Unknown command ^7%s" % cmd)
                else:
                    if self.game.players[sar['player_num']].get_admin_role() < 20:
                        self.game.rcon_tell(sar['player_num'], "^7Available commands: ^7%s" % ', ^7'.join(self.clean_cmd_list(self.user_cmds)))
                    # help for mods - additional commands
                    elif self.game.players[sar['player_num']].get_admin_role() == 20:
                        self.game.rcon_tell(sar['player_num'], "^7Jumper commands: ^7%s" % ', ^7'.join(self.clean_cmd_list(self.mod_cmds)))
                    # help for admins - additional commands
                    elif self.game.players[sar['player_num']].get_admin_role() == 40:
                        self.game.rcon_tell(sar['player_num'], "^7Admin commands: ^7%s" % ', ^7'.join(self.clean_cmd_list(self.admin_cmds)))
                    elif self.game.players[sar['player_num']].get_admin_role() == 60:
                        self.game.rcon_tell(sar['player_num'], "^7Full Admin commands: ^7%s" % ', ^7'.join(self.clean_cmd_list(self.fulladmin_cmds)))
                    elif self.game.players[sar['player_num']].get_admin_role() == 80:
                        self.game.rcon_tell(sar['player_num'], "^7Senior Admin commands: ^7%s" % ', ^7'.join(self.clean_cmd_list(self.senioradmin_cmds)))
                    elif self.game.players[sar['player_num']].get_admin_role() >= 90:
                        self.game.rcon_tell(sar['player_num'], "^7Super Admin commands: ^7%s" % ', ^7'.join(self.clean_cmd_list(self.superadmin_cmds)))

## player commands 20
            # register - register yourself as a basic user
            elif sar['command'] == '!register':
                if not self.game.players[sar['player_num']].get_registered_user():
                    self.game.players[sar['player_num']].register_user_db(role=20 )
                    self.game.rcon_tell(sar['player_num'], "^7%s ^7put in group Jumper" % self.game.players[sar['player_num']].get_name())
                else:
                    self.game.rcon_tell(sar['player_num'], "^7%s ^7is already in a higher level group" % self.game.players[sar['player_num']].get_name())

            # regtest - display current user status
            elif sar['command'] == '!regtest':
                if self.game.players[sar['player_num']].get_registered_user():
                    self.game.rcon_tell(sar['player_num'], "^7%s [^7@%s^7] is registered since ^7%s" % (self.game.players[sar['player_num']].get_name(), self.game.players[sar['player_num']].get_player_id(), self.game.players[sar['player_num']].get_first_seen_date()))
                else:
                    self.game.rcon_tell(sar['player_num'], "^7You are not a registered Jumper.")
            
            # drop - drop your stuff
            elif sar['command'] in ('!drop', '!dr'):  
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['drop']['level']:
                    self.game.send_rcon("spoof %s ut_itemdrop medkit" % (self.game.players[sar['player_num']].get_name()))
                    self.game.send_rcon("spoof %s ut_itemdrop Helmet" % (self.game.players[sar['player_num']].get_name()))
                    self.game.rcon_tell(sar['player_num'], "Drop medkit weapon and Helmet")
                else:
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")
            
            # mapinfo
            # update mapinfo function
            elif sar['command'] == '!mapinfo':
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['mapinfo']['level']:
                    # Check if a map name is provided
                    if line.split(sar['command'])[1]:
                        requested_map = line.split(sar['command'])[1].strip()
                        # Verify if map exists
                        found, map_name, error_msg = self.map_found(requested_map)
                        if not found:
                            msg = error_msg
                        else:
                            map_info = self.get_map_info(map_name)
                            if map_info:
                                msg = "^9Map Info: ^7{}\n^9Author: ^7{}\n^9Jumps: ^7{}\n^9Difficulty: ^7{}/100".format(
                                    map_name, map_info['author'], map_info['jumps'], map_info['difficulty'][0])
                            else:
                                msg = "^8No information available for {}.".format(map_name)
                    else:
                        # No map specified, use current map
                        current_map = self.get_current_map()
                        if current_map:
                            map_info = self.get_map_info(current_map)
                            if map_info:
                                msg = "^9Map Info: ^7{}\n^9Author: ^7{}\n^9Jumps: ^7{}\n^9Difficulty: ^7{}/100".format(
                                    current_map, map_info['author'], map_info['jumps'], map_info['difficulty'][0])
                            else:
                                msg = "^8No information available for {}.".format(current_map)
                        else:
                            msg = "^8Unable to retrieve current map."
                    # Send response to player
                    self.tell_say_message(sar, msg)
                else:
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")

            elif sar['command'] in ('!time', '@time'):
                current_time = ntime.strftime("%H:%M", ntime.localtime())
                msg = "^7Current server time: ^9%s" % current_time
                self.game.rcon_tell(sar['player_num'], msg)

            # spec - move yourself to spectator
            elif sar['command'] in ('!spec', '!sp'): 
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['spec']['level']:
                    self.game.rcon_forceteam(sar['player_num'], 'spectator')
                else:
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")

            # spec - move yourself back to game
            elif sar['command'] in ('!play', '!pl'): 
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['play']['level']:
                    self.game.rcon_forceteam(sar['player_num'], 'free')
                else: 
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")

            #ready - play timer
            elif sar['command'] in ('!ready', '!r'):    
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['ready']['level']:
                    with self.players_lock:
                        for player in self.game.players.itervalues():
                            game_data = {
                                Player.teams[1]: 0, Player.teams[2]: 0, Player.teams[3]: -1}
                            if player.get_team() == 3:
                                msg = "^7Cannot use whilst in spec!"
                                self.tell_say_message(sar, msg)
                                return
                            else:
                                self.game.send_rcon("spoof %s ready" % (self.game.players[sar['player_num']].get_name()))
                                return
                else:
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")

            #noclip
            elif sar['command'] in ('!noclip', '!n'): 
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['ready']['level']:
                    with self.players_lock:
                        for player in self.game.players.itervalues():
                            game_data = {
                                Player.teams[1]: 0, Player.teams[2]: 0, Player.teams[3]: -1}
                            if player.get_team() == 3:
                                msg = "^7Cannot use whilst in spec!"
                                self.tell_say_message(sar, msg)
                                return
                            else:
                                self.game.send_rcon("spoof %s noclip" % (self.game.players[sar['player_num']].get_name()))
                                return
                else:
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")

            #regainstamina
            elif sar['command'] in ('!regainstamina', '!rgs'): 
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['regainstamina']['level']:
                    with self.players_lock:    
                        for player in self.game.players.itervalues():
                            game_data = {
                                Player.teams[1]: 0, Player.teams[2]: 0, Player.teams[3]: -1}
                            if player.get_team() == 3:
                                msg = "^7Cannot use whilst in spec!"
                                self.tell_say_message(sar, msg)
                                return
                            else:
                                self.game.send_rcon("spoof %s regainstamina" % (
                                    self.game.players[sar['player_num']].get_name()))
                                return
                else:    
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")

            # allowgot
            elif sar['command'] in ('!allowgoto', '!alg'):
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['allowgoto']['level']:
                    self.game.send_rcon("spoof %s allowgoto" % (self.game.players[sar['player_num']].get_name()))            
                else:   
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")

            # topruns
            elif sar['command'] in ('!topruns', '!tr'):
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['topruns']['level']:
                    current_map = self.get_current_map()
                    
                    if current_map:
                        records = self.get_jump_records(current_map)
                        
                        if records:
                            # Structure to store times by way
                            ways = {}
                            
                            # Fill the structure with records from the JSON file
                            for player, times in records.items():
                                for way, time in times.items():
                                    if way not in ways:
                                        ways[way] = []
                                    ways[way].append((player, time))
                            
                            # Build message with the top three times for each way
                            for way, results in sorted(ways.items()):
                                # Sort times in ascending order
                                top3 = sorted(results, key=lambda x: x[1])[:3]
                                msg = "^8Way {}:^7 ".format(way)
                                for player, time in top3:
                                    minutes = time // 60000
                                    seconds = (time % 60000) // 1000
                                    milliseconds = time % 1000
                                    msg += "^9{}:^7 {}m {}s {}ms, ".format(player, minutes, seconds, milliseconds)
                                msg = msg.rstrip(', ')
                                # Send message for each way
                                self.tell_say_message(sar, msg)
                        else:
                            msg = "^8No records available for {}.".format(current_map)
                            self.tell_say_message(sar, msg)
                    else:
                        msg = "^8Unable to retrieve current map."
                        self.tell_say_message(sar, msg)
                else:    
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")
            
            
            # !transl <lang> <text>
            elif sar['command'] in ('!transl'):
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['transl']['level']:
                    if len(line.split(sar['command'])) <= 1:
                        self.game.rcon_tell(
                            sar['player_num'], "^7Usage: ^8!transl ^7<^8lang^7> <^8text^7>")
                    else:
                        arg = line.split(sar['command'])[1].split()
                        if len(arg) > 1:
                            pname = self.game.players[sar['player_num']].get_name()
                            lang = arg[0]
                            text = ' '.join(arg[1:])
                            cmd = ['python3', 'mod/translation.py', lang, text]
                            result = subprocess.check_output(
                                cmd, universal_newlines=True).strip()
                            msg = "^9%s ^8%s" % (pname, result)
                            self.game.rcon_say(msg)
                        else:
                            self.game.rcon_tell(
                                sar['player_num'], "^7Usage: ^8!transl ^7<^8lang^7> <^8text^7>")
                else:
                    msg = "^7You are not registered! ^7Please ^9!register ^7to use this command."
                    self.tell_say_message(sar, msg)                

            # vote on cycling map
            elif sar['command'] in ('!votecycle', '!vc'):
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['votecycle']['level']:
                    player_num = sar['player_num']
                    self.game.send_rcon(
                        "spoof %s callvote cyclemap" % (player_num))
                else:
                    msg = "^7You are not registered! ^7Please ^9!register ^7to use this command."
                    self.tell_say_message(sar, msg)   

            # vote on changing current map
            elif sar['command'] in ('!votemap', '!vm'):
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['votemap']['level']:
                    player_num = sar['player_num']
                    if line.split(sar['command'])[1]:
                        arg = line.split(sar['command'])[1].strip()
                        found, newmap, msg = self.map_found(arg)
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        elif self.game.get_cvar('mapname') == newmap:
                            self.game.rcon_tell(
                                sar['player_num'], "^7[^9%s^7]: is already the current map!" % newmap)
                        else:
                            self.game.send_rcon(
                                "spoof %s callvote map %s" % (player_num, newmap))
                    else:
                        self.game.rcon_tell(
                            sar['player_num'], COMMANDS['votemap']['syntax'])
                else:
                    msg = "^7You are not registered! ^7Please ^9!register ^7to use this command."
                    self.tell_say_message(sar, msg) 

            # vote on setting nextmap
            elif sar['command'] in ('!votenextmap', '!vn'):
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['votenextmap']['level']:
                    player_num = sar['player_num']
                    if line.split(sar['command'])[1]:
                        arg = line.split(sar['command'])[1].strip()
                        found, nextmap, msg = self.map_found(arg)
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        elif self.game.get_cvar('g_nextmap') == nextmap:
                            self.game.rcon_bigtext(
                                "^7[^9%s^7]: is already set as the nextmap!" % nextmap)
                        else:
                            self.game.send_rcon(
                                "spoof %s callvote nextmap %s" % (player_num, nextmap))
                    else:
                        self.game.rcon_tell(
                            sar['player_num'], COMMANDS['votenextmap']['syntax'])  
                else:
                    msg = "^7You are not registered! ^7Please ^9!register ^7to use this command."
                    self.tell_say_message(sar, msg)

            

            
            # Command !top (displays only the current player's times)
            elif sar['command'] == '!top':
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['top']['level']:
                    current_map = self.get_current_map()
                    player_name = self.game.players[sar['player_num']].get_name()
                    
                    if current_map:
                        records = self.get_jump_records(current_map)
                        
                        if records and player_name in records:
                            player_records = records[player_name]
                            for way, time in sorted(player_records.items()):
                                minutes = time // 60000
                                seconds = (time % 60000) // 1000
                                milliseconds = time % 1000
                                msg = "^8Way {}:^7 ^9{}:^7 {}m {}s {}ms".format(way, player_name, minutes, seconds, milliseconds)
                                self.tell_say_message(sar, msg)
                        else:
                            msg = "^8No records found for {} on {}.".format(player_name, current_map)
                            self.tell_say_message(sar, msg)
                    else:
                        msg = "^8Unable to retrieve current map."
                        self.tell_say_message(sar, msg)
                else: 
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")

            # !glist command
            elif sar['command'] == '!glist': 
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['glist']['level']:
                    current_map = self.get_current_map()

                    if current_map:
                        map_json_file = os.path.join(self.json_path, "{}.json".format(current_map))
                        if os.path.exists(map_json_file):
                            with open(map_json_file, 'r') as file:
                                map_data = json.load(file)
                            
                            if map_data:
                                # Simple alphabetical sorting of points
                                sorted_points = sorted(map_data.keys())
                                
                                # Building the response message
                                msg = "^9Goto list: ^7{}".format(", ".join(sorted_points))
                            else:
                                msg = "^8No positions found for this map."
                        else:
                            msg = "^8No positions found for this map."
                    else:
                        msg = "^8Unable to retrieve current map."

                    self.tell_say_message(sar, msg)
                else:    
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")

            # Modified !goto command
            elif sar['command'] == '!goto': 
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['goto']['level']:
                    jump_name = line.split(sar['command'])[1].strip()
                    # Get position from JSON
                    position_data = self.get_position_from_json(jump_name)
                   
                    if position_data:
                        # Split position data
                        position_parts = position_data.split(", ")
                        if len(position_parts) == 6:  # Make sure we have coordinates and angles
                            # Build the command with all parameters, including roll
                            position_for_rcon = position_data
                            
                            # Send RCON command to teleport the player
                            player_num = self.game.players[sar['player_num']].get_player_num()
                            rcon_command = "loadplayerpos {} {}".format(player_num, position_for_rcon)
                            try:
                                response = self.game.get_rcon_output(rcon_command)
                                clean_message = response[1].strip()
                                
                                if "ready" in clean_message:
                                    self.tell_say_message(sar, "^7Cannot use Goto in ready")
                                else:
                                    self.tell_say_message(sar, "^9Teleported to: {}".format(jump_name))
                            except Exception as e:
                                self.tell_say_message(sar, "^8Error executing RCON command: {}".format(e))
                        else:
                            self.tell_say_message(sar, "^8Invalid position format: {}".format(position_data))
                    else:
                        self.tell_say_message(sar, "^8Jump name '{}' not found.".format(jump_name))
                else:    
                    self.game.rcon_tell(sar['player_num'], "^7You are not registered! ^7Please ^9!register ^7to use this command.")

            elif sar['command'] == '!msgadmin':
                if self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['msgadmin']['level']:
                    if line.split(sar['command'])[1]:
                        message = line.split(sar['command'])[1].strip()
                        
                        # Find all admins with high level (e.g., 80+)
                        admin_found = False
                        for player in self.game.players.itervalues():
                            if player.get_admin_role() >= 80:  # Senior admin level or higher
                                # Send message to this admin
                                self.add_pending_message(sar, player.get_name(), message)
                                admin_found = True
                        
                        # If no high-level admin is found in the current players list
                        # Look for the last connected admin, or use "admin" as fallback
                        if not admin_found:
                            if self.last_admin:
                                recipient = self.last_admin.get_name()
                            else:
                                # Search for an admin in the database
                                try:
                                    curs.execute("SELECT `name` FROM `xlrstats` WHERE `admin_role` >= 80 ORDER BY `last_played` DESC LIMIT 1")
                                    result = curs.fetchone()
                                    recipient = result[0] if result else "admin"  # Fallback if no admin found
                                except Exception as e:
                                    logger.error("Error searching admin in database: %s", e)
                                    recipient = "admin"  # Fallback in case of error
                            
                            self.add_pending_message(sar, recipient, message)
                        
                        self.game.rcon_tell(sar['player_num'], "^7Your message has been sent to administrators.")
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['msgadmin']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], "^7You are not authorized to use this command")

## mod level 40
            
            elif sar['command'] == '!sendmessage' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['sendmessage']['level']:
                parts = line.split(sar['command'])[1].strip().split(' ', 1)
                if len(parts) == 2:
                    recipient = parts[0]
                    message = parts[1]
                    self.add_pending_message(sar, recipient, message)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['sendmessage']['syntax'])

            elif sar['command'] == '!delmessage' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['delmessage']['level']:
                if line.split(sar['command'])[1]:
                    recipient = line.split(sar['command'])[1].strip()
                    self.delete_pending_messages(sar, recipient)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['delmessage']['syntax'])

            # admintest - display current admin status
            elif sar['command'] == '!admintest' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['admintest']['level']:
                player_admin_role = self.game.players[sar['player_num']].get_admin_role()
                self.game.rcon_tell(sar['player_num'], "^7%s [^7@%s^7] is ^7%s ^7[^9%d^7]" % (self.game.players[sar['player_num']].get_name(), self.game.players[sar['player_num']].get_player_id(), self.game.players[sar['player_num']].roles[player_admin_role], player_admin_role))

            # country / locate
            elif (sar['command'] == '!country' or sar['command'] == '@country' or sar['command'] == '!locate' or sar['command'] == '@locate' or sar['command'] == '!lc') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['country']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        msg = "^7%s ^7is connecting from ^7%s" % (victim.get_name(), victim.get_country())
                        self.tell_say_message(sar, msg)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['country']['syntax'])

            # map downloads !download
            elif sar['command'] == '!download' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['download']['level']:
                map_list = self.game.get_all_maps()
                reload = False

                # Check arguments
                if line.split(sar['command'])[1]:
                    tmp = line.split(sar['command'])[1].strip()
                    maps = tmp.split(" ")

                    for map in maps:
                        map_name = map.replace(".pk3", "")

                        # Check if the map already exists
                        if map_name in map_list:
                            self.game.rcon_tell(sar['player_num'], "^7Map: [^9%s^7] is already on server!" % map_name)
                            continue

                        try:
                            # Build the complete URL
                            full_url = CONFIG.get('server', 'download_url') + map_name + ".pk3"
                            print("Attempting to download:", full_url)

                            # Download the map
                            self.game.rcon_say("^7Downloading map: [^9%s^7], server will reload once complete!" % map_name)
                            wget.download(full_url, out=CONFIG.get('server', 'download_folder'))
                            self.game.rcon_say("^7Downloading map: [^9%s^7] (Finished!), server will now reload!" % map_name)

                            # Add the downloaded map to the mapcycle.txt file
                            try:
                                  # Path to mapcycle.txt file
                                with open(self.mapcycleway, "a") as mapcycle_file:
                                    mapcycle_file.write(map_name + "\n")  # Writing compatible with Python 2.7
                                logger.info("Map '%s' added to mapcycle.txt", map_name)
                                self.game.rcon_tell(sar['player_num'], "^7Map: [^9%s^7] has been added to mapcycle.txt." % map_name)
                            except Exception as mapcycle_err:
                                logger.error("Failed to write map '%s' to mapcycle.txt: %s", map_name, str(mapcycle_err))
                                self.game.rcon_tell(sar['player_num'], "^7Failed to add map: ^7%s to mapcycle.txt!" % map_name)

                            # Add to the in-memory map list
                            map_list.append(map_name)
                            reload = True

                        except Exception as e:
                            # Log the error and notify the user
                            logger.error("Failed to download map %s: %s" % (map_name, str(e)))
                            self.game.rcon_tell(sar['player_num'], "^7Can't download the map: ^7%s in depot UrT maps server address!" % map_name)

                # Reload the server if necessary
                if reload:
                    self.game.send_rcon('reload')
            
            elif sar['command'] == '!delmap' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['delmap']['level']:
                if line.split(sar['command'])[1]:
                    map_name = line.split(sar['command'])[1].strip()
                    # Check if the map exists
                    found, map_name, msg = self.map_found(map_name)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        try:
                            # Read the current content of mapcycle.txt
                            with open(self.mapcycleway, 'r') as f:
                                maps = f.readlines()
                            
                            # Filter to remove the map
                            maps = [m.strip() for m in maps if m.strip() != map_name]
                            
                            # Rewrite the file without the map
                            with open(self.mapcycleway, 'w') as f:
                                f.write('\n'.join(maps) + '\n')
                            
                            # Update the in-memory map list
                            if map_name in self.game.maplist:
                                self.game.maplist.remove(map_name)
                            
                            self.game.rcon_tell(sar['player_num'], "^7Map ^9{map_name} ^7removed from mapcycle")
                            # Reload the server configuration
                            self.game.send_rcon('reload')
                        except Exception as e:
                            self.game.rcon_tell(sar['player_num'], "^8Error removing map: {e}")
                else:
                    self.game.rcon_tell(sar['player_num'], "^7Usage: !delmap <mapname>")
            
            # !setgoto command
            elif sar['command'] == '!setgoto' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['setgoto']['level']:
                jump_name = line.split(sar['command'])[1].strip()
                self.tell_say_message(sar, "^9Processing !setgoto for jump: {}".format(jump_name))

                # Save current player position
                player_id = sar['player_num']
                rcon_command = "saveplayerpos {}".format(player_id)

                try:
                    # Get all RCON output lines
                    rcon_output = self.game.get_rcon_output(rcon_command)
                    clean_message = rcon_output[1].strip()

                    # If no useful line is found
                    if not clean_message:
                        self.tell_say_message(sar, "^8Error: Could not find position data in RCON output.")
                        return

                    # Extract position and angles with a regular expression
                    match = re.search(r"position saved: \((.*?)\) - Angles: \((.*?)\)", clean_message)
                    if match:
                        position = match.group(1)  # Coordinates (x, y, z)
                        angles = match.group(2)    # Angles (pitch, yaw, roll)

                        # Combine position and angles in the expected format
                        full_position = "{}, {}".format(position, angles)

                        # Save to JSON
                        player_name = self.game.players[sar['player_num']].get_name()
                        self.save_position_to_json(sar, jump_name, player_name, full_position)
                        self.tell_say_message(sar, "^9Position saved successfully for jump: {}".format(jump_name))
                    else:
                        self.tell_say_message(sar, "^8Error: Could not parse position from log.")
                except Exception as e:
                    self.tell_say_message(sar, "^8Error processing !setgoto: {}".format(e))

        
            elif sar['command'] == '!setmapinfo' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['setmapinfo']['level']:
                args = line.split(sar['command'])[1].strip().split(' ', 3)  # Split into 4 parts max
                if len(args) >= 4:
                    map_name = args[0]
                    difficulty = args[1]
                    num_jumps = args[2]
                    author = args[3]  # The rest is considered as author(s)
                    
                    if difficulty.isdigit() and 0 <= int(difficulty) <= 100:
                        if num_jumps.isdigit():
                            # Check if the map exists
                            found, map_name, msg = self.map_found(map_name)
                            if not found:
                                msg = "^8Map not found: {}".format(map_name)
                            else:
                                if self.save_map_info(map_name, author.strip(), int(num_jumps), int(difficulty)):
                                    msg = "^7Map info saved for ^9{}: ^7Difficulty: ^9{}/100, ^7Jumps: ^9{}, ^7Author(s): ^9{}".format(
                                        map_name, difficulty, num_jumps, author)
                                else:
                                    msg = "^8Error saving map info"
                        else:
                            msg = "^8Number of jumps must be a number"
                    else:
                        msg = "^8Difficulty must be a number between 0 and 100"
                else:
                    msg = COMMANDS['setmapinfo']['syntax']
        
                self.tell_say_message(sar, msg)

            elif sar['command'] == '!delmapinfo' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['delmapinfo']['level']:
                if line.split(sar['command'])[1]:
                    map_name = line.split(sar['command'])[1].strip()
                    # Check if the map exists
                    found, map_name, msg = self.map_found(map_name)
                    if not found:
                        msg = "^8Map not found: {}".format(map_name)
                    else:
                        if self.delete_map_info(map_name):
                            msg = "^7Map info deleted for ^9{}".format(map_name)
                        else:
                            msg = "^8No info found for map {}".format(map_name) 
                else:
                    msg = COMMANDS['delmapinfo']['syntax']
                
                self.tell_say_message(sar, msg)
            
            elif sar['command'] == '!delgoto' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['delgoto']['level']:
                if line.split(sar['command'])[1]:
                    jump_name = line.split(sar['command'])[1].strip()
                    self.delete_position_from_json(sar, jump_name)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['delgoto']['syntax'])
            
            #!g_stamina
            elif sar['command'] == '!g_stamina' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['g_stamina']['level']:
                stam = self.game.get_cvar('g_stamina')
                stam = int(stam)
                if stam == 1:
                    self.game.send_rcon("g_stamina 2")
                    self.game.rcon_say("^7Full stamina ^9On^7 !")
                else:
                    self.game.send_rcon("g_stamina 1")
                    self.game.rcon_say("^7Full stamina ^8Off^7 !")
            #!walljump
            elif sar['command'] == '!g_walljump' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['g_walljump']['level']:
                wj = self.game.get_cvar('g_walljumps')
                wj = int(wj)
                if wj == 3:
                    self.game.send_rcon("g_walljumps 100")
                    self.game.rcon_say("^7Full walljumps ^9On^7 !")
                else:
                    self.game.send_rcon("g_walljumps 3")
                    self.game.rcon_say("^7Full walljumps ^8Off^7 !")
            
            # poke - notify a player that he needs to move
            elif sar['command'] == '!poke' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['poke']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        self.game.rcon_tell(sar['player_num'], "^7%s %s!" % (random.choice(poke_options), victim.get_name()))
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['poke']['syntax'])

            # leveltest
            elif (sar['command'] == '!leveltest' or sar['command'] == '!lt') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['leveltest']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        victim_admin_role = victim.get_admin_role()
                        if victim_admin_role > 0:
                            self.game.rcon_tell(sar['player_num'], "^7%s [^7@%s^7] is ^7%s ^7[^9%d^7] and registered since ^7%s" % (victim.get_name(), victim.get_player_id(), victim.roles[victim_admin_role], victim_admin_role, victim.get_first_seen_date()))
                        else:
                            self.game.rcon_tell(sar['player_num'], "^7%s [^7@%s^7] is ^7%s ^7[^9%d^7]" % (victim.get_name(), victim.get_player_id(), victim.roles[victim_admin_role], victim_admin_role))
                else:
                    self.game.rcon_tell(sar['player_num'], "^7Level %s [^9%d^7]: ^7%s" % (self.game.players[sar['player_num']].get_name(), self.game.players[sar['player_num']].get_admin_role(), self.game.players[sar['player_num']].roles[self.game.players[sar['player_num']].get_admin_role()]))

            # lastmaps - list the last played maps
            elif sar['command'] == '!lastmaps' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['lastmaps']['level']:
                if self.game.get_last_maps():
                    self.game.rcon_tell(sar['player_num'], "^7Last Maps: ^7%s" % ", ".join(self.game.get_last_maps()))
                else:
                    self.game.rcon_tell(sar['player_num'], "^7No maps have been played since Spunky Bot started")

            # lastvote - display information about the last called vote
            elif sar['command'] == "!lastvote" and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['lastvote']['level']:
                if self.last_vote:
                    self.game.rcon_tell(sar['player_num'], "^7Last vote: ^9%s" % self.last_vote)
                else:
                    self.game.rcon_tell(sar['player_num'], "^7No votes have been called since Spunky Bot started")

            # list - list all connected players
            elif sar['command'] == '!list' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['list']['level']:
                msg = "^7Players online: %s" % ", ".join(["^7%s [^9%d^7]" % (player.get_name(), player.get_player_num()) for player in self.game.players.itervalues() if player.get_player_num() != BOT_PLAYER_NUM])
                self.game.rcon_tell(sar['player_num'], msg)

            # nextmap - display the next map in rotation
            elif (sar['command'] == '!nextmap' or sar['command'] == '@nextmap') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['nextmap']['level']:
                msg = self.get_nextmap()
                self.tell_say_message(sar, msg)

            # mute - mute or unmute a player
            elif sar['command'] == '!mute' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['mute']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    if len(arg) > 1:
                        user = arg[0]
                        duration = arg[1]
                        if not duration.isdigit():
                            duration = ''
                    else:
                        user = arg[0]
                        duration = ''
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        self.game.send_rcon("mute %d %s" % (victim.get_player_num(), duration))
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['mute']['syntax'])

            # warninfo - display how many warnings the player has
            elif (sar['command'] == '!warninfo' or sar['command'] == '!wi') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['warninfo']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        # clear if already expired
                        if victim.get_last_warn_time() + self.warn_expiration < time.time():
                            victim.clear_warning()
                        warn_count = victim.get_warning()
                        warn_time = int(math.ceil(float(victim.get_last_warn_time() + self.warn_expiration - time.time()) / 60))
                        self.game.rcon_tell(sar['player_num'], "^7%s ^7has ^9%s ^7active warning%s%s" % (victim.get_name(), warn_count if warn_count > 0 else 'no', 's' if warn_count > 1 else '', ", expires in ^8%s ^7minute%s: ^7%s" % (warn_time, "s" if warn_time > 1 else "", ", ^7".join(victim.get_all_warn_msg())) if warn_count > 0 else ''))
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['warninfo']['syntax'])

            # warn - warn user - !warn <name> [<reason>]
            elif (sar['command'] == '!warn' or sar['command'] == '!w') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['warn']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    if arg:
                        user = arg[0]
                        reason = ' '.join(arg[1:])[:40].strip() if len(arg) > 1 else 'behave yourself'
                        found, victim, msg = self.player_found(user)
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        else:
                            warn_delay = 15
                            if victim.get_admin_role() >= self.game.players[sar['player_num']].get_admin_role():
                                self.game.rcon_tell(sar['player_num'], "^7You cannot warn an admin")
                            elif victim.get_last_warn_time() + warn_delay > time.time():
                                self.game.rcon_tell(sar['player_num'], "^7Only one warning per %d seconds can be issued" % warn_delay)
                            else:
                                # clear if already expired
                                if victim.get_last_warn_time() + self.warn_expiration < time.time():
                                    victim.clear_warning()
                                show_alert = False
                                ban_duration = 0
                                if victim.get_warning() > 2:
                                    self.game.kick_player(victim.get_player_num(), reason='too many warnings')
                                    msg = "^9%s ^7was kicked, too many warnings" % victim.get_name()
                                else:
                                    if reason in REASONS:
                                        warning = REASONS[reason]
                                        if reason == 'tk' and victim.get_warning() > 1:
                                            ban_duration = victim.add_ban_point('tk, ban by %s' % self.game.players[sar['player_num']].get_name(), 900)
                                        elif reason == 'lang' and victim.get_warning() > 1:
                                            ban_duration = victim.add_ban_point('lang', 300)
                                        elif reason == 'spam' and victim.get_warning() > 1:
                                            ban_duration = victim.add_ban_point('spam', 300)
                                        elif reason == 'racism':
                                            ban_duration = victim.add_ban_point('racism', 900)
                                        elif reason == 'name' and victim.get_warning() > 1:
                                            ban_duration = victim.add_ban_point('name', 900)
                                        elif reason == 'sk' and victim.get_warning() > 1:
                                            ban_duration = victim.add_ban_point('sk', 900)
                                        elif reason == 'camp':
                                            ban_duration = victim.add_ban_point('camp', 900)
                                    else:
                                        warning = reason
                                    victim.add_warning(warning)
                                    msg = "^8WARNING ^7[^7%d^7]: ^9%s^7: %s" % (victim.get_warning(), victim.get_name(), warning)
                                    # ban player if needed
                                    if ban_duration > 0:
                                        msg = "^9%s ^7banned for ^8%d minutes ^7for too many warnings" % (victim.get_name(), ban_duration)
                                        self.game.kick_player(victim.get_player_num(), reason='too many warnings')
                                    # show alert message for player with 3 warnings
                                    elif victim.get_warning() == 3:
                                        show_alert = True
                                self.game.rcon_say(msg)
                                if show_alert:
                                    self.game.rcon_say("^8ALERT: ^9%s ^7auto-kick from warnings if not cleared" % victim.get_name())
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['warn']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['warn']['syntax'])

            # warnremove - remove a player's last warning
            elif (sar['command'] == '!warnremove' or sar['command'] == '!wr') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['warnremove']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        last_warning = victim.clear_last_warning()
                        if last_warning:
                            self.game.rcon_say("^7Last warning removed for %s: ^7%s" % (victim.get_name(), last_warning))
                        else:
                            self.game.rcon_tell(sar['player_num'], "^7%s ^7has no active warning" % victim.get_name())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['warnremove']['syntax'])

            # warns - list the warnings
            elif sar['command'] == '!warns' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['warns']['level']:
                keylist = REASONS.keys()
                keylist.sort()
                self.game.rcon_tell(sar['player_num'], "^7Warnings: ^7%s" % ", ^7".join([key for key in keylist]))

            # warntest - test a warning
            elif (sar['command'] == '!warntest' or sar['command'] == '!wt') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['warntest']['level']:
                if line.split(sar['command'])[1]:
                    reason = line.split(sar['command'])[1].strip()
                    warning = REASONS[reason] if reason in REASONS else reason
                else:
                    warning = 'behave yourself'
                self.game.rcon_tell(sar['player_num'], "^9TEST: ^8WARNING ^7[^71^7]: ^4%s" % warning)

## admin level 40
            # admins - list all the online admins
            elif (sar['command'] == '!admins' or sar['command'] == '@admins') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['admins']['level']:
                msg = self.get_admins_online()
                self.tell_say_message(sar, msg)

            # !regulars/!regs - display the regular players online
            elif (sar['command'] == '!regulars' or sar['command'] == '!regs' or sar['command'] == '@regulars') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['regulars']['level']:
                liste = "%s" % ", ".join(["^7%s [^9%d^7]" % (player.get_name(), player.get_admin_role()) for player in self.game.players.itervalues() if player.get_admin_role() == 2])
                msg = "^7Regulars online: %s" % liste if liste else "^7No regulars online"
                self.tell_say_message(sar, msg)

            # aliases - list the aliases of the player
            elif (sar['command'] == '!aliases' or sar['command'] == '@aliases' or sar['command'] == '!alias' or sar['command'] == '@alias') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['aliases']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        msg = "^7Aliases of ^5%s: ^7%s" % (victim.get_name(), victim.get_aliases())
                        self.tell_say_message(sar, msg)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['aliases']['syntax'])

            # bigtext - display big message on screen
            elif sar['command'] == '!bigtext' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['bigtext']['level']:
                if line.split(sar['command'])[1]:
                    self.game.rcon_bigtext("%s" % line.split(sar['command'])[1].strip())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['bigtext']['syntax'])

            # say - say a message to all players
            elif sar['command'] == '!say' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['say']['level']:
                if line.split(sar['command'])[1]:
                    self.game.rcon_say("^4%s: ^7%s" % (self.game.players[sar['player_num']].get_name(), line.split(sar['command'])[1].strip()))
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['say']['syntax'])

            # !!<text> - allow spectator to say a message to players in-game
            elif sar['command'].startswith('!!') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['say']['level']:
                if line.split('!!')[1]:
                    self.game.rcon_say("^4%s: ^7%s" % (self.game.players[sar['player_num']].get_name(), line.split('!!', 1)[1].strip()))

            # tell - tell a message to a specific player - !tell <name|id> <text>
            elif sar['command'] == '!tell' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['tell']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    if len(arg) > 1:
                        user = arg[0]
                        message = ' '.join(arg[1:]).strip()
                        found, victim, msg = self.player_found(user)
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        else:
                            self.game.rcon_tell(victim.get_player_num(), "^4%s: ^7%s" % (self.game.players[sar['player_num']].get_name(), message))
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['tell']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['tell']['syntax'])

            # exit - display last disconnected player of this match
            elif sar['command'] == '!exit' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['exit']['level']:
                msg = "^7Last disconnected player: ^7%s" % self.last_disconnected_player.get_name() if self.last_disconnected_player else "^7No player left during this match"
                self.game.rcon_tell(sar['player_num'], msg)

            # find - display the slot number of the player
            elif sar['command'] == '!find' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['find']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    self.game.rcon_tell(sar['player_num'], msg)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['find']['syntax'])

            # afk - force a player to spec, because he is away from keyboard - !afk <name>
            elif sar['command'] == '!afk' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['afk']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].split()[0]
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        self.game.rcon_forceteam(victim.get_player_num(), 'spectator')
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['afk']['syntax'])

            # force - force a player to the given team
            elif sar['command'] == '!force' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['force']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    if len(arg) > 1:
                        user = arg[0]
                        team = arg[1]
                        lock = False
                        if len(arg) > 2:
                            lock = True if arg[2] == 'lock' else False
                        team_dict = {'red': 'red', 'r': 'red', 're': 'red',
                                     'blue': 'blue', 'b': 'blue', 'bl': 'blue', 'blu': 'blue',
                                     'spec': 'spectator', 'spectator': 'spectator', 's': 'spectator', 'sp': 'spectator', 'spe': 'spectator',
                                     'green': 'green'}
                        found, victim, msg = self.player_found(user)
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        else:
                            if team in team_dict:
                                victim_player_num = victim.get_player_num()
                                self.game.rcon_forceteam(victim_player_num, team_dict[team])
                                self.game.rcon_tell(victim_player_num, "^7You are forced to: ^7%s" % team_dict[team])
                                # set team lock if defined
                                if lock:
                                    victim.set_team_lock(team_dict[team])
                                else:
                                    victim.set_team_lock(None)
                            # release the player from a forced team
                            elif team == "free":
                                victim.set_team_lock(None)
                            else:
                                self.game.rcon_tell(sar['player_num'], COMMANDS['force']['syntax'])
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['force']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['force']['syntax'])

            # nuke - nuke a player
            elif sar['command'] == '!nuke' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['nuke']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].split()[0]
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        if victim.get_admin_role() >= self.game.players[sar['player_num']].get_admin_role():
                            self.game.rcon_tell(sar['player_num'], "^7Insufficient privileges to nuke an admin")
                        else:
                            self.game.send_rcon("nuke %d" % victim.get_player_num())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['nuke']['syntax'])

            # kick - kick a player
            elif (sar['command'] == '!kick' or sar['command'] == '!k') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['kick']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    if self.game.players[sar['player_num']].get_admin_role() >= 80 and len(arg) == 1:
                        user = arg[0]
                        reason = '.'
                    elif len(arg) > 1:
                        user = arg[0]
                        reason = ' '.join(arg[1:])[:40].strip()
                    else:
                        user = reason = None
                    if user and reason:
                        found, victim, msg = self.player_found(user)
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        else:
                            if sar['player_num'] == victim.get_player_num():
                                self.game.rcon_tell(sar['player_num'], "^7You cannot kick yourself")
                            elif victim.get_admin_role() >= self.game.players[sar['player_num']].get_admin_role():
                                self.game.rcon_tell(sar['player_num'], "^7Insufficient privileges to kick an admin")
                            else:
                                msg = "^9%s ^7was kicked by %s" % (victim.get_name(), self.game.players[sar['player_num']].get_name())
                                if reason in REASONS:
                                    kick_reason = REASONS[reason]
                                    msg = "%s: ^7%s" % (msg, kick_reason)
                                elif reason == '.':
                                    kick_reason = ''
                                else:
                                    kick_reason = reason
                                    msg = "%s: ^7%s" % (msg, kick_reason)
                                self.game.kick_player(victim.get_player_num(), reason=kick_reason)
                                self.game.rcon_say(msg)
                    else:
                        self.game.rcon_tell(sar['player_num'], "^7You need to enter a reason: ^7!kick <name> <reason>")
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['kick']['syntax'])

            # warnclear - clear the user warnings
            elif (sar['command'] == '!warnclear' or sar['command'] == '!wc') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['warnclear']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        victim.clear_warning()
                        for player in self.game.players.itervalues():
                            player.clear_tk(victim.get_player_num())
                        self.game.rcon_say("^8All warnings and team kills cleared for ^9%s" % victim.get_name())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['warnclear']['syntax'])

            # tempban - ban a player temporary for the given period
            elif (sar['command'] == '!tempban' or sar['command'] == '!tb') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['tempban']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    if len(arg) > 1:
                        user = arg[0]
                        duration, duration_output = self.convert_time(arg[1])
                        reason = ' '.join(arg[2:])[:40].strip() if len(arg) > 2 else 'tempban'
                        kick_reason = REASONS[reason] if reason in REASONS else '' if reason == 'tempban' else reason
                        found, victim, msg = self.player_found(user)
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        else:
                            if sar['player_num'] == victim.get_player_num():
                                self.game.rcon_tell(sar['player_num'], "^7You cannot ban yourself")
                            elif victim.get_admin_role() >= self.game.players[sar['player_num']].get_admin_role():
                                self.game.rcon_tell(sar['player_num'], "^7Insufficient privileges to ban an admin")
                            else:
                                if victim.ban(duration=duration, reason=reason, admin=self.game.players[sar['player_num']].get_name()):
                                    msg = "^9%s ^8banned ^7for ^7%s ^7by %s" % (victim.get_name(), duration_output, self.game.players[sar['player_num']].get_name())
                                    if kick_reason:
                                        msg = "%s: ^7%s" % (msg, kick_reason)
                                    self.game.rcon_say(msg)
                                else:
                                    self.game.rcon_tell(sar['player_num'], "^7This player has already a longer ban")
                                self.game.kick_player(player_num=victim.get_player_num(), reason=kick_reason)
                    else:
                        self.game.rcon_tell(sar['player_num'], "^7You need to enter a duration: ^7!tempban <name> <duration> [<reason>]")
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['tempban']['syntax'])

## full admin level 60
            # ping - display the ping of a player
            elif sar['command'] == '!ping' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['ping']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    player_ping = 0
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        # update rcon status
                        self.game.quake.rcon_update()
                        for player in self.game.quake.players:
                            if victim.get_player_num() == player.num:
                                player_ping = player.ping
                        msg = "^7%s has a ping of ^9%s ms" % (victim.get_name(), player_ping)
                        self.game.rcon_tell(sar['player_num'], msg)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['ping']['syntax'])

            # id - show the IP, guid and authname of a player - !id <name>
            elif sar['command'] == '!id' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['id']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        msg = "^7[^9@%s^7] %s ^9%s ^7[^5%s^7] since ^7%s" % (victim.get_player_id(), victim.get_name(), victim.get_ip_address(), victim.get_authname() if victim.get_authname() else "---", victim.get_first_seen_date())
                        self.game.rcon_tell(sar['player_num'], msg)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['id']['syntax'])

            # scream - scream a message in different colors to all players
            elif sar['command'] == '!scream' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['scream']['level']:
                if line.split(sar['command'])[1]:
                    self.game.rcon_say("^8%s" % line.split(sar['command'])[1].strip())
                    self.game.rcon_say("^9%s" % line.split(sar['command'])[1].strip())
                    self.game.rcon_say("^7%s" % line.split(sar['command'])[1].strip())
                    self.game.rcon_say("^5%s" % line.split(sar['command'])[1].strip())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['scream']['syntax'])

            # slap - slap a player (a number of times); (1-15 times)
            elif sar['command'] == '!slap' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['slap']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    if len(arg) > 1:
                        user = arg[0]
                        number = arg[1]
                        if not number.isdigit():
                            number = 1
                        else:
                            number = int(number)
                        if number > 15:
                            number = 15
                    else:
                        user = arg[0]
                        number = 1
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        if victim.get_admin_role() >= self.game.players[sar['player_num']].get_admin_role():
                            self.game.rcon_tell(sar['player_num'], "^7Insufficient privileges to slap an admin")
                        else:
                            for _ in xrange(0, number):
                                self.game.send_rcon("slap %d" % victim.get_player_num())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['slap']['syntax'])

            # status - report the status of the bot
            elif sar['command'] == '!status' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['status']['level']:
                curs.execute("SELECT 1 FROM player LIMIT 1;")
                msg = "^7Database is ^9UP^7 and Bot started at ^9%s" % self.uptime if curs.fetchall() else "^7Database appears to be ^8DOWN"
                self.game.rcon_tell(sar['player_num'], msg)

            # version - display the version of the bot
            elif sar['command'] == '!version' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['version']['level']:
                self.game.rcon_tell(sar['player_num'], "^7Spunky Bot ^9v%s" % __version__)

            # veto - stop voting process
            elif sar['command'] == '!veto' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['veto']['level']:
                self.game.send_rcon('veto')

            # ci - kick player with connection interrupted
            elif sar['command'] == '!ci' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['ci']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    player_ping = 0
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        # update rcon status
                        self.game.quake.rcon_update()
                        for player in self.game.quake.players:
                            if victim.get_player_num() == player.num:
                                player_ping = player.ping
                        if player_ping == 999:
                            self.game.kick_player(victim.get_player_num(), reason='connection interrupted, try to reconnect')
                            self.game.rcon_say("^9%s ^7was kicked by %s: ^4connection interrupted" % (victim.get_name(), self.game.players[sar['player_num']].get_name()))
                        else:
                            self.game.rcon_tell(sar['player_num'], "^7%s has no connection interrupted" % victim.get_name())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['ci']['syntax'])

            # ban - ban a player for several days
            elif (sar['command'] == '!ban' or sar['command'] == '!b') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['ban']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    if len(arg) == 1 and self.game.players[sar['player_num']].get_admin_role() >= 80:
                        user = arg[0]
                        reason = "tempban"
                    elif len(arg) > 1:
                        user = arg[0]
                        reason = ' '.join(arg[1:])[:40].strip()
                    else:
                        user = reason = None
                    if user and reason:
                        found, victim, msg = self.player_found(user)
                        kick_reason = REASONS[reason] if reason in REASONS else '' if reason == 'tempban' else reason
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        else:
                            if sar['player_num'] == victim.get_player_num():
                                self.game.rcon_tell(sar['player_num'], "^7You cannot ban yourself")
                            elif victim.get_admin_role() >= self.game.players[sar['player_num']].get_admin_role():
                                self.game.rcon_tell(sar['player_num'], "^7Insufficient privileges to ban an admin")
                            else:
                                # ban for given duration in days
                                if victim.ban(duration=(self.ban_duration * 86400), reason=reason, admin=self.game.players[sar['player_num']].get_name()):
                                    msg = "^9%s ^8banned ^7for ^7%d day%s ^7by %s" % (victim.get_name(), self.ban_duration, 's' if self.ban_duration > 1 else '', self.game.players[sar['player_num']].get_name())
                                    if kick_reason:
                                        msg = "%s: ^7%s" % (msg, kick_reason)
                                    self.game.rcon_say(msg)
                                else:
                                    self.game.rcon_tell(sar['player_num'], "^7This player has already a longer ban")
                                self.game.kick_player(player_num=victim.get_player_num(), reason=kick_reason)
                    else:
                        self.game.rcon_tell(sar['player_num'], "^7You need to enter a reason: ^7!ban <name> <reason>")
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['ban']['syntax'])

            # baninfo - display active bans of a player
            elif (sar['command'] == '!baninfo' or sar['command'] == '!bi') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['baninfo']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        curs.execute("SELECT `expires` FROM `ban_list` WHERE `expires` > '{}' AND `guid` = '{}'".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), victim.get_guid()))
                        result = curs.fetchone()
                        if result:
                            self.game.rcon_tell(sar['player_num'], "^7%s ^7has an active ban until [^8%s^7]" % (victim.get_name(), str(result[0])))
                        else:
                            self.game.rcon_tell(sar['player_num'], "^7%s ^7has no active ban" % victim.get_name())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['baninfo']['syntax'])

            # rain - enables or disables rain - !rain <on/off>
            elif sar['command'] == '!rain' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['rain']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip()
                    if arg == "off":
                        self.game.send_rcon('g_enableprecip 0')
                        self.game.rcon_tell(sar['player_num'], "^7Rain: ^8Off")
                    elif arg == "on":
                        self.game.send_rcon('g_enableprecip 1')
                        self.game.rcon_tell(sar['player_num'], "^7Rain: ^9On")
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['rain']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['rain']['syntax'])

## senior admin level 80
            # !kickall <pattern> [<reason>]- kick all players matching <pattern>
            elif (sar['command'] == '!kickall' or sar['command'] == '!kall') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['kickall']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    user = arg[0]
                    reason = ' '.join(arg[1:])[:40].strip() if len(arg) > 1 else ''
                    if len(user) > 2:
                        pattern_list = [player for player in self.game.players.itervalues() if user.upper() in player.get_name().upper() and player.get_player_num() != BOT_PLAYER_NUM]
                        if pattern_list:
                            for player in pattern_list:
                                if player.get_admin_role() >= self.game.players[sar['player_num']].get_admin_role():
                                    self.game.rcon_tell(sar['player_num'], "^7Insufficient privileges to kick an admin")
                                else:
                                    self.game.kick_player(player.get_player_num(), reason)
                        else:
                            self.game.rcon_tell(sar['player_num'], "^7No Players found matching %s" % user)
                    else:
                        self.game.rcon_tell(sar['player_num'], "^7Pattern must be at least 3 characters long")
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['kickall']['syntax'])

            # !banall <pattern> [<reason>]- ban all players matching <pattern>
            elif (sar['command'] == '!banall' or sar['command'] == '!ball') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['banall']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    user = arg[0]
                    reason = ' '.join(arg[1:])[:40].strip() if len(arg) > 1 else 'tempban'
                    if len(user) > 2:
                        pattern_list = [player for player in self.game.players.itervalues() if user.upper() in player.get_name().upper() and player.get_player_num() != BOT_PLAYER_NUM]
                        if pattern_list:
                            for player in pattern_list:
                                if player.get_admin_role() >= self.game.players[sar['player_num']].get_admin_role():
                                    self.game.rcon_tell(sar['player_num'], "^7Insufficient privileges to ban an admin")
                                else:
                                    player.ban(duration=(self.ban_duration * 86400), reason=reason, admin=self.game.players[sar['player_num']].get_name())
                                    self.game.rcon_say("^9%s ^8banned ^7for ^7%d day%s ^7by %s" % (player.get_name(), self.ban_duration, 's' if self.ban_duration > 1 else '', self.game.players[sar['player_num']].get_name()))
                        else:
                            self.game.rcon_tell(sar['player_num'], "^7No Players found matching %s" % user)
                    else:
                        self.game.rcon_tell(sar['player_num'], "^7Pattern must be at least 3 characters long")
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['banall']['syntax'])

            # clear - clear all player warnings - !clear [<player>]
            elif sar['command'] in ('!clear', '!kiss') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['clear']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        victim.clear_warning()
                        for player in self.game.players.itervalues():
                            player.clear_tk(victim.get_player_num())
                        self.game.rcon_say("^8All warnings and team kills cleared for ^9%s" % victim.get_name())
                else:
                    for player in self.game.players.itervalues():
                        player.clear_warning()
                    self.game.rcon_say("^8All player warnings and team kills cleared")

            elif sar['command'] == '!map' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['map']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip()
                    found, newmap, msg = self.map_found(arg)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        self.game.rcon_bigtext("Changing map to: %s " % newmap)
                        self.game.send_rcon('g_nextmap %s' % newmap)
                    
                        self.game.send_rcon('cyclemap')
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['map']['syntax'])

            # mapcycle - list the map rotation
            elif sar['command'] in ('!mapcycle', '@mapcycle') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['mapcycle']['level']:
                self.tell_say_message(sar, "^7Mapcycle: ^7%s" % ', '.join(self.game.maplist))

            # maps - display all available maps
            elif (sar['command'] == '!maps' or sar['command'] == '@maps') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['maps']['level']:
                # Get all available maps
                map_list = self.game.get_all_maps()
                msg1 = "^7Available Maps [^9%s^7] watch liste maps at lafumisterie.net/q3ut4 !" % len(map_list)
                self.tell_say_message(sar, msg1)
                
                # Get next 10 maps
                current_map = self.get_current_map()
                if current_map in self.game.maplist:
                    current_index = self.game.maplist.index(current_map)
                    next_maps = []
                    for i in range(5):
                        next_index = (current_index + i + 1) % len(self.game.maplist)
                        next_maps.append(self.game.maplist[next_index])
                    msg2 = "^7Next maps: ^9%s" % ', '.join(next_maps)
                    self.tell_say_message(sar, msg2)

            # maprestart - restart the map
            elif (sar['command'] == '!maprestart' or sar['command'] == '!restart') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['maprestart']['level']:
                self.game.send_rcon('restart')
                self.stats_reset()

            # moon - activate Moon mode (low gravity)
            elif sar['command'] in ('!moon', '!lowgravity') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['moon']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip()
                    if arg == "off":
                        self.game.send_rcon('g_gravity 800')
                        self.game.rcon_tell(sar['player_num'], "^7Moon mode: ^8Off")
                    elif arg == "on":
                        self.game.send_rcon('g_gravity 100')
                        self.game.rcon_tell(sar['player_num'], "^7Moon mode: ^9On")
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['moon']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['moon']['syntax'])

            # !setgravity <value> - set the gravity value. default = 800 (less means less gravity)
            elif sar['command'] == '!setgravity' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['setgravity']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip()
                    if arg.isdigit():
                        self.game.send_rcon('g_gravity %s' % arg)
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['setgravity']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['setgravity']['syntax'])

            # instagib on/off
            elif sar['command'] == '!instagib' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['instagib']['level']:
                if self.urt_modversion >= 43:
                    if line.split(sar['command'])[1]:
                        arg = line.split(sar['command'])[1].strip()
                        if arg == "off":
                            self.game.send_rcon('g_instagib 0')
                            self.game.rcon_tell(sar['player_num'], "^7Instagib: ^8Off")
                            self.game.rcon_tell(sar['player_num'], "^7Instagib changed for next map")
                        elif arg == "on":
                            self.game.send_rcon('g_instagib 1')
                            self.game.rcon_tell(sar['player_num'], "^7Instagib: ^9On")
                            self.game.rcon_tell(sar['player_num'], "^7Instagib changed for next map")
                        else:
                            self.game.rcon_tell(sar['player_num'], COMMANDS['instagib']['syntax'])
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['instagib']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], "^7The command ^7!instagib ^7is not supported")

            # cyclemap - start next map in rotation
            elif sar['command'] == '!cyclemap' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['cyclemap']['level']:
                self.game.send_rcon('cyclemap')

            elif sar['command'] == '!cvarmap' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['cvarmap']['level']:
                if line.split(sar['command'])[1]:
                    args = line.split(sar['command'])[1].strip().split()
                    if len(args) >= 2:
                        cvar = args[0]
                        value = args[1]
                        current_map = self.get_current_map()
                        
                        # Save cvar for the current map
                        if self.save_map_cvar(current_map, cvar, value):
                            # Apply cvar immediately
                            self.game.send_rcon('%s %s' % (cvar, value))
                            self.game.rcon_tell(sar['player_num'], "^7Custom cvar ^9%s ^7set to ^9%s ^7for map ^9%s" % (cvar, value, current_map))
                        else:
                            self.game.rcon_tell(sar['player_num'], "^8Error saving custom cvar")
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['customcvar']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['customcvar']['syntax'])

            # setnextmap - set the given map as nextmap
            elif sar['command'] == '!setnextmap' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['setnextmap']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip()
                    found, nextmap, msg = self.map_found(arg)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        self.game.send_rcon('g_nextmap %s' % nextmap)
                        self.game.next_mapname = nextmap
                        self.game.rcon_tell(sar['player_num'], "^7Next Map set to: ^7%s" % nextmap)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['setnextmap']['syntax'])

            # rebuild - sync up all available maps
            elif sar['command'] == '!rebuild' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['rebuild']['level']:
                # get full map list
                self.game.set_all_maps()
                self.game.maplist = filter(None, self.game.get_mapcycle_path())
                self.game.rcon_tell(sar['player_num'], "^7Rebuild maps: ^7%s ^7maps found" % len(self.game.get_all_maps()))
                # set current and next map
                self.game.set_current_map()
                self.game.rcon_tell(sar['player_num'], self.get_nextmap())
                self.game.rcon_say("^7Server is now reloading!")
                self.game.send_rcon('reload')
            
            # exec - execute given config file
            elif sar['command'] == '!exec' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['exec']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip()
                    self.game.send_rcon('exec %s' % arg)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['exec']['syntax'])

            # !gear - set allowed weapons
            elif sar['command'] == '!gear' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['gear']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip()
                    # docs: http://www.urbanterror.info/support/180-server-cvars/#2
                    if "all" in arg:
                        self.game.send_rcon('g_gear 0')
                        self.game.rcon_say("^7Gear: ^9All weapons enabled")
                    elif "default" in arg:
                        self.game.send_rcon('g_gear "%s"' % self.default_gear)
                        self.game.rcon_say("^7Gear: ^9Server defaults enabled")
                    elif "knife" in arg:
                        self.game.send_rcon('g_gear "%s"' % 'FGHIJKLMNZacefghijklOQRSTUVWX' if self.urt_modversion > 41 else '63')
                        self.game.rcon_say("^7Gear: ^9Knife only")
                    elif "pistol" in arg:
                        self.game.send_rcon('g_gear "%s"' % 'HIJKLMNZacehijkOQ' if self.urt_modversion > 41 else '55')
                        self.game.rcon_say("^7Gear: ^9Pistols only")
                    elif "shotgun" in arg:
                        self.game.send_rcon('g_gear "%s"' % 'FGIJKLMNZacefghiklOQ' if self.urt_modversion > 41 else '59')
                        self.game.rcon_say("^7Gear: ^9Shotguns only")
                    elif "sniper" in arg:
                        self.game.send_rcon('g_gear "%s"' % 'FGHIJKLMacefghjklOQ' if self.urt_modversion > 41 else '61')
                        self.game.rcon_say("^7Gear: ^9Sniper rifles only")
                    elif "magnum" in arg and self.urt_modversion > 42:
                        self.game.send_rcon('g_gear FGHIJKLMNZacefghijkOQRSTUVWX')
                        self.game.rcon_say("^7Gear: ^9Magnums only")
                    elif "mac" in arg and self.urt_modversion > 42:
                        self.game.send_rcon('g_gear FGHIJKLMNZacefgijklOQ')
                        self.game.rcon_say("^7Gear: ^9MAC11 only")
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['gear']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['gear']['syntax'])

            # kill - kill a player
            elif sar['command'] == '!kill' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['kill']['level']:
                if self.urt_modversion > 41:
                    if line.split(sar['command'])[1]:
                        user = line.split(sar['command'])[1].strip()
                        found, victim, msg = self.player_found(user)
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        else:
                            if victim.get_admin_role() >= self.game.players[sar['player_num']].get_admin_role():
                                self.game.rcon_tell(sar['player_num'], "^7Insufficient privileges to kill an admin")
                            else:
                                self.game.send_rcon("smite %d" % victim.get_player_num())
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['kill']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], "^7The command ^7!kill ^7is not supported")

            # lastadmin - display the last disconnected admin
            elif sar['command'] == '!lastadmin' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['lastadmin']['level']:
                msg = "^7Last disconnected admin: ^7%s [^9%d^7]" % (self.last_admin.get_name(), self.last_admin.get_admin_role()) if self.last_admin else "^7No admin left the server yet"
                self.game.rcon_tell(sar['player_num'], msg)

            # lookup - search for player in database
            elif (sar['command'] == '!lookup' or sar['command'] == '!l') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['lookup']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip()
                    curs.execute("SELECT `id`,`name`,`time_joined` FROM `player` WHERE `name` like '%{}%' ORDER BY `time_joined` DESC LIMIT 8".format(arg))
                    result = curs.fetchall()
                    for row in result:
                        self.game.rcon_tell(sar['player_num'], "^7[^9@%s^7] %s ^7[^8%s^7]" % (str(row[0]), str(row[1]), str(row[2])), False)
                    if not result:
                        self.game.rcon_tell(sar['player_num'], "^7No Player found matching %s" % arg)
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['lookup']['syntax'])

            # permban - ban a player permanent
            elif (sar['command'] == '!permban' or sar['command'] == '!pb') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['permban']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    if len(arg) > 1:
                        user = arg[0]
                        reason = ' '.join(arg[1:])[:40].strip()
                        found, victim, msg = self.player_found(user)
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        else:
                            if sar['player_num'] == victim.get_player_num():
                                self.game.rcon_tell(sar['player_num'], "^7You cannot ban yourself")
                            elif victim.get_admin_role() >= self.game.players[sar['player_num']].get_admin_role():
                                self.game.rcon_tell(sar['player_num'], "^7Insufficient privileges to ban an admin")
                            else:
                                # ban for 20 years
                                victim.ban(duration=630720000, reason=reason, admin=self.game.players[sar['player_num']].get_name())
                                self.game.rcon_say("^9%s ^8banned permanently ^7by %s: ^4%s" % (victim.get_name(), self.game.players[sar['player_num']].get_name(), reason))
                                self.game.kick_player(victim.get_player_num())
                                # add IP address to bot-banlist.txt
                                with open(os.path.join(HOME, 'bot-banlist.txt'), 'a') as banlist:
                                    banlist.write("%s:-1   // %s    banned on  %s, reason : %s\n" % (victim.get_ip_address(), victim.get_name(), time.strftime("%d/%m/%Y (%H:%M)", time.localtime(time.time())), reason))
                    else:
                        self.game.rcon_tell(sar['player_num'], "^7You need to enter a reason: ^7!permban <name> <reason>")
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['permban']['syntax'])

            # makereg - make a player a regular (Level 2) user
            elif (sar['command'] == '!makereg' or sar['command'] == '!mr') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['makereg']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        if victim.get_registered_user():
                            if victim.get_admin_role() < 2:
                                victim.update_db_admin_role(role=2)
                                self.game.rcon_tell(sar['player_num'], "^8%s ^7put in group Regular" % victim.get_name())
                            else:
                                self.game.rcon_tell(sar['player_num'], "^7%s is already in a higher level group" % victim.get_name())
                        else:
                            # register new user in DB and set role to 2
                            victim.register_user_db(role=2)
                            self.game.rcon_tell(sar['player_num'], "^8%s ^7put in group Regular" % victim.get_name())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['makereg']['syntax'])

            # !unreg <player> - remove a player from the regular group
            elif sar['command'] == '!unreg' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['unreg']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        if victim.get_admin_role() == 2:
                            victim.update_db_admin_role(role=1)
                            self.game.rcon_tell(sar['player_num'], "^8%s ^7put in group User" % victim.get_name())
                        else:
                            self.game.rcon_tell(sar['player_num'], "^7%s is not in the regular group" % victim.get_name())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['unreg']['syntax'])

            # putgroup - add a client to a group
            elif sar['command'] == '!putgroup' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['putgroup']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].split()
                    if len(arg) > 1:
                        user = arg[0]
                        right = arg[1]
                        found, victim, msg = self.player_found(user)
                        if not found:
                            self.game.rcon_tell(sar['player_num'], msg)
                        else:
                            if victim.get_registered_user():
                                new_role = victim.get_admin_role()
                            else:
                                # register new user in DB and set role to 1
                                victim.register_user_db(role=1)
                                new_role = 1

                            if right == "user" and victim.get_admin_role() < 80:
                                self.game.rcon_tell(sar['player_num'], "^7%s put in group ^7User" % victim.get_name())
                                new_role = 1
                            elif "reg" in right and victim.get_admin_role() < 80:
                                self.game.rcon_tell(sar['player_num'], "^7%s put in group ^7Regular" % victim.get_name())
                                new_role = 2
                            elif "mod" in right and victim.get_admin_role() < 80:
                                self.game.rcon_tell(sar['player_num'], "^7%s added as ^7Jumper" % victim.get_name())
                                self.game.rcon_tell(victim.get_player_num(), "^7You are added as ^7Jumper")
                                new_role = 20
                            elif right == "admin" and victim.get_admin_role() < 80:
                                self.game.rcon_tell(sar['player_num'], "^7%s added as ^7Admin" % victim.get_name())
                                self.game.rcon_tell(victim.get_player_num(), "^7You are added as ^7Admin")
                                new_role = 40
                            elif "fulladmin" in right and victim.get_admin_role() < 80:
                                self.game.rcon_tell(sar['player_num'], "^7%s added as ^7Full Admin" % victim.get_name())
                                self.game.rcon_tell(victim.get_player_num(), "^7You are added as ^7Full Admin")
                                new_role = 60
                            # Note: senioradmin level can only be set by head admin or super admin
                            elif "senioradmin" in right and self.game.players[sar['player_num']].get_admin_role() >= 90 and victim.get_player_num() != sar['player_num']:
                                self.game.rcon_tell(sar['player_num'], "^7%s added as ^6Senior Admin" % victim.get_name())
                                self.game.rcon_tell(victim.get_player_num(), "^7You are added as ^6Senior Admin")
                                new_role = 80
                            # Note: superadmin level can only be set by head admin
                            elif "superadmin" in right and self.game.players[sar['player_num']].get_admin_role() == 100 and victim.get_player_num() != sar['player_num']:
                                self.game.rcon_tell(sar['player_num'], "^7%s added as ^9Super Admin" % victim.get_name())
                                self.game.rcon_tell(victim.get_player_num(), "^7You are added as ^9Super Admin")
                                new_role = 90
                            else:
                                self.game.rcon_tell(sar['player_num'], "^7Sorry, you cannot put %s in group <%s>" % (victim.get_name(), right))
                            victim.update_db_admin_role(role=new_role)
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['putgroup']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['putgroup']['syntax'])

            # banlist - display the last active 10 bans
            elif sar['command'] == '!banlist' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['banlist']['level']:
                curs.execute("SELECT `id`,`name` FROM `ban_list` WHERE `expires` > '{}' ORDER BY `timestamp` DESC LIMIT 10".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
                result = curs.fetchall()
                banlist = ['^7[^9@%s^7] %s' % (row[0], row[1]) for row in result]
                msg = 'Currently no one is banned' if not banlist else str(", ".join(banlist))
                self.game.rcon_tell(sar['player_num'], "^7Banlist: %s" % msg)

            # lastbans - list the last 4 bans
            elif (sar['command'] == '!lastbans' or sar['command'] == '!bans') and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['lastbans']['level']:
                curs.execute("SELECT `id`,`name`,`expires` FROM `ban_list` ORDER BY `timestamp` DESC LIMIT 4")
                result = curs.fetchall()
                lastbanlist = ['^7[^9@%s^7] ^7%s ^7(^8%s^7)' % (row[0], row[1], row[2]) for row in result]
                if result:
                    for item in lastbanlist:
                        self.game.rcon_tell(sar['player_num'], str(item))
                else:
                    self.game.rcon_tell(sar['player_num'], "^7Currently no one is banned")

            # unban - unban a player from the database via ID
            elif sar['command'] == '!unban' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['unban']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip().lstrip('@')
                    if arg.isdigit():
                        curs.execute("SELECT `guid`,`name`,`ip_address` FROM `ban_list` WHERE `id` = {}".format(int(arg)))
                        result = curs.fetchone()
                        if result:
                            guid = result[0]
                            name = str(result[1])
                            ip_addr = str(result[2])
                            curs.execute("DELETE FROM `ban_list` WHERE `id` = {}".format(int(arg)))
                            conn.commit()
                            self.game.rcon_tell(sar['player_num'], "^7Player ^9%s ^7unbanned" % name)
                            curs.execute("DELETE FROM `ban_list` WHERE `guid` = '{}' OR ip_address = '{}'".format(guid, ip_addr))
                            conn.commit()
                            self.game.rcon_tell(sar['player_num'], "^7Try to remove duplicates of [^8%s^7]" % ip_addr)
                        else:
                            self.game.rcon_tell(sar['player_num'], "^7Invalid ID, no Player found")
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['unban']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['unban']['syntax'])

## head admin level 100 or super admin level 90
            # password - set private server password
            elif sar['command'] == '!password' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['password']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip()
                    self.game.send_rcon('g_password %s' % arg)
                    self.game.rcon_tell(sar['player_num'], "^7Password set to '%s' - Server is private" % arg)
                else:
                    self.game.send_rcon('g_password ""')
                    self.game.rcon_tell(sar['player_num'], "^7Password removed - Server is public")

            # reload
            elif sar['command'] == '!reload' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['reload']['level']:
                self.game.send_rcon('reload')

            # ungroup - remove the admin level from a player
            elif sar['command'] == '!ungroup' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['ungroup']['level']:
                if line.split(sar['command'])[1]:
                    user = line.split(sar['command'])[1].strip()
                    found, victim, msg = self.player_found(user)
                    if not found:
                        self.game.rcon_tell(sar['player_num'], msg)
                    else:
                        if (1 < victim.get_admin_role() < COMMANDS['ungroup']['level'] or self.game.players[sar['player_num']].get_admin_role() == 100) and victim.get_player_num() != sar['player_num']:
                            self.game.rcon_tell(sar['player_num'], "^8%s ^7put in group User" % victim.get_name())
                            victim.update_db_admin_role(role=1)
                        else:
                            self.game.rcon_tell(sar['player_num'], "^7Sorry, you cannot put %s in group User" % victim.get_name())
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['ungroup']['syntax'])

            # !gametype <mode> - set gametype
            elif sar['command'] == '!gametype' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['gametype']['level']:
                if line.split(sar['command'])[1]:
                    arg = line.split(sar['command'])[1].strip()
                    if arg == "ffa":
                        self.game.send_rcon('g_gametype 0')
                        self.game.rcon_say("^8FFA ^7next round")
                    elif arg == "tdm":
                        self.game.send_rcon('g_gametype 3')
                        self.game.rcon_say("^8TDM ^7next round")
                    elif arg == "ts":
                        self.game.send_rcon('g_gametype 4')
                        self.game.rcon_say("^8TS ^7next round")
                    elif arg == "ctf":
                        self.game.send_rcon('g_gametype 7')
                        self.game.rcon_say("^8CTF ^7next round")
                    elif arg == "bomb":
                        self.game.send_rcon('g_gametype 8')
                        self.game.rcon_say("^8BOMB ^7next round")
                    else:
                        self.game.rcon_tell(sar['player_num'], COMMANDS['gametype']['syntax'])
                else:
                    self.game.rcon_tell(sar['player_num'], COMMANDS['gametype']['syntax'])

            # switch to gametype
            elif sar['command'] == '!ffa' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['ffa']['level']:
                self.game.send_rcon('g_gametype 0')
                self.game.rcon_tell(sar['player_num'], "^7Game Mode: ^9Free For All")
                self.game.rcon_tell(sar['player_num'], "^7Mode changed for next map")
            elif sar['command'] == '!lms' and self.urt_modversion > 42 and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['lms']['level']:
                self.game.send_rcon('g_gametype 1')
                self.game.rcon_tell(sar['player_num'], "^7Game Mode: ^9Last Man Standing")
                self.game.rcon_tell(sar['player_num'], "^7Mode changed for next map")
            elif sar['command'] == '!tdm' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['tdm']['level']:
                self.game.send_rcon('g_gametype 3')
                self.game.rcon_tell(sar['player_num'], "^7Game Mode: ^9Team Deathmatch")
                self.game.rcon_tell(sar['player_num'], "^7Mode changed for next map")
            elif sar['command'] == '!ts' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['ts']['level']:
                self.game.send_rcon('g_gametype 4')
                self.game.rcon_tell(sar['player_num'], "^7Game Mode: ^9Team Survivor")
                self.game.rcon_tell(sar['player_num'], "^7Mode changed for next map")
            # 5: Follow The Leader
            # 6: Capture And Hold
            elif sar['command'] == '!ctf' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['ctf']['level']:
                self.game.send_rcon('g_gametype 7')
                self.game.rcon_tell(sar['player_num'], "^7Game Mode: ^9Capture the Flag")
                self.game.rcon_tell(sar['player_num'], "^7Mode changed for next map")
            elif sar['command'] == '!bomb' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['bomb']['level']:
                self.game.send_rcon('g_gametype 8')
                self.game.rcon_tell(sar['player_num'], "^7Game Mode: ^9Bomb")
                self.game.rcon_tell(sar['player_num'], "^7Mode changed for next map")
            elif sar['command'] == '!jump' and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['jump']['level']:
                self.game.send_rcon('g_gametype 9')
                self.game.rcon_tell(sar['player_num'], "^7Game Mode: ^9Jump")
                self.game.rcon_tell(sar['player_num'], "^7Mode changed for next map")
            # 10 Freeze Tag
            elif sar['command'] == '!gungame' and self.urt_modversion > 42 and self.game.players[sar['player_num']].get_admin_role() >= COMMANDS['gungame']['level']:
                self.game.send_rcon('g_gametype 11')
                self.game.rcon_tell(sar['player_num'], "^7Game Mode: ^9Gun Game")
                self.game.rcon_tell(sar['player_num'], "^7Mode changed for next map")

## iamgod
            # iamgod - register user as Head Admin
            elif sar['command'] == '!iamgod':
                if self.iamgod:
                    if not self.game.players[sar['player_num']].get_registered_user():
                        # register new user in DB and set admin role to 100
                        self.game.players[sar['player_num']].register_user_db(role=100)
                    else:
                        self.game.players[sar['player_num']].update_db_admin_role(role=100)
                    self.iamgod = False
                    self.game.rcon_tell(sar['player_num'], "^7You are registered as ^6Head Admin")

## unknown command
            elif sar['command'].startswith('!') and len(sar['command']) > 1 and self.game.players[sar['player_num']].get_admin_role() > 20:
                if sar['command'].lstrip('!') in self.superadmin_cmds:
                    self.game.rcon_tell(sar['player_num'], "^7Insufficient privileges to use command ^7%s" % sar['command'])
                else:
                    self.game.rcon_tell(sar['player_num'], "^7Unknown command ^7%s" % sar['command'])

## bad words
            elif self.bad_words_autokick and [sample for sample in bad_words if sample in line.lower()] and self.game.players[sar['player_num']].get_admin_role() < self.admin_immunity:
                victim = self.game.players[sar['player_num']]
                victim.add_warning('bad language')
                self.kick_high_warns(victim, 'bad language', 'Behave, stop using bad language')

    def kick_high_warns(self, player, reason, text):
        if player.get_warning() > 3:
            self.game.rcon_say("^9%s ^7was kicked, %s" % (player.get_name(), reason))
            self.game.kick_player(player.get_player_num(), reason=reason)
        else:
            self.game.rcon_tell(player.get_player_num(), "^8WARNING ^7[^7%d^7]: %s" % (player.get_warning(), text))
            if player.get_warning() == 3:
                self.game.rcon_say("^8ALERT: ^9%s ^7auto-kick from warnings if not cleared" % player.get_name())

    def get_admins_online(self):
        """
        return list of Admins online
        """
        liste = "%s" % ", ".join(["^7%s [^9%d^7]" % (player.get_name(), player.get_admin_role()) for player in self.game.players.itervalues() if player.get_admin_role() >= 20])
        return "^7Admins online: %s" % liste if liste else "^7No admins online"

    def get_admin_count(self):
        """
        return number of Admins online
        """
        counter = sum(1 for player in self.game.players.itervalues() if player.get_admin_role() >= 20)
        return "^7%d Admin%s online" % (counter, 's' if counter > 1 else '')

    def get_nextmap(self):
        """
        return the next map in the mapcycle
        """
        g_nextmap = self.game.get_cvar('g_nextmap')
        if not g_nextmap or "num score ping name" in g_nextmap:
            g_nextmap = self.game.get_cvar('g_nextCycleMap')
        if not g_nextmap:
            g_nextmap = self.game.get_cvar('g_nextCycleMap')

        if g_nextmap in self.game.get_all_maps():
            msg = "^7Next Map: ^7%s" % g_nextmap
            self.game.next_mapname = g_nextmap
        else:
            msg = "^7Next Map: ^7%s" % self.game.next_mapname
        return msg

    def tell_say_message(self, sar, msg):
        """
        display message in private or global chat
        """
        if sar['command'].startswith('@'):
            self.game.rcon_say(msg)
        else:
            self.game.rcon_tell(sar['player_num'], msg)

    def convert_time(self, time_string):
        """
        convert time string in duration and time unit
        """
        if time_string.endswith('d'):
            duration_string = time_string.rstrip('d')
            duration = int(duration_string) * 86400 if duration_string.isdigit() else 86400
        elif time_string.endswith('h'):
            duration_string = time_string.rstrip('h')
            duration = int(duration_string) * 3600 if duration_string.isdigit() else 3600
        elif time_string.endswith('m'):
            duration_string = time_string.rstrip('m')
            duration = int(duration_string) * 60 if duration_string.isdigit() else 60
        elif time_string.endswith('s'):
            duration_string = time_string.rstrip('s')
            duration = int(duration_string) if duration_string.isdigit() else 30
        else:
            duration = 3600
        # default ban duration = 1 hour
        if duration == 0:
            duration = 3600
        # limit to max duration = 72 hours
        elif duration > 259200:
            duration = 259200
        # modulo
        days = (duration - (duration % 86400)) / 86400
        hours = ((duration % 86400) - (duration % 3600)) / 3600
        mins = ((duration % 3600) - (duration % 60)) / 60
        secs = duration % 60
        duration_output = []
        append = duration_output.append
        if days > 0:
            append("%s day%s" % (days, 's' if days > 1 else ''))
        if hours > 0:
            append("%s hour%s" % (hours, 's' if hours > 1 else ''))
        if mins > 0:
            append("%s minute%s" % (mins, 's' if mins > 1 else ''))
        if secs > 0:
            append("%s second%s" % (secs, 's' if secs > 1 else ''))
        return duration, ' '.join(duration_output)

    def handle_flag(self, line):
        """
        handle flag
        """
        with self.players_lock:
            tmp = line.split()
            player_num = int(tmp[0])
            player = self.game.players[player_num]
            player_name = player.get_name()
            action = tmp[1]
            if action == '1:':
                player.return_flag()
                logger.debug("Player %d %s returned the flag", player_num, player_name)
            elif action == '2:':
                player.capture_flag()
                cap_count = player.get_flags_captured()
                self.game.send_rcon("^7%s has captured ^9%s ^7flag%s" % (player_name, cap_count, 's' if cap_count > 1 else ''))
                logger.debug("Player %d %s captured the flag", player_num, player_name)

    def handle_bomb(self, line):
        """
        handle bomb
        """
        with self.players_lock:
            tmp = line.split("is") if "Bombholder" in line else line.split("by")
            action = tmp[0].strip()
            player_num = int(tmp[1].rstrip('!').strip())
            name = self.game.players[player_num].get_name()
            player = self.game.players[player_num]
            if action == 'Bomb was defused':
                player.defused_bomb()
                logger.debug("Player %d %s defused the bomb", player_num, name)
                self.game.send_rcon("^7The ^9BOMB ^7has been defused by ^9%s^7!" % name)
                self.handle_teams_ts_mode('Blue')
                # kill all survived red players
                if self.kill_survived_opponents and self.urt_modversion > 41:
                    for player in self.game.players.itervalues():
                        if player.get_team() == 1 and player.get_alive():
                            self.game.send_rcon("smite %d" % player.get_player_num())
            elif action == 'Bomb was planted':
                player.planted_bomb()
                logger.debug("Player %d %s planted the bomb", player_num, name)
                self.game.send_rcon("^7The ^8BOMB ^7has been planted by ^8%s^7! ^9%s ^7seconds to detonation." % (name, self.explode_time))
                if self.spam_bomb_planted_msg:
                    self.game.rcon_bigtext("^8The ^7BOMB ^8has been planted by ^7%s^8!" % name)
                    self.game.rcon_bigtext("^7The ^8BOMB ^7has been planted by ^8%s^7!" % name)
                    self.game.rcon_bigtext("^8The ^7BOMB ^8has been planted by ^7%s^8!" % name)
                    self.game.rcon_bigtext("^7The ^8BOMB ^7has been planted by ^8%s^7!" % name)
            elif action == 'Bomb was tossed':
                player.bomb_tossed()
                for mate in self.game.players.itervalues():
                    if mate.get_team() == 1 and mate.get_alive() and mate != player:
                        self.game.rcon_tell(mate.get_player_num(), "^7The ^8BOMB ^7is loose!")
            elif action == 'Bomb has been collected':
                player.is_bombholder()
                for mate in self.game.players.itervalues():
                    if mate.get_team() == 1 and mate.get_alive() and mate != player:
                        self.game.rcon_tell(mate.get_player_num(), "^7Help ^8%s ^7to plant the ^8BOMB" % name)
            elif action == 'Bombholder':
                player.is_bombholder()

    def handle_bomb_exploded(self):
        """
        handle bomb exploded
        """
        logger.debug("Bomb exploded!")
        if self.kill_survived_opponents and self.urt_modversion > 41:
            # start Thread to kill all survived blue players
            processor = Thread(target=self.kill_blue_team_bomb_exploded)
            processor.setDaemon(True)
            processor.start()
        self.handle_teams_ts_mode('Red')

    def kill_blue_team_bomb_exploded(self):
        """
        Kill all survived blue players when the bomb exploded
        """
        self.game.rcon_say("^7Planted?")
        time.sleep(1.3)
        with self.players_lock:
            for player in self.game.players.itervalues():
                if player.get_team() == 2 and player.get_alive():
                    self.game.send_rcon("smite %d" % player.get_player_num())

    def handle_teams_ts_mode(self, line):
        """
        handle team balance in Team Survivor mode
        """
        logger.debug("SurvivorWinner: %s", line)
        self.game.send_rcon("%s%s ^7team wins" % ('^8' if line == 'Red' else '^4', line) if 'Draw' not in line else "^7Draw")
        self.autobalancer()
        if self.ts_do_team_balance:
            self.allow_cmd_teams = True
            self.handle_team_balance()
            if self.allow_cmd_teams_round_end:
                self.allow_cmd_teams = False

    def handle_team_balance(self):
        """
        balance teams if needed
        """
        with self.players_lock:
            game_data = self.game.get_gamestats()
            self.game.rcon_say("^7Red: ^8%s ^7- Blue: ^4%s ^7- Spectator: ^7%s" % (game_data[Player.teams[1]], game_data[Player.teams[2]], game_data[Player.teams[3]]))
            if (abs(game_data[Player.teams[1]] - game_data[Player.teams[2]])) > 1:
                if self.allow_cmd_teams:
                    self.game.balance_teams(game_data)
                    self.ts_do_team_balance = False
                    logger.debug("Balance teams by user request")
                else:
                    if self.ts_gametype or self.bomb_gametype or self.freeze_gametype:
                        self.ts_do_team_balance = True
                        self.game.rcon_say("^7Teams will be balanced at the end of this round!")
            else:
                self.game.rcon_say("^7Teams are already balanced")
                self.ts_do_team_balance = False

    def autobalancer(self):
        """
        auto balance teams at the end of the round if needed
        """
        if self.teams_autobalancer:
            with self.players_lock:
                game_data = self.game.get_gamestats()
                if (abs(game_data[Player.teams[1]] - game_data[Player.teams[2]])) > 1:
                    self.game.balance_teams(game_data)
                    logger.debug("Autobalancer performed team balance")
                self.ts_do_team_balance = False

    def handle_freeze(self, line):
        """
        handle freeze
        """
        with self.players_lock:
            info = line.split(":", 1)[0].split()
            player_num = int(info[0])
            self.game.players[player_num].freeze()

    def handle_thawout(self, line):
        """
        handle thaw out
        """
        with self.players_lock:
            info = line.split(":", 1)[0].split()
            player_num = int(info[0])
            self.game.players[player_num].thawout()

    def handle_awards(self):
        """
        display awards and personal stats at the end of the round
        """
        most_kills = 0
        most_flags = 0
        most_streak = 0
        most_hs = 0
        most_frozen = 0
        most_thawouts = 0
        most_defused = 0
        most_planted = 0
        most_he_kills = 0
        most_knife_kills = 0
        fastest_cap = 999
        most_flag_returns = 0
        flagrunner = ""
        serialkiller = ""
        streaker = ""
        freezer = ""
        thawouter = ""
        headshooter = ""
        defused_by = ""
        planted_by = ""
        nader = ""
        knifer = ""
        fastrunner = ""
        defender = ""
        msg = []
        append = msg.append
        with self.players_lock:
            for player in self.game.players.itervalues():
                player_num = player.get_player_num()
                if player_num == BOT_PLAYER_NUM:
                    continue
                player_name = player.get_name()
                player_kills = player.get_kills()
                player_headshots = player.get_headshots()
                if player.get_flags_captured() > most_flags:
                    most_flags = player.get_flags_captured()
                    flagrunner = player_name
                if player_kills > most_kills:
                    most_kills = player_kills
                    serialkiller = player_name
                if player.get_max_kill_streak() > most_streak:
                    most_streak = player.get_max_kill_streak()
                    streaker = player_name
                if player_headshots > most_hs:
                    most_hs = player_headshots
                    headshooter = player_name
                if player.get_freeze() > most_frozen:
                    most_frozen = player.get_freeze()
                    freezer = player_name
                if player.get_thawout() > most_thawouts:
                    most_thawouts = player.get_thawout()
                    thawouter = player_name
                if player.get_defused_bomb() > most_defused:
                    most_defused = player.get_defused_bomb()
                    defused_by = player_name
                if player.get_planted_bomb() > most_planted:
                    most_planted = player.get_planted_bomb()
                    planted_by = player_name
                if player.get_he_kills() > most_he_kills:
                    most_he_kills = player.get_he_kills()
                    nader = player_name
                if player.get_knife_kills() > most_knife_kills:
                    most_knife_kills = player.get_knife_kills()
                    knifer = player_name
                if 0 < player.get_flag_capture_time() < fastest_cap:
                    fastest_cap = player.get_flag_capture_time()
                    fastrunner = player_name
                if player.get_flags_returned() > most_flag_returns:
                    most_flag_returns = player.get_flags_returned()
                    defender = player_name

                # display personal stats at the end of the round, stats for players in spec will not be displayed
                if player.get_team() != 3:
                    if self.freeze_gametype:
                        self.game.rcon_tell(player_num, "^7Stats %s: ^7F ^9%d ^7T ^7%d ^7HS ^8%d ^7TK ^8%d" % (player_name, player.get_freeze(), player.get_thawout(), player.get_headshots(), player.get_team_kill_count()))
                    else:
                        self.game.rcon_tell(player_num, "^7Stats %s: ^7K ^9%d ^7D ^7%d ^7HS ^8%d ^7TK ^8%d" % (player_name, player_kills, player.get_deaths(), player_headshots, player.get_team_kill_count()))

            # get Awards
            if most_flags > 1:
                append("^7%s: ^9%d ^4caps" % (flagrunner, most_flags))
            if most_planted > 1:
                append("^7%s: ^9%d ^5planted" % (planted_by, most_planted))
            if most_defused > 1:
                append("^7%s: ^9%d ^4defused" % (defused_by, most_defused))
            if most_frozen > 1:
                append("^7%s: ^9%d ^7freezes" % (freezer, most_frozen))
            if most_thawouts > 1:
                append("^7%s: ^9%d ^4thaws" % (thawouter, most_thawouts))
            if most_kills > 1:
                append("^7%s: ^9%d ^7kills" % (serialkiller, most_kills))
            if most_streak > 1:
                append("^7%s: ^9%d ^6streaks" % (streaker, most_streak))
            if most_hs > 1:
                append("^7%s: ^9%d ^8heads" % (headshooter, most_hs))

            # Bomb statistics
            if most_planted > 1 or most_defused > 1:
                self.game.rcon_say("^9Top Objectives: ^7%s [^8%s^7]" % ((planted_by, most_planted) if most_planted > most_defused else (defused_by, most_defused)))

            # CTF statistics
            if most_flags > 1:
                self.game.rcon_say("^9Top Objectives: ^7%s [^8%s^7]" % (flagrunner, most_flags))

            # HE grenade kills
            if most_he_kills > 1:
                self.game.rcon_say("^9Most HE grenade kills: ^7%s (^8%d ^7HE kills)" % (nader, most_he_kills))

            if most_knife_kills > 1:
                self.game.rcon_say("^9Most knife kills: ^7%s (^8%d ^7kills)" % (knifer, most_knife_kills))

            # CTF statistics
            if fastest_cap < 999:
                self.game.rcon_say("^9Fastest cap: ^7%s (^8%s ^7sec)" % (fastrunner, fastest_cap))
            if most_flag_returns > 1:
                self.game.rcon_say("^9Best defender: ^7%s (^8%d ^7flag returns)" % (defender, most_flag_returns))

            # display Awards
            if msg:
                self.game.rcon_say("^8AWARDS: %s" % " ^7- ".join(msg))


### CLASS Player ###
class Player(object):
    """
    Player class
    """
    teams = {0: "green", 1: "red", 2: "blue", 3: "spectator"}
    roles = {0: "Guest", 1: "User", 2: "Regular", 20: "Jumper", 40: "Admin", 60: "Full Admin", 80: "Senior Admin", 90: "Super Admin", 100: "Head Admin"}

    def __init__(self, player_num, ip_address, guid, name, auth=''):
        """
        create a new instance of Player
        """
        self.player_num = player_num
        self.guid = guid
        self.name = ""
        self.authname = auth
        self.player_id = 0
        self.aliases = []
        self.registered_user = False
        self.num_played = 0
        self.last_visit = 0
        self.admin_role = 0
        self.first_seen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        self.kills = 0
        self.froze = 0
        self.thawouts = 0
        self.db_kills = 0
        self.killing_streak = 0
        self.losing_streak = 0
        self.max_kill_streak = 0
        self.db_killing_streak = 0
        self.deaths = 0
        self.db_deaths = 0
        self.db_suicide = 0
        self.head_shots = 0
        self.db_head_shots = 0
        self.hitzone = {'body': 0, 'arms': 0, 'legs': 0}
        self.all_hits = 0
        self.he_kills = 0
        self.knife_kills = 0
        self.tk_count = 0
        self.db_tk_count = 0
        self.db_team_death = 0
        self.tk_victim_names = []
        self.tk_killer_names = []
        self.grudged_player = []
        self.ping_value = 0
        self.warn_list = []
        self.last_warn_time = 0
        self.flags_captured = 0
        self.flags_returned = 0
        self.flag_capture_time = 999
        self.bombholder = False
        self.bomb_carrier_killed = 0
        self.killed_with_bomb = 0
        self.bomb_planted = 0
        self.bomb_defused = 0
        self.address = ip_address
        self.team = 3
        self.team_lock = None
        self.time_joined = time.time()
        self.welcome_msg = True
        self.first_time = False
        self.country = None
        self.ban_id = 0
        self.ban_msg = ''
        self.alive = False
        self.respawn_time = 0
        self.monsterkill = {'time': 999, 'kills': 0}

        # set player name
        self.set_name(name)

        # GeoIP lookup
        info = GEOIP.lookup(ip_address)
        if info.country:
            self.country = "%s (%s)" % (info.country_name, info.country)

        # check ban_list
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.time_joined))
        curs.execute("SELECT `id`,`reason` FROM `ban_list` WHERE `guid` = '{}' AND `expires` > '{}'".format(self.guid, now))
        result = curs.fetchone()
        if result:
            self.ban_id = result[0]
            self.ban_msg = str(result[1]).split(',')[0]
        else:
            curs.execute("SELECT `id`,`reason` FROM `ban_list` WHERE `ip_address` = '{}' AND `expires` > '{}'".format(self.address, now))
            result = curs.fetchone()
            if result:
                self.ban_id = result[0]
                self.ban_msg = str(result[1]).split(',')[0]

    def ban(self, duration=900, reason='tk', admin=None):
        if admin:
            reason = "%s, ban by %s" % (reason, admin)
        try:
            expire_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + duration))
        except ValueError:
            expire_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(2147483647))
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        curs.execute("SELECT `expires` FROM `ban_list` WHERE `guid` = '{}'".format(self.guid))
        result = curs.fetchone()
        if result:
            if result[0] < expire_date:
                # update already existing ban
                curs.execute("UPDATE `ban_list` SET `ip_address` = '{}',`expires` = '{}',`reason` = '{}' WHERE `guid` = '{}'".format(self.address, expire_date, reason, self.guid))
                conn.commit()
                return True
            # update IP address of existing ban
            curs.execute("UPDATE `ban_list` SET `ip_address` = '{}' WHERE `guid` = '{}'".format(self.address, self.guid))
            conn.commit()
            return False
        # create new ban
        curs.execute('INSERT INTO `ban_list` (`id`,`guid`,`name`,`ip_address`,`expires`,`timestamp`,`reason`) VALUES ({},"{}","{}","{}","{}","{}","{}")'.format(self.player_id, self.guid, self.name, self.address, expire_date, timestamp, reason))
        conn.commit()
        return True

    def add_ban_point(self, point_type, duration):
        try:
            expire_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + duration))
        except ValueError:
            expire_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(2147483647))
        # add ban_point to database
        curs.execute("INSERT INTO `ban_points` (`guid`,`point_type`,`expires`) VALUES ('{}','{}','{}')".format(self.guid, point_type, expire_date))
        conn.commit()
        # check amount of ban_points
        curs.execute("SELECT COUNT(*) FROM `ban_points` WHERE `guid` = '{}' AND `expires` > '{}'".format(self.guid, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        # ban player when he gets more than 2 ban_points
        if int(curs.fetchone()[0]) > 2:
            # ban duration = 3 * expiration time
            ban_duration = duration * 3
            self.ban(duration=ban_duration, reason=point_type, admin='bot')
            return ban_duration / 60
        return 0

    def reset(self, reset_headshot_hits=True, reset_kill_spree=True):
        self.kills = 0
        self.froze = 0
        self.thawouts = 0
        if reset_kill_spree:
            self.killing_streak = 0
            self.max_kill_streak = 0
            self.losing_streak = 0
        self.deaths = 0
        if reset_headshot_hits:
            self.head_shots = 0
        self.hitzone = {'body': 0, 'arms': 0, 'legs': 0}
        self.all_hits = 0
        self.he_kills = 0
        self.knife_kills = 0
        self.tk_count = 0
        self.tk_victim_names = []
        self.tk_killer_names = []
        self.grudged_player = []
        self.warn_list = []
        self.last_warn_time = 0
        self.flags_captured = 0
        self.flags_returned = 0
        self.flag_capture_time = 999
        self.bombholder = False
        self.bomb_carrier_killed = 0
        self.killed_with_bomb = 0
        self.bomb_planted = 0
        self.bomb_defused = 0
        self.team_lock = None
        self.alive = False
        self.respawn_time = 0
        self.monsterkill = {'time': 999, 'kills': 0}

    def reset_flag_stats(self):
        self.flags_captured = 0
        self.flags_returned = 0
        self.flag_capture_time = 999

    def save_info(self):
        if self.registered_user:
            ratio = round(float(self.db_kills) / float(self.db_deaths), 2) if self.db_deaths > 0 else 1.0
            curs.execute("UPDATE `xlrstats` SET `kills` = {},`deaths` = {},`headshots` = {},`team_kills` = {},`team_death` = {},`max_kill_streak` = {},`suicides` = {},`rounds` = `rounds` + 1,`ratio` = {} WHERE `guid` = '{}'".format(self.db_kills, self.db_deaths, self.db_head_shots, self.db_tk_count, self.db_team_death, self.db_killing_streak, self.db_suicide, ratio, self.guid))
            conn.commit()

    def check_database(self):
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        # check player table
        curs.execute("SELECT COUNT(*) FROM `player` WHERE `guid` = '{}'".format(self.guid))
        if int(curs.fetchone()[0]) == 0:
            # add new player to database
            curs.execute('INSERT INTO `player` (`guid`,`name`,`ip_address`,`time_joined`,`aliases`) VALUES ("{}","{}","{}","{}","{}")'.format(self.guid, self.name, self.address, now, self.name))
            conn.commit()
            self.aliases.append(self.name)
            self.first_time = True
        else:
            # update name, IP address and last join date
            curs.execute('UPDATE `player` SET `name` = "{}",`ip_address` = "{}",`time_joined` = "{}" WHERE `guid` = "{}"'.format(self.name, self.address, now, self.guid))
            conn.commit()
            # get known aliases
            curs.execute('SELECT `aliases` FROM `player` WHERE `guid` = "{}"'.format(self.guid))
            result = curs.fetchone()
            # create list of aliases
            self.aliases = result[0].split(", ")
            # add new alias to list
            if self.name not in self.aliases and len(self.aliases) < 15:
                self.aliases.append(self.name)
                alias_string = ', '.join(self.aliases)
                curs.execute('UPDATE `player` SET `aliases` = "{}" WHERE `guid` = "{}"'.format(alias_string, self.guid))
                conn.commit()
        # get player-id
        curs.execute("SELECT `id` FROM `player` WHERE `guid` = '{}'".format(self.guid))
        self.player_id = curs.fetchone()[0]
        # check XLRSTATS table
        curs.execute("SELECT COUNT(*) FROM `xlrstats` WHERE `guid` = '{}'".format(self.guid))
        if int(curs.fetchone()[0]) == 0:
            self.registered_user = False
        else:
            self.registered_user = True
            # get DB DATA for XLRSTATS
            curs.execute("SELECT `last_played`,`num_played`,`kills`,`deaths`,`headshots`,`team_kills`,`team_death`,`max_kill_streak`,`suicides`,`admin_role`,`first_seen` FROM `xlrstats` WHERE `guid` = '{}'".format(self.guid))
            result = curs.fetchone()
            self.last_visit = result[0]
            self.num_played = result[1]
            self.db_kills = result[2]
            self.db_deaths = result[3]
            self.db_head_shots = result[4]
            self.db_tk_count = result[5]
            self.db_team_death = result[6]
            self.db_killing_streak = result[7]
            self.db_suicide = result[8]
            self.admin_role = result[9]
            self.first_seen = result[10]
            # update name, last_played and increase num_played counter
            curs.execute('UPDATE `xlrstats` SET `name` = "{}",`last_played` = "{}",`num_played` = `num_played` + 1 WHERE `guid` = "{}"'.format(self.name, now, self.guid))
            conn.commit()

    def define_offline_player(self, player_id):
        self.player_id = player_id
        # get known aliases
        curs.execute("SELECT `aliases` FROM `player` WHERE `guid` = '{}'".format(self.guid))
        result = curs.fetchone()
        # create list of aliases
        self.aliases = result[0].split(", ")
        curs.execute("SELECT COUNT(*) FROM `xlrstats` WHERE `guid` = '{}'".format(self.guid))
        if int(curs.fetchone()[0]) == 0:
            self.admin_role = 0
            self.registered_user = False
        else:
            curs.execute("SELECT `last_played`,`admin_role` FROM `xlrstats` WHERE `guid` = '{}'".format(self.guid))
            result = curs.fetchone()
            self.last_visit = result[0]
            self.admin_role = result[1]
            self.registered_user = True

    def register_user_db(self, role=1):
        if not self.registered_user:
            now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            curs.execute('INSERT INTO `xlrstats` (`guid`,`name`,`ip_address`,`first_seen`,`last_played`,`num_played`,`admin_role`) VALUES ("{}","{}","{}","{}","{}",1,{})'.format(self.guid, self.name, self.address, now, now, role))
            conn.commit()
            self.registered_user = True
            self.admin_role = role
            self.welcome_msg = False
            self.first_seen = now
            self.last_visit = now

    def update_db_admin_role(self, role):
        curs.execute("UPDATE `xlrstats` SET `admin_role` = {} WHERE `guid` = '{}'".format(role, self.guid))
        conn.commit()
        # overwrite admin role in game, no reconnect of player required
        self.set_admin_role(role)

    def get_ban_id(self):
        return self.ban_id

    def get_ban_msg(self):
        return REASONS[self.ban_msg] if self.ban_msg in REASONS else self.ban_msg

    def get_first_time(self):
        return self.first_time

    def set_name(self, name):
        # remove whitespaces
        self.name = name.replace(" ", "")
        # remove color character
        for item in xrange(10):
            self.name = self.name.replace("^%d" % item, "")
        # limit length of name to 20 character
        self.name = self.name[:20]

    def get_name(self):
        return self.name

    def set_authname(self, authname):
        self.authname = authname

    def get_authname(self):
        return self.authname

    def get_aliases(self):
        if len(self.aliases) == 15:
            self.aliases.append("and more...")
        return str(", ^7".join(self.aliases))

    def set_guid(self, guid):
        self.guid = guid

    def get_guid(self):
        return self.guid

    def get_player_num(self):
        return self.player_num

    def get_player_id(self):
        return self.player_id

    def set_team(self, team):
        self.team = team

    def get_team(self):
        return self.team

    def get_team_lock(self):
        return self.team_lock

    def set_team_lock(self, team):
        self.team_lock = team

    def get_num_played(self):
        return self.num_played

    def get_last_visit(self):
        return str(self.last_visit)

    def get_first_seen_date(self):
        return str(self.first_seen)

    def get_db_kills(self):
        return self.db_kills

    def get_kills(self):
        return self.kills

    def get_db_deaths(self):
        return self.db_deaths

    def get_deaths(self):
        return self.deaths

    def get_db_headshots(self):
        return self.db_head_shots

    def get_headshots(self):
        return self.head_shots

    def disable_welcome_msg(self):
        self.welcome_msg = False

    def get_welcome_msg(self):
        return self.welcome_msg

    def get_country(self):
        return self.country

    def get_registered_user(self):
        return self.registered_user

    def set_admin_role(self, role):
        self.admin_role = role

    def get_admin_role(self):
        return self.admin_role

    def get_ip_address(self):
        return self.address

    def get_time_joined(self):
        return self.time_joined

    def get_max_kill_streak(self):
        return self.max_kill_streak

    def kill(self):
        now = time.time()
        self.killing_streak += 1
        self.losing_streak = 0
        self.kills += 1
        self.db_kills += 1
        if now - self.monsterkill['time'] < 5:
            self.monsterkill['kills'] += 1
        else:
            self.monsterkill['time'] = int(now)
            self.monsterkill['kills'] = 1

    def die(self):
        if self.killing_streak > self.max_kill_streak:
            self.max_kill_streak = self.killing_streak
        if self.max_kill_streak > self.db_killing_streak:
            self.db_killing_streak = self.max_kill_streak
        self.losing_streak += 1
        self.killing_streak = 0
        self.deaths += 1
        self.db_deaths += 1
        self.monsterkill = {'time': 999, 'kills': 0}

    def get_losing_streak(self):
        return self.losing_streak

    def get_monsterkill(self):
        return self.monsterkill['kills']

    def set_alive(self, status):
        self.alive = status
        if status:
            self.respawn_time = time.time()

    def get_alive(self):
        return self.alive

    def get_respawn_time(self):
        return self.respawn_time

    def suicide(self):
        self.db_suicide += 1

    def headshot(self):
        self.head_shots += 1
        self.db_head_shots += 1

    def set_hitzones(self, part):
        self.hitzone[part] += 1

    def get_hitzones(self, part):
        return self.hitzone[part]

    def set_all_hits(self):
        self.all_hits += 1

    def get_all_hits(self):
        return self.all_hits

    def set_he_kill(self):
        self.he_kills += 1

    def get_he_kills(self):
        return self.he_kills

    def set_knife_kill(self):
        self.knife_kills += 1

    def get_knife_kills(self):
        return self.knife_kills

    def get_killing_streak(self):
        return self.killing_streak

    def get_db_tks(self):
        return self.db_tk_count

    def get_team_kill_count(self):
        return self.tk_count

    def add_killed_me(self, killer):
        self.tk_killer_names.append(killer)

    def get_killed_me(self):
        return self.tk_killer_names

    def clear_killed_me(self, victim):
        while self.tk_victim_names.count(victim) > 0:
            self.warn_list.remove("stop team killing")
            self.tk_victim_names.remove(victim)

    def add_tk_victims(self, victim):
        self.tk_victim_names.append(victim)

    def get_tk_victim_names(self):
        return self.tk_victim_names

    def set_grudge(self, killer):
        self.grudged_player.append(killer)
        self.clear_tk(killer)

    def get_grudged_player(self):
        return self.grudged_player

    def clear_grudged_player(self, killer):
        while self.grudged_player.count(killer) > 0:
            self.grudged_player.remove(killer)

    def clear_tk(self, killer):
        while self.tk_killer_names.count(killer) > 0:
            self.tk_killer_names.remove(killer)

    def clear_all_tk(self):
        self.tk_killer_names = []

    def clear_all_killed_me(self):
        self.tk_victim_names = []
        self.clear_specific_warning("stop team killing")

    def add_high_ping(self, value):
        self.warn_list.append('fix your ping')
        self.ping_value = value

    def get_ping_value(self):
        return self.ping_value

    def clear_specific_warning(self, warning):
        while self.warn_list.count(warning) > 0:
            self.warn_list.remove(warning)

    def add_warning(self, warning, timer=True):
        self.warn_list.append(warning)
        if timer:
            self.last_warn_time = time.time()

    def get_warning(self):
        return len(self.warn_list)

    def get_all_warn_msg(self):
        return list(set(self.warn_list))

    def get_last_warn_msg(self):
        return self.warn_list[-1] if self.warn_list else ''

    def get_last_warn_time(self):
        return self.last_warn_time

    def clear_last_warning(self):
        if self.warn_list:
            last_warning = self.warn_list[-1]
            self.warn_list.pop()
            self.last_warn_time = self.last_warn_time - 60 if self.warn_list else 0
            if "stop team killing" in last_warning:
                self.tk_victim_names.pop()
            return last_warning
        return None

    def clear_warning(self):
        self.warn_list = []
        self.tk_victim_names = []
        self.tk_killer_names = []
        self.last_warn_time = 0
        # clear ban_points
        curs.execute("DELETE FROM `ban_points` WHERE `guid` = '{}' and `expires` > '{}'".format(self.guid, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
        conn.commit()

    def team_death(self):
        # increase team death counter
        self.db_team_death += 1

    def team_kill(self):
        # increase teamkill counter
        self.tk_count += 1
        self.db_tk_count += 1

# CTF Mode
    def capture_flag(self):
        self.flags_captured += 1

    def get_flags_captured(self):
        return self.flags_captured

    def return_flag(self):
        self.flags_returned += 1

    def get_flags_returned(self):
        return self.flags_returned

    def set_flag_capture_time(self, cap_time):
        if cap_time < self.flag_capture_time:
            self.flag_capture_time = cap_time

    def get_flag_capture_time(self):
        if self.flag_capture_time == 999:
            return 0
        return self.flag_capture_time

# Bomb Mode
    def is_bombholder(self):
        self.bombholder = True

    def bomb_tossed(self):
        self.bombholder = False

    def get_bombholder(self):
        return self.bombholder

    def kill_bomb_carrier(self):
        self.bomb_carrier_killed += 1

    def get_bomb_carrier_kills(self):
        return self.bomb_carrier_killed

    def kills_with_bomb(self):
        self.killed_with_bomb += 1

    def get_kills_with_bomb(self):
        return self.killed_with_bomb

    def planted_bomb(self):
        self.bomb_planted += 1
        self.bombholder = False

    def get_planted_bomb(self):
        return self.bomb_planted

    def defused_bomb(self):
        self.bomb_defused += 1

    def get_defused_bomb(self):
        return self.bomb_defused

# Freeze Tag
    def freeze(self):
        self.froze += 1

    def get_freeze(self):
        return self.froze

    def thawout(self):
        self.thawouts += 1

    def get_thawout(self):
        return self.thawouts


### CLASS Game ###
class Game(object):
    """
    Game class
    """
    def __init__(self, urt_modversion):
        """
        create a new instance of Game
        """
        self.all_maps_list = []
        self.next_mapname = ''
        self.mapname = ''
        self.maplist = []
        self.last_maps_list = []
        self.players = {}
        self.live = False
        self.urt_modversion = urt_modversion
        self.quake = PyQuake3("%s:%s" % (CONFIG.get('server', 'server_ip'), CONFIG.get('server', 'server_port')), CONFIG.get('server', 'rcon_password'))
        self.queue = Queue()
        self.rcon_lock = RLock()
        self.thread_rcon()
        logger.info("Opening RCON socket   : OK")

        # dynamic mapcycle
        self.dynamic_mapcycle = CONFIG.getboolean('mapcycle', 'dynamic_mapcycle') if CONFIG.has_option('mapcycle', 'dynamic_mapcycle') else False
        if self.dynamic_mapcycle:
            self.switch_count = CONFIG.getint('mapcycle', 'switch_count') if CONFIG.has_option('mapcycle', 'switch_count') else 4
            self.big_cycle = filter(None, CONFIG.get('mapcycle', 'big_cycle').replace(' ', '').split(',')) if CONFIG.has_option('mapcycle', 'big_cycle') else []
            self.small_cycle = filter(None, CONFIG.get('mapcycle', 'small_cycle').replace(' ', '').split(',')) if CONFIG.has_option('mapcycle', 'small_cycle') else []

        # add Spunky Bot as player 'World' to the game
        spunky_bot = Player(BOT_PLAYER_NUM, '127.0.0.1', 'NONE', 'World')
        self.add_player(spunky_bot)
        logger.info("Activating the Bot    : OK")
        logger.info("Startup completed     : Let's get ready to rumble!")
        logger.info("Spunky Bot is running until you are closing this session or pressing CTRL + C to abort this process.")
        logger.info("*** Note: Use the provided initscript to run Spunky Bot as daemon ***")

    def thread_rcon(self):
        """
        Thread process for starting method rcon_process
        """
        # start Thread
        processor = Thread(target=self.rcon_process)
        processor.setDaemon(True)
        processor.start()

    def rcon_process(self):
        """
        Thread process
        """
        while 1:
            try:
                if not self.queue.empty() and self.live:
                    with self.rcon_lock:
                        command = self.queue.get_nowait()  # Non-bloquant
                        if command and command != 'status':
                            try:
                                self.quake.rcon(command)
                                time.sleep(RCON_DELAY)  # Pause entre les commandes
                            except Exception as err:
                                logger.error("RCON error: %s", err)
                        elif command == 'status':
                            try:
                                self.quake.rcon_update()
                            except Exception:
                                pass
                else:
                    time.sleep(RCON_DELAY)  # Éviter d'épuiser le CPU
            except Exception as err:
                logger.error("Thread error: %s", err)
                time.sleep(RCON_DELAY)

    def get_quake_value(self, value):
        """
        get Quake3 value

        @param value: The Quake3 value
        @type  value: String
        """
        if self.live:
            with self.rcon_lock:
                self.quake.update()
                return self.quake.values[value]
        return ''

    def get_rcon_output(self, value):
        """
        get RCON output for value

        @param value: The RCON output for value
        @type  value: String
        """
        if self.live:
            with self.rcon_lock:
                return self.quake.rcon(value)
        return ''

    def get_cvar(self, value):
        """
        get CVAR value

        @param value: The CVAR value
        @type  value: String
        """
        if self.live:
            with self.rcon_lock:
                try:
                    ret_val = self.quake.rcon(value)[1].split(':', 1)[1].split('^7')[0].lstrip('"')
                except IndexError:
                    ret_val = None
                time.sleep(RCON_DELAY)
                return ret_val
        return ''

    def get_number_players(self):
        """
        get the number of online players
        """
        return len(self.players) - 1  # bot is counted as player

    def get_mapcycle_path(self):
        """
        get the full path of mapcycle.txt file
        """
        maplist = []
        #self.get_cvar('')
        # get path of fs_homepath and fs_basepath
        fs_homepath = self.get_cvar('fs_homepath')
        if not fs_homepath:
            fs_homepath = self.get_cvar('fs_homepath')
        logger.debug("fs_homepath           : %s", fs_homepath)
        fs_basepath = self.get_cvar('fs_basepath')
        logger.debug("fs_basepath           : %s", fs_basepath)
        fs_game = self.get_cvar('fs_game')
        # get file name of mapcycle.txt
        mapcycle_file = self.get_cvar('g_mapcycle')
        try:
            # set full path of mapcycle.txt
            mc_home_path = os.path.join(fs_homepath, fs_game, mapcycle_file) if fs_homepath else ""
            mc_base_path = os.path.join(fs_basepath, fs_game, mapcycle_file) if fs_basepath else ""
        except TypeError:
            raise Exception('Server did not respond to mapcycle path request, please restart the Bot')
        mapcycle_path = mc_home_path if os.path.isfile(mc_home_path) else mc_base_path if os.path.isfile(mc_base_path) else None
        if mapcycle_path:
            logger.info("Mapcycle path         : %s", mapcycle_path)
            with open(mapcycle_path, 'r') as file_handle:
                lines = [line for line in file_handle if line != '\n']
            try:
                while 1:
                    tmp = lines.pop(0).strip()
                    if tmp[0] == '{':
                        while tmp[0] != '}':
                            tmp = lines.pop(0).strip()
                        tmp = lines.pop(0).strip()
                    maplist.append(tmp)
            except IndexError:
                pass
        return maplist

    def send_rcon(self, command):
        """
        send RCON command

        @param command: The RCON command
        @type  command: String
        """
        if self.live:
            with self.rcon_lock:
                self.queue.put(command)

    def rcon_say(self, msg):
        """
        display message in global chat

        @param msg: The message to display in global chat
        @type  msg: String
        """
        # wrap long messages into shorter list elements
        lines = textwrap.wrap(msg, 140)
        for line in lines:
            self.send_rcon('say %s' % line)

    def rcon_tell(self, player_num, msg, pm_tag=True):
        """
        tell message to a specific player

        @param player_num: The player number
        @type  player_num: Integer
        @param msg: The message to display in private chat
        @type  msg: String
        @param pm_tag: Display '[pm]' (private message) in front of the message
        @type  pm_tag: bool
        """
        lines = textwrap.wrap(msg, 128)
        prefix = "^9[pm] "
        for line in lines:
            if pm_tag:
                self.send_rcon('tell %d %s%s' % (player_num, prefix, line))
                prefix = ""
            else:
                self.send_rcon('tell %d %s' % (player_num, line))

    def rcon_bigtext(self, msg):
        """
        display bigtext message

        @param msg: The message to display in global chat
        @type  msg: String
        """
        self.send_rcon('bigtext "%s"' % msg)

    def rcon_forceteam(self, player_num, team):
        """
        force player to given team

        @param player_num: The player number
        @type  player_num: Integer
        @param team: The team (red, blue, spectator)
        @type  team: String
        """
        self.send_rcon('forceteam %d %s' % (player_num, team))

    def rcon_clear(self):
        """
        clear RCON queue
        """
        self.queue.queue.clear()

    def kick_player(self, player_num, reason=''):
        """
        kick player

        @param player_num: The player number
        @type  player_num: Integer
        @param reason: Reason for kick
        @type  reason: String
        """
        if reason and self.urt_modversion > 41:
            self.send_rcon('kick %d "%s"' % (player_num, reason))
        else:
            self.send_rcon('kick %d' % player_num)
        logger.debug("%s kicked%s%s", player_num, ": " if reason else '', reason)

    def set_all_maps(self):
        """
        Set a list of all available maps based strictly on mapcycle.txt.
        """
        try:
            all_maps_list = []
            logger.debug("Attempting to load maps from mapcycle.txt...")
            # Read maps specified in mapcycle.txt
            mapcycle = CONFIG.get('server', 'mapcycle')
            with open(mapcycle, "r") as mapcycle_file:
                for line in mapcycle_file:
                    map_name = line.strip()  # Remove unnecessary spaces
                    if map_name and not map_name.startswith("#"):  # Ignore empty lines and comments
                        all_maps_list.append(map_name.lower())
                        logger.debug("Map added from mapcycle.txt: %s", map_name)
            
            # Remove duplicates and sort maps
            self.all_maps_list = sorted(set(all_maps_list))
            

        except Exception as err:
            logger.error("Error loading maps from mapcycle.txt: %s", err, exc_info=True)
            self.all_maps_list = []  # In case of error, empty the list.

    def set_current_map(self):
        """
        set the current and next map in rotation
        """
            
        if self.mapname:
            self.last_maps_list = [self.mapname]  # Update to keep only the last map
        try:
            self.mapname = self.get_quake_value('mapname')
        except KeyError:
            self.mapname = self.next_mapname

        if self.dynamic_mapcycle:
            self.maplist = filter(None, (self.small_cycle if self.get_number_players() < self.switch_count else self.big_cycle))
            logger.debug("Players online: %s / Mapcycle: %s", self.get_number_players(), self.maplist)
            self.send_rcon("g_mapcycle dynamic.fake")
        else:
            if self.get_cvar('g_mapcycle') == "dynamic.fake":
                self.send_rcon("g_mapcycle mapcycle.txt")

        random_map = self.get_all_maps()        
        
        if self.maplist:
            if self.mapname in self.maplist:
                if self.maplist.index(self.mapname) < (len(self.maplist) - 1):
                    self.next_mapname = self.maplist[self.maplist.index(self.mapname) + 1]
                else:
                    self.next_mapname = (random.choice(random_map))
            else:
                self.next_mapname = (random.choice(random_map))
        else:
            self.next_mapname = self.mapname

        if (self.mapname == self.next_mapname):
            if self.mapname in self.maplist:
                if self.maplist.index(self.mapname) < (len(self.maplist) - 1):
                    self.next_mapname = self.maplist[self.maplist.index(self.mapname) + 1]
                else:
                    self.next_mapname = (random.choice(random_map))
            else:
                self.next_mapname = (random.choice(random_map))
        else:
            self.next_mapname = self.mapname
        
        logger.debug("Current map: %s / Next map: %s", self.mapname, self.next_mapname)

        if self.dynamic_mapcycle:
            self.send_rcon('g_nextmap %s' % self.next_mapname)
            self.send_rcon('g_nextCycleMap %s' % self.next_mapname)
            if self.mapname != self.next_mapname:
                self.rcon_say("^7Next Map: ^7%s" % self.next_mapname)
    
    def get_all_maps(self):
        """
        Get the list of maps defined in mapcycle.txt.
        """
        logger.debug("Returning all maps list: %s", self.all_maps_list)
        return self.all_maps_list

    def go_live(self):
        """
        go live
        """
        self.live = True
        self.set_all_maps()
        self.maplist = filter(None, self.get_mapcycle_path())
        self.set_current_map()
        self.rcon_say("^7Powered by ^7[Spunky Bot %s] ^8[www.spunkybot.de]" % __version__)
        logger.info("*** Live tracking: Current map: %s / Next map: %s ***", self.mapname, self.next_mapname)
        logger.info("Total number of maps  : %s", len(self.get_all_maps()))
        logger.info("Server CVAR g_logsync : %s", self.get_cvar('g_logsync'))
        logger.info("Server CVAR g_loghits : %s", self.get_cvar('g_loghits'))

        if self.get_cvar('g_logsync') == '0':
            logger.error("Server CVAR 'g_logsync' is set to '0' but must be '1' to support interaction with the bot")

    def get_last_maps(self):
        """
        get a list of the last played maps
        """
        return self.last_maps_list

    def add_player(self, player):
        """
        add a player to the game

        @param player: The instance of the player
        @type  player: Instance
        """
        self.players[player.get_player_num()] = player
        # check DB for real players and exclude bots which have IP 0.0.0.0
        if player.get_ip_address() != '0.0.0.0':
            player.check_database()

    def get_gamestats(self):
        """
        get number of players in red team, blue team and spectator
        """
        game_data = {Player.teams[1]: 0, Player.teams[2]: 0, Player.teams[3]: -1}
        for player in self.players.itervalues():
            game_data[Player.teams[player.get_team()]] += 1
        return game_data

    def balance_teams(self, game_data):
        """
        balance teams if needed

        @param game_data: Dictionary of players in each team
        @type  game_data: dict
        """
        if (game_data[Player.teams[1]] - game_data[Player.teams[2]]) > 1:
            team1 = 1
            team2 = 2
        elif (game_data[Player.teams[2]] - game_data[Player.teams[1]]) > 1:
            team1 = 2
            team2 = 1
        else:
            self.rcon_say("^7Teams are already balanced")
            return
        self.rcon_bigtext("AUTOBALANCING TEAMS...")
        num_ptm = math.floor((game_data[Player.teams[team1]] - game_data[Player.teams[team2]]) / 2)
        player_list = [player for player in self.players.itervalues() if player.get_team() == team1 and not player.get_team_lock()]
        player_list.sort(cmp=lambda player1, player2: cmp(player2.get_time_joined(), player1.get_time_joined()))
        for player in player_list[:int(num_ptm)]:
            self.rcon_forceteam(player.get_player_num(), Player.teams[team2])
        self.rcon_say("^7Autobalance complete!")


### Main ###
if __name__ == "__main__":
    # get full path of spunky.py
    HOME = os.path.dirname(os.path.realpath(__file__))

    # load the GEO database and store it globally in interpreter memory
    GEOIP = pygeoip.Database(os.path.join(HOME, 'lib', 'GeoIP.dat'))

    # connect to database
    conn = sqlite3.connect(os.path.join(HOME, 'data.sqlite'))
    curs = conn.cursor()
    CONFIG = ConfigParser.ConfigParser()
    CONF_PATH = os.path.join(HOME, 'conf', 'settings.conf')
    CONFIG.read(CONF_PATH)

    # enable/disable debug output
    verbose = CONFIG.getboolean('bot', 'verbose') if CONFIG.has_option('bot', 'verbose') else False
    # logging format
    formatter = logging.Formatter('[%(asctime)s] %(levelname)-8s %(message)s', datefmt='%d.%m.%Y %H:%M:%S')
    # console logging
    console = logging.StreamHandler()
    if not verbose:
        console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    # devel.log file
    devel_log = logging.handlers.RotatingFileHandler(filename=os.path.join(HOME, 'devel.log'), maxBytes=2097152, backupCount=1, encoding='utf8')
    devel_log.setLevel(logging.INFO)
    devel_log.setFormatter(formatter)
    # add logging handler
    logger.addHandler(console)
    logger.addHandler(devel_log)

    logger.info("*** Spunky Bot v%s : www.spunkybot.de ***", __version__)
    logger.info("Loading config file   : %s", CONF_PATH)
    # create tables if not exists
    curs.execute('CREATE TABLE IF NOT EXISTS xlrstats (id INTEGER PRIMARY KEY NOT NULL, guid TEXT NOT NULL, name TEXT NOT NULL, ip_address TEXT NOT NULL, first_seen DATETIME, last_played DATETIME, num_played INTEGER DEFAULT 1, kills INTEGER DEFAULT 0, deaths INTEGER DEFAULT 0, headshots INTEGER DEFAULT 0, team_kills INTEGER DEFAULT 0, team_death INTEGER DEFAULT 0, max_kill_streak INTEGER DEFAULT 0, suicides INTEGER DEFAULT 0, ratio REAL DEFAULT 0, rounds INTEGER DEFAULT 0, admin_role INTEGER DEFAULT 1)')
    curs.execute('CREATE TABLE IF NOT EXISTS player (id INTEGER PRIMARY KEY NOT NULL, guid TEXT NOT NULL, name TEXT NOT NULL, ip_address TEXT NOT NULL, time_joined DATETIME, aliases TEXT)')
    curs.execute('CREATE TABLE IF NOT EXISTS ban_list (id INTEGER PRIMARY KEY NOT NULL, guid TEXT NOT NULL, name TEXT, ip_address TEXT, expires DATETIME DEFAULT 259200, timestamp DATETIME, reason TEXT)')
    curs.execute('CREATE TABLE IF NOT EXISTS ban_points (id INTEGER PRIMARY KEY NOT NULL, guid TEXT NOT NULL, point_type TEXT, expires DATETIME)')

    # create instance of LogParser
    LogParser()

    # close database connection
    conn.close()
