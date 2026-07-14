"""
Complete player data for FIFA World Cup 2026.
Sources: 
  - ESPN top scorers & assists (as of July 10, 2026)
  - Transfermarkt market values (via PlanetFootball ranking)
"""

# ============================================================
# TOP SCORERS & ASSISTERS (from ESPN, as of Quarter-finals)
# ============================================================
TOP_SCORERS = {
    "Kylian Mbappé": {"goals": 8, "team": "France", "position": "FW", "assists": 3, "age": 27},
    "Lionel Messi": {"goals": 8, "team": "Argentina", "position": "FW", "assists": 1, "age": 39},
    "Erling Haaland": {"goals": 7, "team": "Norway", "position": "FW", "assists": 0, "age": 25},
    "Harry Kane": {"goals": 6, "team": "England", "position": "FW", "assists": 1, "age": 32},
    "Ousmane Dembélé": {"goals": 5, "team": "France", "position": "FW", "assists": 2, "age": 29},
    "Vinícius Júnior": {"goals": 4, "team": "Brazil", "position": "FW", "assists": 1, "age": 25},
    "Julián Quiñones": {"goals": 4, "team": "Mexico", "position": "FW", "assists": 1, "age": 29},
    "Jude Bellingham": {"goals": 4, "team": "England", "position": "MF", "assists": 0, "age": 23},
    "Mikel Oyarzabal": {"goals": 4, "team": "Spain", "position": "FW", "assists": 0, "age": 29},
    "Ismaïla Sarr": {"goals": 4, "team": "Senegal", "position": "FW", "assists": 0, "age": 28},
    "Cristiano Ronaldo": {"goals": 3, "team": "Portugal", "position": "FW", "assists": 0, "age": 41},
    "Jonathan David": {"goals": 3, "team": "Canada", "position": "FW", "assists": 0, "age": 26},
    "Ismael Saibari": {"goals": 3, "team": "Morocco", "position": "MF", "assists": 0, "age": 25},
    "Matheus Cunha": {"goals": 3, "team": "Brazil", "position": "FW", "assists": 0, "age": 27},
    "Romelu Lukaku": {"goals": 3, "team": "Belgium", "position": "FW", "assists": 0, "age": 33},
    "Cody Gakpo": {"goals": 3, "team": "Netherlands", "position": "FW", "assists": 0, "age": 27},
    "Yoane Wissa": {"goals": 3, "team": "Democratic Republic of the Congo", "position": "FW", "assists": 0, "age": 29},
    "Kai Havertz": {"goals": 3, "team": "Germany", "position": "FW", "assists": 0, "age": 27},
    "Raúl Jiménez": {"goals": 3, "team": "Mexico", "position": "FW", "assists": 0, "age": 35},
    "Folarin Balogun": {"goals": 3, "team": "United States", "position": "FW", "assists": 0, "age": 25},
    "Brian Brobbey": {"goals": 3, "team": "Netherlands", "position": "FW", "assists": 0, "age": 24},
    "Johan Manzambi": {"goals": 3, "team": "Switzerland", "position": "FW", "assists": 0, "age": 26},
    "Deniz Undav": {"goals": 3, "team": "Germany", "position": "FW", "assists": 2, "age": 29},
    "Elijah Just": {"goals": 3, "team": "New Zealand", "position": "FW", "assists": 0, "age": 26},
}

# Top assist providers
TOP_ASSISTERS = {
    "Michael Olise": {"assists": 5, "team": "France", "position": "MF", "age": 24},
    "Brahim Díaz": {"assists": 4, "team": "Morocco", "position": "FW", "age": 26},
    "Bruno Guimarães": {"assists": 4, "team": "Brazil", "position": "MF", "age": 28},
    "Roberto Alvarado": {"assists": 3, "team": "Mexico", "position": "MF", "age": 27},
    "Bukayo Saka": {"assists": 3, "team": "England", "position": "FW", "age": 24},
    "Andreas Schjelderup": {"assists": 3, "team": "Norway", "position": "FW", "age": 22},
    "Florian Wirtz": {"assists": 3, "team": "Germany", "position": "MF", "age": 23},
    "Alexander Isak": {"assists": 3, "team": "Sweden", "position": "FW", "age": 26},
    "Martin Ødegaard": {"assists": 3, "team": "Norway", "position": "MF", "age": 27},
}

# ============================================================
# TEAM MARKET VALUES (Transfermarkt, via PlanetFootball ranking)
# Units: EUR
# ============================================================
TEAM_MARKET_VALUES = {
    # Tier 1: > €1B
    "France": 1_520_000_000,
    "England": 1_360_000_000,
    "Spain": 1_220_000_000,
    "Portugal": 1_010_000_000,
    # Tier 2: €700M-€1B
    "Germany": 947_000_000,
    "Brazil": 928_000_000,
    "Argentina": 807_000_000,
    "Netherlands": 754_000_000,
    "Belgium": 680_000_000,
    "Norway": 646_000_000,
    # Tier 3: €350M-€650M
    "Ivory Coast": 522_100_000,
    "Turkey": 473_000_000,
    "Morocco": 430_000_000,
    "Senegal": 420_000_000,
    "United States": 385_600_000,
    "Ecuador": 368_700_000,
    "Uruguay": 359_300_000,
    "Colombia": 420_000_000,
    "Croatia": 380_000_000,
    "Switzerland": 350_000_000,
    "Austria": 340_000_000,
    "Sweden": 320_000_000,
    # Tier 4: €200M-€350M
    "Japan": 270_850_000,
    "Mexico": 265_000_000,
    "Egypt": 250_000_000,
    "South Korea": 245_000_000,
    "Iran": 230_000_000,
    "Algeria": 210_000_000,
    "Ghana": 200_000_000,
    "Canada": 195_000_000,
    "Bosnia and Herzegovina": 185_000_000,
    "Scotland": 175_000_000,
    "Paraguay": 165_000_000,
    # Tier 5: €100M-€200M
    "Australia": 160_000_000,
    "Tunisia": 155_000_000,
    "South Africa": 140_000_000,
    "Saudi Arabia": 135_000_000,
    "Cape Verde": 120_000_000,
    "Czech Republic": 115_000_000,
    "Democratic Republic of the Congo": 110_000_000,
    # Tier 6: < €100M
    "Uzbekistan": 85_000_000,
    "Panama": 70_000_000,
    "New Zealand": 65_000_000,
    "Haiti": 50_000_000,
    "Iraq": 45_000_000,
    "Curaçao": 40_000_000,
    "Qatar": 19_930_000,
    "Jordan": 15_980_000,
}


def get_market_value(team_name: str) -> int:
    """Get market value for a team (in EUR)."""
    return TEAM_MARKET_VALUES.get(team_name, 0)


def get_top_scorers(top_n: int = 10) -> list:
    """Get top N goalscorers."""
    sorted_scorers = sorted(TOP_SCORERS.items(), key=lambda x: -x[1]["goals"])
    return [{"name": name, **data} for name, data in sorted_scorers[:top_n]]


def get_team_top_scorers(team_name: str) -> list:
    """Get top scorers for a specific team."""
    result = []
    for name, data in sorted(TOP_SCORERS.items(), key=lambda x: -x[1]["goals"]):
        if data["team"] == team_name:
            result.append({"name": name, **data})
    return result


def get_team_assisters(team_name: str) -> list:
    """Get top assist providers for a specific team."""
    result = []
    for name, data in sorted(TOP_ASSISTERS.items(), key=lambda x: -x[1]["assists"]):
        if data["team"] == team_name:
            result.append({"name": name, **data})
    return result


def get_player_stats(player_name: str) -> dict:
    """Get stats for a specific player."""
    if player_name in TOP_SCORERS:
        return TOP_SCORERS[player_name]
    if player_name in TOP_ASSISTERS:
        return {"goals": 0, **TOP_ASSISTERS[player_name]}
    return None
