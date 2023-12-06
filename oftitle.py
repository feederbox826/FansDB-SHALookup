import re

dmRegex = "(?:^|\s*|[^\w]*)(dm)(?:[\'\‘\’\`\"\“\”]*)(?:s?)(?:$|\s*|[^\w]*)"
triggerArray = [
    # DM / in your DMs
    "dm",
    "dms"
    "inbox",
    "messages"
    # sending
    "sending you",
    "sending this",
    # partial video
    "teaser",
    "snippet",
    "entire",
    "full video",
    "full vid",
    # message prompts
    "with the message",
    "message me",
    "send me"
    # unlocking
    "unlock",
    "receive it",
    "purchase",
    # tipping
    "under this post",
    "tip",
    # rebill
    "rebills",
    "rebillers",
]

def findTrailerTrigger(oftitle):
    # check regex
    if re.search(dmRegex, oftitle, re.IGNORECASE):
        return True
    # check other regex array
    for trigger in triggerArray:
        triggerRegex = "(?:^|\s)(" + trigger + ")(?:$|\s)"
        if re.search(triggerRegex, oftitle, re.IGNORECASE):
            return True
    return False