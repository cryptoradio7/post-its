# ARCHITECTURE — Post-its Desktop

Date : 2026-03-20
Auteur : Architecte (coding-team)
Statut : Validee

---

## 1. Contexte

Application de post-its memo pour bureau Linux. Prototype rapide, mono-utilisateur,
persistance locale. Reference visuelle : Sticky Notes Windows (post-its colores
superposables).

---

## 2. Evaluation des stacks

### Option A — Python + GTK3 (PyGObject)

| Critere | Score | Justification |
|---------|-------|---------------|
| Adequation | 5/5 | Fenetres flottantes natives, transparence, drag & drop natif |
| Maturite | 5/5 | GTK3 stable depuis 10+ ans, PyGObject maintenu |
| Ecosysteme | 4/5 | CSS natif pour le styling, Cairo pour le rendu |
| Performance | 5/5 | Natif, pas de runtime lourd |
| Courbe apprentissage | 3/5 | GTK un peu verbeux mais bien documente |
| Dispo locale | 5/5 | Python 3.12 + GTK3 deja installes |
| **Total** | **27/30** | |

### Option B — Python + GTK4 (PyGObject)

| Critere | Score | Justification |
|---------|-------|---------------|
| Adequation | 4/5 | API plus moderne mais moins de controle sur le window management |
| Maturite | 3/5 | GTK4 plus recent, moins d'exemples disponibles |
| Ecosysteme | 3/5 | Transition en cours, certaines APIs changent |
| Performance | 5/5 | Natif |
| Courbe apprentissage | 2/5 | API differente de GTK3, moins de tutoriels |
| Dispo locale | 5/5 | Installe |
| **Total** | **22/30** | |

### Option C — Electron (Node.js)

| Critere | Score | Justification |
|---------|-------|---------------|
| Adequation | 4/5 | HTML/CSS = design facile, fenetres multiples possibles |
| Maturite | 5/5 | Tres mature |
| Ecosysteme | 5/5 | npm, tout existe |
| Performance | 1/5 | ~150 Mo RAM pour des post-its = absurde |
| Courbe apprentissage | 4/5 | HTML/CSS/JS classique |
| Dispo locale | 4/5 | Node present, npm a installer |
| **Total** | **23/30** | Surdimensionne pour le besoin |

### Verdict

**Python + GTK3 (PyGObject)** — score le plus eleve (27/30).

Raisons decisives :
1. **Deja installe** — zero installation supplementaire
2. **Fenetres flottantes natives** — chaque post-it = une fenetre GTK independante, deplacable, redimensionnable
3. **Empreinte memoire minimale** — quelques Mo vs 150+ Mo pour Electron
4. **CSS GTK** — styling des post-its (couleurs, ombres, coins arrondis) via CSS natif
5. **Prototype rapide** — un fichier Python suffit pour le MVP

---

## 3. Stack retenue

| Composant | Choix | Version |
|-----------|-------|---------|
| Langage | Python | 3.12.3 |
| Toolkit GUI | GTK3 via PyGObject | 3.x (systeme) |
| Persistance | JSON fichier local | stdlib |
| Styling | CSS GTK | natif |
| Tests | pytest | a installer |

---

## 4. Architecture applicative

### Pattern : mono-fichier evolutif

Pour un prototype de post-its, pas de clean architecture ni MVC lourd.
Un module principal + un fichier de donnees + un fichier CSS.

```
post-its/
├── BRIEF.md                  # Cahier des charges
├── ARCHITECTURE.md           # Ce document
├── .gitignore
├── references/
│   └── assets/
│       └── sticky_notes_ref.png
├── src/
│   ├── main.py               # Point d'entree + logique applicative
│   ├── note.py               # Classe Note (fenetre GTK d'un post-it)
│   ├── store.py              # Persistance JSON (save/load)
│   └── style.css             # Theme visuel des post-its
├── data/
│   └── notes.json            # Donnees utilisateur (gitignore)
└── tests/
    └── test_store.py         # Tests persistance
```

### Composants

#### main.py — Controleur principal
- Charge les notes depuis `data/notes.json` au demarrage
- Cree une fenetre GTK par note existante
- Bouton "+" flottant ou menu tray pour creer un nouveau post-it
- Sauvegarde automatique a chaque modification (debounce 500ms)
- Gere le cycle de vie GTK (Gtk.main)

#### note.py — Fenetre post-it
- Chaque post-it = une `Gtk.Window` independante
  - Type POPUP ou UTILITY pour rester au-dessus sans barre de titre lourde
  - Decoree minimalement (pas de barre de titre standard)
  - Deplacable par drag sur la zone de titre
  - Redimensionnable
- Contenu : `Gtk.TextView` pour edition libre
- Barre de titre custom : couleur du post-it + bouton fermer (supprimer)
- Menu clic droit : changer couleur, supprimer
- Couleurs : jaune (#FDFD96), vert (#77DD77), bleu (#AEC6CF), rose (#FFB7CE)

#### store.py — Persistance
- Format JSON simple :
  ```json
  {
    "notes": [
      {
        "id": "uuid",
        "content": "texte du post-it",
        "color": "#FDFD96",
        "x": 100, "y": 200,
        "width": 250, "height": 250,
        "created": "2026-03-20T10:00:00",
        "modified": "2026-03-20T10:05:00"
      }
    ]
  }
  ```
- Sauvegarde atomique (ecrire dans .tmp puis rename)
- Creation auto du fichier si absent

#### style.css — Theme visuel
- Fond colore par post-it (classe CSS dynamique)
- Ombre portee legere (si supporte)
- Coins legerement arrondis
- Police : sans-serif 11pt
- Zone de titre : meme couleur, legerement plus fonce

---

## 5. Flux utilisateur MVP

```
Lancement (main.py)
  ├── Charger notes.json
  ├── Pour chaque note → creer fenetre post-it
  └── Afficher indicateur systeme (icone tray ou fenetre controle)

Creer un post-it
  ├── Clic sur "+" → nouvelle fenetre jaune par defaut
  ├── Position : centre ecran (decalee si deja un post-it la)
  └── Sauvegarde auto

Editer
  ├── Clic dans le post-it → focus TextView
  ├── Taper du texte → sauvegarde auto (debounce)
  └── Deplacer/redimensionner → sauvegarde position

Supprimer
  ├── Clic bouton X sur le post-it
  ├── Suppression immediate (pas de confirmation — prototype)
  └── Sauvegarde auto

Fermer l'app
  └── Sauvegarde finale → toutes les fenetres se ferment
```

---

## 6. Decisions techniques

| Decision | Justification |
|----------|---------------|
| 1 fenetre GTK par post-it | Comportement natif : chaque note est independante sur le bureau, comme Sticky Notes Windows |
| JSON pour la persistance | Suffisant pour < 100 notes, lisible, pas de dependance externe |
| Pas de base de donnees | SQLite serait overkill pour ce volume |
| Pas de systray pour le MVP | Complexite inutile — une fenetre "controle" avec le bouton + suffit |
| Sauvegarde atomique | Eviter la corruption si crash pendant l'ecriture |
| CSS GTK pour le theme | Separation style/logique, facile a modifier |
| Pas de virtualenv | Prototype avec uniquement des libs systeme (PyGObject) — zero pip install pour le MVP |

---

## 7. Outils manquants

| Outil | Statut | Action |
|-------|--------|--------|
| Python 3.12 | OK | — |
| GTK3 + PyGObject | OK | — |
| git | OK | — |
| gh CLI | Absent | A installer pour le push GitHub (`sudo apt install gh` ou `conda install gh`) |
| python3-tk | Absent | Non necessaire (on utilise GTK) |
| pytest | Absent | `pip install pytest` quand on attaque les tests |

---

## 8. Contraintes et limites

- **Mono-utilisateur** : pas de sync, pas de conflit
- **Pas de chiffrement** : les notes sont en clair dans `data/notes.json`
- **Pas d'autostart** : l'utilisateur lance manuellement (ajout `.desktop` possible plus tard)
- **Pas de recherche** : MVP sans barre de recherche
- **Pas d'undo** : prototype — edition directe sans historique
