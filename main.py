"""club elec’s Discord server for the electrogram service"""

import datetime
import glob
import os
import re
from typing import Optional, Union
from zoneinfo import ZoneInfo

import aiohttp
import unicodedata
import discord
import emoji as emojilib
import markdown
import mysql.connector
from discord.ext import tasks
from moviepy.editor import VideoFileClip
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN: str = os.environ.get("BOT_TOKEN")
CHANNEL_ID: int = int(os.environ.get("CHANNEL_ID"))
GUILD_ID: int = int(os.environ.get("GUILD_ID"))
ELECTROGRAM_URL: str = os.environ.get(
    "ELECTROGRAM_URL", "https://electrogram.clubelec.org"
)
DB_CONFIG: dict[str, str] = {
    "user": os.environ.get("DB_USER", "electrogram"),
    "password": os.environ.get("DB_PASSWORD", "electrogram"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "database": os.environ.get("DB_NAME", "electrogram"),
}
ATTACHMENTS_FOLDER: str = os.environ.get("ATTACHMENTS_FOLDER", "shared/attachments")
AVATARS_FOLDER: str = os.environ.get("AVATARS_FOLDER", "shared/avatars")
FONT_FILE: str = os.environ.get("FONT_FILE", "fonts/VarelaRound-Regular.ttf")
INPUT_LEVEL_IMG: str = os.environ.get("INPUT_LEVEL_IMG", "img/level_base.png")
OUTPUT_LEVEL_FOLDER: str = os.environ.get("OUTPUT_LEVEL_FOLDER", "shared/levels")
CUSTOM_EMOJIS_FOLDER: str = os.environ.get("CUSTOM_EMOJIS_FOLDER", "shared/emojis")
ALLOWED_IMG_EXTENSIONS: str = os.environ.get(
    "ALLOWED_IMG_EXTENSIONS", ".png,.jpg,.jpeg,.gif"
)
ALLOWED_VID_EXTENSIONS: str = os.environ.get("ALLOWED_VID_EXTENSIONS", ".mp4,.mov,.avi")
ALLOWED_AUD_EXTENSIONS: str = os.environ.get("ALLOWED_AUD_EXTENSIONS", ".mp3,.wav,.ogg")
ALLOWED_EXTENSIONS = (
    ALLOWED_IMG_EXTENSIONS + ALLOWED_VID_EXTENSIONS + ALLOWED_AUD_EXTENSIONS
)

intents = discord.Intents.all()
client: discord.Client = discord.Client(intents=intents)

time: datetime.time = datetime.time(hour=0, minute=00, tzinfo=ZoneInfo("Europe/Paris"))


def create_tables(cursor: mysql.connector.cursor.MySQLCursor) -> None:
    try:
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS messages (id BIGINT PRIMARY KEY, content TEXT, timestamp DATETIME, user_id BIGINT)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS tags (id BIGINT AUTO_INCREMENT PRIMARY KEY, message_id BIGINT, emoji VARCHAR(255), description VARCHAR(255), filename VARCHAR(255)) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS attachments (id BIGINT AUTO_INCREMENT PRIMARY KEY, message_id BIGINT, filename VARCHAR(255), type VARCHAR(255))"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS users (id BIGINT PRIMARY KEY, username VARCHAR(255), display_name VARCHAR(255), avatar VARCHAR(255))"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS streaks (user_id BIGINT PRIMARY KEY, streak INT, max_streak INT, last_message_date DATE)"
        )
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Error: Access denied.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Error: Database does not exist.")
        else:
            print("Error:", err)
        exit()


async def create_role_icon(streak: int) -> str:
    output_image_path = os.path.join(
        OUTPUT_LEVEL_FOLDER, f"electrogram_level_{streak}.png"
    )
    if os.path.exists(output_image_path):
        return output_image_path

    img = Image.open(INPUT_LEVEL_IMG)
    font_size = int(min(img.size))
    font = ImageFont.truetype(FONT_FILE, font_size)
    draw = ImageDraw.Draw(img)
    text = str(streak)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    width, height = img.size
    x = (width - text_width) / 2
    y = (height - text_height) / 2 - text_bbox[1]
    draw.text((x, y), text, font=font, fill="#e1e0e2")
    output_image_path = os.path.join(
        OUTPUT_LEVEL_FOLDER, f"electrogram_level_{streak}.png"
    )
    img.save(output_image_path)
    return output_image_path


async def image_to_bytes(image_path: str) -> bytes:
    with open(image_path, "rb") as image_file:
        return image_file.read()


def get_reactions() -> dict:
    with open("reactions.txt", "r") as file:
        lines = file.readlines()
    reactions = {
        line.split("=")[0].strip(): line.split("=")[1].strip() for line in lines
    }
    return reactions


reactions = get_reactions()


def detect_link(text: str) -> str:
    regex = re.compile(r"(?<!\[)(https?://\S+|mailto:\S+)(?!\])")
    formated_text = regex.sub(r"<a href=\"\1\">\1</a>", text)
    return formated_text


async def download_file(url: str, destination: str) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(destination, "wb") as f:
                    f.write(await resp.read())

    _, extension = os.path.splitext(destination)
    extension = extension[1:].lower()
    thumbnail_path = f"{destination}.thumb.jpg"

    if extension in ALLOWED_IMG_EXTENSIONS:
        generate_image_thumbnail(destination, thumbnail_path)
    elif extension in ALLOWED_VID_EXTENSIONS:
        generate_video_thumbnail(destination, thumbnail_path)

    resize_thumbnail(thumbnail_path, max_size=(500, 500))
    if extension in ALLOWED_VID_EXTENSIONS:
        add_play_icon_to_thumbnail(thumbnail_path)


def resize_thumbnail(thumbnail_path: str, max_size: tuple[int, int]) -> None:
    thumbnail = Image.open(thumbnail_path)
    thumbnail.thumbnail(max_size, Image.Resampling.LANCZOS)
    thumbnail.save(thumbnail_path)


def generate_image_thumbnail(image_path: str, thumbnail_path: str) -> None:
    image = Image.open(image_path)
    image = image.convert("RGB")
    max_size = (500, 500)
    image.thumbnail(max_size)
    image.save(thumbnail_path)


def generate_video_thumbnail(video_path: str, thumbnail_path: str) -> None:
    video = VideoFileClip(video_path)
    thumbnail = video.get_frame(0)
    Image.fromarray(thumbnail).save(thumbnail_path, "JPEG")
    video.close()


def add_play_icon_to_thumbnail(thumbnail_path: str) -> None:
    thumbnail = Image.open(thumbnail_path)
    icon_size = min(thumbnail.width, thumbnail.height) // 2
    play_icon = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(play_icon)
    triangle_width = int(icon_size * 0.6)
    triangle_height = int(icon_size * 0.5)
    triangle_top = (icon_size - triangle_height) // 2
    triangle_bottom = triangle_top + triangle_height
    triangle_left = (icon_size - triangle_width) // 2
    triangle_right = triangle_left + triangle_width
    draw.polygon(
        [
            (triangle_left, triangle_top),
            (triangle_right, icon_size // 2),
            (triangle_left, triangle_bottom),
        ],
        fill="#e1e0e299",
    )
    play_icon = play_icon.resize((icon_size, icon_size))
    thumbnail.paste(
        play_icon,
        (thumbnail.width // 2 - icon_size // 2, thumbnail.height // 2 - icon_size // 2),
        play_icon,
    )
    thumbnail.save(thumbnail_path)


def get_file_type(path: str) -> str:
    _, extension = os.path.splitext(path)
    extension = extension[1:].lower()

    if extension in ALLOWED_AUD_EXTENSIONS:
        return "audio"
    elif extension in ALLOWED_VID_EXTENSIONS:
        return "video"
    elif extension in ALLOWED_IMG_EXTENSIONS:
        return "picture"
    else:
        return "unknown"


async def get_user_display_name(user: Union[discord.User, discord.Member]) -> str:
    guild = client.get_guild(GUILD_ID)
    member = guild.get_member(user.id)
    if member.name != member.display_name:
        return member.display_name
    else:
        return member.global_name


async def update_user_roles(
    user: discord.Member,
    days_difference: int,
    streak: Optional[int] = None,
    auto: Optional[bool] = False,
) -> None:
    guild = client.get_guild(GUILD_ID)

    if auto == False:
        new_role = discord.utils.get(user.roles, name=f"electrogram niveau {streak}")
        if new_role is None:
            new_role = discord.utils.get(
                guild.roles, name=f"electrogram niveau {streak}"
            )
            if new_role is None:
                icon_path = await create_role_icon(streak)
                icon_bytes = await image_to_bytes(icon_path)
                new_role = await guild.create_role(
                    name=f"electrogram niveau {streak}", display_icon=icon_bytes
                )
        for role in user.roles:
            if role.name.startswith("electrogram niveau"):
                await user.remove_roles(role)
                if len(role.members) == 0:
                    await role.delete()
        await user.add_roles(new_role)
    else:
        if days_difference >= 2:
            for role in user.roles:
                if role.name.startswith("electrogram niveau"):
                    await user.remove_roles(role)
                    if len(role.members) == 0:
                        await role.delete()


async def update_user_profile(
    cursor: mysql.connector.cursor.MySQLCursor,
    user: Union[discord.User, discord.Member],
    create_if_not_exist: Optional[bool] = False,
) -> None:
    cursor.execute("SELECT * FROM users WHERE id = %s", (user.id,))
    result = cursor.fetchone()
    if result is not None or create_if_not_exist is True:
        avatar = f"{AVATARS_FOLDER}/{user.id}.png"
        if result is None:
            cursor.execute(
                "INSERT INTO users (id, username, display_name, avatar) VALUES (%s, %s, %s, %s)",
                (user.id, user.name, await get_user_display_name(user), avatar),
            )
        else:
            cursor.execute(
                "UPDATE users SET avatar = %s, username = %s, display_name = %s WHERE id = %s",
                (avatar, user.name, await get_user_display_name(user), user.id),
            )
        avatar_url = str(user.display_avatar.url)
        await download_file(avatar_url, avatar)


def get_streak_message(display_name: str, streak: int, state: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"Streak de {display_name}",
        color=0x1E1F1D,
    )

    if streak == 2:
        value = "Votre chaîne débute, c’est beau !\nContinuez comme cela ! :muscle:"
    elif streak == 3:
        value = "Super travail ! :fire:"
    elif streak <= 5:
        value = "Impressionnant ! :tada:"
    elif streak <= 10:
        value = "Incroyable ! :star2:"
    elif streak <= 15:
        value = "Spectaculaire ! :trophy:"
    elif streak <= 20:
        value = "Fantastique ! :medal:"
    elif streak <= 25:
        value = "Époustouflant ! :crown:"
    elif streak <= 30:
        value = "Incroyable ! :sparkles:"
    else:
        value = "Félicitations ! 🚀"

    if state == "again":
        name = f"Votre streak de {streak} ne bouge pas d’un poil !"
        value = "Vous avez déjà posté aujourd’hui.\nVotre streak ne sera donc pas augmenté.\nMais cela ne vous empêche pas de poster autant de messages que vous souhaitez par jour.\nBon travail ! :+1:"
    elif state == "new":
        name = "Bienvenue sur club elec electrogram !"
        value = "Oh mais c’est votre premier post sur club elec electrogram !\nAjoutez chaque jour un nouveau post et faites grimper votre score !"
    elif state == "reset":
        name = "Remise à zéro de votre streak..."
        value = "Votre streak est revenu à 1, car vous n’avez pas posté hier.\nEssayez de poster chaque jour pour augmenter votre streak ! :wink:"
    elif state == "ok":
        name = f"Votre streak est maintenant de {streak} jours !"

    return embed.add_field(
        name=name,
        value=value,
        inline=False,
    )


def remove_accents(input: str):
    nfkd_form = unicodedata.normalize("NFKD", input)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


class OpenElectrogram(discord.ui.View):
    def __init__(self, username: str, display_name: str):
        super().__init__()
        url = f"{ELECTROGRAM_URL}/user/{username}"
        self.add_item(
            discord.ui.Button(label=f"Ouvrir l’electrogram de {display_name}", url=url)
        )


@client.event
async def on_ready() -> None:
    try:
        mydb = mysql.connector.connect(**DB_CONFIG)
        cursor = mydb.cursor()
        create_tables(cursor)
        mydb.close()
        guild = client.get_guild(GUILD_ID)
        for member in guild.members:
            mydb = mysql.connector.connect(**DB_CONFIG)
            cursor = mydb.cursor()
            await update_user_profile(cursor, member)
            cursor.execute(
                "SELECT last_message_date FROM streaks WHERE user_id = %s", (member.id,)
            )
            result = cursor.fetchone()
            if result is not None:
                last_message_date = result[0]
                mydb.commit()
                mydb.close()
                today = datetime.date.today()
                days_difference = (today - last_message_date).days
                await update_user_roles(member, days_difference, None, True)
            else:
                mydb.commit()
                mydb.close()

        streak_update.start()
    except Exception as e:
        print("Error in on_ready:", e)


@client.event
async def on_message(message: discord.Message) -> None:
    try:
        if message.channel.id == CHANNEL_ID:
            mydb = mysql.connector.connect(**DB_CONFIG)
            cursor = mydb.cursor()

            if len(message.attachments) == 0 or message.content.strip() == "":
                await message.delete()
                await message.author.send(
                    "Coucou ! :wave:\nVotre publication a été malheureusement refusée... :sob:\nPour être publiée sur electrogram, elle doit contenir du texte ainsi qu’une ou plusieurs images et/ou vidéos.\nRéessayez, je reste à votre service. :wink:"
                )
                return

            if not all(
                os.path.splitext(attachment.filename)[1] in ALLOWED_EXTENSIONS
                for attachment in message.attachments
            ):
                await message.delete()
                await message.author.send(
                    "Coucou ! :wave:\nVotre publication a été malheureusement refusée... :sob:\nVous avez envoyé un fichier qui n’est pas une image ou une vidéo.\nRéessayez, je reste à votre service. :wink:"
                )
                return

            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")

            sql = "INSERT INTO messages (id, content, user_id, timestamp) VALUES (%s, %s, %s, %s)"
            val = (
                message.id,
                markdown.markdown(detect_link(message.content)),
                message.author.id,
                timestamp,
            )
            cursor.execute(sql, val)

            for attachment in message.attachments:
                attachment_name = (
                    f"{ATTACHMENTS_FOLDER}/{message.id}_{attachment.filename}"
                )
                await download_file(attachment.url, attachment_name)
                sql = "INSERT INTO attachments (message_id, filename, type) VALUES (%s, %s, %s)"
                val = (message.id, attachment_name, get_file_type(attachment_name))
                cursor.execute(sql, val)

            try:
                mydb.commit()
                cursor.execute(
                    "SELECT streak, max_streak, last_message_date FROM streaks WHERE user_id = %s",
                    (message.author.id,),
                )
                result = cursor.fetchone()

                today = datetime.date.today()

                display_name = await get_user_display_name(message.author)

                if result is None:
                    streak = 1
                    cursor.execute(
                        "INSERT INTO streaks (user_id, streak, max_streak, last_message_date) VALUES (%s, %s, %s, %s)",
                        (message.author.id, streak, streak, today),
                    )
                    streak_message = get_streak_message(display_name, streak, "new")
                    last_message_date = today
                else:
                    streak, max_streak, last_message_date = result
                    if last_message_date == today - datetime.timedelta(days=1):
                        streak += 1
                        if max_streak is None or max_streak < streak:
                            max_streak = streak
                        cursor.execute(
                            "UPDATE streaks SET streak = %s, max_streak = %s, last_message_date = %s WHERE user_id = %s",
                            (streak, max_streak, today, message.author.id),
                        )
                        streak_message = get_streak_message(display_name, streak, "ok")
                    elif last_message_date == today:
                        streak_message = get_streak_message(
                            display_name, streak, "again"
                        )
                    else:
                        streak = 1
                        cursor.execute(
                            "UPDATE streaks SET streak = %s, last_message_date = %s WHERE user_id = %s",
                            (streak, today, message.author.id),
                        )
                        streak_message = get_streak_message(
                            display_name, streak, "reset"
                        )
                await update_user_profile(cursor, message.author, True)
                days_difference = (today - last_message_date).days
                thread = await message.create_thread(
                    name=f"Nouvelle publication dans l’electrogram de {display_name}"
                )
                streak_message.set_author(
                    name=f"{display_name}", icon_url=message.author.avatar
                )
                await thread.send(
                    view=OpenElectrogram(message.author.name, display_name)
                )
                await thread.send(embed=streak_message)
                embed = discord.Embed(
                    title=f"Discutez de cette publication avec {display_name} !",
                    color=0x1E1F1D,
                )
                embed.add_field(
                    name="Vous avez quelque chose à dire, des avis, des suggestions, des insultes... ?",
                    value="Faites-le donc dans ce fil, c’est fait pour cela. :smile:",
                    inline=False,
                )
                embed.set_author(name=f"{display_name}", icon_url=message.author.avatar)
                await thread.send(embed=embed)
                await message.add_reaction("🚀")
                added_reactions = set()
                for pattern, reaction in reactions.items():
                    if (
                        re.search(
                            rf"\b{re.escape(pattern)}\b",
                            remove_accents(message.content.lower()),
                        )
                        and reaction not in added_reactions
                    ):
                        if reaction.startswith("<:") and reaction.endswith(">"):
                            emoji_id = int(reaction.split(":")[-1][:-1])
                            emoji = discord.utils.get(client.emojis, id=emoji_id)
                            if emoji:
                                await message.add_reaction(emoji)
                                added_reactions.add(str(emoji))
                        else:
                            await message.add_reaction(reaction)
                            added_reactions.add(reaction)
            except Exception as e:
                print("Error in on_message:", e)

            finally:
                try:
                    mydb.commit()
                except:
                    print("Error in on_message:", e)
                    await message.add_reaction("❌")
                    await message.delete()
                    await message.author.send(
                        "Coucou ! :wave:\nUne erreur est survenue... :sob:\nNous faisons tout notre possible pour résoudre ce problème\nRetentez dans quelques minutes."
                    )
                mydb.close()
                if days_difference != 0:
                    await update_user_roles(message.author, days_difference, streak)
    except Exception as e:
        print("Error in on_message:", e)
        await message.add_reaction("❌")
        await message.delete()
        await message.author.send(
            "Coucou ! :wave:\nUne erreur est survenue... :sob:\nNous faisons tout notre possible pour résoudre ce problème\nRetentez dans quelques minutes."
        )


@client.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent) -> None:
    try:
        channel = await client.fetch_channel(payload.channel_id)
        if channel.id == CHANNEL_ID:
            message = await channel.fetch_message(payload.message_id)
            mydb = mysql.connector.connect(**DB_CONFIG)
            cursor = mydb.cursor()

            if len(message.attachments) == 0 or message.content.strip() == "":
                await message.delete()
                await message.author.send(
                    "Coucou ! :wave:\nVotre publication a été malheureusement refusée... :sob:\nPour être publiée sur electrogram, elle doit contenir du texte ainsi qu’une ou plusieurs images et/ou vidéos.\nRéessayez, je reste à votre service. :wink:"
                )
                return

            if not all(
                os.path.splitext(attachment.filename)[1] in ALLOWED_EXTENSIONS
                for attachment in message.attachments
            ):
                await message.delete()
                await message.author.send(
                    "Coucou ! :wave:\nVotre publication a été malheureusement refusée... :sob:\nVous avez envoyé un fichier qui n’est pas une image ou une vidéo.\nRéessayez, je reste à votre service. :wink:"
                )
                return

            for filename in glob.glob(f"{ATTACHMENTS_FOLDER}/{message.id}_*"):
                os.remove(filename)
            cursor.execute(
                "DELETE FROM attachments WHERE message_id = %s",
                (message.id,),
            )

            for attachment in message.attachments:
                attachment_name = (
                    f"{ATTACHMENTS_FOLDER}/{message.id}_{attachment.filename}"
                )
                await download_file(attachment.url, attachment_name)
                sql = "INSERT INTO attachments (message_id, filename, type) VALUES (%s, %s, %s)"
                val = (message.id, attachment_name, get_file_type(attachment_name))
                cursor.execute(sql, val)

            sql = "UPDATE messages SET content = %s WHERE id = %s"
            val = (markdown.markdown(detect_link(message.content)), message.id)
            cursor.execute(sql, val)
            mydb.commit()

            for reaction in message.reactions:
                if reaction.me:
                    users = [user async for user in reaction.users()]
                    for user in users:
                        if user == client.user:
                            if isinstance(
                                reaction.emoji, (discord.Emoji, discord.PartialEmoji)
                            ):
                                emoji = str(reaction.emoji)
                            else:
                                emoji = reaction.emoji
                            for pattern, reaction_pattern in reactions.items():
                                if re.search(
                                    pattern, remove_accents(message.content.lower())
                                ):
                                    if str(emoji) == str("🚀") or str(emoji) == str("❌"):
                                        break
                                    if reaction_pattern == emoji:
                                        break
                            else:
                                await message.remove_reaction(
                                    reaction.emoji, client.user
                                )

            added_reactions = set()
            for pattern, reaction in reactions.items():
                if (
                    re.search(pattern, remove_accents(message.content.lower()))
                    and reaction not in added_reactions
                ):
                    if reaction.startswith("<:") and reaction.endswith(">"):
                        emoji_id = int(reaction.split(":")[-1][:-1])
                        emoji = discord.utils.get(client.emojis, id=emoji_id)
                        if emoji:
                            await message.add_reaction(emoji)
                            added_reactions.add(str(emoji))
                    else:
                        await message.add_reaction(reaction)
                        added_reactions.add(reaction)

            mydb.close()
    except Exception as e:
        print("Error in on_raw_message_edit:", e)


@client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent) -> None:
    try:
        message_id = payload.message_id
        channel_id = payload.channel_id

        if channel_id == CHANNEL_ID:
            mydb = mysql.connector.connect(**DB_CONFIG)
            cursor = mydb.cursor()

            cursor.execute("SELECT user_id FROM messages WHERE id = %s", (message_id,))
            result = cursor.fetchone()
            if result is None:
                return
            user_id = result[0]

            cursor.execute(
                "SELECT COUNT(*) FROM messages WHERE user_id = %s", (user_id,)
            )
            count = cursor.fetchone()[0]
            if count == 1:
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))

            cursor.execute(
                "SELECT filename FROM attachments WHERE message_id = %s", (message_id,)
            )
            result = cursor.fetchall()
            for row in result:
                if os.path.exists(row[0]):
                    os.remove(row[0])
                    os.remove(row[0] + ".thumb.jpg")

            cursor.execute("DELETE FROM messages WHERE id = %s", (message_id,))
            cursor.execute(
                "DELETE FROM attachments WHERE message_id = %s", (message_id,)
            )
            cursor.execute("DELETE FROM tags WHERE message_id = %s", (message_id,))
            mydb.commit()
            mydb.close()
    except Exception as e:
        print("Error in on_raw_message_delete:", e)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    try:
        if str(payload.emoji) == str("🚀") or str(payload.emoji) == str("❌"):
            return
        mydb = mysql.connector.connect(**DB_CONFIG)
        cursor = mydb.cursor()
        if payload.channel_id == CHANNEL_ID:
            emoji = payload.emoji
            emoji_name = str(emoji)
            emoji_id = (
                emoji.id
                if isinstance(emoji, (discord.Emoji, discord.PartialEmoji))
                else None
            )
            if emoji_id is not None:
                emoji_description = emoji_name.split(":")[1]
                filename = f"{CUSTOM_EMOJIS_FOLDER}/{emoji.id}.png"
            else:
                emoji_description = (
                    str(emojilib.demojize(emoji_name, language="fr"))
                    .replace(":", "")
                    .replace("_", " ")
                )
                filename = None
            message_id = payload.message_id

            cursor.execute(
                "SELECT * FROM tags WHERE message_id = %s AND emoji = %s",
                (message_id, emoji_name),
            )
            result = cursor.fetchone()
            if result is None:
                cursor.execute(
                    "INSERT INTO tags (message_id, emoji, description, filename) VALUES (%s, %s, %s, %s)",
                    (message_id, emoji_name, emoji_description, filename),
                )
                mydb.commit()

                if (
                    isinstance(emoji, (discord.Emoji, discord.PartialEmoji))
                    and filename is not None
                ):
                    async with aiohttp.ClientSession() as session:
                        async with session.get(str(emoji.url)) as resp:
                            if resp.status == 200:
                                with open(filename, "wb") as f:
                                    f.write(await resp.read())
        mydb.close()
    except Exception as e:
        print("Error in on_raw_reaction_add:", e)


@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
    try:
        if str(payload.emoji) == str("🚀") or str(payload.emoji) == str("❌"):
            return
        mydb = mysql.connector.connect(**DB_CONFIG)
        cursor = mydb.cursor()

        if payload.channel_id == CHANNEL_ID:
            emoji = payload.emoji
            emoji_name = str(emoji)
            message_id = payload.message_id

            channel = client.get_channel(payload.channel_id)
            message = await channel.fetch_message(message_id)

            for reaction in message.reactions:
                if str(reaction.emoji) == emoji_name and reaction.count > 0:
                    return

            cursor.execute(
                "DELETE FROM tags WHERE message_id = %s AND emoji = %s",
                (message_id, emoji_name),
            )
            mydb.commit()

        mydb.close()
    except Exception as e:
        print("Error in on_raw_reaction_remove:", e)


@client.event
async def on_raw_reaction_clear_emoji(
    payload: discord.RawReactionClearEmojiEvent,
) -> None:
    try:
        if str(payload.emoji) == str("🚀") or str(payload.emoji) == str("❌"):
            return
        mydb = mysql.connector.connect(**DB_CONFIG)
        cursor = mydb.cursor()

        if payload.channel_id == CHANNEL_ID:
            emoji = payload.emoji
            emoji_name = str(emoji)
            message_id = payload.message_id

            cursor.execute(
                "DELETE FROM tags WHERE message_id = %s AND emoji = %s",
                (message_id, emoji_name),
            )
            mydb.commit()

        mydb.close()
    except Exception as e:
        print("Error in on_raw_reaction_clear_emoji:", e)


@client.event
async def on_raw_reaction_clear(payload: discord.RawMessageDeleteEvent) -> None:
    try:
        mydb = mysql.connector.connect(**DB_CONFIG)
        cursor = mydb.cursor()
        if payload.channel_id == CHANNEL_ID:
            message_id = payload.message_id

            cursor.execute("DELETE FROM tags WHERE message_id = %s", (message_id,))
            mydb.commit()

        mydb.close()
    except Exception as e:
        print("Error in on_raw_reaction_clear:", e)


@client.event
async def on_user_update(before: discord.User, after: discord.User) -> None:
    try:
        mydb = mysql.connector.connect(**DB_CONFIG)
        cursor = mydb.cursor()
        await update_user_profile(cursor, after)
        mydb.commit()
        mydb.close()
    except Exception as e:
        print("Error in on_user_update:", e)


@client.event
async def on_member_update(before: discord.Member, after: discord.Member) -> None:
    try:
        mydb = mysql.connector.connect(**DB_CONFIG)
        cursor = mydb.cursor()
        await update_user_profile(cursor, after)
        mydb.commit()
        mydb.close()
    except Exception as e:
        print("Error in on_member_update:", e)


@tasks.loop(time=time)
async def streak_update() -> None:
    try:
        guild = client.get_guild(GUILD_ID)
        for member in guild.members:
            mydb = mysql.connector.connect(**DB_CONFIG)
            cursor = mydb.cursor()
            cursor.execute(
                "SELECT last_message_date FROM streaks WHERE user_id = %s", (member.id,)
            )
            result = cursor.fetchone()
            if result is not None:
                last_message_date = result[0]
                mydb.commit()
                mydb.close()
                today = datetime.date.today()
                days_difference = (today - last_message_date).days
                await update_user_roles(member, days_difference, None, True)
            else:
                mydb.commit()
                mydb.close()
    except Exception as e:
        print("Error in streak_update:", e)


client.run(BOT_TOKEN)
