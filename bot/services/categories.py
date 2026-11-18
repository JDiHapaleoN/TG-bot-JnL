"""Expense and income categories catalog, store/brand recognition, and payment method detection."""

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class CategoryInfo:
    code: str
    tx_type: str  # 'expense' | 'income'
    icon: str
    name_ru: str
    name_en: str
    keywords: Tuple[str, ...]
    name_de: str = ""


CATEGORIES: Dict[str, CategoryInfo] = {
    # Expense categories
    "groceries": CategoryInfo(
        code="groceries",
        tx_type="expense",
        icon="🛒",
        name_ru="Продукты",
        name_en="Groceries",
        name_de="Lebensmittel",
        keywords=(
            # German & European supermarkets / discounters
            "rewe", "aldi", "aldi süd", "aldi nord", "lidl", "netto", "penny",
            "edeka", "kaufland", "norma", "globus", "tegut", "hit", "real",
            "nahkauf", "marktkauf", "famila", "combi", "np-markt", "np markt",
            "mix markt", "mixmarkt", "alnatura", "denns", "biomarkt", "vitalia",
            "spar", "eurospar", "interspar", "billa", "hofer", "adeg", "mpreis",
            "migros", "coop", "denner", "volg", "carrefour", "auchan", "leclerc",
            "intermarche", "monoprix", "franprix", "picard", "tesco", "sainsbury",
            "asda", "morrisons", "waitrose", "marks & spencer", "walmart",
            "costco", "target", "whole foods", "trader joe", "kroger", "safeway",
            "biedronka", "zabka", "żabka", "dino", "lewiatan", "stokrotka",
            "albert heijn", "jumbo", "dirk", "mercadona", "eroski", "conad",
            "esselunga", "coopitalia", "trinkgut", "getränkemarkt", "getrankemarkt",
            "flaschenpost", "picnic", "gorillas", "flink", "knuspr",
            # CIS / Central Asia supermarkets
            "korzinka", "корзинка", "makro", "макро", "havas", "хавас", "baraka",
            "барака", "andalus", "bi1", "magnum", "магнум", "small", "смолл",
            "пятерочка", "пятёрочка", "магнит", "перекресток", "перекрёсток",
            "вкусвилл", "ашан", "лента", "дикси", "метро кэш", "окей", "азбука вкуса",
            "глобус гурмэ", "чижик", "светофор", "самокат", "яндекс лавка", "лавка",
            "евроопт", "соседи", "атб", "сильпо", "сільпо", "фора", "новус", "novus",
            # General grocery & food items (RU / EN / DE)
            "продукты", "супермаркет", "гастроном", "универсам", "базар", "рынок",
            "овощной", "мясной", "пекарня", "булочная", "хлеб", "молоко", "кефир",
            "сыр", "творог", "масло", "яйца", "мясо", "курица", "говядина", "рыба",
            "колбаса", "фрукты", "овощи", "яблоки", "бананы", "картошка", "томаты",
            "вода", "сок", "напитки", "сладости", "шоколад", "крупа", "макароны",
            "мука", "сахар", "соль", "специи",
            "groceries", "supermarket", "grocery", "market", "bakery", "butcher",
            "bread", "milk", "cheese", "meat", "chicken", "beef", "fish", "fruit",
            "fruits", "vegetables", "veggies", "water", "drinks", "snacks",
            "lebensmittel", "supermarkt", "wocheneinkauf", "lebensmitteleinkauf",
            "bäckerei", "backerei", "bäcker", "backer", "kamps", "backwerk",
            "back-factory", "backfactory", "metzgerei", "metzger", "fleischer",
            "obst", "gemüse", "gemuse", "brot", "brötchen", "brotchen", "milch",
            "käse", "kase", "fleisch", "wurst", "wasser", "getränke", "getranke",
            "späti", "spati", "spätkauf", "kiosk",
        ),
    ),
    "shopping": CategoryInfo(
        code="shopping",
        tx_type="expense",
        icon="🛍",
        name_ru="Покупки",
        name_en="Shopping",
        name_de="Einkaufen",
        keywords=(
            # Electronics, home & DIY stores (including common typos like mediamrkt)
            "ikea", "mediamarkt", "mediamrkt", "media markt", "media-markt",
            "saturn", "medimax", "expert", "euronics", "cyberport", "notebooksbilliger",
            "alternate", "mindfactory", "conrad", "gravis", "apple store", "samsung",
            "xiaomi", "rebuy", "backmarket", "back market", "refurbed", "grover",
            "obi", "bauhaus", "hornbach", "toom", "hellweg", "hagebau", "hagebaumarkt",
            "globus baumarkt", "baumarkt", "poco", "pocohome", "roller", "xxxlutz",
            "mömax", "momax", "hoeffner", "höffner", "porta", "ostermann", "segmüller",
            "segmuller", "jysk", "dänisches bettenlager", "danisches bettenlager",
            "depot", "butlers", "nanu-nana", "nanu nana", "tedi", "action",
            "woolworth", "kik", "euroshop", "mäc-geiz", "mac-geiz", "thomas philipps",
            "tk maxx", "tkmaxx", "muji", "flying tiger", "sostrene grene",
            "søstrene grene", "wmf", "zwilling", "tchibo", "thalia", "hugendubel",
            "osiander", "dussmann", "mcvities",
            # Drugstores, cosmetics & perfume
            "dm", "dm-drogerie", "dm drogerie", "rossmann", "müller", "muller",
            "budni", "budnikowsky", "douglas", "sephora", "rituals", "lush",
            "the body shop", "kiko", "mac cosmetics", "flaconi", "notino",
            "золотое яблоко", "лэтуаль", "летуаль", "рив гош", "подружка",
            "магнит косметик", "улыбка радуги", "mc cosmetic", "bellstore",
            # Clothing, shoes & sports retail
            "zara", "h&m", "hm", "c&a", "uniqlo", "mango", "bershka", "pull&bear",
            "pull and bear", "stradivarius", "massimo dutti", "oysho", "zara home",
            "peek & cloppenburg", "p&c", "breuninger", "engelhorn", "anson's",
            "ansons", "new yorker", "newyorker", "primark", "reserved", "sinsay",
            "cropp", "house brand", "mohito", "only", "vero moda", "jack & jones",
            "esprit", "s.oliver", "soliver", "tommy hilfiger", "calvin klein",
            "levi's", "levis", "hugo boss", "marc o'polo", "gant", "lacoste",
            "ralph lauren", "moncler", "gucci", "prada", "louis vuitton",
            "deichmann", "görz", "görtz", "goertz", "reno", "tamaris", "geox",
            "eccoshoes", "ecco", "snipes", "foot locker", "footlocker", "jd sports",
            "decathlon", "intersport", "sportscheck", "globetrotter", "jack wolfskin",
            "the north face", "columbia", "patagonia", "adidas", "nike", "puma",
            "reebok", "new balance", "asics", "under armour", "lululemon",
            "fielmann", "apollo optik", "mister spex", "christ", "swarovski",
            "pandora", "bijou brigitte", "fressnapf", "zooplus", "futterhaus",
            # Online marketplaces & department stores
            "amazon", "amzn", "ebay", "otto", "zalando", "about you", "aboutyou",
            "asos", "bestsecret", "limango", "westwing", "home24", "wayfair",
            "galaxus", "digitec", "idealo", "kleinanzeigen", "vinted", "etsy",
            "aliexpress", "алиэкспресс", "temu", "тему", "shein", "шеин", "iherb",
            "kaufhof", "galeria", "karstadt", "kaDeWe",
            "ozon", "озон", "wildberries", "вайлдберриз", "wb", "вб", "яндекс маркет",
            "мегамаркет", "ламода", "lamoda", "авито", "avito", "olx", "олх",
            "uzum", "узум", "uzum market", "texnomart", "техномарт", "mediapark",
            "медиапарк", "idea", "ishonch", "elmakon", "macbro", "sulpak", "technodom",
            "мечта", "каспи", "kaspi", "розетка", "rozetka", "алло", "комфи", "comfy",
            "эпицентр", "мвидео", "м.видео", "эльдорадо", "dns", "днс", "ситилинк",
            "рестор", "re:store", "леруа", "леруа мерлен", "leroy merlin", "оби",
            "хофф", "hoff", "детский мир", "спортмастер", "глория джинс", "ostin",
            "остин", "befree", "бифри", "lime", "лайм", "12 storeez", "sokolov",
            # General shopping keywords (RU / EN / DE)
            "одежда", "обувь", "куртка", "пальто", "пуховик", "кроссовки", "ботинки",
            "туфли", "футболка", "рубашка", "джинсы", "брюки", "платье", "костюм",
            "сумка", "рюкзак", "чемодан", "часы", "очки", "украшения", "техника",
            "электроника", "телефон", "смартфон", "айфон", "iphone", "ноутбук",
            "компьютер", "наушники", "airpods", "зарядка", "кабель", "чехол",
            "мебель", "диван", "стол", "стул", "кровать", "матрас", "лампа",
            "посуда", "сковорода", "кастрюля", "постельное", "полотенце",
            "косметика", "парфюм", "духи", "шампунь", "крем", "зубная паста",
            "бытовая химия", "порошок", "уборка", "инструменты", "ремонт",
            "игрушки", "покупки", "шоппинг", "шопинг", "торговый центр", "тц",
            "shopping", "clothes", "clothing", "shoes", "sneakers", "jacket",
            "shirt", "jeans", "dress", "bag", "backpack", "electronics", "laptop",
            "headphones", "charger", "furniture", "cosmetics", "perfume", "drugstore",
            "hardware", "mall", "outlet",
            "einkaufen", "shopping", "kleidung", "klamotten", "schuhe", "sneaker",
            "jacke", "hose", "hemd", "kleid", "tasche", "rucksack", "koffer",
            "elektronik", "technik", "handy", "ladekabel", "kopfhörer", "kopfhorer",
            "möbel", "mobel", "einrichtung", "deko", "haushalt", "drogerie",
            "kosmetik", "parfüm", "parfum", "shampoo", "waschmittel", "werkzeug",
            "spielzeug", "kaufhaus",
        ),
    ),
    "food": CategoryInfo(
        code="food",
        tx_type="expense",
        icon="🍔",
        name_ru="Еда и кафе",
        name_en="Food & Dining",
        name_de="Essen & Café",
        keywords=(
            "обед", "ужин", "завтрак", "ланч", "бранч", "перекус", "кофе", "кофейня",
            "чай", "матча", "капучино", "латте", "эспрессо", "кафе", "ресторан",
            "столовая", "буфет", "бистро", "пекарня", "кондитерская", "круассан",
            "десерт", "торт", "мороженое", "выпечка", "фастфуд", "мак", "макдональдс",
            "mcdonald", "mcdonalds", "mc donalds", "вкусно и точка", "kfc", "кфс",
            "ростикс", "rostics", "burger king", "burgerking", "бургер кинг",
            "subway", "сабвей", "starbucks", "старбакс", "costa coffee", "шоколадница",
            "кофемания", "surf coffee", "dodo", "додо", "додо пицца", "dominos",
            "domino's", "pizza hut", "папа джонс", "papa johns", "якитория", "тануки",
            "фарш", "теремок", "крошка картошка", "evos", "эвос", "oqtepa", "октепа",
            "bellissimo", "беллиссимо", "wendy's", "wendys", "popeyes", "hardee's",
            "shakeshack", "shake shack", "five guys", "chipotle", "taco bell",
            "nordsee", "vapiano", "l'osteria", "losteria", "peter pane",
            "hans im glück", "hans im gluck", "dean&david", "dean & david",
            "block house", "maredo", "cotidiano", "extrablatt", "cafe extrablatt",
            "alex", "balzac", "espresso house", "tchibo", "ditsch", "le crobag",
            "yormas", "yorma's", "immergrün", "immergrun", "haferkater",
            "бургер", "burger", "пицца", "pizza", "шаурма", "шаверма", "донер",
            "дёнер", "döner", "doener", "doner", "kebap", "kebab", "гирос", "фалафель",
            "суши", "sushi", "роллы", "рамен", "ramen", "вок", "wok", "фо бо", "pho",
            "плов", "шашлык", "самса", "манты", "лагман", "хинкали", "хачапури",
            "стейк", "паста", "салат", "суп",
            "lieferando", "wolt", "uber eats", "ubereats", "deliveroo", "just eat",
            "яндекс еда", "yandex eats", "деливери", "delivery club", "купер",
            "uzum tezkor", "express24", "glovo", "bolt food",
            "lunch", "dinner", "breakfast", "brunch", "coffee", "cafe", "café",
            "restaurant", "bistro", "canteen", "mensa", "takeaway", "takeout",
            "fastfood", "fast food", "dining", "tip",
            "frühstück", "fruhstuck", "mittagessen", "mittagstisch", "abendessen",
            "kaffee", "kuchen", "eiscafe", "eiscafé", "eisdiele", "imbiss",
            "mensa", "kantine", "kneipe", "biergarten", "brauhaus", "wirtshaus",
            "lieferservice", "trinkgeld", "bäckerei cafe",
        ),
    ),
    "transport": CategoryInfo(
        code="transport",
        tx_type="expense",
        icon="🚕",
        name_ru="Транспорт",
        name_en="Transport",
        name_de="Verkehr & Mobilität",
        keywords=(
            "такси", "метро", "автобус", "трамвай", "троллейбус", "маршрутка",
            "проезд", "проездной", "тройка", "подорожник", "atto", "атто",
            "бензин", "дизель", "топливо", "газ авто", "заправка", "азс", "лукойл",
            "газпромнефть", "роснефть", "татнефть", "ung", "узбекнефтегаз",
            "поезд", "электричка", "ржд", "сапсан", "ласточка", "афросиаб", "afrosiyob",
            "билет", "авиабилет", "самолет", "самолёт", "аэропорт", "багаж",
            "парковка", "паркинг", "платная дорога", "автомойка", "мойка", "шиномонтаж",
            "сто", "автосервис", "запчасти", "масло авто", "техосмотр", "штраф гибдд",
            "каршеринг", "делимобиль", "ситидрайв", "яндекс драйв", "самокат",
            "whoosh", "вуш", "юрент", "urent",
            "uber", "bolt", "freenow", "free now", "lyft", "cabify", "careem",
            "yandex", "яндекс", "яндекс такси", "яндекс го", "yandex go", "uklon",
            "уклон", "inDriver", "indrive", "maxim",
            "db", "deutsche bahn", "bahn", "ice", "ic", "flixbus", "flixtrain",
            "bvg", "vbb", "hvv", "mvv", "mvg", "vrs", "kvb", "vrr", "rheinbahn",
            "rmv", "vgf", "vvs", "ssb", "dvb", "lvb", "havag", "mdv", "gvh",
            "bsag", "rnv", "kvv", "vag", "swm", "wiener linien", "öbb", "oebb",
            "sbb", "zvv", "s-bahn", "sbahn", "u-bahn", "ubahn", "straßenbahn",
            "strassenbahn", "deutschlandticket", "d-ticket", "49 euro", "58 euro",
            "semesterticket", "jobticket", "monatskarte", "fahrkarte", "fahrschein",
            "einzelfahrschein", "streifenkarte",
            "sixt", "sixt share", "miles", "share now", "sharenow", "free2move",
            "cambio", "stadtmobil", "teilauto", "flinkster", "europcar", "hertz",
            "avis", "budget", "enterprise", "buchbinder",
            "tier", "lime", "voi", "dott", "bolt scooter", "nextbike", "call a bike",
            "swapfiets", "stadtrad",
            "aral", "shell", "esso", "total", "totalenergies", "jet", "hem",
            "star tankstelle", "orlen", "omv", "agip", "eni", "avia", "bft",
            "westfalen", "sprint", "oil!", "tankstelle", "tanken", "benzin",
            "super e10", "super e5", "autowäsche", "autowasche", "waschanlage",
            "parkhaus", "parken", "parkticket", "parkschein", "easypark", "parkster",
            "paybyphone", "apcoa", "contipark", "adac", "tüv", "tuv", "dekra",
            "atu", "a.t.u", "carglass", "werkstatt", "reifen", "kfz", "maut", "vignette",
            "ryanair", "lufthansa", "eurowings", "condor", "tuifly", "easyjet",
            "wizzair", "wizz air", "british airways", "air france", "klm", "iberia",
            "vueling", "pegasus", "turkish airlines", "uzbekistan airways", "qanot sharq",
            "centrum air", "air astana", "flyarystan", "emirates", "flydubai", "qatar",
            "аэрофлот", "победа", "s7", "уральские авиалинии", "utair",
            "taxi", "bus", "metro", "subway", "train", "tram", "ticket", "transit",
            "fuel", "gas station", "petrol", "parking", "toll", "carwash", "flight",
            "airline", "airport",
        ),
    ),
    "housing": CategoryInfo(
        code="housing",
        tx_type="expense",
        icon="🏠",
        name_ru="Жильё и счета",
        name_en="Housing & Bills",
        name_de="Wohnen & Nebenkosten",
        keywords=(
            "аренда", "квартира", "жилье", "жильё", "общежитие", "общага", "комната",
            "коммуналка", "коммунальные", "жкх", "квартплата", "тсж", "капремонт",
            "свет", "электричество", "электроэнергия", "газ", "отопление", "тепло",
            "горячая вода", "холодная вода", "водоканал", "канализация", "мусор",
            "вывоз мусора", "домофон", "консьерж", "охрана",
            "интернет", "вайфай", "wifi", "wi-fi", "связь", "телефон", "мобильный",
            "сотовая", "симка", "сим-карта", "тариф", "роуминг", "мтс", "билайн",
            "мегафон", "теле2", "tele2", "yota", "ростелеком", "дом.ру", "ucell",
            "uzmobile", "mobiuz", "beeline", "sarkor", "turon", "tcell", "activ",
            "kcell", "київстар", "kyivstar", "lifecell",
            "страховка", "осаго", "каско", "страхование", "налог", "пошлина",
            "нотариус", "юрист", "кредит", "ипотека",
            "rent", "apartment", "flat", "dorm", "housing", "mortgage", "utilities",
            "electricity", "power bill", "water bill", "heating", "gas bill",
            "internet", "broadband", "phone bill", "mobile plan", "sim card",
            "insurance", "tax",
            "miete", "kaltmiete", "warmmiete", "untermiete", "wg", "wohnung",
            "wohnheim", "studierendenwerk", "studentenwerk", "kaution", "hausgeld",
            "nebenkosten", "betriebskosten", "heizkosten", "strom", "stromabschlag",
            "gasabschlag", "heizung", "fernwärme", "fernwarme", "wasserwerk",
            "rundfunkbeitrag", "gez", "ard zdf", "müllabfuhr", "mullabfuhr",
            "schornsteinfeger", "hausmeister",
            "telekom", "deutsche telekom", "t-mobile", "vodafone", "o2", "telefonica",
            "1&1", "1und1", "pyur", "congstar", "fraenk", "freenet", "klarmobil",
            "mobilcom", "alditalk", "aldi talk", "lidl connect", "kaufland mobil",
            "nettokom", "penny mobil", "ja! mobil", "sim.de", "winsim", "premiumsim",
            "drillisch", "lebara", "lycamobile", "oray", "glasfaser", "fritzbox",
            "e.on", "eon", "vattenfall", "enbw", "rwe", "innogy", "lichtblick",
            "yello", "ostrom", "tibber", "octopus energy", "stadtwerke", "gasag",
            "mainova", "rheinenergie", "swb", "enercity", "enviaM", "enviam",
            "allianz", "huk", "huk-coburg", "huk24", "debeka", "ergo", "axa",
            "generali", "signal iduna", "r+v", "devk", "gothaer", "provinzial",
            "hansemerkur", "barmenia", "wuerttembergische", "württembergische",
            "cosmosdirekt", "clark", "feather", "getsaf", "getsafe", "check24",
            "verivox", "haftpflicht", "privathaftpflicht", "hausrat", "rechtsschutz",
            "berufsunfähigkeit", "kfz-versicherung", "versicherung", "finanzamt",
            "steuer", "rundfunk", "schufa", "bürgeramt", "burgeramt", "rathaus",
        ),
    ),
    "entertainment": CategoryInfo(
        code="entertainment",
        tx_type="expense",
        icon="🎬",
        name_ru="Развлечения и подписки",
        name_en="Entertainment",
        name_de="Freizeit & Abos",
        keywords=(
            "кино", "кинотеатр", "театр", "концерт", "стендап", "выставка", "музей",
            "галерея", "зоопарк", "парк", "аттракционы", "аквапарк", "боулинг",
            "бильярд", "караоке", "квест", "клуб", "дискотека", "вечеринка", "бар",
            "паб", "кальян", "отдых", "отпуск", "путешествие", "экскурсия", "отель",
            "гостиница", "хостел", "сауна", "баня", "спа", "хобби", "цветы",
            "подписка", "подписки", "яндекс плюс", "кинопоиск", "иви", "ivi", "okko",
            "окко", "wink", "kion", "start", "premier", "вк музыка", "vk music",
            "мтс премиум", "сберпрайм", "т-про", "тинькофф про",
            "netflix", "spotify", "youtube", "youtube premium", "apple", "apple music",
            "apple one", "icloud", "google one", "google play", "app store",
            "amazon prime", "prime video", "audible", "kindle", "disney", "disney+",
            "hbo", "max", "paramount", "peacock", "crunchyroll", "dazn", "sky",
            "wow", "rtl+", "joyn", "waipu", "zattoo", "mubi", "deezer", "tidal",
            "soundcloud", "patreon", "onlyfans", "twitch", "discord", "nitro",
            "telegram", "telegram premium", "chatgpt", "openai", "claude", "anthropic",
            "midjourney", "cursor", "copilot", "perplexity", "notion", "canva",
            "figma", "adobe", "dropbox", "1password", "nordvpn", "expressvpn",
            "игры", "steam", "стим", "playstation", "psn", "ps4", "ps5", "xbox",
            "game pass", "nintendo", "eshop", "epic games", "ea play", "ubisoft",
            "blizzard", "battle.net", "riot", "valorant", "league of legends",
            "genshin", "roblox", "minecraft", "pubg", "dota", "cs2", "faceit",
            "cinemaxx", "cineplex", "cinestar", "uci", "astor", "kino", "theater",
            "oper", "philharmonie", "konzert", "eventim", "ticketmaster", "reservix",
            "museum", "zoo", "tierpark", "therme", "freizeitpark", "europapark",
            "phantasialand", "heide park", "legoland", "bowling", "billard",
            "escape room", "lasertag", "kartbahn", "minigolf",
            "urlaub", "reise", "booking", "booking.com", "airbnb", "expedia",
            "hotels.com", "trivago", "agoda", "hostelworld", "hrs", "tui",
            "alltours", "check24 reisen", "hotel", "hostel", "pension", "ferienwohnung",
            "movie", "cinema", "concert", "subscription", "games", "gaming",
            "party", "club", "bar", "pub", "vacation", "holiday", "travel",
            "freizeit", "unterhaltung", "abo", "abonnement", "blumen",
        ),
    ),
    "health": CategoryInfo(
        code="health",
        tx_type="expense",
        icon="💊",
        name_ru="Здоровье и спорт",
        name_en="Health & Sport",
        name_de="Gesundheit & Sport",
        keywords=(
            "аптека", "лекарства", "таблетки", "витамины", "бады", "мазь", "капли",
            "антибиотики", "обезболивающее", "линзы", "раствор для линз",
            "врач", "доктор", "клиника", "поликлиника", "больница", "госпиталь",
            "анализы", "инвитро", "invitro", "гемотест", "хеликс", "синево",
            "узи", "мрт", "кт", "рентген", "прием врача", "консультация",
            "стоматолог", "зубной", "дантист", "чистка зубов", "пломба", "брекеты",
            "офтальмолог", "дерматолог", "терапевт", "психолог", "психотерапевт",
            "массаж", "реабилитация", "вакцина", "прививка",
            "спортзал", "зал", "фитнес", "тренажерный", "абонемент", "тренировка",
            "тренер", "бассейн", "плавание", "йога", "пилатес", "бокс", "теннис",
            "футбол", "баскетбол", "бег", "марафон", "протеин", "креатин", "спортпит",
            "парикмахерская", "барбершоп", "салон красоты", "стрижка", "маникюр",
            "педикюр", "косметолог", "спа", "солярий",
            "pharmacy", "medicine", "medication", "pills", "vitamins", "doctor",
            "clinic", "hospital", "dentist", "dental", "therapy", "massage",
            "gym", "fitness", "workout", "sport", "pool", "swimming", "yoga",
            "pilates", "haircut", "barber", "barbershop", "salon", "health",
            "apotheke", "docmorris", "shop apotheke", "shop-apotheke", "medpex",
            "apodiscounter", "medikamente", "arznei", "tabletten", "rezept",
            "zuzahlung", "vitamine", "kontaktlinsen",
            "arzt", "hausarzt", "facharzt", "zahnarzt", "zahnreinigung", "augenarzt",
            "hautarzt", "frauenarzt", "orthopäde", "orthopade", "physiotherapie",
            "physio", "krankenhaus", "klinik", "praxis", "labor", "blutbild",
            "psychotherapie", "heilpraktiker",
            "tk", "techniker krankenkasse", "aok", "barmer", "dak", "ikk", "bkk",
            "knappschaft", "hek", "hkk", "pkv", "krankenkasse", "krankenversicherung",
            "pflegeversicherung",
            "mcfit", "fitx", "clever fit", "cleverfit", "john reed", "fitness first",
            "holmes place", "elements", "body+soul", "fitti", "fitstar", "all inclusive fitness",
            "easyfitness", "injoy", "mrs.sporty", "kieser", "urban sports",
            "urbansports", "urban sports club", "wellpass", "egym", "classpass",
            "hochschulsport", "unisport", "fitnessstudio", "sportverein", "verein",
            "schwimmbad", "hallenbad", "kletterhalle", "boulderhalle", "bouldern",
            "tennis", "fußball", "fussball", "myprotein", "esn", "more nutrition",
            "friseur", "frisör", "haarschnitt", "kosmetikstudio", "nagelstudio",
            "gesundheit", "körperpflege",
        ),
    ),
    "education": CategoryInfo(
        code="education",
        tx_type="expense",
        icon="📚",
        name_ru="Образование",
        name_en="Education",
        name_de="Bildung & Studium",
        keywords=(
            "курсы", "курс", "обучение", "тренинг", "вебинар", "лекция", "семинар",
            "книга", "книги", "учебник", "тетрадь", "канцелярия", "ручки", "печать",
            "распечатка", "ксерокс", "копицентр",
            "учеба", "учёба", "университет", "универ", "институт", "колледж",
            "штудиенколлег", "школа", "лицей", "детский сад", "садик",
            "семестр", "семестровый взнос", "контракт", "оплата учебы",
            "репетитор", "преподаватель", "учитель", "немецкий", "английский",
            "языковой курс", "экзамен", "тест", "сертификат", "диплом", "перевод документов",
            "skillbox", "geekbrains", "яндекс практикум", "нетология", "skyeng",
            "course", "courses", "book", "books", "textbook", "stationery",
            "study", "studies", "university", "college", "school", "tuition",
            "semester", "tutor", "teacher", "language course", "exam", "education",
            "udemy", "coursera", "edx", "pluralsight", "datacamp", "leetcode",
            "duolingo", "babbel", "busuu", "memrise", "preply", "italki", "cambly",
            "uni", "universität", "universitat", "hochschule", "fachhochschule",
            "studium", "studienkolleg", "semesterbeitrag", "studiengebühren",
            "studiengebuhren", "immatrikulation", "uni-assist", "uni assist",
            "vhs", "volkshochschule", "goethe", "goethe-institut", "telc",
            "testdaf", "dsh", "ielts", "toefl", "sprachschule", "sprachkurs",
            "deutschkurs", "englischkurs", "integrationskurs", "prüfung", "prufung",
            "nachhilfe", "lehrbuch", "fachbuch", "bücher", "bucher", "schreibwaren",
            "heft", "ordner", "stifte", "copyshop", "drucken", "kopieren",
            "bibliothek", "mensa-karte", "bildung", "weiterbildung", "seminar",
        ),
    ),
    "other": CategoryInfo(
        code="other",
        tx_type="expense",
        icon="📦",
        name_ru="Прочее",
        name_en="Other",
        name_de="Sonstiges",
        keywords=(),
    ),
    # Income categories
    "salary": CategoryInfo(
        code="salary",
        tx_type="income",
        icon="💼",
        name_ru="Зарплата",
        name_en="Salary",
        name_de="Gehalt & Lohn",
        keywords=(
            "зарплата", "зп", "аванс", "оклад", "премия", "бонус", "работа",
            "подработка", "смена", "чаевые", "отпускные", "больничный",
            "salary", "wage", "wages", "paycheck", "payroll", "bonus", "work",
            "job", "overtime", "tips",
            "gehalt", "lohn", "arbeitslohn", "vergütung", "vergutung", "prämie",
            "pramie", "weihnachtsgeld", "urlaubsgeld", "minijob", "werkstudent",
            "nebenjob", "arbeit", "trinkgeld",
        ),
    ),
    "stipend": CategoryInfo(
        code="stipend",
        tx_type="income",
        icon="🎓",
        name_ru="Стипендия",
        name_en="Stipend",
        name_de="Stipendium & BAföG",
        keywords=(
            "стипендия", "стипуха", "грант", "пособие", "выплата",
            "stipend", "scholarship", "grant", "fellowship", "allowance",
            "stipendium", "bafög", "bafoeg", "daad", "deutschlandstipendium",
            "kindergeld", "wohngeld", "bürgergeld", "burgergeld", "elterngeld",
            "unterhalt", "sperrkonto", "fintiba", "expatrio", "coracle",
        ),
    ),
    "freelance": CategoryInfo(
        code="freelance",
        tx_type="income",
        icon="💻",
        name_ru="Фриланс и доход",
        name_en="Freelance & Business",
        name_de="Freelance & Geschäft",
        keywords=(
            "фриланс", "заказ", "проект", "клиент", "гонорар", "консультация",
            "услуга", "продажа", "авито", "арендный", "сдача квартиры",
            "дивиденды", "инвестиции", "проценты", "вклад", "депозит", "акции",
            "крипта", "бизнес", "выручка", "прибыль",
            "freelance", "project", "client", "contract", "consulting", "sale",
            "sold", "rental income", "dividend", "dividends", "interest",
            "investment", "profit", "business", "upwork", "fiverr",
            "honorar", "auftrag", "kunde", "rechnung", "selbstständig",
            "selbststandig", "gewerbe", "verkauf", "kleinanzeigen", "vinted",
            "mieteinnahmen", "dividende", "zinsen", "tagesgeld", "festgeld",
            "trade republic", "scalable", "ing", "dkb", "comdirect", "aktien",
            "etf", "rendite", "gewinn",
        ),
    ),
    "gift": CategoryInfo(
        code="gift",
        tx_type="income",
        icon="🎁",
        name_ru="Подарок и кэшбэк",
        name_en="Gift & Cashback",
        name_de="Geschenk & Cashback",
        keywords=(
            "подарок", "перевод", "скинули", "вернули", "долг", "возврат",
            "кэшбэк", "кешбэк", "бонусы", "родители", "мама", "папа", "семья",
            "нашел", "выигрыш", "налоговый вычет",
            "gift", "present", "birthday", "cashback", "refund", "reimbursement",
            "returned", "transfer", "parents", "family", "tax refund", "payback",
            "geschenk", "geburtstag", "überweisung", "uberweisung", "rückerstattung",
            "ruckerstattung", "erstattung", "retoure", "pfand", "leergut",
            "steuerrückerstattung", "steuererstattung", "eltern", "familie",
            "payback", "shoop", "topcashback", "schulden",
        ),
    ),
    "other_income": CategoryInfo(
        code="other_income",
        tx_type="income",
        icon="💰",
        name_ru="Прочий доход",
        name_en="Other Income",
        name_de="Sonstige Einnahmen",
        keywords=(),
    ),
}

EXPENSE_CATEGORY_CODES: List[str] = [
    "food",
    "groceries",
    "transport",
    "housing",
    "shopping",
    "entertainment",
    "health",
    "education",
    "other",
]

INCOME_CATEGORY_CODES: List[str] = [
    "salary",
    "stipend",
    "freelance",
    "gift",
    "other_income",
]

# Short keywords (<=3 chars) that should match on word boundaries to avoid false positives
# e.g., "db", "dm", "wb", "вб", "зп", "кфс", "мак", "тц", "uni", "vhs", "tk", "o2", "kik"
_SHORT_BOUNDARY_KEYWORDS = {
    "db", "dm", "wb", "вб", "зп", "кфс", "мак", "тц", "uni", "vhs",
    "tk", "o2", "kik", "hit", "np", "hm", "p&c", "aok", "dak", "ikk",
    "bkk", "hek", "hkk", "pkv", "atu", "tüv", "tuv", "kfz", "bvg",
    "hvv", "mvv", "mvg", "vrs", "kvb", "vrr", "rmv", "vgf", "vvs",
    "ssb", "dvb", "lvb", "mdv", "gvh", "rnv", "kvv", "vag", "swm",
    "sbb", "zvv", "öbb", "gez", "rwe", "swb", "erg", "axa", "tui",
    "hrs", "uci", "wow", "sky", "max", "ps4", "ps5", "psn", "cs2",
    "etf", "ing", "dkb", "s7", "азс", "сто", "ржд", "жкх", "тсж",
    "мтс", "олх", "olx", "днс", "dns", "оби", "obi", "узи", "мрт",
    "кт", "спа", "зал", "бег", "сок", "сыр", "чай", "суп", "вок",
    "wok", "pho", "бар", "паб", "tip", "bus", "cab", "car", "gas",
    "oil", "tax", "gym", "spa", "pub", "bar", "vet", "pet", "diy",
}

_CASH_KEYWORDS = {
    "нал", "наличка", "наличные", "наличными",
    "cash", "bargeld", "bar",
}

_CARD_KEYWORDS = {
    "карта", "картой", "безнал",
    "card", "karte", "kartenzahlung", "ec", "girocard", "apple pay", "google pay",
}


def detect_category(description: str, tx_type: str = "expense") -> str:
    """
    Automatically detect category code from transaction description keywords.
    Uses word-boundary matching for short brand codes (e.g. 'dm', 'db', 'obi')
    and substring matching for full store/product keywords (e.g. 'rewe', 'lidl', 'mediamarkt').
    """
    default_code = "other_income" if tx_type == "income" else "other"
    if not description or not description.strip():
        return default_code

    lower_desc = description.lower().strip()
    # Tokenize words for exact token checks on short keywords
    tokens = set(re.findall(r"[a-zа-яёäöüß0-9&+.-]+", lower_desc))

    codes = INCOME_CATEGORY_CODES if tx_type == "income" else EXPENSE_CATEGORY_CODES

    for code in codes:
        info = CATEGORIES[code]
        for kw in info.keywords:
            if kw in _SHORT_BOUNDARY_KEYWORDS or len(kw) <= 3:
                if kw in tokens:
                    return code
            else:
                if kw in lower_desc:
                    return code

    return default_code


def detect_payment_method(description: str, default: str = "card") -> str:
    """Detect 'cash' or 'card' from optional keywords in description, defaulting to 'card'."""
    if not description or not description.strip():
        return default
    lower_desc = description.lower().strip()
    tokens = set(re.findall(r"[a-zа-яёäöüß]+", lower_desc))
    if tokens & _CASH_KEYWORDS:
        return "cash"
    if tokens & _CARD_KEYWORDS:
        return "card"
    return default


def get_category_info(code: str, tx_type: str = "expense") -> CategoryInfo:
    if code in CATEGORIES:
        return CATEGORIES[code]
    fallback = "other_income" if tx_type == "income" else "other"
    return CATEGORIES[fallback]


def get_category_name(code: str, lang: str = "ru", tx_type: str = "expense") -> str:
    info = get_category_info(code, tx_type=tx_type)
    lang_low = (lang or "ru").lower()
    if lang_low.startswith("de"):
        return info.name_de or info.name_en
    if lang_low.startswith("en"):
        return info.name_en
    return info.name_ru


def get_category_label(code: str, lang: str = "ru", tx_type: str = "expense") -> str:
    info = get_category_info(code, tx_type=tx_type)
    name = get_category_name(code, lang=lang, tx_type=tx_type)
    return f"{info.icon} {name}"
