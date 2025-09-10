import plugins
import plugins.libdiscordutil as DiscordUtil
import cfg
import yaml
import plugins.liblogger as logger
from openai import OpenAI
import plugins.libmesh as LibMesh
import plugins.libinfo as libinfo
import plugins.libcommand as LibCommand

class gpt(plugins.Base):

    def __init__(self):
        pass

    def start(self):
        logger.info("Loading OpenAI")

        # Register GPT command
        def cmd_gpt(packet, interface, client, args):
            prompt = args.strip()
            if not prompt:
                logger.info("No prompt provided after 'gpt' command")
                return "Please provide a prompt."

            ai_client = self.gpt_setup()
            response = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Make a short comment not exceeding 20 words"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=60
            )

            gpt_response = response.choices[0].message.content.strip()

            logger.info(f"Sent GPT response: {gpt_response}")
            return gpt_response

        LibCommand.simpleCommand().registerCommand("gpt", "Use chatgpt", cmd_gpt)

    def gpt_setup(self):
        with open("./plugins/gpt-config.yml", 'r') as file:
            cfg.gptconfig = yaml.safe_load(file)

        open_ai_token = cfg.gptconfig["open_ai_token"]
        return OpenAI(api_key=open_ai_token)