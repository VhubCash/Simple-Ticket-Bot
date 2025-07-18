# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import os
from dotenv import load_dotenv
import io
from discord.ext import tasks
import random

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

PANEL_EMBED_CONFIG = {
    "title": "Support Tickets",
    "description": "Click the button below to create a new support ticket.",
    "color": discord.Color.blue().value,
    "footer": "Our team will respond as soon as possible.",
    "thumbnail": None,
    "image": None
}

# Configuración
TICKET_CATEGORY_NAME = "🎫 TICKETS"
SUPPORT_ROLE_NAME = "⚙️ Support Team"
LOG_CHANNEL_NAME = "📜 ticket-logs"
TRANSCRIPT_CHANNEL_NAME = "📁 ticket-transcripts"

status_options = [
    discord.Game("PRIVATE BOT 🔐"),
    discord.Streaming(name="Made by Nexus ✨", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    discord.Activity(type=discord.ActivityType.listening, name="🎶🎶🎶"),
    discord.Activity(type=discord.ActivityType.watching, name="👁‍🗨👁‍🗨👁‍🗨"),
    discord.Activity(type=discord.ActivityType.competing, name="⚔⚔🤺")
]

@tasks.loop(seconds=5)
async def change_status():
    activity = random.choice(status_options)
    await bot.change_presence(activity=activity, status=discord.Status.online)

# Ticket types (now using a function to get defaults)
def get_default_ticket_types():
    return {
        "general": {
            "name": "General Support",
            "emoji": "❓",
            "color": discord.Color.blue().value,
            "description": "For general questions and support"
        },
        "technical": {
            "name": "Technical Support",
            "emoji": "🔧",
            "color": discord.Color.green().value,
            "description": "For technical issues and bugs"
        },
        "billing": {
            "name": "Billing/Payments",
            "emoji": "💳",
            "color": discord.Color.gold().value,
            "description": "For payment-related questions"
        },
        "report": {
            "name": "Report User",
            "emoji": "⚠️",
            "color": discord.Color.red().value,
            "description": "To report a user or content"
        }
    }

TICKET_TYPES = get_default_ticket_types().copy()


# Global variables
support_role = None
log_channel = None
transcript_channel = None
class PanelCustomizationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.button(label="Change Title", style=discord.ButtonStyle.primary)
    async def change_title(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PanelTextModal("title", "Edit Title", PANEL_EMBED_CONFIG["title"])
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Change Description", style=discord.ButtonStyle.primary)
    async def change_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PanelTextModal("description", "Edit Description", PANEL_EMBED_CONFIG["description"])
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Change Color", style=discord.ButtonStyle.primary)
    async def change_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PanelTextModal("color", "Edit Color (hex)", f"#{hex(PANEL_EMBED_CONFIG['color'])[2:].upper()}")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Change Footer", style=discord.ButtonStyle.primary)
    async def change_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PanelTextModal("footer", "Edit Footer", PANEL_EMBED_CONFIG["footer"])
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Add Thumbnail", style=discord.ButtonStyle.secondary)
    async def add_thumbnail(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PanelImageModal("thumbnail")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Add Image", style=discord.ButtonStyle.secondary)
    async def add_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PanelImageModal("image")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Preview Panel", style=discord.ButtonStyle.success)
    async def preview_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_panel_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Finish", style=discord.ButtonStyle.danger)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "✅ Panel configuration saved. Use /create_panel to publish it.",
            ephemeral=True
        )
        self.stop()

class PanelTextModal(discord.ui.Modal):
    def __init__(self, field: str, title: str, current_value: str):
        super().__init__(title=title)
        self.field = field
        
        self.text_input = discord.ui.TextInput(
            label=f"New value for {field}",
            default=current_value,
            style=discord.TextStyle.paragraph if field == "description" else discord.TextStyle.short,
            required=True
        )
        self.add_item(self.text_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        global PANEL_EMBED_CONFIG
        
        if self.field == "color":
            color_value = self.text_input.value.strip()
            try:
                if color_value.startswith("#"):
                    color_value = color_value[1:]
                PANEL_EMBED_CONFIG["color"] = int(color_value, 16)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid color format. Use hex code (e.g., FF0000 for red).",
                    ephemeral=True
                )
                return
        else:
            PANEL_EMBED_CONFIG[self.field] = self.text_input.value
        
        await interaction.response.send_message(
            f"✅ {self.title} updated successfully!",
            ephemeral=True
        )

class PanelImageModal(discord.ui.Modal):
    def __init__(self, field: str):
        super().__init__(title=f"Add {field}")
        self.field = field
        
        self.image_url = discord.ui.TextInput(
            label="Image URL",
            placeholder="https://example.com/image.jpg",
            required=True
        )
        self.add_item(self.image_url)
    
    async def on_submit(self, interaction: discord.Interaction):
        global PANEL_EMBED_CONFIG
        
        if not self.image_url.value.startswith(("http://", "https://")):
            await interaction.response.send_message(
                "❌ Invalid URL. Must start with http:// or https://",
                ephemeral=True
            )
            return
        
        PANEL_EMBED_CONFIG[self.field] = self.image_url.value
        await interaction.response.send_message(
            f"✅ {self.field.capitalize()} added successfully!",
            ephemeral=True
        )

def create_panel_embed():
    embed = discord.Embed(
        title=PANEL_EMBED_CONFIG["title"],
        description=PANEL_EMBED_CONFIG["description"],
        color=discord.Color(PANEL_EMBED_CONFIG["color"])
    )
    
    if PANEL_EMBED_CONFIG["footer"]:
        embed.set_footer(text=PANEL_EMBED_CONFIG["footer"])
    
    if PANEL_EMBED_CONFIG["thumbnail"]:
        embed.set_thumbnail(url=PANEL_EMBED_CONFIG["thumbnail"])
    
    if PANEL_EMBED_CONFIG["image"]:
        embed.set_image(url=PANEL_EMBED_CONFIG["image"])
    
    return embed

class TicketSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TicketTypeModal()
        await interaction.response.send_modal(modal)

class TicketTypeModal(discord.ui.Modal, title="Create New Ticket"):
    issue = discord.ui.TextInput(
        label="Briefly describe your issue",
        style=discord.TextStyle.paragraph,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        view = discord.ui.View(timeout=180)
        for ticket_type in TICKET_TYPES:
            btn = TicketTypeButton(ticket_type, self.issue.value)
            view.add_item(btn)
        
        await interaction.response.send_message(
            "Please select the type of ticket you need:",
            view=view,
            ephemeral=True
        )

class TicketTypeButton(discord.ui.Button):
    def __init__(self, ticket_type: str, issue: str):
        super().__init__(
            label=TICKET_TYPES[ticket_type]["name"],
            emoji=TICKET_TYPES[ticket_type]["emoji"],
            style=discord.ButtonStyle.secondary
        )
        self.ticket_type = ticket_type
        self.issue = issue
    
    async def callback(self, interaction: discord.Interaction):
        await create_ticket_channel(interaction, self.ticket_type, self.issue)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CloseTicketModal())
    
    @discord.ui.button(label="Add User", style=discord.ButtonStyle.green, custom_id="add_user")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has Support Team role
        if not any(role.name == SUPPORT_ROLE_NAME for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ Only Support Team members can add users to tickets.",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(AddUserModal())
    
    @discord.ui.button(label="Remove User", style=discord.ButtonStyle.gray, custom_id="remove_user")
    async def remove_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has Support Team role or is ticket creator
        is_support = any(role.name == SUPPORT_ROLE_NAME for role in interaction.user.roles)
        is_creator = interaction.user.name in (interaction.channel.topic or "")
        
        if not (is_support or is_creator):
            await interaction.response.send_message(
                "❌ Only Support Team or ticket creator can remove users.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_modal(RemoveUserModal())

class RemoveUserModal(discord.ui.Modal, title="Remove User from Ticket"):
    user_id = discord.ui.TextInput(
        label="User ID to remove",
        placeholder="Enter the user's ID",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = await interaction.guild.fetch_member(int(self.user_id.value))
            
            # Prevent removing Support Team or ticket creator
            topic = interaction.channel.topic or ""
            creator_name = topic.split("Ticket by ")[1].split(" |")[0] if "Ticket by" in topic else ""
            creator = discord.utils.get(interaction.guild.members, name=creator_name)
            
            if any(role.name == SUPPORT_ROLE_NAME for role in user.roles):
                await interaction.response.send_message(
                    "❌ Cannot remove Support Team members from tickets.",
                    ephemeral=True
                )
                return
                
            if creator and user.id == creator.id:
                await interaction.response.send_message(
                    "❌ Cannot remove ticket creator from ticket.",
                    ephemeral=True
                )
                return
            
            await interaction.channel.set_permissions(
                user,
                overwrite=None  # Removes all specific permissions
            )
            
            embed = discord.Embed(
                title="User Removed",
                description=f"{user.mention} has been removed from the ticket.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
            
            # Log the action
            await log_action(
                interaction.guild,
                f"👤 User removed from ticket\n"
                f"• Channel: {interaction.channel.mention}\n"
                f"• Removed by: {interaction.user.mention}\n"
                f"• User removed: {user.mention}"
            )
            
        except ValueError:
            await interaction.response.send_message(
                "Invalid user ID. Please enter a numeric ID.",
                ephemeral=True
            )
        except discord.NotFound:
            await interaction.response.send_message(
                "User not found. Please check the ID and try again.",
                ephemeral=True
            )
class CloseTicketModal(discord.ui.Modal, title="Close Ticket"):
    reason = discord.ui.TextInput(
        label="Reason for closing (optional)",
        style=discord.TextStyle.short,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await handle_ticket_close(interaction, self.reason.value)

class AddUserModal(discord.ui.Modal, title="Add User to Ticket"):
    user_id = discord.ui.TextInput(
        label="User ID to add",
        placeholder="Enter the user's ID",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = await interaction.guild.fetch_member(int(self.user_id.value))
            await interaction.channel.set_permissions(
                user,
                read_messages=True,
                send_messages=True,
                read_message_history=True
            )
            
            embed = discord.Embed(
                title="User Added",
                description=f"{user.mention} has been added to the ticket.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            
            await log_action(
                interaction.guild,
                f"👤 User added to ticket\n"
                f"• Channel: {interaction.channel.mention}\n"
                f"• Added by: {interaction.user.mention}\n"
                f"• User added: {user.mention}"
            )
            
        except ValueError:
            await interaction.response.send_message(
                "Invalid user ID. Please enter a numeric ID.",
                ephemeral=True
            )
        except discord.NotFound:
            await interaction.response.send_message(
                "User not found. Please check the ID and try again.",
                ephemeral=True
            )

async def setup_ticket_system(guild):
    """Setup the ticket system in a guild"""
    global support_role, log_channel, transcript_channel
    
    support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)
    if not support_role:
        support_role = await guild.create_role(
            name=SUPPORT_ROLE_NAME,
            color=discord.Color.green(),
            permissions=discord.Permissions(
                read_messages=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True
            )
        )
    
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if not category:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            support_role: discord.PermissionOverwrite(read_messages=True)
        }
        category = await guild.create_category(
            TICKET_CATEGORY_NAME,
            overwrites=overwrites
        )
    
    log_channel = discord.utils.get(guild.channels, name=LOG_CHANNEL_NAME)
    if not log_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            support_role: discord.PermissionOverwrite(read_messages=True)
        }
        log_channel = await guild.create_text_channel(
            LOG_CHANNEL_NAME,
            overwrites=overwrites,
            category=category
        )
    
    transcript_channel = discord.utils.get(guild.channels, name=TRANSCRIPT_CHANNEL_NAME)
    if not transcript_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            support_role: discord.PermissionOverwrite(read_messages=True)
        }
        transcript_channel = await guild.create_text_channel(
            TRANSCRIPT_CHANNEL_NAME,
            overwrites=overwrites,
            category=category
        )
    
    return category, log_channel, transcript_channel

async def create_ticket_channel(interaction: discord.Interaction, ticket_type: str, issue: str):
    """Create a new ticket channel"""
    global support_role
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        category = discord.utils.get(interaction.guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category, _, _ = await setup_ticket_system(interaction.guild)
        
        ticket_data = TICKET_TYPES[ticket_type]
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True)
        }
        
        channel_name = f"{ticket_data['emoji']}-{interaction.user.name[:10]}"
        ticket_channel = await category.create_text_channel(
            name=channel_name,
            topic=f"Ticket by {interaction.user.name} | Type: {ticket_data['name']} | Issue: {issue[:100]}",
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title=f"{ticket_data['emoji']} {ticket_data['name']}",
            description=f"Thank you for creating a ticket!\n\n**Your issue:** {issue}",
            color=discord.Color(ticket_data["color"])
        )
        embed.add_field(name="User", value=interaction.user.mention, inline=True)
        embed.add_field(name="Support", value=support_role.mention, inline=True)
        embed.set_footer(text="The support team will assist you shortly.")
        
        await ticket_channel.send(
            content=f"{interaction.user.mention} {support_role.mention}",
            embed=embed,
            view=TicketControlView()
        )
        
        await interaction.followup.send(
            embed=discord.Embed(
                title="Ticket Created",
                description=f"Your ticket has been created in {ticket_channel.mention}",
                color=discord.Color.green()
            ),
            ephemeral=True
        )
        
        await log_action(
            interaction.guild,
            f"🎟️ New ticket created\n"
            f"• Channel: {ticket_channel.mention}\n"
            f"• User: {interaction.user.mention}\n"
            f"• Type: {ticket_data['name']}\n"
            f"• Issue: {issue[:200]}"
        )
        
    except Exception as e:
        print(f"Error creating ticket channel: {e}")
        await interaction.followup.send(
            "Failed to create ticket. Please try again.",
            ephemeral=True
        )

async def handle_ticket_close(interaction: discord.Interaction, reason: str):
    """Handle ticket closing process"""
    try:
        if not interaction.channel or interaction.channel.guild is None:
            raise ValueError("Channel no longer exists")
        
        await interaction.response.defer(ephemeral=True)
        
        transcript = await generate_transcript(interaction.channel)
        
        transcript_embed = discord.Embed(
            title=f"Transcript: {interaction.channel.name}",
            description=f"Closed by {interaction.user.mention}",
            color=discord.Color.blue()
        )
        if reason:
            transcript_embed.add_field(name="Reason", value=reason, inline=False)
        
        transcript_msg = await transcript_channel.send(
            embed=transcript_embed,
            file=transcript
        )
        
        try:
            topic = interaction.channel.topic or ""
            if "Ticket by" in topic:
                username = topic.split("Ticket by ")[1].split(" |")[0]
                user = discord.utils.get(interaction.guild.members, name=username)
                if user:
                    notify_embed = discord.Embed(
                        title="Your Ticket Has Been Closed",
                        description=f"Ticket: {interaction.channel.name}",
                        color=discord.Color.blue()
                    )
                    notify_embed.add_field(
                        name="Transcript",
                        value=f"[View transcript]({transcript_msg.jump_url})",
                        inline=False
                    )
                    if reason:
                        notify_embed.add_field(name="Reason", value=reason, inline=False)
                    await user.send(embed=notify_embed)
        except Exception as e:
            print(f"Error notifying user: {e}")
        
        await log_action(
            interaction.guild,
            f"🔒 Ticket closed\n"
            f"• Channel: {interaction.channel.name}\n"
            f"• Closed by: {interaction.user.mention}\n"
            f"• Reason: {reason or 'Not specified'}\n"
            f"• Transcript: [View here]({transcript_msg.jump_url})"
        )
        
        await interaction.channel.delete(reason=f"Closed by {interaction.user.name}")
        
        await interaction.followup.send(
            "Ticket closed successfully.",
            ephemeral=True
        )
        
    except discord.NotFound:
        print("Channel already deleted or not found")
        await interaction.followup.send(
            "Ticket already closed.",
            ephemeral=True
        )
    except Exception as e:
        print(f"Error closing ticket: {e}")
        await interaction.followup.send(
            "Failed to close ticket properly. Please contact an admin.",
            ephemeral=True
        )

async def generate_transcript(channel):
    """Generate a transcript of the ticket"""
    messages = []
    async for message in channel.history(limit=None, oldest_first=True):
        messages.append(message)
    
    transcript = f"Transcript for {channel.name}\n\n"
    transcript += f"Created: {channel.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
    transcript += f"Closed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    transcript += f"Total messages: {len(messages)}\n\n"
    
    for message in messages:
        timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        author = message.author.display_name
        content = message.clean_content
        
        if not content:
            if message.attachments:
                content = f"[Attachment: {message.attachments[0].filename}]"
            elif message.embeds:
                content = "[Embed content]"
            else:
                content = "[No text content]"
        
        transcript += f"[{timestamp}] {author}: {content}\n"
    
    transcript_bytes = transcript.encode('utf-8')
    return discord.File(io.BytesIO(transcript_bytes), filename=f"transcript-{channel.name}.txt")

async def log_action(guild, message):
    """Log an action to the log channel"""
    if not log_channel:
        await setup_ticket_system(guild)
    
    embed = discord.Embed(
        description=message,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    await log_channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    
    for guild in bot.guilds:
        await setup_ticket_system(guild)
        print(f"Setup complete in {guild.name}")
    
    bot.add_view(TicketSetupView())
    bot.add_view(TicketControlView())
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands globally")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Ticket Management Commands
@bot.tree.command(name="setup_tickets", description="Setup the ticket system in this server")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    await setup_ticket_system(interaction.guild)
    await interaction.response.send_message(
        "Ticket system has been set up successfully!",
        ephemeral=True
    )

@bot.tree.command(name="customize_panel", description="Customize the ticket panel with an interactive menu")
@app_commands.checks.has_permissions(administrator=True)
async def customize_panel(interaction: discord.Interaction):
    """Open the panel customization menu"""
    embed = discord.Embed(
        title="🔧 Ticket Panel Customization",
        description="Use the buttons below to customize each aspect of the panel.\n"
                   "You can add images, change colors and texts.",
        color=discord.Color.blue()
    )
    
    view = PanelCustomizationView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="create_panel", description="Create the ticket panel with current configuration")
@app_commands.checks.has_permissions(administrator=True)
async def create_panel(interaction: discord.Interaction):
    embed = create_panel_embed()
    await interaction.response.send_message(embed=embed, view=TicketSetupView())
    
@bot.tree.command(name="close", description="Close the current ticket")
async def close_ticket_command(interaction: discord.Interaction):
    if not interaction.channel.category or TICKET_CATEGORY_NAME not in interaction.channel.category.name:
        await interaction.response.send_message(
            "This command can only be used in ticket channels.",
            ephemeral=True
        )
        return
    
    await interaction.response.send_modal(CloseTicketModal())

# Ticket Type Management Commands
@bot.tree.command(name="list_ticket_types", description="List all available ticket types")
async def list_ticket_types(interaction: discord.Interaction):
    if not TICKET_TYPES:
        await interaction.response.send_message(
            "No ticket types have been configured yet.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Available Ticket Types",
        color=discord.Color.blue()
    )

    for t_type, data in TICKET_TYPES.items():
        embed.add_field(
            name=f"{data['emoji']} {data['name']} (ID: {t_type})",
            value=data["description"],
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="add_ticket_type", description="Add a new ticket type (Admin only)")
@app_commands.describe(
    type_id="Unique ID for the ticket type (no spaces)",
    name="Display name for the ticket type",
    emoji="Emoji to represent the ticket type",
    color="Hex color code (e.g. FF0000 for red)",
    description="Description shown to users"
)
@app_commands.checks.has_permissions(administrator=True)
async def add_ticket_type(
    interaction: discord.Interaction,
    type_id: str,
    name: str,
    emoji: str,
    color: str,
    description: str
):
    try:
        if color.startswith("#"):
            color = color[1:]
        color_int = int(color, 16)
        
        TICKET_TYPES[type_id] = {
            "name": name,
            "emoji": emoji,
            "color": color_int,
            "description": description
        }
        
        await interaction.response.send_message(
            f"✅ Ticket type '{name}' added successfully!",
            ephemeral=True
        )
    except ValueError:
        await interaction.response.send_message(
            "❌ Invalid color format. Please use a hex color (e.g., FF0000 for red).",
            ephemeral=True
        )

@bot.tree.command(name="remove_ticket_type", description="Remove an existing ticket type (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def remove_ticket_type(interaction: discord.Interaction):
    if len(TICKET_TYPES) <= 1:
        await interaction.response.send_message(
            "❌ You cannot remove the last ticket type.",
            ephemeral=True
        )
        return

    options = [
        discord.SelectOption(
            label=TICKET_TYPES[t_type]["name"],
            value=t_type,
            emoji=TICKET_TYPES[t_type]["emoji"]
        ) for t_type in TICKET_TYPES
    ]

    select = discord.ui.Select(
        placeholder="Select a ticket type to remove...",
        options=options,
        min_values=1,
        max_values=1
    )

    async def select_callback(interaction: discord.Interaction):
        selected_type = select.values[0]
        removed_type = TICKET_TYPES.pop(selected_type)
        
        await interaction.response.send_message(
            f"✅ Ticket type '{removed_type['name']}' has been removed.",
            ephemeral=True
        )

    select.callback = select_callback
    view = discord.ui.View()
    view.add_item(select)

    await interaction.response.send_message(
        "Select the ticket type you want to remove:",
        view=view,
        ephemeral=True
    )

@bot.tree.command(name="reset_ticket_types", description="Reset ticket types to defaults (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def reset_ticket_types(interaction: discord.Interaction):
    global TICKET_TYPES
    TICKET_TYPES = get_default_ticket_types().copy()
    await interaction.response.send_message(
        "✅ Ticket types have been reset to defaults.",
        ephemeral=True
    )

# Command to force sync commands
@bot.command()
@commands.is_owner()
async def sync(ctx):
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Synced {len(synced)} commands globally")
    except Exception as e:
        await ctx.send(f"❌ Error syncing commands: {e}")

async def load_cogs():
    try:
        await bot.load_extension("clear")
        await bot.load_extension("currency")
        await bot.load_extension("math_operations")
        await bot.load_extension("referral_system")        
        print("✅ Clear cog loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load clear cog: {e}")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    change_status.start()
    await load_cogs()  
    
    for guild in bot.guilds:
        await setup_ticket_system(guild)
        print(f"Setup complete in {guild.name}")
    
   
    bot.add_view(TicketSetupView())
    bot.add_view(TicketControlView())
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands globally")
    except Exception as e:
        print(f"Error syncing commands: {e}")

if __name__ == '__main__':
    bot.run(TOKEN)