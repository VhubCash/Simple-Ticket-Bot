# referral_system.py
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
from typing import Dict, List, Optional, Tuple

class ReferralSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {guild_id: {invite_code: {"uses": int, "inviter_id": int}}}
        self.invite_cache = {}
        # {user_id: invite_count}
        self.user_invites = {}
        # {(guild_id, invite_code): user_id} - Para trackear invitaciones del bot
        self.bot_invites = {}
        # List of role IDs that can use referral commands
        self.allowed_role_ids = []
        # Welcome/leave settings {guild_id: {"channel_id": int, "welcome_msg": str, "leave_msg": str}}
        self.welcome_settings = {}
        self.load_data()
        
        # Initialize cache on startup
        self.bot.loop.create_task(self.initialize_invite_cache())

    async def initialize_invite_cache(self):
        """Initialize invite cache for all guilds"""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                self.invite_cache[guild.id] = {
                    invite.code: {
                        "uses": invite.uses,
                        "inviter_id": invite.inviter.id if invite.inviter else None
                    } 
                    for invite in invites
                }
            except Exception as e:
                print(f"Couldn't fetch invites for {guild.name}: {e}")
                continue

    def load_data(self):
        """Load saved data from file"""
        if os.path.exists('referral_data.json'):
            with open('referral_data.json', 'r') as f:
                data = json.load(f)
                self.user_invites = data.get('invites', {})
                self.allowed_role_ids = data.get('allowed_role_ids', [])
                self.welcome_settings = data.get('welcome_settings', {})
                # Cargar datos de invitaciones del bot
                bot_invites_data = data.get('bot_invites', {})
                self.bot_invites = {
                    (int(guild_id), invite_code): user_id 
                    for (guild_id, invite_code), user_id in bot_invites_data.items()
                }

    def save_data(self):
        """Save data to file"""
        with open('referral_data.json', 'w') as f:
            # Convertir tuplas a strings para ser serializables
            bot_invites_serializable = {
                f"{guild_id},{invite_code}": user_id 
                for (guild_id, invite_code), user_id in self.bot_invites.items()
            }
            json.dump({
                'invites': self.user_invites,
                'allowed_role_ids': self.allowed_role_ids,
                'welcome_settings': self.welcome_settings,
                'bot_invites': bot_invites_serializable
            }, f, indent=4)

    async def has_permission(self, user: discord.Member) -> bool:
        """Check if user has permission to use referral commands"""
        if user.guild_permissions.administrator:
            return True
        return any(role.id in self.allowed_role_ids for role in user.roles)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Track invite usage when new members join"""
        await asyncio.sleep(5)  # Wait for Discord to update invite counts
        
        try:
            guild_id = member.guild.id
            current_invites = await member.guild.invites()
            
            # Find the used invite by comparing with cache
            used_invite = None
            for invite in current_invites:
                cached_invite = self.invite_cache.get(guild_id, {}).get(invite.code, {})
                
                # Check if uses increased
                if invite.uses > cached_invite.get("uses", 0):
                    used_invite = invite
                    break
            
            if used_invite:
                # Check if this is a bot-generated invite
                if used_invite.inviter and used_invite.inviter.id == self.bot.user.id:
                    referrer_id = self.bot_invites.get((guild_id, used_invite.code))
                else:
                    referrer_id = str(used_invite.inviter.id) if used_invite.inviter and not used_invite.inviter.bot else None
                
                if referrer_id:
                    # Update count
                    self.user_invites[referrer_id] = self.user_invites.get(referrer_id, 0) + 1
                    self.save_data()
                    
                    # Notify referrer if not a bot invite
                    if not (used_invite.inviter and used_invite.inviter.id == self.bot.user.id):
                        try:
                            referrer = await member.guild.fetch_member(int(referrer_id))
                            embed = discord.Embed(
                                title="🎉 New Referral!",
                                description=f"{member.display_name} joined using your invite link!",
                                color=discord.Color.green()
                            )
                            embed.add_field(
                                name="Your Total Invites",
                                value=f"`{self.user_invites[referrer_id]}`",
                                inline=True
                            )
                            embed.set_thumbnail(url=member.display_avatar.url)
                            await referrer.send(embed=embed)
                        except Exception as e:
                            print(f"Couldn't notify referrer: {e}")
            
            # Update cache
            self.invite_cache[guild_id] = {
                invite.code: {
                    "uses": invite.uses,
                    "inviter_id": invite.inviter.id if invite.inviter else None
                }
                for invite in current_invites
            }
            
            # Send welcome message if configured
            await self.send_welcome_message(member)
            
        except Exception as e:
            print(f"Error tracking invite: {e}")

    async def send_welcome_message(self, member: discord.Member):
        """Helper function to send welcome message"""
        if member.guild.id in self.welcome_settings:
            settings = self.welcome_settings[member.guild.id]
            channel = member.guild.get_channel(settings.get('channel_id'))
            if channel and settings.get('welcome_msg'):
                welcome_msg = settings['welcome_msg'].replace("{user}", member.mention)
                
                embed = discord.Embed(
                    title=f"👋 Welcome to {member.guild.name}!",
                    description=welcome_msg,
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(
                    name="Member Count",
                    value=f"`{member.guild.member_count}`",
                    inline=True
                )
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Send leave message if configured"""
        if member.guild.id in self.welcome_settings:
            settings = self.welcome_settings[member.guild.id]
            channel = member.guild.get_channel(settings.get('channel_id'))
            if channel and settings.get('leave_msg'):
                leave_msg = settings['leave_msg'].replace("{user}", member.display_name)
                
                embed = discord.Embed(
                    title="😢 Goodbye!",
                    description=leave_msg,
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"We now have {member.guild.member_count} members")
                
                await channel.send(embed=embed)

    @app_commands.command(name="set_referral_role", description="[ADMIN] Set which role can use referral commands")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="The role that can use referral commands")
    async def set_referral_role(self, interaction: discord.Interaction, role: discord.Role):
        """Set the referral role"""
        if role.id not in self.allowed_role_ids:
            self.allowed_role_ids = [role.id]  # Replace existing roles
            self.save_data()
        
        embed = discord.Embed(
            title="✅ Referral Role Set",
            description=f"Only users with {role.mention} can now use referral commands.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup_welcome", description="[ADMIN] Configure welcome/leave messages")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Channel for welcome/leave messages",
        welcome_message="Welcome message (use {user} for mention)",
        leave_message="Leave message (use {user} for name)"
    )
    async def setup_welcome(self, interaction: discord.Interaction, 
                          channel: discord.TextChannel,
                          welcome_message: str,
                          leave_message: str):
        """Configure welcome and leave messages"""
        guild_id = interaction.guild_id
        self.welcome_settings[guild_id] = {
            "channel_id": channel.id,
            "welcome_msg": welcome_message,
            "leave_msg": leave_message
        }
        self.save_data()
        
        embed = discord.Embed(
            title="✅ Welcome Messages Configured",
            description=f"Welcome/leave messages will now be sent in {channel.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="Welcome Message", value=welcome_message, inline=False)
        embed.add_field(name="Leave Message", value=leave_message, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="my_invites", description="Check your invite statistics")
    async def my_invites(self, interaction: discord.Interaction):
        """Show user's invite stats"""
        if not await self.has_permission(interaction.user):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        user_id = str(interaction.user.id)
        count = self.user_invites.get(user_id, 0)
        
        # Create a progress bar-like visualization
        progress = "🟩" * min(count, 10) + "⬜" * max(0, 10 - count)
        if count > 10:
            progress += f" +{count-10}"
        
        embed = discord.Embed(
            title="📊 Your Invite Statistics",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Total Invites",
            value=f"```\n{count} members joined\n{progress}\n```",
            inline=False
        )
        
        # Add rank if in top 10
        sorted_invites = sorted(self.user_invites.items(), key=lambda x: x[1], reverse=True)
        user_ids = [uid for uid, _ in sorted_invites]
        if user_id in user_ids:
            rank = user_ids.index(user_id) + 1
            embed.add_field(
                name="Server Rank",
                value=f"🏆 #{rank}",
                inline=True
            )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="get_invite", description="Get your personal invite link")
    async def get_invite(self, interaction: discord.Interaction):
        """Generate unique invite link"""
        if not await self.has_permission(interaction.user):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            # Create temporary invite
            invite = await interaction.channel.create_invite(
                max_uses=1,
                max_age=86400,  # 24 hours
                unique=True,
                reason=f"Personal invite for {interaction.user.name}"
            )
            
            # Track this bot-generated invite
            self.bot_invites[(interaction.guild.id, invite.code)] = str(interaction.user.id)
            self.save_data()
            
            # Update our cache
            invites = await interaction.guild.invites()
            self.invite_cache[interaction.guild.id] = {
                i.code: {
                    "uses": i.uses,
                    "inviter_id": i.inviter.id if i.inviter else None
                }
                for i in invites
            }
            
            embed = discord.Embed(
                title="🔗 Your Personal Invite Link",
                description=f"Use this link to invite friends to **{interaction.guild.name}**:",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Invite Link",
                value=f"```\n{invite.url}\n```",
                inline=False
            )
            embed.add_field(
                name="Expires After",
                value="1 use or 24 hours",
                inline=True
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Share this link with friends to grow our community!")
            
            try:
                await interaction.user.send(embed=embed)
                success_embed = discord.Embed(
                    title="📩 Invite Sent",
                    description="Check your DMs for your personal invite link!",
                    color=discord.Color.green()
                )
                await interaction.response.send_message(embed=success_embed, ephemeral=True)
            except:
                error_embed = discord.Embed(
                    title="❌ Couldn't DM You",
                    description="Please enable DMs from server members to receive your invite link.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
                
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error Creating Invite",
                description=str(e),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


    @app_commands.command(name="invite_stats", description="[ADMIN] View all invite statistics")
    @app_commands.checks.has_permissions(administrator=True)
    async def invite_stats(self, interaction: discord.Interaction):
        """Show all invite statistics"""
        if not self.user_invites:
            embed = discord.Embed(
                title="📊 Invite Statistics",
                description="No invite data available yet.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        sorted_invites = sorted(self.user_invites.items(), key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(
            title="🏆 Invite Leaderboard",
            description="Top referrers in this server",
            color=discord.Color.gold()
        )
        
        # Add medal emojis for top 3
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (user_id, count) in enumerate(sorted_invites[:10], 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                name = user.display_name
                avatar = user.display_avatar.url
            except:
                name = f"Unknown User ({user_id})"
                avatar = None
                
            rank = medals[i-1] if i <= 3 else f"#{i}"
            
            embed.add_field(
                name=f"{rank} {name}",
                value=f"**{count}** invite{'s' if count != 1 else ''}",
                inline=False
            )
            
            if avatar and i <= 3:  # Only set image for top 3
                embed.set_thumbnail(url=avatar)
        
        total_invites = sum(self.user_invites.values())
        embed.set_footer(text=f"Total server invites: {total_invites}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ReferralSystem(bot))