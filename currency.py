# currency.py
import discord
from discord.ext import commands
from discord import app_commands
import requests
import json

class CurrencyConverter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.crypto_list = {
            'btc': 'bitcoin',
            'eth': 'ethereum',
            'ltc': 'litecoin',
            'xrp': 'ripple',
            'doge': 'dogecoin',
            'ada': 'cardano',
            'sol': 'solana',
            'matic': 'polygon'
        }
        self.fiat_list = ['usd', 'eur', 'gbp', 'jpy', 'cad', 'mxn', 'brl', 'ars', 'clp', 'cop', 'pen']

    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """Gets the exchange rate between two currencies"""
        from_currency = from_currency.lower()
        to_currency = to_currency.lower()

        # Crypto to crypto conversion
        if from_currency in self.crypto_list and to_currency in self.crypto_list:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={self.crypto_list[from_currency]}&vs_currencies={to_currency}"
            response = requests.get(url)
            data = response.json()
            return data[self.crypto_list[from_currency]][to_currency]

        # Crypto to fiat conversion
        elif from_currency in self.crypto_list and to_currency in self.fiat_list:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={self.crypto_list[from_currency]}&vs_currencies={to_currency}"
            response = requests.get(url)
            data = response.json()
            return data[self.crypto_list[from_currency]][to_currency]

        # Fiat to crypto conversion
        elif from_currency in self.fiat_list and to_currency in self.crypto_list:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={self.crypto_list[to_currency]}&vs_currencies={from_currency}"
            response = requests.get(url)
            data = response.json()
            return 1 / data[self.crypto_list[to_currency]][from_currency]

        # Fiat to fiat conversion (using a different API)
        elif from_currency in self.fiat_list and to_currency in self.fiat_list:
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            response = requests.get(url)
            data = response.json()
            return data['rates'][to_currency.upper()]

        else:
            raise ValueError("Unsupported currency pair")

    @app_commands.command(name="convert", description="Convert between currencies and cryptocurrencies")
    @app_commands.describe(
        amount="Amount to convert",
        from_currency="Source currency (e.g. USD, EUR, BTC, LTC, MXN)",
        to_currency="Target currency (e.g. USD, EUR, BTC, LTC, MXN)"
    )
    async def convert(self, interaction: discord.Interaction, amount: float, from_currency: str, to_currency: str):
        """Converts an amount from one currency to another"""
        await interaction.response.defer(ephemeral=False)
        
        try:
            rate = await self.get_exchange_rate(from_currency, to_currency)
            converted_amount = amount * rate
            
            embed = discord.Embed(
                title="💰 Currency Conversion",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="Result",
                value=f"{amount:.2f} {from_currency.upper()} = {converted_amount:.6f} {to_currency.upper()}",
                inline=False
            )
            embed.add_field(
                name="Exchange Rate",
                value=f"1 {from_currency.upper()} = {rate:.6f} {to_currency.upper()}",
                inline=False
            )
            
            # Add currency names for better UX
            currency_names = {
                'mxn': 'Mexican Peso',
                'usd': 'US Dollar',
                'eur': 'Euro',
                'btc': 'Bitcoin',
                'ltc': 'Litecoin'
                # Add more as needed
            }
            
            from_name = currency_names.get(from_currency.lower(), from_currency.upper())
            to_name = currency_names.get(to_currency.lower(), to_currency.upper())
            embed.set_footer(text=f"Exchange rates may vary • {from_name} → {to_name}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Conversion error: {str(e)}\n\nSupported currencies:\n"
                f"Crypto: {', '.join(self.crypto_list.keys())}\n"
                f"Fiat: {', '.join(self.fiat_list)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(CurrencyConverter(bot))