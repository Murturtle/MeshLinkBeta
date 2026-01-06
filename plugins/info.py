import plugins
import plugins.libdiscordutil as DiscordUtil
import cfg
import plugins.liblogger as logger
import plugins.libinfo as libinfo
import plugins.libcommand as LibCommand
import plugins.libmesh as LibMesh

class pluginInfo(plugins.Base):

    def __init__(self):
        pass

    def calcPages(self, lines):
        max_len = cfg.config["max_message_length"]
        if not lines:
            return 0

        pages = []
        current_page = ""
        for line in lines:
            if len(current_page) + len(line) + 1 > max_len:
                pages.append(current_page.rstrip("\n"))
                current_page = ""
            current_page += line + "\n"

        if current_page:
            pages.append(current_page.rstrip("\n"))

        return len(pages), pages

    def start(self):
        logger.info("Loading info")

        def cmd_info(packet, interface, client, args):
            try:
                page = int(args.strip()) if args.strip() else 0
                if page < 0:
                    page = 0
            except ValueError:
                page = 0

            num_pages, pages = self.calcPages(libinfo.info)
            
            if page > num_pages:
                page = 0


            if page == 0:
                final_info = f"""Welcome to Flyover Mesh!
Use '{cfg.config["prefix"]}info <page>' to view other pages.
Use {cfg.config["prefix"]} before any command to interact with me.
Page 0/{num_pages}"""
            
            else:
                final_info = pages[page-1]

            

            
            return final_info

        LibCommand.simpleCommand().registerCommand("info", "info <page>", cmd_info)