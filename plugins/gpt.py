
import cfg
import yaml
from openai import OpenAI
import plugins.libdiscordutil as DiscordUtil

with open("./config.yml",'r') as file:
    cfg.config = yaml.safe_load(file)

open_ai_token = cfg.config["open_ai_token"]
ai_client = OpenAI(api_key=open_ai_token)

async def gpt_handle_discord_message(message, interface):
    """
    Handles Discord messages and sends a GPT response if needed.
    """
    if message.author.bot:
        return

    if message.content.startswith(cfg.config['discord_prefix'] + 'gpt'):
        prompt = message.content[len('$gpt'):].strip()

        if prompt:
            response = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30
            )

            gpt_response = response.choices[0].message.content.strip()

            # Send the GPT response back to the Discord channel
            await message.channel.send(gpt_response)

            ## Also send the response over the mesh network
            # if interface:
            #     interface.sendText(gpt_response, channelIndex=cfg.config["send_channel_index"])

        else:
            await message.channel.send("Please provide a prompt after `$gpt`.")

def gpt_handle_meshtastic_message(packet, interface, client):
    """
    Handles Meshtastic messages and sends a GPT response if needed.
    """
    if "decoded" in packet and packet["decoded"].get("portnum") == "TEXT_MESSAGE_APP":
        incoming_message = packet["decoded"]["text"]
        print(f"Received message: {incoming_message}")

        if incoming_message.startswith(cfg.config['prefix'] + 'gpt'):
            prompt = incoming_message[len(cfg.config['prefix'] + 'gpt'):].strip()

            if prompt:
                response = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=40
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
