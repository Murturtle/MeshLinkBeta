quotes = [
    # Presidents & National Figures (Kansas)
    "Plans are worthless, but planning is everything. - Dwight D. Eisenhower",
    "Leadership is the art of getting someone else to do something you want done because he wants to do it. - Dwight D. Eisenhower",
    "Farming looks mighty easy when your plow is a pencil and you're a thousand miles from the corn field. - Dwight D. Eisenhower",

    "Liberty is the only thing you cannot have unless you give it to others. - William Allen White",
    "The trouble with every reform movement is that it has no fun in it. - William Allen White",

    "The test of progress is not whether we add more to the abundance of those who have much. - Alf Landon",

    "There is no royal road to learning. - Charles Curtis",

    # Aviation & Exploration
    "Adventure is worthwhile in itself. - Amelia Earhart",
    "The most difficult thing is the decision to act. - Amelia Earhart",
    "Never interrupt someone doing what you said couldn't be done. - Amelia Earhart",
    "Flying may not be all plain sailing, but the fun is worth the price. - Amelia Earhart",
    "I learned to fly by crashing. - Clyde Cessna",
    "An airplane is only as good as the men who build it. - Walter Beech",
    "Flying is not dangerous. Crashing is what's dangerous. - Lloyd Stearman",

    # Frontier & Old West (Kansas-connected)
    "I never killed anyone who didn't deserve it. - Wild Bill Hickok",
    "Take away my reputation and what have I left? - Wild Bill Hickok",
    "I was a peace chief, not a war chief. - Jesse Chisholm",
    "I traded with everyone. That was the point. - Jesse Chisholm",

    # Arts, Culture, & Media
    "I am not a fine artist. I am a storyteller. - Blackbear Bosin",
    "My art belongs to the people. - Blackbear Bosin",
    "I chose my camera as a weapon against what I hated most about the universe. - Gordon Parks",
    "The camera is my tool. Through it I give a reason to everything around me. - Gordon Parks",
    "Poverty is a poor teacher. - Gordon Parks",
    "I was born in Wichita, Kansas. - Hattie McDaniel",
    "Life's been good to me so far. - Joe Walsh",
    "Rock and roll is about freedom. - Joe Walsh",
    "The tribe has spoken. - Jeff Probst",
    "Survivor is a social experiment. - Jeff Probst",
    "I don't regret anything. I regret not doing more. - Kirstie Alley",
    "The older you get, the more important it is to appreciate the little things. - Kirstie Alley",
    "Comedy is rooted in honesty. - Eric Stonestreet",
    "I embrace where I come from. - Eric Stonestreet",
    "When I was a kid, I wanted to be a clown. I didn't want to be an actor, I wanted to join the circus and entertain people. - Eric Stonestreet",
    "Country music tells the truth about people's lives. - Martina McBride",

    # Sports
    "Success isn't owned. It's leased, and rent is due every day. - Barry Sanders",
    "I never wanted to be loud. I wanted to be good. - Barry Sanders",

    # Infamous Kansans
    "I'm proud of this job. - John C. Woods",
    "Some people get a kick out of killing. I don't. - John C. Woods",
    "Ten men in 103 minutes, that's fast work. - John C. Woods",
    "I hanged those ten Nazis...and I am proud of it...I wasn't nervous. A fellow can't afford to have nerves in this business. - John C. Woods",

    # Regional & Historical Voices
    "Kansas is a good place to be from. - Langston Hughes",
    "I swear to the Lord I can't see why democracy means everybody but me. - Langston Hughes",
    "The middle of the map matters more than people think. - William Least Heat-Moon",
    "You don't come to Kansas by accident. - William Inge",
    "Small towns shape big emotions. - William Inge"
]


import plugins
import plugins.libcommand as LibCommand
import plugins.liblogger as logger
import random

class pluginInfo(plugins.Base):

    def __init__(self):
        pass

    def cmd_quote(self, packet, interface, client, args):
        return random.choice(quotes)
    
    def cmd_coinflip(self, packet, interface, client, args):
        return random.choice(["Heads", "Tails"])
    
    def cmd_8ball(self, packet, interface, client, args):
        responses = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes - definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful."
        ]
        return random.choice(responses)
    
    def start(self):
        LibCommand.simpleCommand().registerCommand("quote", "A random quote", self.cmd_quote)
        LibCommand.simpleCommand().registerCommand("coinflip", "Flip a coin", self.cmd_coinflip)
        LibCommand.simpleCommand().registerCommand("8ball", "Magic eight ball", self.cmd_8ball)