# Fonte Musculation

Carnet de musculation installable sur smartphone, qui fonctionne hors ligne.

**Ouvrir l'app :** https://foufighterz.github.io/fonte/

## Installer sur le téléphone
- **iPhone** : ouvrir l'adresse dans Safari → Partager → « Sur l'écran d'accueil ».
- **Android** : ouvrir l'adresse dans Chrome → ⋮ → « Installer l'application ».

Les données (séances, programmes, mesures) restent dans le téléphone. Pensez à exporter une sauvegarde depuis Réglages → Exporter (JSON).

## Organisation du dépôt
- `source/fonte.html` : le code source de l'app (c'est le seul fichier à modifier).
- `source/build_app.py` : construit l'app installable à la racine du dépôt.
- `index.html`, `sw.js`, `manifest.webmanifest`, `icons/` : l'app générée, servie par GitHub Pages. Ne pas les modifier à la main.

## Mettre à jour l'app
```bash
pip install pillow
python source/build_app.py
git add -A
git commit -m "Mise à jour"
git push
```
GitHub Pages republie en une minute environ ; les téléphones récupèrent la nouvelle version à la prochaine ouverture avec du réseau.
