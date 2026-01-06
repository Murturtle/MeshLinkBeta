import plugins.liblogger as logger
import plugins.libdiscordutil as DiscordUtil
import plugins.libinfo as LibInfo
import plugins.libmesh as LibMesh
import cfg

commands = []

class simpleCommand():
    """Basic command class, use this to create simple commands.
    registerCommand("Hello", "This command tells you hello!", callback function)
    """
    name = ""
    info = ""
    callback = None


    def registerCommand(self, name, info, callback):
        self.name = name
        self.info = info
        self.callback = callback
        commands.append(self)

        LibInfo.info.append(f"{name} - {info}")

    def onReceive(self, packet, interface, client):
        if("decoded" in packet):
            if(packet["decoded"]["portnum"] == "TEXT_MESSAGE_APP"):
                text = packet["decoded"]["text"]
                if(text.startswith(cfg.config["prefix"])):

                    noprefix = text[len(cfg.config["prefix"]):]

                    parts = noprefix.split(maxsplit=1)
                    command_name = parts[0]
                    args = parts[1] if len(parts) > 1 else ""

                    if command_name == self.name:
                        # Check if command is from ignored channels (1-7)
                        send_channel = int(packet["channel"]) if "channel" in packet else 0
                        ignored_channels = [1, 2, 3, 4, 5, 6, 7]
                        is_ignored_channel = send_channel in ignored_channels

                        if is_ignored_channel:
                            logger.info(f"Skipping command '{command_name}' from channel {send_channel} (ignored)")
                            return

                        reply = self.executeCommand(packet, interface, client, args)
                        LibMesh.sendReply(reply, interface, packet)

                        if(cfg.config["send_mesh_commands_to_discord"]):
                                DiscordUtil.send_embed("fl0v reply", reply, client, cfg.config, color=0x6bc19b)
                    
    
    def executeCommand(self, packet, interface, client, args):
        return self.callback(packet, interface, client, args)
        

