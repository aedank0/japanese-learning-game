#!/usr/bin/env python3

from enum import Enum
import sys
from os import listdir
from os.path import isfile, join
import re

class ItemType(Enum):
    none = 0


class Item:
    def __init__(self):
        self.name = ""
        self.description = ""
        self.id = 0

class ItemUse:
    def __init__(self):
        self.ids = {}
        self.location = [-1] #-1 for anywhere
        self.event = -1 #-1 for no event
        self.delItems = True

class Location:
    def __init__(self):
        self.name = ""
        self.description = ""
        self.items = []
        self.exits = []

class Choice:
    def __init__(self):
        self.text = ""
        self.nextEvent = -1

class Event:
    def __init__(self):
        self.text = ""
        self.command = ""
        self.triggered = False
        self.triggerChain = False
        self.choices = []

class SearchLoc:
    def __init__(self):
        self.loc = 0
        self.event = 0
        self.place = ""

playerName = ""
playerItems = []
playerLocation = 0

playerCommands = ["help", "たすけて", "リスト", "見る", "とる", "つかう", "行く", "インベントリ", "さがす", "ドロップ", "セーブ"]
gameCommands = ["echo", "give", "teleport", "mkexit", "cat", "river", "end"]

usages = [
    "\"help\"; same as \"たすけて\".\n",
    "\"たすけて\" to display help message; \"たすけて <command>\" to display command usage.\n",
    "\"リスト\" to list commands.\n",
    "\"見る\" to look at surroundings; \"見る <item>\" to look at an item.",
    "\"とる <item>\" to take an item",
    "\"つかう <item>\" to use item; \"つかう <item> <item>\" to combine two items",
    "\"行く <location>\" to go to a location. Use 見る to see what locations are available.",
    "\"インベントリ\" to display inventory.",
    "\"さがす\" to search location; \"さがす <place>\" to search a specific spot in a location.",
    "\"ドロップ <item>\" drops and item from your inventory.",
    "\"セーブ <name>\" to save and quit the game."
]



locations = []
events = []
itemUses = []
searchables = []
addedExits = []
dropOK = [(2, 21), (3, 19), (6, 18), (7, 22)]

playing = True
devMode = True

def ginput():
    strin = input()
    print()
    return strin

def GetLoc():
    return locations[playerLocation]
def BadArg(args):
    print("Argument parsing error: " + args)

def GetFormatDesc(text, hasEvents):
    text = re.sub("\\\\n", "\n", text)
    text = re.sub("\\\\t", "\t", text)
    text = re.sub("$name$", playerName, text)
    if "$" in text:
        print(text)

    if hasEvents:
        if "??" in text:
            text = text.split("??")
            return text[0], text[1:]
        else:
            return text, []
    else:
        return text

def RunEvent(eid, force = False, parent = -1):
    if parent < 0:
        parent = eid
    def trigger():
        if (events[eid].triggerChain):
            events[parent].triggered = True

    if force or not events[eid].triggered:
        trigger()
        print(GetFormatDesc(events[eid].text, False))
        print()
        if (events[eid].command):
            DoCommand(events[eid].command, True)
        if (len(events[eid].choices) == 0):
            return
        elif (len(events[eid].choices) == 1):
            RunEvent(events[eid].choices[0].nextEvent, True, parent)
        else:
            i = 0
            for choice in events[eid].choices:
                print("  [" + str(i) + "] " + GetFormatDesc(choice.text, False))
                i += 1
            ini = -1
            while not (ini >= 0 and ini <= i):
                print("Please enter your choice. To reprint your choices, enter \"choices\"")
                s = ginput()
                if s == "choices":
                    tmp = 0
                    for choice in events[eid].choices:
                        print("[" + str(tmp) + "] " + events[eid].choice.text)
                        tmp += 1
                else:
                    ini = int(s)

            RunEvent(events[eid].choices[ini].nextEvent, True, parent)

def FindItem(name, inventory):
    i = 0
    for item in inventory:
        if name in item.name:
            break
        i += 1

    return i != len(inventory), i


def UseItem(item):
    for use in itemUses:
        if len(use.ids) == 1 and use.ids[0] == item.id and (use.location[0] == -1 or playerLocation in use.location):
            RunEvent(use.event)
            return use.delItems
    print("すみません、ここでつかいません。")
    return False

def CombineItems(a, b):
    for use in itemUses:
        if len(use.ids) == 2 and use.ids == {a.id, b.id} and (use.location[0] == -1 or playerLocation in use.location):
            RunEvent(use.event)
            return use.delItems
    print("すみません、ここでつかいません。")
    return False

def LookAtLoc(printLoc):
    desc, event = GetFormatDesc(GetLoc().description, True)

    if printLoc:
        print(GetLoc().name + ":")
        print(f"  {desc}\n  Items:")
        for item in GetLoc().items:
            print(f"  >\t{item.name}")
        print("\n  Exits:")
        for iexit in GetLoc().exits:
            print(f"  >\t{locations[iexit].name}")
        for pair in addedExits:
            if playerLocation == pair[0]:
                print(f"  >\t{locations[pair[1]].name}")

    if len(event) > 0:
        for i in event:
            RunEvent(int(i))

    print()

def DoCommand(input, isScript):
    if input.strip() == "":
        print("Please enter a command:")
        return

    words = input.split(maxsplit=1)
    command = words[0]
    if len(words) > 1:
        words = words[1]
        if "\"" in words:
            words = words.split("\"")
        else:
            words = words.split(" ")
    else:
        words = []

    for i, word in enumerate(words):
        words[i] = word.strip()
    while "" in words:
        words.remove("")

    commands = playerCommands
    if (isScript):
        commands = commands + gameCommands
    
    if (not (command in commands)):
        print("Command " + command + "　not found.")
        return

    def checkArg(num):
        if len(words) != num:
            BadArg(f"need {num} arguments")
            return True
        return False
    
    def checkArgs(min, max):
        if len(words) < min or len(words) > max:
            BadArg(f"need between {min} and {max} arguments")
            return True
        return False

    def isgood(good, i):
        if not good:
            print("Item \"" + words[i] + "\" not found")
            return

    if (command == "たすけて" or command == "help"):
        if len(words) == 0:
            print("Help:\nThis is a text based game mostly in Japanese. To do something, enter a command. The commands are also mostly in Japanese, so you'll have to be enter Japanese characters.\nTo see what commands are available, enter \"リスト\". To see how to use each command, use \"たすけて　<command>\".\nTip: you can put english quotes around multiple words to treat them as a single argument.\nTo see this message again, type \"たすけて\".\n")
        else:
            if words[0] in playerCommands:
                print(usages[playerCommands.index(words[0])])
            else:
                BadArg(words[0])
                return
    elif (command == "リスト"):
        print(*commands, sep=", ")
    elif (command == "見る"):
        if len(words) == 0:
            LookAtLoc(True)
        else:
            good, i = FindItem(words[0], playerItems)
            isgood(good, 0)
            if not good:
                return

            print(playerItems[i].name + ":")
            print(GetFormatDesc(playerItems[i].description, False) + "\n")
    elif (command == "とる"):
        if checkArg(1):
            return

        good, i = FindItem(words[0], GetLoc().items)
        isgood(good, 0)
        if not good:
            return

        playerItems.append(GetLoc().items.pop(i))
        print("「" + playerItems[-1].name + "」をとりました。")
    elif (command == "つかう"):
        if checkArgs(1, 2):
            return
        if len(words) == 1:
            good, i = FindItem(words[0], playerItems)
            isgood(good, 0)
            if not good:
                return

            if UseItem(playerItems[i]):
                del playerItems[i]
        else:
            if words[0] in words[1] or words[1] in words[0]:
                print("\"" + words[0] + "\" and \"" + words[1] + "\" are too similar. You can't use an item on itself.")
                return
            
            good, i = FindItem(words[0], playerItems)
            isgood(good, 0)
            if not good:
                return

            good, j = FindItem(words[1], playerItems)
            isgood(good, 1)
            if not good:
                return

            if CombineItems(playerItems[i], playerItems[j]):
                del playerItems[max(i, j)]
                del playerItems[min(i, j)]
    elif (command == "行く"):
        global playerLocation
        if checkArg(1):
            return
        i = -1
        for locI in GetLoc().exits:
            if locI != playerLocation and words[0] in locations[locI].name:
                i = locI
                break
        

        if i == -1:
            for pair in addedExits:
                if pair[0] == playerLocation and pair[1] != playerLocation and words[0] in locations[pair[1]].name:
                    playerLocation = pair[1]
                    LookAtLoc(True)
                    return
            print(f"Location \"{words[0]}\" not found")
        else:
            playerLocation = i
            LookAtLoc(True)
        
        #print(f"「{GetLoc().name}」に来ました")
    elif (command == "インベントリ"):
        print("インベントリ：")
        for item in playerItems:
            print(f">\t{item.name}")
        print()
    elif (command == "さがす"):
        for tmp in searchables:
            if tmp.loc == playerLocation and (tmp.place == "" or tmp.place == words[0]):
                RunEvent(tmp.event)
                return
    elif (command == "ドロップ"):
        good, i = FindItem(words[0], playerItems)

        if not good:
            print("Item not found.")

        for drop in dropOK:
            if playerItems[i].id == drop[0] and playerLocation == drop[1]:
                print(f"Dropped item <{playerItems[i].name}>.")
                GetLoc().items.append(playerItems.pop(i))
                return
        
        print("Cannot drop that here.")
        
    elif command == "セーブ":
        print("Are you sure you want to save? y/n")
        strin = ginput()
        while strin != "y" and strin != "n":
            print("Please enter y or n")
            strin = ginput()
        strin = ""
        while strin == "":
            print("Please enter a save name:")
            strin = ginput()
        WriteSave(strin)
    elif (command == "quit"):
        playing = False
    elif (command == "echo"):
        print(words)
    elif (command == "give"):
        item = Item()
        item.name = words[0]
        item.description = words[1]
        item.id = int(words[2])
        playerItems.append(item)
    elif (command == "teleport"):
        playerLocation = int(words[0])
        LookAtLoc(True)
    elif command == "mkexit":
        addedExits.append((int(words[0]), int(words[1])))
        addedExits.append((int(words[1]), int(words[0])))
    elif command == "cat":
        for i, item in enumerate(playerItems):
            if item.name == "ハンバーガー":
                del playerItems[i]
                print("あなたはねこにハンバーガをあげます。ねこはでました。それから、ねこは来て、あなたにRFIDカードをあげます。そして、ねこは高いオフィスの千かいを見て、出ます。RFIDカードがつかって、あのオフィスに入ることができるともいます。")
                DoCommand("mkexit 10 13", True)
                events[16].triggered = True
                return
        print("ねこはあなたを見て、出ます。")
    elif command == "river":
        def checkItem(loc, id):
            for item in locations[loc].items:
                if item.id == id:
                    return True
            return False
        
        if (checkItem(18, 6) and checkItem(19, 3) and checkItem(21, 2) and checkItem(22, 7)):
            print("新しい家を見ていて、家が古くなります。それから、古い家の前にあなたを見えています。ゆっくりに家にいきます。そして、あなたはゆっくりに家の中にいって、家の下にいきます。あなたはちかてつのえきにいって、ちかてつが右に出ます。右にもういきましたから、左にいきます。それから、ドアがあって、あなたははいります。")
            DoCommand("teleport 24", True)
        else:
            print("新しい家を見ていて、何もしていません。")
    elif command == "end":
        print("Congratulations, you've found the Cat's Eye Brooch and completed the game!")
        WriteSave("completed_autosave")
        print("Game autosaved, enter \"quit\" to exit the game.")
        ins = ""
        while (ins != "quit"):
            ins = ginput()
        sys.exit(0)


def ParseItems(lines, i):
    items = []
    while True:
            itemstart = lines[i].split(" ", 1)
            if "#" == itemstart[0]:
                item = Item()
                item.name = itemstart[1]
                i += 1
                item.description = lines[i]
                i += 1
                item.id = int(lines[i])
                i += 1
                items.append(item)
            else:
                break

    return items, i

def PrintItems(items, f):
    for item in items:
        print("# " + item.name, file=f)
        print(item.description, file=f)
        print(str(item.id), file=f)

def ParseError(lineNum, line):
    print ("Could not parse, error on line " + str(lineNum) + ":\n" + line)

def ParseStory(readItems):
    file = open("story.dat", "r", encoding="utf-8")
    lines = [s.rstrip("\n") for s in file.readlines()]

    lines = [line for line in lines if not "//" in line]

    if lines[0] != "locations {":
        ParseError(0, lines[0])
        return

    end = 0
    for line in lines:
        if "}" == line:
            break
        end += 1

    #Get Locations
    i = 1
    while i < end:
        loc = Location()
        loc.name = lines[i]
        i += 1
        loc.description = lines[i]
        i += 1
        if len(lines[i]) > 0:
            loc.exits = list(map(int, lines[i].split()))
        i += 1

        tmp, i = ParseItems(lines, i)
        if readItems:
            loc.items = tmp

        locations.append(loc)
    
    #Get Events
    if (i != end):
        ParseError(i, lines[i])
        print("'i' not correct")
        return
    i += 1
    if (lines[i] != "events {"):
        ParseError(i, lines[i])
        return
    i += 1

    end = lines.index("}", i)
    while (i < end):
        event = Event()
        event.text = lines[i]
        i += 1

        if lines[i][0] == "?":
            line = lines[i].split(" ", 1)
            event.command = line[1]
            i += 1

        event.triggered = False

        event.triggerChain = lines[i] == "True"
        i += 1
        
        while lines[i][0] == "#":
            choicestart = lines[i].split(" ", 1)
            choice = Choice()
            choice.text = choicestart[1]
            i += 1
            choice.nextEvent = int(lines[i])
            i += 1
            event.choices.append(choice)
        events.append(event)

    #Get item uses
    if (i != end):
        ParseError(i, lines[i])
        print("'i' not correct")
        return
    i += 1
    if (lines[i] != "uses {"):
        ParseError(i, lines[i])
        return
    i += 1

    end = lines.index("}", i)
    while (i < end):
        use = ItemUse()
        use.location = list(map(int, lines[i].split(" ")))
        i += 1
        use.event = int(lines[i])
        i += 1
        use.delItems = lines[i] == "True"
        i += 1
        use.ids = list(map(int, lines[i].split(" ")))
        i += 1

        itemUses.append(use)

    #Get searchables
    if (i != end):
        ParseError(i, lines[i])
        print("'i' not correct")
        return
    i += 1
    if (lines[i] != "searchables {"):
        ParseError(i, lines[i])
        return
    i += 1

    end = lines.index("}", i)
    while (i < end):
        loc = lines[i]
        i += 1
        place = ""
        if (loc.isnumeric()):
            loc = int(loc)
        else:
            stuff = loc.split(" ")
            loc = int(stuff[0])
            place = stuff[1]
        
        search = SearchLoc()
        search.loc = loc
        search.place = place
        search.event = int(lines[i])
        i += 1
        searchables.append(search)
        


    file.close()

def WriteSave(name):
    f = open(name + ".sav", "w+", encoding="utf-8")

    print(playerName, file=f)
    print(str(playerLocation), file=f)
    PrintItems(playerItems, f)

    print("locItems {", file=f)
    for i in range(len(locations)):
        if len(locations[i].items) > 0:
            print(str(i), file=f)
            PrintItems(locations[i].items, f)
    print("}", file=f)
    
    print("triggered {", file=f)
    for i in range(len(events)):
        if events[i].triggered:
            print(str(i), file=f)
    print("}", file=f)

    print("exits {", file=f)
    for pair in addedExits:
        print(f"{pair[0]} {pair[1]}", file=f)
    print("}", file=f)

def ReadSave(name):
    file = open(name + ".sav", encoding="utf-8")
    lines = [s.rstrip("\n") for s in file.readlines()]

    i = 0

    playerName = lines[i]
    i += 1

    playerLocation = int(lines[i])

    playerItems, i = ParseItems(lines, i)

    if lines[i] != "locItems {":
        ParseError(0, lines[0])
        return

    end = i
    for line in lines:
        if "}" == line:
            break
        end += 1

    while i < end:
        iid = int(lines[i])
        i += 1
        locations[iid].items, i = ParseItems(lines, i)

    i += 1

    if lines[i] != "triggered {":
        ParseError(0, lines[0])
        return
    
    end = i
    for line in lines:
        if "}" == line:
            break
        end += 1    

    while i < end:
        eid = int(lines[i])
        i += 1
        events[eid].triggered = True

    if (i != end):
        ParseError(i, lines[i])
        print("'i' not correct")
        return
    i += 1
    if (lines[i] != "exits {"):
        ParseError(i, lines[i])
        return
    i += 1

    end = lines.index("}", i)
    while i < end:
        inl = lines[i].split()
        addedExits.append((inl[0], inl[1]))

    file.close()



#STARTS HERE
print("Welcome!")
strin = ""
b = True
while strin != "new game" and strin != "quit" and b:
    print("Please enter \"new game\", \"load\", or \"quit\"")
    strin = ginput()

    if strin == "quit":
        print("Quitting . . .")
        sys.exit(0)

    if strin == "new game":
        ParseStory(True)
        while True:
            print("Please enter your character's name, or enter nothing for 「あなた」")
            strin = ginput()
            if strin == "":
                strin = "あなた"
            print(f"Is 「{strin}」 correct? y/n")
            strin2 = ginput()
            while strin2 != "y" and strin2 != "n":
                print("Enter y or n")
                strin2 = ginput()
            if strin2 == "y":
                playerName = strin
                break
        DoCommand("teleport 0", True)
        break
    elif strin == "load":
        filenames = [f for f in listdir(".") if isfile(join(".", f))]
        if len(filenames) > 0:
            print("Saves:")
            for save in filenames:
                if ".sav" in save:
                    print("\t" + save.split(".", 1)[0])
        else:
            print("No saves found.")

        while True:
            print("Enter save name; enter \"cancel\" to go back:")
            strin = ginput()
            if strin == "cancel":
                break
                
            try:
                ReadSave(ginput())
            except FileNotFoundError:
                print("File not found")
                continue

            b = False
            break



while playing:
    DoCommand(ginput(), devMode)
