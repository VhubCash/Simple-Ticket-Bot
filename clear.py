# clear.py
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear", description="Delete a specific number of messages")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = 1):
        """Clear a specified number of messages from the channel"""
        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "Please specify a number between 1 and 100.",
                ephemeral=True
            )
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "This command can only be used in text channels.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        
        confirmation = await interaction.followup.send(
            f"Successfully deleted {len(deleted)} message(s).",
            ephemeral=True
        )
        
        await asyncio.sleep(5)
        await confirmation.delete()

async def setup(bot):
    await bot.add_cog(Clear(bot))