# math_operations.py
import discord
from discord.ext import commands
from discord import app_commands

class MathOperations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="calculate", description="Perform basic math operations")
    @app_commands.describe(
        expression="Mathematical expression (e.g. 5+3, 10*2, 8/4)"
    )
    async def calculate(self, interaction: discord.Interaction, expression: str):
        """Calculate basic math expressions"""
        try:
            # Validate the expression for security
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Only numbers and basic operators (+, -, *, /) are allowed")
            
            result = eval(expression)
            
            embed = discord.Embed(
                title="🧮 Calculation Result",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Expression",
                value=f"`{expression}`",
                inline=False
            )
            embed.add_field(
                name="Result",
                value=f"`{result}`",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except ZeroDivisionError:
            await interaction.response.send_message(
                "❌ Error: Division by zero is not allowed",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error calculating expression: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="percentage", description="Calculate percentages")
    @app_commands.describe(
        value="The base value",
        percent="The percentage to calculate"
    )
    async def percentage(self, interaction: discord.Interaction, value: float, percent: float):
        """Calculate a percentage of a value"""
        try:
            result = (value * percent) / 100
            embed = discord.Embed(
                title="📊 Percentage Calculation",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Calculation",
                value=f"{percent}% of {value}",
                inline=False
            )
            embed.add_field(
                name="Result",
                value=f"{result}",
                inline=False
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error calculating percentage: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="discount", description="Calculate discounted price")
    @app_commands.describe(
        original_price="Original price",
        discount_percent="Discount percentage"
    )
    async def discount(self, interaction: discord.Interaction, original_price: float, discount_percent: float):
        """Calculate a discounted price"""
        try:
            discount_amount = (original_price * discount_percent) / 100
            final_price = original_price - discount_amount
            
            embed = discord.Embed(
                title="💰 Discount Calculation",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="Original Price",
                value=f"{original_price}",
                inline=True
            )
            embed.add_field(
                name="Discount",
                value=f"{discount_percent}%",
                inline=True
            )
            embed.add_field(
                name="You Save",
                value=f"{discount_amount}",
                inline=False
            )
            embed.add_field(
                name="Final Price",
                value=f"{final_price}",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error calculating discount: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(MathOperations(bot))