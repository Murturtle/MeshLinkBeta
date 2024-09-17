import plugins
import plugins.libdiscordutil as DiscordUtil
import cfg
import yaml
import plugins.liblogger as logger
from openai import OpenAI

class gpt(plugins.Base):

    def __init__(self):
        pass

    def start(self):
        logger.info("[INFO] Loading OpenAI")

    def gpt_setup(self):
        with open("./plugins/gpt-config.yml",'r') as file:
            cfg.gptconfig = yaml.safe_load(file)

        open_ai_token = cfg.gptconfig["open_ai_token"]
        return OpenAI(api_key=open_ai_token)

    def onReceive(self, packet, interface, client):
        """
        Handles Meshtastic messages and sends a GPT response if needed.
        """
        if "decoded" in packet and packet["decoded"].get("portnum") == "TEXT_MESSAGE_APP":
            incoming_message = packet["decoded"]["text"]
            logger.info(f"Received message: {incoming_message}")

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
                        logger.info("Sending to Discord")

                    logger.info(f"Sent GPT response: {gpt_response}")
                    
                else:
                    logger.info("No prompt provided after '$gpt' command.")
            else:
                logger.info("Message does not contain the GPT trigger.")

    def onConnect(self,interface,client):
        pass
    
    def onDisconnect(self,interface,client):
        pass