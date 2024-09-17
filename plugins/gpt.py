import plugins
import plugins.libdiscordutil as DiscordUtil
import cfg
from openai import OpenAI

class gpt(plugins.Base):

    def __init(self):
        pass

    def start(self):
        print ("[INFO] Loading OpenAI")

    def gpt_setup(self):
        open_ai_token = cfg.config["open_ai_token"]
        return OpenAI(api_key=open_ai_token)

    def onReceive(self, packet, interface, client):
        """
        Handles Meshtastic messages and sends a GPT response if needed.
        """
        if cfg.config["use_ai"]:
            if "decoded" in packet and packet["decoded"].get("portnum") == "TEXT_MESSAGE_APP":
                incoming_message = packet["decoded"]["text"]
                print(f"Received message: {incoming_message}")

                if incoming_message.startswith(cfg.config['prefix'] + 'gpt'):
                    prompt = incoming_message[len(cfg.config['prefix'] + 'gpt'):].strip()

                    if prompt:
                        ai_client = self.gpt_setup()
                        response = ai_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "Make a short comment not exceeding 20 words" },
                                {"role": "user", "content": prompt}
                                ],
                            max_tokens=60
                        )

                        gpt_response = response.choices[0].message.content.strip()

                        # Send GPT response over Meshtastic
                        interface.sendText(gpt_response, channelIndex=cfg.config["send_channel_index"])

                        if(cfg.config["send_mesh_commands_to_discord"]):
                            DiscordUtil.send_msg("`MeshLink`> "+gpt_response,client,cfg.config)
                            print ("Sending to Discord")

                        print(f"Sent GPT response: {gpt_response}")
                        
                    else:
                        print("No prompt provided after '$gpt' command.")
                else:
                    print("Message does not contain the GPT trigger.")

    # def on_message(self, message, interface):
    #     """
    #     Handles Discord messages and sends a GPT response if needed.
    #     """
    #     if cfg.config["use_ai"]:
    #         if message.author.bot:
    #             return

    #         if message.content.startswith(cfg.config['discord_prefix'] + 'gpt'):
    #             prompt = message.content[len('$gpt'):].strip()

    #             if prompt:
    #                 ai_client = self.gpt_setup()
    #                 response = ai_client.chat.completions.create(
    #                     model="gpt-4o-mini",
    #                     messages=[
    #                         {"role": "system", "content": "Make a short comment not exceeding 20 words" },
    #                         {"role": "user", "content": prompt}
    #                         ],
    #                     max_tokens=60
    #                 )

    #                 gpt_response = response.choices[0].message.content.strip()

    #                 # Send the GPT response back to the Discord channel
    #                 message.channel.send(gpt_response)
   
    #                 ## Also send the response over the mesh network
    #                 # if interface:
    #                 #     interface.sendText(gpt_response, channelIndex=config["send_channel_index"])

    #             else:
    #                 message.channel.send("Please provide a prompt after `gpt`.")


    def onConnect(interface):
        pass

    def onDisconnect(interface):
        pass