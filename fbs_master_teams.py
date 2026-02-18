"""
FBS Master Team List — Generated from The Odds API /participants endpoint
API call date: February 2026 | Cost: 1 credit
Cross-referenced against Wikipedia "List of NCAA Division I FBS football programs"

136 FBS teams (2025 season) + 2 incoming for 2026 (North Dakota State, Sacramento State) = 138 total

Usage: This list serves as the master reference for:
  1. Populating the FBSMasterTeam table (or Team table with is_fbs flag)
  2. Building TEAM_NAME_MAP for import_games.py (api_name -> short_name)
  3. Building TEAM_CONFERENCES for routes/main.py
  4. Admin team selection UI before each season

Update annually: Check for conference realignment, new FBS transitions, and
verify against /participants endpoint (1 credit).
"""

# Each entry: (short_display_name, odds_api_full_name, odds_api_id, conference, is_2026_incoming)
FBS_MASTER_TEAMS = [
    ("Air Force", "Air Force Falcons", "par_01hqmkr2bze9waa4p2cd9c93wb", "Mountain West", False),
    ("Akron", "Akron Zips", "par_01hqmkr2c0ee7t9ccymz73x0gq", "MAC", False),
    ("Alabama", "Alabama Crimson Tide", "par_01hqmkr2c1e8c8t2rsknszeqxe", "SEC", False),
    ("Appalachian State", "Appalachian State Mountaineers", "par_01hqmkr2c4erzvd8ghcyyrnecb", "Sun Belt", False),
    ("Arizona", "Arizona Wildcats", "par_01hqmkr2c6esfvg010kdn9nf88", "Big 12", False),
    ("Arizona State", "Arizona State Sun Devils", "par_01hqmkr2c5fx4bze4nskp3c5z6", "Big 12", False),
    ("Arkansas", "Arkansas Razorbacks", "par_01hqmkr2c8ej38rtq238ad47zf", "SEC", False),
    ("Arkansas State", "Arkansas State Red Wolves", "par_01hqmkr2c9fd0r8yf37nz6ds6f", "Sun Belt", False),
    ("Army", "Army Black Knights", "par_01hqmkr2caerht3fgbb07m0mke", "American", False),
    ("Auburn", "Auburn Tigers", "par_01hqmkr2cbf0n8g1chgd36xhve", "SEC", False),
    ("BYU", "BYU Cougars", "par_01hqmkr2cdfde99znq0bc5q8wx", "Big 12", False),
    ("Ball State", "Ball State Cardinals", "par_01hqmkr2ceekga6842w12xg325", "MAC", False),
    ("Baylor", "Baylor Bears", "par_01hqmkr2cfe1jv74t5p0r5v2xv", "Big 12", False),
    ("Boise State", "Boise State Broncos", "par_01hqmkr2chfcya2w0tgx1azh4n", "Mountain West", False),
    ("Boston College", "Boston College Eagles", "par_01hqmkr2cjevbv90gt5bs4y9a2", "ACC", False),
    ("Bowling Green", "Bowling Green Falcons", "par_01hqmkr2ckex0vc4kb1hegwrrb", "MAC", False),
    ("Buffalo", "Buffalo Bulls", "par_01hqmkr2cpe4nsepap11jqmgw9", "MAC", False),
    ("California", "California Golden Bears", "par_01hqmkr2csfgm8f80c352qhard", "ACC", False),
    ("Central Michigan", "Central Michigan Chippewas", "par_01hqmkr2cwfg5abn1nn66dafxe", "MAC", False),
    ("Charlotte", "Charlotte 49ers", "par_01hqmkr2cye7mr9xvcg8qztsce", "American", False),
    ("Cincinnati", "Cincinnati Bearcats", "par_01hqmkr2d0f4abxrt2xt4w280h", "Big 12", False),
    ("Clemson", "Clemson Tigers", "par_01hqmkr2d2fcnaynkrvhm371ve", "ACC", False),
    ("Coastal Carolina", "Coastal Carolina Chanticleers", "par_01hqmkr2d3etysw7j5tpj0asyg", "Sun Belt", False),
    ("Colorado", "Colorado Buffaloes", "par_01hqmkr2d5etwsffw4mexxmfkx", "Big 12", False),
    ("Colorado State", "Colorado State Rams", "par_01hqmkr2d6fbga7wnz6exjc105", "Mountain West", False),
    ("Delaware", "Delaware Blue Hens", "par_01hqmkr2dbeqy9b03q4mfvbvtq", "CUSA", False),
    ("Duke", "Duke Blue Devils", "par_01hqmkr2dfew5v52gvwc7s1gye", "ACC", False),
    ("East Carolina", "East Carolina Pirates", "par_01hqmkr2dgfhkb1jg6rm1a93b1", "American", False),
    ("Eastern Michigan", "Eastern Michigan Eagles", "par_01hqmkr2dkfeeta800nd6z84w5", "MAC", False),
    ("FIU", "Florida International Panthers", "par_01hqmkr2dse5493v5fdhwhzz9p", "CUSA", False),
    ("Florida", "Florida Gators", "par_01hqmkr2drebetw7r2b9tfw68e", "SEC", False),
    ("Florida Atlantic", "Florida Atlantic Owls", "par_01hqmkr2dqf6g91ztm242pvzxs", "American", False),
    ("Florida State", "Florida State Seminoles", "par_01hqmkr2dtfmh82gmjkbn6r8d6", "ACC", False),
    ("Fresno State", "Fresno State Bulldogs", "par_01hqmkr2dwf4kasz5jvn0fs6ra", "Mountain West", False),
    ("Georgia", "Georgia Bulldogs", "par_01hqmkr2e0fdnsz5qjew534wzk", "SEC", False),
    ("Georgia Southern", "Georgia Southern Eagles", "par_01hqmkr2e1ffhr0m9r3vzjbjy0", "Sun Belt", False),
    ("Georgia State", "Georgia State Panthers", "par_01hqmkr2e2fbzsjjy474ewkjpb", "Sun Belt", False),
    ("Georgia Tech", "Georgia Tech Yellow Jackets", "par_01hqmkr2e3f3n8g4gmy8pep3g8", "ACC", False),
    ("Hawaii", "Hawaii Rainbow Warriors", "par_01hqmkr2e7e5a91h224g38aq9t", "Mountain West", False),
    ("Houston", "Houston Cougars", "par_01hqmkr2eafjc8fyjt3nc46jm6", "Big 12", False),
    ("Illinois", "Illinois Fighting Illini", "par_01hqmkr2eee76vxcwh2mf75zzx", "Big Ten", False),
    ("Indiana", "Indiana Hoosiers", "par_01hqmkr2ehfd4bpnzmpm1ygq6p", "Big Ten", False),
    ("Iowa", "Iowa Hawkeyes", "par_01hqmkr2ekfzhv5g5h9dnnvx73", "Big Ten", False),
    ("Iowa State", "Iowa State Cyclones", "par_01hqmkr2emes5vxzykx0a0e99m", "Big 12", False),
    ("Jacksonville State", "Jacksonville State Gamecocks", "par_01hqmkr2epecz9x8jt8fz9qj2a", "CUSA", False),
    ("James Madison", "James Madison Dukes", "par_01hqmkr2eqf848wxa2trbq4qry", "Sun Belt", False),
    ("Kansas", "Kansas Jayhawks", "par_01hqmkr2ese0mb62xv3znvs752", "Big 12", False),
    ("Kansas State", "Kansas State Wildcats", "par_01hqmkr2etftfsmwpa3s87tmex", "Big 12", False),
    ("Kennesaw State", "Kennesaw State Owls", "par_01hqmkr2eve1e9mhwph4jh3r63", "CUSA", False),
    ("Kent State", "Kent State Golden Flashes", "par_01hqmkr2ewfhdrsbemcmskb2n0", "MAC", False),
    ("Kentucky", "Kentucky Wildcats", "par_01hqmkr2eyew3t5xv5afre6s8r", "SEC", False),
    ("LSU", "LSU Tigers", "par_01hqmkr2f0etjr70y0vrjjrcdx", "SEC", False),
    ("Liberty", "Liberty Flames", "par_01hqmkr2f4efktw3c1xrkmzw0h", "CUSA", False),
    ("Louisiana Tech", "Louisiana Tech Bulldogs", "par_01hqmkr2f7ey7rvpa8hszjqs8d", "CUSA", False),
    ("Louisiana-Lafayette", "Louisiana Ragin Cajuns", "par_01hqmkr2f6fyxbqqjpngmae1qn", "Sun Belt", False),
    ("Louisville", "Louisville Cardinals", "par_01hqmkr2f8fdcahme30st5637r", "ACC", False),
    ("Marshall", "Marshall Thundering Herd", "par_01hqmkr2fbfcevjpy984k1y1hx", "Sun Belt", False),
    ("Maryland", "Maryland Terrapins", "par_01hqmkr2fce9wsn7qcnftpv68f", "Big Ten", False),
    ("Memphis", "Memphis Tigers", "par_01hqmkr2fee3rv7s3774b7w5d4", "American", False),
    ("Miami", "Miami Hurricanes", "par_01hqmkr2fjfhzb1344050dr84y", "ACC", False),
    ("Miami (OH)", "Miami (OH) RedHawks", "par_01hqmkr2fhe0jvdah7p7q02sr5", "MAC", False),
    ("Michigan", "Michigan Wolverines", "par_01hqmkr2fmf8h9avy0nd5zgjrf", "Big Ten", False),
    ("Michigan State", "Michigan State Spartans", "par_01hqmkr2fkejfvybbs6p8a87dy", "Big Ten", False),
    ("Middle Tennessee", "Middle Tennessee Blue Raiders", "par_01hqmkr2fnev9rp66k21jxh2e0", "CUSA", False),
    ("Minnesota", "Minnesota Golden Gophers", "par_01hqmkr2fpfrs91wegchm2r67z", "Big Ten", False),
    ("Mississippi State", "Mississippi State Bulldogs", "par_01hqmkr2fqf22bhnwmdhd2kjn8", "SEC", False),
    ("Missouri", "Missouri Tigers", "par_01hqmkr2ftf7ct4q4bfphcqc6g", "SEC", False),
    ("Missouri State", "Missouri State Bears", "par_01hqmkr2fsf1m96j5v7yymj6ns", "CUSA", False),
    ("NC State", "NC State Wolfpack", "par_01hqmkr2g1f4q9v66kkva1962s", "ACC", False),
    ("Navy", "Navy Midshipmen", "par_01hqmkr2g2eygsv3p1t3p53h2z", "American", False),
    ("Nebraska", "Nebraska Cornhuskers", "par_01hqmkr2g3evyvxb2wp1p1zwhv", "Big Ten", False),
    ("Nevada", "Nevada Wolf Pack", "par_01hqmkr2g4fg0vhx9fyv2jx6yd", "Mountain West", False),
    ("New Mexico", "New Mexico Lobos", "par_01hqmkr2g6en3av2hyczzpmdvh", "Mountain West", False),
    ("New Mexico State", "New Mexico State Aggies", "par_01hqmkr2g7fvw8ks932hwvefxk", "CUSA", False),
    ("North Carolina", "North Carolina Tar Heels", "par_01hqmkr2gcf1v8stp0x42t01vd", "ACC", False),
    ("North Dakota State", "North Dakota State Bison", "par_01hqmkr2geeqfrhzdh7jk1303e", "Mountain West", True),
    ("North Texas", "North Texas Mean Green", "par_01hqmkr2gfenxvr1ebc7enc6w0", "American", False),
    ("Northern Illinois", "Northern Illinois Huskies", "par_01hqmkr2gjf94ra4nsj18kmfwx", "MAC", False),
    ("Northwestern", "Northwestern Wildcats", "par_01hqmkr2gneqrb6749sc5q47t5", "Big Ten", False),
    ("Notre Dame", "Notre Dame Fighting Irish", "par_01hqmkr2gpfcvsjkmz4mh3qnsh", "Independent", False),
    ("Ohio", "Ohio Bobcats", "par_01hqmkr2gqfe1brkcakx2w2hs2", "MAC", False),
    ("Ohio State", "Ohio State Buckeyes", "par_01hqmkr2grex7ahyqjr06nfcpr", "Big Ten", False),
    ("Oklahoma", "Oklahoma Sooners", "par_01hqmkr2gsezragwjgzkvhabs7", "SEC", False),
    ("Oklahoma State", "Oklahoma State Cowboys", "par_01hqmkr2gtfvy8rjbktr154ft7", "Big 12", False),
    ("Old Dominion", "Old Dominion Monarchs", "par_01hqmkr2gven2trj27t9zwdnkt", "Sun Belt", False),
    ("Ole Miss", "Ole Miss Rebels", "par_01hqmkr2gwezts6hdfddx5nwjk", "SEC", False),
    ("Oregon", "Oregon Ducks", "par_01hqmkr2gxfzaa8j81pf7vb2yr", "Big Ten", False),
    ("Oregon State", "Oregon State Beavers", "par_01hqmkr2gyem0a082a78a8dq9v", "Pac-12", False),
    ("Penn State", "Penn State Nittany Lions", "par_01hqmkr2gzf4bs5cr8h1xc3xk7", "Big Ten", False),
    ("Pittsburgh", "Pittsburgh Panthers", "par_01hqmkr2h1e41br4sbx376bxhs", "ACC", False),
    ("Purdue", "Purdue Boilermakers", "par_01hqmkr2h6frbax6pmzk8fwypn", "Big Ten", False),
    ("Rice", "Rice Owls", "par_01hqmkr2h8f1b9d8wdfns0tqc3", "American", False),
    ("Rutgers", "Rutgers Scarlet Knights", "par_01hqmkr2hbfz2bfswh49pdx03h", "Big Ten", False),
    ("SMU", "SMU Mustangs", "par_01hqmkr2hcfqpstbw33a07k18b", "ACC", False),
    ("Sacramento State", "Sacramento State Hornets", "par_01hqmkr2hdem3sz28v5dds05te", "Pac-12", True),
    ("Sam Houston", "Sam Houston State Bearkats", "par_01hqmkr2hffpdrjxadkz42ppw5", "CUSA", False),
    ("San Diego State", "San Diego State Aztecs", "par_01hqmkr2hhehdttrcgv6ekzszd", "Mountain West", False),
    ("San Jose State", "San Jose State Spartans", "par_01hqmkr2hkfmzsf7mhhg5gb33d", "Mountain West", False),
    ("South Alabama", "South Alabama Jaguars", "par_01hqmkr2hnfdxsb91dzrmwfvyr", "Sun Belt", False),
    ("South Carolina", "South Carolina Gamecocks", "par_01hqmkr2hpfvxsygyfnkpd0pq9", "SEC", False),
    ("South Florida", "South Florida Bulls", "par_01hqmkr2htf91rm9jvn57cwsqq", "American", False),
    ("Southern Miss", "Southern Mississippi Golden Eagles", "par_01hqmkr2hyf3tbzganmmz9kby9", "Sun Belt", False),
    ("Stanford", "Stanford Cardinal", "par_01hqmkr2j2fjety117cwkwer04", "ACC", False),
    ("Syracuse", "Syracuse Orange", "par_01hqmkr2j5fbdagnja04bx3byc", "ACC", False),
    ("TCU", "TCU Horned Frogs", "par_01hqmkr2j6emwv9nr4ycvjcnbs", "Big 12", False),
    ("Temple", "Temple Owls", "par_01hqmkr2j7f6jrf5emg1y09s6p", "American", False),
    ("Tennessee", "Tennessee Volunteers", "par_01hqmkr2jae6na0v519gjm9q9b", "SEC", False),
    ("Texas", "Texas Longhorns", "par_01hqmkr2jde19td0j9ksjv0z5k", "SEC", False),
    ("Texas A&M", "Texas A&M Aggies", "par_01hqmkr2jbfwmsgbbzss4f4rrp", "SEC", False),
    ("Texas State", "Texas State Bobcats", "par_01hqmkr2jffzzv7d4tphyftx7e", "Sun Belt", False),
    ("Texas Tech", "Texas Tech Red Raiders", "par_01hqmkr2jgepz9bx1bcjka55m1", "Big 12", False),
    ("Toledo", "Toledo Rockets", "par_01hqmkr2jhe00vnd66demmm6k1", "MAC", False),
    ("Troy", "Troy Trojans", "par_01hqmkr2jketn9e8k27nk1b4p5", "Sun Belt", False),
    ("Tulane", "Tulane Green Wave", "par_01hqmkr2jmewztzg73x4a39530", "American", False),
    ("Tulsa", "Tulsa Golden Hurricane", "par_01hqmkr2jnfqwv2tjchpa01bzv", "American", False),
    ("UAB", "UAB Blazers", "par_01hqmkr2jpea1a5k0hpwc9qngq", "American", False),
    ("UCF", "UCF Knights", "par_01hqmkr2jrfvg8ceexct1sbkgx", "Big 12", False),
    ("UCLA", "UCLA Bruins", "par_01hqmkr2jsed1rvjdy2bxzz0sd", "Big Ten", False),
    ("UConn", "UConn Huskies", "par_01hqmkr2jteyp94q873hs7xd4b", "Independent", False),
    ("UL Monroe", "UL Monroe Warhawks", "par_01hqmkr2jveaesysqemde06nep", "Sun Belt", False),
    ("UMass", "UMass Minutemen", "par_01hqmkr2jwemesyt4amdtgq2wb", "MAC", False),
    ("UNLV", "UNLV Rebels", "par_01hqmkr2jxem0rdgyfbckwa611", "Mountain West", False),
    ("USC", "USC Trojans", "par_01hqmkr2jyf0xb3g282ddm9gjn", "Big Ten", False),
    ("UTEP", "UTEP Miners", "par_01hqmkr2k0fjxv6cjwb9j6dpds", "CUSA", False),
    ("UTSA", "UTSA Roadrunners", "par_01hqmkr2k1fnwtfm0hcaxm928z", "American", False),
    ("Utah", "Utah Utes", "par_01hqmkr2k4e6mrb4f7kj54rcd2", "Big 12", False),
    ("Utah State", "Utah State Aggies", "par_01hqmkr2k2frts2aqztas39w6d", "Mountain West", False),
    ("Vanderbilt", "Vanderbilt Commodores", "par_01hqmkr2k7f8ksrb7fqw7g81g9", "SEC", False),
    ("Virginia", "Virginia Cavaliers", "par_01hqmkr2k9edpbevdc3fgmd6n7", "ACC", False),
    ("Virginia Tech", "Virginia Tech Hokies", "par_01hqmkr2kafdt8mg973a6kztm3", "ACC", False),
    ("Wake Forest", "Wake Forest Demon Deacons", "par_01hqmkr2kcem6vr8c4h9608c8b", "ACC", False),
    ("Washington", "Washington Huskies", "par_01hqmkr2kdeeyv02ttcappmas9", "Big Ten", False),
    ("Washington State", "Washington State Cougars", "par_01hqmkr2kee6c9venjvfcbaqxr", "Pac-12", False),
    ("West Virginia", "West Virginia Mountaineers", "par_01hqmkr2kffbtbwtyr0arxv9qq", "Big 12", False),
    ("Western Kentucky", "Western Kentucky Hilltoppers", "par_01hqmkr2kjeegvcye6rygdrtzk", "CUSA", False),
    ("Western Michigan", "Western Michigan Broncos", "par_01hqmkr2kkf5bsvp0ek56ky1ts", "MAC", False),
    ("Wisconsin", "Wisconsin Badgers", "par_01hqmkr2kpf148kx5sra1set9r", "Big Ten", False),
    ("Wyoming", "Wyoming Cowboys", "par_01hqmkr2kre0vvjx5e3anbs2dg", "Mountain West", False),
]

# Total: 138 teams
# FBS 2025: 136 teams
# Incoming 2026: 2 teams

# Convenience dicts (generated from FBS_MASTER_TEAMS)
# Maps API long name -> short display name (replaces hardcoded TEAM_NAME_MAP)
TEAM_NAME_MAP = {api_name: short for short, api_name, _, _, _ in FBS_MASTER_TEAMS}

# Maps short display name -> conference (replaces hardcoded TEAM_CONFERENCES)
TEAM_CONFERENCES = {short: conf for short, _, _, conf, _ in FBS_MASTER_TEAMS}

# Maps short display name -> API long name (for reverse lookups)
SHORT_TO_API = {short: api_name for short, api_name, _, _, _ in FBS_MASTER_TEAMS}
