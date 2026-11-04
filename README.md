# LakayTV Direct — données sport

Copie quotidienne des réponses de [TheSportsDB](https://www.thesportsdb.com) que l'app LakayTV Direct demande
(matchs à venir et passés des ligues proposées, et de leurs équipes). Sports Radar lit ces fichiers d'abord et
n'appelle l'API TheSportsDB qu'en secours, ce qui reste sous la limite de la clé gratuite (30 requêtes par minute).

- Source des données : **TheSportsDB** (https://www.thesportsdb.com), selon ses conditions d'utilisation
  (« You can scrape, copy and modify content returned from the API… », « must mention us as the source of the data »).
- Les images (logos, bannières) ne sont pas copiées : seuls leurs liens vers TheSportsDB sont dans les fichiers.
- Mise à jour : `.github/workflows/mirror.yml`, chaque jour à 06:15 UTC (et à la main : *Run workflow*).
- Ligues copiées : `leagues.txt`. Fichiers : `v1/<endpoint>/<id>.json`, sommaire `v1/index.json`.
