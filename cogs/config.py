import disnake
from disnake.ext import commands

from utilities.database import is_admin, config_reset

class Config(commands.Cog, name="Admin Config"):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Reset server to default config.")
    async def config_reset(self, inter):
        if is_admin(inter.author, inter.guild):
            await inter.response.send_message(config_reset(inter.guild))

