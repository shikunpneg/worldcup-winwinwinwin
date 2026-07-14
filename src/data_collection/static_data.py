"""
Static data for team coaches and discipline (cards) data.
Market values moved to players.py for better organization.
"""

# Head coaches
COACHES = {
    "Algeria": "Vladimir Petković",
    "Argentina": "Lionel Scaloni",
    "Australia": "Graham Arnold",
    "Austria": "Ralf Rangnick",
    "Belgium": "Domenico Tedesco",
    "Bosnia and Herzegovina": "Sergej Barbarez",
    "Brazil": "Dorival Júnior",
    "Canada": "Jesse Marsch",
    "Cape Verde": "Bubista",
    "Colombia": "Néstor Lorenzo",
    "Croatia": "Zlatko Dalić",
    "Curaçao": "Dick Advocaat",
    "Czech Republic": "Ivan Hašek",
    "Democratic Republic of the Congo": "Sébastien Desabre",
    "Ecuador": "Félix Sánchez Bas",
    "Egypt": "Hossam Hassan",
    "England": "Gareth Southgate",
    "France": "Didier Deschamps",
    "Germany": "Julian Nagelsmann",
    "Ghana": "Otto Addo",
    "Haiti": "Sébastien Migné",
    "Iran": "Amir Ghalenoei",
    "Iraq": "Jesús Casas",
    "Ivory Coast": "Emerse Faé",
    "Japan": "Hajime Moriyasu",
    "Jordan": "Hussein Ammouta",
    "Mexico": "Jaime Lozano",
    "Morocco": "Walid Regragui",
    "Netherlands": "Ronald Koeman",
    "New Zealand": "Darren Bazeley",
    "Norway": "Ståle Solbakken",
    "Panama": "Thomas Christiansen",
    "Paraguay": "Daniel Garnero",
    "Portugal": "Roberto Martínez",
    "Qatar": "Tintín Márquez",
    "Saudi Arabia": "Hervé Renard",
    "Scotland": "Steve Clarke",
    "Senegal": "Pape Thiaw",
    "South Africa": "Hugo Broos",
    "South Korea": "Kim Do-hoon",
    "Spain": "Luis de la Fuente",
    "Sweden": "Jon Dahl Tomasson",
    "Switzerland": "Murat Yakin",
    "Tunisia": "Jalel Kadri",
    "Turkey": "Vincenzo Montella",
    "United States": "Gregg Berhalter",
    "Uruguay": "Marcelo Bielsa",
    "Uzbekistan": "Srečko Katanec",
}

# Red/yellow cards data for teams
CARDS_DATA = {
    "England": {"yellow": 7, "red": 0, "fouls": 54},
    "Morocco": {"yellow": 5, "red": 0, "fouls": 49},
    "Belgium": {"yellow": 5, "red": 0, "fouls": 50},
    "Argentina": {"yellow": 4, "red": 0, "fouls": 88},
    "France": {"yellow": 6, "red": 0, "fouls": 45},
    "Spain": {"yellow": 5, "red": 0, "fouls": 40},
    "Switzerland": {"yellow": 4, "red": 0, "fouls": 35},
    "Norway": {"yellow": 6, "red": 0, "fouls": 48},
    "Mexico": {"yellow": 5, "red": 0, "fouls": 42},
    "South Korea": {"yellow": 4, "red": 0, "fouls": 38},
    "Canada": {"yellow": 3, "red": 0, "fouls": 30},
    "Brazil": {"yellow": 5, "red": 0, "fouls": 46},
    "Germany": {"yellow": 4, "red": 0, "fouls": 36},
    "Netherlands": {"yellow": 5, "red": 0, "fouls": 44},
    "Japan": {"yellow": 3, "red": 0, "fouls": 32},
    "Portugal": {"yellow": 6, "red": 0, "fouls": 52},
    "United States": {"yellow": 4, "red": 0, "fouls": 40},
    "Colombia": {"yellow": 5, "red": 0, "fouls": 47},
    "Austria": {"yellow": 4, "red": 0, "fouls": 38},
    "Croatia": {"yellow": 5, "red": 0, "fouls": 44},
    "Ivory Coast": {"yellow": 4, "red": 0, "fouls": 36},
    "Cape Verde": {"yellow": 3, "red": 0, "fouls": 28},
    "Egypt": {"yellow": 4, "red": 0, "fouls": 35},
    "Australia": {"yellow": 5, "red": 0, "fouls": 42},
}


def get_coach(team_name: str) -> str:
    """Get coach name for a team."""
    return COACHES.get(team_name, "Unknown")


def get_cards(team_name: str) -> dict:
    """Get red/yellow cards data for a team."""
    return CARDS_DATA.get(team_name, {"yellow": 0, "red": 0, "fouls": 0})
