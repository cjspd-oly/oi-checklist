import sqlite3

fields = ["name", "number", "source", "year", "link"]

raw_problems = [
    ## NOI

    # 2007
    ("Gift", 1, "NOIFINAL", 2007, "https://codebreaker.xyz/problem/gift"),
    
    # 2008
    ("Prime", 1, "NOIFINAL", 2008, "https://codebreaker.xyz/problem/nprime"),
    ("LVM", 2, "NOIFINAL", 2008, "https://codebreaker.xyz/problem/lvm"),
    ("Gecko", 3, "NOIFINAL", 2008, "https://codebreaker.xyz/problem/gecko"),
    ("4sum", 4, "NOIFINAL", 2008, "https://codebreaker.xyz/problem/4sum"),
    ("Rank", 5, "NOIFINAL", 2008, "https://codebreaker.xyz/problem/rank"),
    
    # 2009
    ("Xmas", 1, "NOIFINAL", 2009, "https://codebreaker.xyz/problem/xmas"),
    
    # 2010 Selection Test
    ("Chess Islands", 1, "NOIPRELIM", 2010, "https://codebreaker.xyz/problem/chessislands"),
    ("Triangle Sum", 2, "NOIPRELIM", 2010, "https://codebreaker.xyz/problem/trianglesum"),
    # 2010 Finals
    ("Card", 3, "NOIFINAL", 2010, "https://codebreaker.xyz/problem/card"),
    
    # 2011
    ("Change", 1, "NOIFINAL", 2011, "https://codebreaker.xyz/problem/change"),
    ("Paint", 2, "NOIFINAL", 2011, "https://codebreaker.xyz/problem/paint"),
    ("Tour", 3, "NOIFINAL", 2011, "https://codebreaker.xyz/problem/tour"),
    
    # 2012
    ("Mod Sum", 1, "NOIFINAL", 2012, "https://oj.uz/problem/view/NOI12_modsum"),
    ("Pancake", 2, "NOIFINAL", 2012, "https://oj.uz/problem/view/NOI12_pancake"),
    ("Forensic", 3, "NOIFINAL", 2012, "https://oj.uz/problem/view/NOI12_forensic"),
    ("Walking", 4, "NOIFINAL", 2012, "https://oj.uz/problem/view/NOI12_walking"),
    
    # 2013
    ("Global Warming", 1, "NOIFINAL", 2013, "https://oj.uz/problem/view/NOI13_gw"),
    ("Trucking Diesel", 2, "NOIFINAL", 2013, "https://codebreaker.xyz/problem/diesel"),
    ("Ferries", 3, "NOIFINAL", 2013, "https://oj.uz/problem/view/NOI13_ferries"),
    
    # 2014
    ("Orchard", 1, "NOIFINAL", 2014, "https://oj.uz/problem/view/NOI14_orchard"),
    ("Sightseeing", 2, "NOIFINAL", 2014, "https://oj.uz/problem/view/NOI14_sightseeing"),
    ("CATS", 3, "NOIFINAL", 2014, "https://oj.uz/problem/view/NOI14_cats"),
    ("OBELISK", 4, "NOIFINAL", 2014, "https://oj.uz/problem/view/NOI14_obelisk"),
    
    # 2015
    ("Ask One Get One Free", 1, "NOIFINAL", 2015, "https://codebreaker.xyz/problem/askonegetonefree"),
    ("Sudoku", 2, "NOIFINAL", 2015, "https://codebreaker.xyz/problem/sudoku"),
    ("Radioactive", 3, "NOIFINAL", 2015, "https://codebreaker.xyz/problem/radioactive"),
    ("Banana Farm", 4, "NOIFINAL", 2015, "https://codebreaker.xyz/problem/bananafarm"),
    
    # 2017
    ("Best Place", 1, "NOIFINAL", 2017, "https://oj.uz/problem/view/NOI17_bestplace"),
    ("Roadside Advertisements", 2, "NOIFINAL", 2017, "https://oj.uz/problem/view/NOI17_roadsideadverts"),
    ("Hotspot", 3, "NOIFINAL", 2017, "https://oj.uz/problem/view/NOI17_hotspot"),
    ("RMQ", 4, "NOIFINAL", 2017, "https://oj.uz/problem/view/NOI17_rmq"),
    ("I want to be the very best too!", 5, "NOIFINAL", 2017, "https://oj.uz/problem/view/NOI17_pokemonmaster"),

    # 2018 Preliminary
    ("Snail", 1, "NOIPRELIM", 2018, "https://oj.uz/problem/view/NOI18_snail"),
    ("Knapsack", 2, "NOIPRELIM", 2018, "https://oj.uz/problem/view/NOI18_knapsack"),
    ("Island", 3, "NOIPRELIM", 2018, "https://oj.uz/problem/view/NOI18_island"),
    # 2018 Finals
    ("Collecting Mushrooms", 1, "NOIFINAL", 2018, "https://oj.uz/problem/view/NOI18_collectmushrooms"),
    ("Journey", 2, "NOIFINAL", 2018, "https://oj.uz/problem/view/NOI18_journey"),
    ("Lightning Rod", 3, "NOIFINAL", 2018, "https://oj.uz/problem/view/NOI18_lightningrod"),
    ("City Mapping", 4, "NOIFINAL", 2018, "https://oj.uz/problem/view/NOI18_citymapping"),
    ("Safety", 5, "NOIFINAL", 2018, "https://oj.uz/problem/view/NOI18_safety"),

    # 2019 Preliminary
    ("Palindromic FizzBuzz", 1, "NOIPRELIM", 2019, "https://oj.uz/problem/view/NOI19_palindrome"),
    ("Lost Array", 2, "NOIPRELIM", 2019, "https://oj.uz/problem/view/NOI19_lostarray"),
    ("Experimental Charges", 3, "NOIPRELIM", 2019, "https://oj.uz/problem/view/NOI19_charges"),
    ("Square or Rectangle?", 4, "NOIPRELIM", 2019, "https://oj.uz/problem/view/NOI19_squarerect"),
    # 2019 Finals
    ("Pilot", 1, "NOIFINAL", 2019, "https://oj.uz/problem/view/NOI19_pilot"),
    ("Lasers", 2, "NOIFINAL", 2019, "https://oj.uz/problem/view/NOI19_lasers"),
    ("Feast", 3, "NOIFINAL", 2019, "https://oj.uz/problem/view/NOI19_feast"),
    ("Rigged Roads", 4, "NOIFINAL", 2019, "https://oj.uz/problem/view/NOI19_riggedroads"),
    ("Shuffle", 5, "NOIFINAL", 2019, "https://oj.uz/problem/view/NOI19_shuffle"),

    # 2020 Preliminary
    ("Mountains", 1, "NOIPRELIM", 2020, "https://oj.uz/problem/view/NOI20_mountains"),
    ("Visiting Singapore", 2, "NOIPRELIM", 2020, "https://oj.uz/problem/view/NOI20_visitingsingapore"),
    ("Solar Storm", 3, "NOIPRELIM", 2020, "https://oj.uz/problem/view/NOI20_solarstorm"),

    # 2020 Finals
    ("Labels", 1, "NOIFINAL", 2020, "https://oj.uz/problem/view/NOI20_labels"),
    ("Discharging", 2, "NOIFINAL", 2020, "https://oj.uz/problem/view/NOI20_discharging"),
    ("Progression", 3, "NOIFINAL", 2020, "https://oj.uz/problem/view/NOI20_progression"),
    ("Arcade", 4, "NOIFINAL", 2020, "https://oj.uz/problem/view/NOI20_arcade"),
    ("Aesthetic", 5, "NOIFINAL", 2020, "https://oj.uz/problem/view/NOI20_aesthetic"),

    # 2020 Qualification
    ("Cryptography", 1, "NOIQUAL", 2020, "https://oj.uz/problem/view/NOI20_crypto"),
    ("Fuel Station", 2, "NOIQUAL", 2020, "https://oj.uz/problem/view/NOI20_fuelstation"),
    ("Relay Marathon", 3, "NOIQUAL", 2020, "https://oj.uz/problem/view/NOI20_relaymarathon"),
    ("Firefighting", 4, "NOIQUAL", 2020, "https://oj.uz/problem/view/NOI20_firefighting"),

    # 2021 Finals
    ("Fraud", 1, "NOIFINAL", 2021, "https://codebreaker.xyz/problem/fraud"),
    ("Archaeologist", 2, "NOIFINAL", 2021, "https://codebreaker.xyz/problem/archaeologist"),
    ("Password", 3, "NOIFINAL", 2021, "https://codebreaker.xyz/problem/password"),
    ("Tiles", 4, "NOIFINAL", 2021, "https://codebreaker.xyz/problem/tiles"),
    ("Pond", 5, "NOIFINAL", 2021, "https://codebreaker.xyz/problem/pond"),

    # 2021 Qualification
    ("Competition", 1, "NOIQUAL", 2021, "https://codebreaker.xyz/problem/competition"),
    ("Departure", 2, "NOIQUAL", 2021, "https://codebreaker.xyz/problem/departure"),
    ("Truck", 3, "NOIQUAL", 2021, "https://codebreaker.xyz/problem/truck"),

    # 2022 Finals
    ("Voting City", 1, "NOIFINAL", 2022, "https://oj.uz/problem/view/NOI22_votingcity"),
    ("Gym Badges", 2, "NOIFINAL", 2022, "https://oj.uz/problem/view/NOI22_gymbadges"),
    ("Towers", 3, "NOIFINAL", 2022, "https://oj.uz/problem/view/NOI22_towers"),
    ("Grapevine", 4, "NOIFINAL", 2022, "https://oj.uz/problem/view/NOI22_grapevine"),
    ("Fruits", 5, "NOIFINAL", 2022, "https://oj.uz/problem/view/NOI22_fruits"),

    # 2022 Qualification
    ("L-Board", 1, "NOIQUAL", 2022, "https://codebreaker.xyz/problem/lboard"),
    ("Tree Cutting", 2, "NOIQUAL", 2022, "https://codebreaker.xyz/problem/treecutting"),
    ("Dragonfly", 3, "NOIQUAL", 2022, "https://codebreaker.xyz/problem/dragonfly"),

    # 2023 Qualification
    ("Area", 1, "NOIQUAL", 2023, "https://codebreaker.xyz/problem/area_noi"),
    ("Swords", 2, "NOIQUAL", 2023, "https://codebreaker.xyz/problem/swords"),
    ("Dolls", 3, "NOIQUAL", 2023, "https://codebreaker.xyz/problem/doll_noi"),
    ("Burgers", 4, "NOIQUAL", 2023, "https://codebreaker.xyz/problem/burgers"),
    ("Network", 5, "NOIQUAL", 2023, "https://codebreaker.xyz/problem/network"),

    # 2023 Finals
    ("Topical", 1, "NOIFINAL", 2023, "https://oj.uz/problem/view/NOI23_topical"),
    ("Inspections", 2, "NOIFINAL", 2023, "https://oj.uz/problem/view/NOI23_inspections"),
    ("Airplane", 3, "NOIFINAL", 2023, "https://oj.uz/problem/view/NOI23_airplane"),
    ("Curtains", 4, "NOIFINAL", 2023, "https://oj.uz/problem/view/NOI23_curtains"),
    ("Toxic Gene", 5, "NOIFINAL", 2023, "https://oj.uz/problem/view/NOI23_toxic"),

    # 2024 Finals
    ("Problem Setter", 1, "NOIFINAL", 2024, "https://codebreaker.xyz/problem/problemsetter"),
    ("Shops", 2, "NOIFINAL", 2024, "https://codebreaker.xyz/problem/shops"),
    ("Toxic Gene 2", 3, "NOIFINAL", 2024, "https://codebreaker.xyz/problem/toxic2"),
    ("Coins", 4, "NOIFINAL", 2024, "https://codebreaker.xyz/problem/coin"),
    ("Field", 5, "NOIFINAL", 2024, "https://codebreaker.xyz/problem/field"),

    # 2024 Qualification
    ("Tourist", 1, "NOIQUAL", 2024, "https://codebreaker.xyz/problem/tourist_noi"),
    ("Party", 2, "NOIQUAL", 2024, "https://codebreaker.xyz/problem/party_noi"),
    ("School Photo", 3, "NOIQUAL", 2024, "https://codebreaker.xyz/problem/photo"),
    ("Amusement Park", 4, "NOIQUAL", 2024, "https://codebreaker.xyz/problem/park"),
    ("Explosives", 5, "NOIQUAL", 2024, "https://codebreaker.xyz/problem/explosives"),

    ## JOISC
    # 2019
    ("Examination", 1, "JOISC", 2019, "https://oj.uz/problem/view/JOI19_examination"),
    ("Naan", 2, "JOISC", 2019, "https://oj.uz/problem/view/JOI19_naan"),
    ("Meetings", 3, "JOISC", 2019, "https://oj.uz/problem/view/JOI19_meetings"),
    ("Two Antennas", 4, "JOISC", 2019, "https://oj.uz/problem/view/JOI19_antennas"),
    ("Two Dishes", 5, "JOISC", 2019, "https://oj.uz/problem/view/JOI19_dishes"),
    ("Two Transportations", 6, "JOISC", 2019, "https://oj.uz/problem/view/JOI19_transportations"),

    ## APIO
    # 2014
    ("Palindrome", 1, "APIO", 2014, "https://oj.uz/problem/view/APIO14_palindrome"),
    ("Sequence", 2, "APIO", 2014, "https://oj.uz/problem/view/APIO14_sequence"),
    ("Beads", 3, "APIO", 2014, "https://oj.uz/problem/view/APIO14_beads"),

    # 2019
    ("Strange Device", 1, "APIO", 2019, "https://oj.uz/problem/view/APIO19_strange_device"),
    ("Bridges", 2, "APIO", 2019, "https://oj.uz/problem/view/APIO19_bridges"),
    ("Street Lamps", 3, "APIO", 2019, "https://oj.uz/problem/view/APIO19_street_lamps"),

    # 2024
    ("September", 1, "APIO", 2024, "https://oj.uz/problem/view/APIO24_september"),
    ("Train", 2, "APIO", 2024, "https://oj.uz/problem/view/APIO24_train"),
    ("Magic Show", 3, "APIO", 2024, "https://oj.uz/problem/view/APIO24_show")
]

problems = [dict(zip(fields, p)) for p in raw_problems]

conn = sqlite3.connect('database.db')
cur = conn.cursor()

# Optional: clear existing problems
cur.execute("DELETE FROM problems")

for p in problems:
    cur.execute('''
        INSERT INTO problems (name, number, source, year, link)
        VALUES (?, ?, ?, ?, ?)
    ''', (p["name"], p["number"], p["source"], p["year"], p["link"]))

conn.commit()
conn.close()
