import plugins
import plugins.libcommand as LibCommand
import plugins.liblogger as logger

class pluginInfo(plugins.Base):

    def __init__(self):
        pass

    def cmdHello(self, packet, interface, client, args):
        logger.info("Hello command executed")
        return "Hello!"
    
    def start(self):
        LibCommand.simpleCommand().registerCommand("hello", "This command tells you hello!", self.cmdHello)