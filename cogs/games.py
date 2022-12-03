from random import choice

from disnake.ext import commands


class MagicEightball(commands.Cog, name="Magic Eight Ball"):
    def __init__(self, bot):
        self.bot = bot
        self.EIGHTBALL = [
            # Yes
            'It is certain.',
            'It is decidedly so.',
            'Without a doubt.',
            'Yes -- definitely.',
            'You may rely on it.',
            'As I see it, yes.',
            'Most likely.',
            'Outlook good.',
            'Yes.',
            'Signs point to yes.',
            # Maybe
            'Reply hazy, try again.',
            'Ask again later.',
            'Better not tell you now.',
            'Cannot predict now.',
            'Concentrate and ask again.',
            # No
            'Don\'t count on it.',
            'My reply is no.',
            'My sources say no.',
            'Outlook not so good',
            'Very doubtful.'
        ]

    @commands.slash_command(description="Predict the future with 'magic'.")
    async def eightball(self, inter, question: str):
        await inter.response.send_message(f"*\"{question}\"*\r{choice(self.EIGHTBALL)}")