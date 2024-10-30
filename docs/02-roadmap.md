**[Retour au sommaire de la documentation](../README.md)**

# Papi-web - Roadmap

- LAN = usage en réseau local (sur un serveur local)
- SaaS = usage en ligne (sur un serveur distant)

|                                      | 1.19       | 2.0         | 2.1         | 2.2           | 2.3           | 2.4           | 2.x             | 3.0             | Cible           |
|--------------------------------------|------------|-------------|-------------|---------------|---------------|---------------|-----------------|-----------------|-----------------|
| **LAN**<br/>Open source              | :x:        | :ok:        | :ok:        | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **LAN**<br/>Logiciel libre           | :x:        | :x:         | :x:         | :x:           | :x:           | :ok: AGPL     | :ok: AGPL       | :ok: AGPL       | :ok: AGPL       |
| **LAN**<br/>Serveur web inclus       | :x: XAMPP  | :ok: Django | :ok: Django | :ok: LiteStar | :ok: Litestar | :ok: Litestar | :ok: Litestar   | :ok: Litestar   | :ok: Litestar   |
| **LAN**<br/>Pilote BDD inclus        | :x: ODBC   | :x: ODBC    | :x: ODBC    | :x: ODBC      | :x: ODBC      | :x: ODBC      | :grey_question: | :ok: SQLite     | :ok: SQLite     |
| **LAN**<br/>Support Windows          | :ok:       | :ok:        | :ok:        | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **LAN**<br/>Exécutable Windows       | :x:        | :ok:        | :ok:        | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **LAN**<br/>Support Linux            | :x:        | :x:         | :x:         | :x:           | :x:           | :x:           | :x:             | :grey_question: | :ok:            |
| **LAN**<br/>Support Mac              | :x:        | :x:         | :x:         | :x:           | :x:           | :x:           | :x:             | :grey_question: | :ok:            |
| **LAN**<br/>Config. Papi-web         | :x: PHP    | :ok: INI    | :ok: INI    | :ok: INI      | :ok: INI      | :ok: INI      | :ok: INI        | :ok: INI        | :ok: INI        |
| **LAN**<br/>Config. évènements       | :x: PHP    | :x: INI     | :x: INI     | :x: INI       | :x: INI       | :ok: web      | :ok: web        | :ok: web        | :ok: web        |
| **LAN**<br/>Stockage tournois        | :x: Access | :x: Access  | :x: Access  | :x: Access    | :x: Access    | :x: Access    | :grey_question: | :ok: SQLite     | :ok: SQLite     |
| **LAN**<br/>Stockage évènements      | -          | :x: File    | :x: File    | :x: File      | :x: File      | :ok: SQLite   | :ok: SQLite     | :ok: SQLite     | :ok: SQLite     |
| **SaaS**                             | :x:        | :x:         | :x:         | :x:           | :x:           | :x:           | :x:             | :grey_question: | :ok:            |
| **SaaS**<br/>Open source             | -          | -           | -           | -             | -             | -             | -               | :grey_question: | :ok:            |
| **SaaS**<br/>Logiciel libre          | -          | -           | -           | -             | -             | -             | -               | :grey_question: | :grey_question: |
| **SaaS**<br/>Stockage                | -          | -           | -           | -             | -             | -             | -               | :grey_question: | :ok: Postgres   |
| **Appariement**<br/>Moteur           | :x: Papi   | :x: Papi    | :x: Papi    | :x: Papi      | :x: Papi      | :x: Papi      | :grey_question: | :ok: bbp        | :ok: bbp        |
| **Appariement**<br/>Support Papi     | 3.3.6      | 3.3.6       | 3.3.7       | 3.3.7         | 3.3.7         | 3.3.8         | :grey_question: | -               | -               |           
| **Internationalisation**             | :x: FR     | :x: FR      | :x: FR      | :x: FR        | :x: FR        | :x: FR        | :grey_question: | :ok: EN/FR      | :ok: EN/FR      |
| **Homologation FIDE**                | :x:        | :x:         | :x:         | :x:           | :x:           | :x:           | :x:             | :grey_question: | :ok:            |
| **Utilisation**<br/>HTMX             | :x:        | :x:         | :x:         | :x:           | :x:           | :ok:          | :ok:            | :ok:            | :ok:            |
| **Utilisation**<br/>Multi-écrans     | :ok:       | :ok:        | :ok:        | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **Utilisation**<br/>Multi-colonnes   | :x:        | :ok:        | :ok:        | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **Utilisation**<br/>Appar. alpha.    | :x:        | :ok:        | :ok:        | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **Utilisation**<br/>Écrans rotatifs  | :x:        | :ok:        | :ok:        | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **Utilisation**<br/>Coups illégaux   | :x:        | :x:         | :x:         | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **Utilisation**<br/>Pointage         | :x:        | :x:         | :x:         | :x:           | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **Utilisation**<br/>Modif. résultats | :x:        | :x:         | :x:         | :x:           | :x:           | :ok:          | :ok:            | :ok:            | :ok:            |
| **FFE**<br/>Envoi tournois           | :ok:       | :ok:        | :ok:        | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **FFE**<br/>Protection données       | :x:        | :x:         | :ok:        | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
| **Chess Event**                      | :x:        | :x:         | :ok:        | :ok:          | :ok:          | :ok:          | :ok:            | :ok:            | :ok:            |
