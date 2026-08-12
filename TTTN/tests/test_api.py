def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "version": "2.0.0", "database": "connected"}


def test_openapi_documentation(client):
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "World Cup Data REST API"
    assert schema["info"]["version"] == "2.0.0"
    assert {tag["name"] for tag in schema["tags"]} >= {"System", "Tournaments", "Statistics", "Search"}
    assert schema["paths"]["/api/v1/statistics/teams/titles"]["get"]["tags"] == ["Statistics"]
    assert schema["paths"]["/api/v1/stats/teams/most-titles"]["get"]["deprecated"] is True
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_statistics(client):
    assert client.get("/api/v1/stats/teams/most-titles").json()[0]["team_name"] == "Argentina"
    scorers = client.get("/api/v1/stats/players/top-scorers").json()
    assert [(x["player_name"], x["value"]) for x in scorers] == [("Kylian Mbappé", 3), ("Lionel Messi", 2)]
    assert client.get("/api/v1/stats/matches/most-goals").json()[0]["value"] == 6
    assert client.get("/api/v1/stats/matches/most-cards").json()[0]["value"] == 2


def test_rest_team_statistics(client):
    titles = client.get("/api/v1/statistics/teams/titles").json()
    assert titles["meta"] == {"metric": "titles", "count": 1, "filters": {}}
    assert titles["data"][0]["team_name"] == "Argentina"
    assert titles["data"][0]["value"] == 1

    participations = client.get("/api/v1/statistics/teams/tournaments").json()
    assert {row["team_name"] for row in participations["data"]} == {"Argentina", "France"}
    assert client.get("/api/v1/statistics/teams/goals").json()["data"][0]["team_name"] == "France"
    assert client.get("/api/v1/statistics/teams/wins").json()["data"][0]["team_name"] == "Argentina"


def test_rest_player_statistics_and_filters(client):
    scorers = client.get("/api/v1/statistics/players/goals?year=2022&stage=Final").json()
    assert scorers["meta"]["filters"] == {"year": 2022, "stage": "Final"}
    assert scorers["data"][0]["player_name"] == "Kylian Mbappé"
    assert scorers["data"][0]["metric"] == "goals"

    matches = client.get("/api/v1/statistics/players/matches").json()
    tournaments = client.get("/api/v1/statistics/players/tournaments").json()
    assert matches["data"][0]["value"] == 1
    assert tournaments["data"][0]["value"] == 1


def test_rest_match_statistics_and_advanced_search(client):
    goals = client.get("/api/v1/statistics/matches/goals?year=2022&stage=Final").json()
    assert goals["data"][0]["value"] == 6
    assert goals["data"][0]["stage"] == "final"

    cards = client.get("/api/v1/statistics/matches/cards?card_type=yellow").json()
    assert cards["data"][0]["yellow_cards"] == 2
    assert cards["data"][0]["red_cards"] == 0
    assert client.get("/api/v1/statistics/matches/cards?card_type=blue").status_code == 422

    filtered = client.get("/api/v1/matches?year=2022&stage=Final").json()
    assert len(filtered) == 1
    assert len(client.get("/api/v1/matches?year=2022&stage=final").json()) == 1
    assert client.get("/api/v1/matches/stages").json() == ["final"]
    assert client.get("/api/v1/matches?year=2018&tournament_year=2022").status_code == 422

    search = client.get("/api/v1/search?q=France&year=2022").json()
    assert search["teams"][0]["name"] == "France"
    assert search["matches"][0]["away_team"]["name"] == "France"


def test_frontend_detail_and_visualization_endpoints(client):
    overview = client.get("/api/v1/statistics/overview")
    assert overview.status_code == 200
    assert overview.json()["data"]["matches"] == 1

    yearly_goals = client.get("/api/v1/statistics/tournaments/goals").json()
    assert yearly_goals["data"] == [{"tournament_year": 2022, "metric": "goals", "value": 5}]

    team_id = client.get("/api/v1/teams?q=Argentina").json()[0]["id"]
    player_id = client.get("/api/v1/players?q=Messi").json()[0]["id"]
    match_id = client.get("/api/v1/matches").json()[0]["id"]
    assert client.get(f"/api/v1/teams/{team_id}").json()["name"] == "Argentina"
    assert client.get(f"/api/v1/players/{player_id}").json()["full_name"] == "Lionel Messi"
    detail = client.get(f"/api/v1/matches/{match_id}").json()
    assert detail["match"]["home_team"]["name"] == "Argentina"
    assert len(detail["events"]) == 7

    assert client.get("/static/js/pages.js").status_code == 200
    assert "results.news" in client.get("/static/app.js").text
    assert "matchStages" in client.get("/static/js/api.js").text
    assert 'type="module"' in client.get("/").text


def test_seed_contains_no_duplicate_entities(client):
    assert len(client.get("/api/v1/matches").json()) == 1
    assert len(client.get("/api/v1/players").json()) == 2


def test_news_api_only_exposes_world_cup_articles(client):
    articles = client.get("/api/v1/news").json()
    assert [article["title"] for article in articles] == ["Lịch thi đấu World Cup 2022"]
    assert client.get("/api/v1/news/2").status_code == 404
    assert client.get("/api/v1/search?q=ASEAN%20Cup").json()["news"] == []


def test_new_edition_routes_and_frontend(client):
    overview = client.get("/api/v1/tournaments/2022/overview")
    assert overview.status_code == 200
    assert overview.json()["matches_count"] == 1
    assert client.get("/api/v1/tournaments/1900").status_code == 404
    assert "World Cup Atlas" in client.get("/").text
