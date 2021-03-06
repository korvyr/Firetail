from discord.ext import commands
import aiohttp
import json
import urllib
import re

from firetail.utils import make_embed
from firetail.core import checks


class GroupLookup:
    """This extension handles looking up corps and alliance."""

    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.logger = bot.logger

    @commands.command(name='group', aliases=["corp", "alliance"])
    @checks.spam_check()
    @checks.is_whitelist()
    async def _group(self, ctx):
        """Shows corp and alliance information.
        Do '!group name'"""
        global alliance_name, most_active_system, corp_description, most_active_system, corp_description, most_active_system
        if len(ctx.message.content.split()) == 1:
            dest = ctx.author if ctx.bot.config.dm_only else ctx
            return await dest.send('**ERROR:** Use **!help group** for more info.')
        group_name = ctx.message.content.split(' ', 1)[1]
        self.logger.info('GroupLookup - {} requested group info for the group {}'.format(str(ctx.message.author),
                                                                                         group_name))
        corp_data = None
        alliance_data = None
        corp_id = None
        alliance_id = None
        corp = 'corporation'
        corp_ids = await ctx.bot.esi_data.esi_search(group_name, corp)
        if corp_ids is not None and 'corporation' in corp_ids:
            if len(corp_ids['corporation']) > 1:
                for corporation_id in corp_ids['corporation']:
                    group_data = await ctx.bot.esi_data.corporation_info(corporation_id)
                    if group_data['name'].lower().strip() == group_name.lower().strip():
                        corp_id = corporation_id
                        corp_data = await ctx.bot.esi_data.corporation_info(corp_id)
                        break
            elif len(corp_ids['corporation']) == 1:
                corp_id = corp_ids['corporation'][0]
                corp_data = await ctx.bot.esi_data.corporation_info(corp_id)
        alliance = 'alliance'
        alliance_ids = await ctx.bot.esi_data.esi_search(group_name, alliance)
        if alliance_ids is not None and 'alliance' in alliance_ids:
            if len(alliance_ids['alliance']) > 1:
                for ally_id in alliance_ids['alliance']:
                    group_data = await ctx.bot.esi_data.alliance_info(ally_id)
                    if group_data['name'].lower().strip() == group_name.lower().strip():
                        alliance_id = ally_id
                        alliance_data = await ctx.bot.esi_data.alliance_info(alliance_id)
                        break
            elif len(alliance_ids['alliance']) == 1:
                alliance_id = alliance_ids['alliance'][0]
                alliance_data = await ctx.bot.esi_data.alliance_info(alliance_id)
        # Check if a corp and alliance were both found
        if corp_data is not None and alliance_data is not None:
            if corp_data['name'].lower().strip() == group_name.lower().strip():
                alliance_data = None
            elif alliance_data['name'].lower().strip() == group_name.lower().strip():
                corp_data = None
            else:
                dest = ctx.author if ctx.bot.config.dm_only else ctx
                self.logger.info('GroupLookup ERROR - {} could not be found'.format(group_name))
                return await dest.send('**ERROR:** Multiple Groups Found With Names Similiar To {}'.format(group_name))
        if corp_data is not None:
            group = 'corporation'
            group_id = corp_id
            group_data = corp_data
            zkill_stats = await self.zkill_stats(group_id, 'corporationID')
            raw_corp_description = group_data['description']
            new_lines = re.sub('<br\s*?>', '\n', raw_corp_description)
            tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
            corp_description = tag_re.sub('', new_lines)
            try:
                alliance_id = group_data['alliance_id']
                alliance_info = await ctx.bot.esi_data.alliance_info(alliance_id)
                alliance_name = alliance_info['name']
                alliance = True
            except Exception:
                alliance = False
            zkill_link = 'https://zkillboard.com/corporation/{}/'.format(group_id)
            eve_who = 'https://evewho.com/corp/{}'.format(urllib.parse.quote(group_name))
            dotlan = 'http://evemaps.dotlan.net/corporation/{}'.format(urllib.parse.quote(group_name))
            logo = 'https://imageserver.eveonline.com/Corporation/{}_64.png'.format(group_id)
        elif alliance_data is not None:
            group = 'alliance'
            group_id = alliance_id
            group_data = alliance_data
            zkill_stats = await self.zkill_stats(group_id, 'allianceID')
            zkill_link = 'https://zkillboard.com/alliance/{}/'.format(group_id)
            eve_who = 'https://evewho.com/alli/{}'.format(urllib.parse.quote(group_name))
            dotlan = 'http://evemaps.dotlan.net/alliance/{}'.format(urllib.parse.quote(group_name))
            logo = 'https://imageserver.eveonline.com/Alliance/{}_64.png'.format(group_id)
        else:
            dest = ctx.author if ctx.bot.config.dm_only else ctx
            self.logger.info('GroupLookup ERROR - {} could not be found'.format(group_name))
            return await dest.send('**ERROR:** No Group Found With The Name {}'.format(group_name))
        if zkill_stats:
            total_kills = '{0:}'.format(zkill_stats['allTimeSum'])
            danger_ratio = zkill_stats['dangerRatio']
            gang_ratio = zkill_stats['gangRatio']
            solo_kills = '{0:}'.format(zkill_stats['soloKills'])
            if zkill_stats['hasSupers']:
                try:
                    super_count = len(zkill_stats['supers']['supercarriers']['data'])
                except Exception:
                    super_count = 'N/A'
                try:
                    titan_count = len(zkill_stats['supers']['titans']['data'])
                except Exception:
                    titan_count = 'N/A'
            else:
                super_count = 'N/A'
                titan_count = 'N/A'
            for top in zkill_stats['topLists']:
                try:
                    if top['type'] == 'solarSystem':
                        most_active_system = top['values'][0]['solarSystemName']
                except Exception:
                    most_active_system = 'N/A'
        else:
            total_kills = 'N/A'
            danger_ratio = 'N/A'
            gang_ratio = 'N/A'
            solo_kills = 'N/A'
            super_count = 'N/A'
            titan_count = 'N/A'
            most_active_system = 'N/A'

        embed = make_embed(guild=ctx.guild,
                           title=group_name,
                           content='[ZKill]({}) / [EveWho]({}) / [Dotlan]({})'.format(zkill_link, eve_who, dotlan))
        embed.set_footer(icon_url=ctx.bot.user.avatar_url,
                         text="Provided Via Firetail Bot")
        embed.set_thumbnail(
            url=logo)
        if group == 'corporation' and alliance:
            embed.add_field(name="General Info", value='Name:\nTicker:\nMember Count:\nAlliance:',
                            inline=True)
            embed.add_field(name="-",
                            value='{}\n{}\n{}\n{}'.format(group_data['name'], group_data['ticker'],
                                                          group_data['member_count'], alliance_name),
                            inline=True)
            embed.add_field(name="PVP Info", value='Threat Rating:\nGang Ratio:\nSolo Kills:\nTotal Kills:'
                                                   '\nKnown Super Count:\nKnown Titan Count:\nMost Active System:',
                            inline=True)
            embed.add_field(name="-",
                            value='{}%\n{}%\n{}\n{}\n{}\n{}\n{}'.format(danger_ratio, gang_ratio, solo_kills,
                                                                        total_kills, super_count, titan_count,
                                                                        most_active_system),
                            inline=True)
            embed.add_field(name="Description", value=corp_description[:1023])
        elif group == 'corporation' and not alliance:
            embed.add_field(name="General Info", value='Name:\nTicker:\nMember Count:',
                            inline=True)
            embed.add_field(name="-",
                            value='{}\n{}\n{}'.format(group_data['name'], group_data['ticker'],
                                                      group_data['member_count']),
                            inline=True)
            embed.add_field(name="PVP Info", value='Threat Rating:\nGang Ratio:\nSolo Kills:\nTotal Kills:'
                                                   '\nKnown Super Count:\nKnown Titan Count:\nMost Active System:',
                            inline=True)
            embed.add_field(name="-",
                            value='{}%\n{}%\n{}\n{}\n{}\n{}\n{}'.format(danger_ratio, gang_ratio, solo_kills,
                                                                        total_kills, super_count, titan_count,
                                                                        most_active_system),
                            inline=True)
            embed.add_field(name="Description", value=corp_description[:1023])
        elif group == 'alliance':
            embed.add_field(name="General Info", value='Name:\nTicker:',
                            inline=True)
            embed.add_field(name="-",
                            value='{}\n{}'.format(group_data['name'], group_data['ticker']),
                            inline=True)
            embed.add_field(name="PVP Info", value='Threat Rating:\nGang Ratio:\nSolo Kills:\nTotal Kills:\nKnown '
                                                   'Super Count:\nKnown Titan Count:\nMost Active System:',
                            inline=True)
            embed.add_field(name="-",
                            value='{}%\n{}%\n{}\n{}\n{}\n{}\n{}'.format(danger_ratio, gang_ratio, solo_kills,
                                                                        total_kills, super_count, titan_count,
                                                                        most_active_system),
                            inline=True)
        dest = ctx.author if ctx.bot.config.dm_only else ctx
        await dest.send(embed=embed)
        if ctx.bot.config.delete_commands:
            await ctx.message.delete()

    async def zkill_stats(self, group_id, group_type):
        async with aiohttp.ClientSession() as session:
            url = 'https://zkillboard.com/api/stats/{}/{}/'.format(group_type, group_id)
            async with session.get(url) as resp:
                data = await resp.text()
                data = json.loads(data)
                try:
                    all_time_kills = data['allTimeSum']
                    return data
                except Exception:
                    return None
