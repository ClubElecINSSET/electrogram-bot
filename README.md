[![](https://upload.wikimedia.org/wikipedia/commons/thumb/b/bb/Gitea_Logo.svg/48px-Gitea_Logo.svg.png)](https://forge.collabore.fr)

![English:](https://upload.wikimedia.org/wikipedia/commons/thumb/7/77/Flag_of_the_United_States_and_United_Kingdom.png/20px-Flag_of_the_United_States_and_United_Kingdom.png) **club elec** uses **Gitea** for the development of its free softwares. Our GitHub repositories are only mirrors.
If you want to work with us, **fork us on [collabore forge](https://forge.collabore.fr/)** (no registration needed, you can sign in with your GitHub account).

![Français :](https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Flag_of_France_(1794%E2%80%931815%2C_1830%E2%80%931974%2C_2020%E2%80%93present).svg/20px-Flag_of_France_(1794%E2%80%931815%2C_1830%E2%80%931974%2C_2020%E2%80%93present).svg.png) **club elec** utilise **Gitea** pour le développement de ses logiciels libres. Nos dépôts GitHub ne sont que des miroirs.
Si vous souhaitez travailler avec nous, **forkez-nous sur [collabore forge](https://forge.collabore.fr/)** (l’inscription n’est pas nécessaire, vous pouvez vous connecter avec votre compte GitHub).
* * *

<h2 align="center">electrogram bot</h2>
<p align="center">
club elec’s Discord bot for the electrogram service</p>
<p align="center">
    <a href="#about">About</a> •
    <a href="#features">Features</a> •
    <a href="#deploy">Deploy</a> •
    <a href="#configuration">Configuration</a> •
    <a href="#license">License</a>
</p>

## About

Discord bot for saving messages from a given chat room and making them accessible via a Web interface?

## Features

- ✅ **Easy** to use
- ✅ **Save** **messages**
- ✅ **Save** **attachments**
- ✅ **Create** **threads** for each message
- ✅ **Add** a **score** when publishing messages on a **daily basis**
- ✅ **Thumbnail generation**
- ✅ Efficient **management** of **user profile** **updates**
- ✅ Management of **message** and/or **attachment** **deletion**
- ✅ Management of **changes** to **messages** and/or **attachments**
- ✨ Using **Discord interactions**

## Deploy

We have deployed electrogram bot on a server running Debian 11.

**Please adapt these steps to your configuration, ...**  
*We do not describe the usual server configuration steps.*

### Install required packages

```
apt install python3-pip python3-venv libmariadb-dev
```

### Create `electrogram-bot` user

```
groupadd electrogram-bot
```

```
useradd -r -s /sbin/nologin -g electrogram-bot electrogram-bot
```

### Retrieve sources

```
mkdir /opt/electrogram-bot
```

```
chown electrogram-bot:electrogram-bot /opt/electrogram-bot
```

```
cd /opt/electrogram-bot
```

```
runuser -u electrogram-bot -- git clone https://forge.collabore.fr/ClubElecINSSET/electrogram-bot .
```

### Create Python virtual environment

```
runuser -u electrogram-bot -- virtualenv .env
```

### Install Python dependencies

```
runuser -u electrogram-bot -- .env/bin/pip install -r requirements.txt
```

### Install systemd service

```
cp electrogram-bot.service /etc/systemd/system/
```

### Enable and start systemd service

```
systemctl enable electrogram-bot
```

```
systemctl start electrogram-bot
```

## Configuration

To configure electrogram bot, please modify the configurations of the systemd service according to your needs.

Do not forget to create an application in the Discord Developer Portal and to give the permissions:
- Manage Roles
- Create Public Threads
- Manage Messages

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see http://www.gnu.org/licenses/.

