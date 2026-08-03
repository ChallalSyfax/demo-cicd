"""API Flask minimale : gestion d'une collection d'« items » en mémoire.

Cette application sert uniquement de support aux expérimentations CI/CD
(tests, couverture, qualité, SBOM, scan de vulnérabilités). Elle ne
comporte volontairement ni base de données, ni authentification, ni
frontend : le stockage est un simple dictionnaire en mémoire, réinitialisé
à chaque appel de ``create_app`` (utile pour l'isolation des tests).
"""

from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, request


def create_app() -> Flask:
    """Crée et configure une instance de l'application Flask.

    L'utilisation d'une *application factory* permet de repartir d'un
    stockage vide à chaque instanciation, ce qui rend les tests fiables
    et indépendants les uns des autres.
    """
    app = Flask(__name__)

    # Stockage en mémoire, propre à cette instance d'application.
    items: dict[int, dict[str, Any]] = {}
    counter = {"next_id": 1}

    @app.get("/health")
    def health() -> Any:
        """Sonde de disponibilité : renvoie l'état de l'application."""
        return jsonify({"status": "ok"}), 200

    @app.get("/items")
    def list_items() -> Any:
        """Renvoie la liste de tous les items enregistrés."""
        return jsonify(list(items.values())), 200

    @app.post("/items")
    def create_item() -> Any:
        """Crée un nouvel item.

        Attend un corps JSON contenant au minimum un champ ``name`` non
        vide. Renvoie 400 si le corps est absent ou invalide, 201 sinon.
        """
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "corps JSON invalide ou manquant"}), 400

        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            return jsonify({"error": "le champ 'name' est requis"}), 400

        item = {
            "id": counter["next_id"],
            "name": name.strip(),
            "description": payload.get("description", ""),
        }
        items[item["id"]] = item
        counter["next_id"] += 1
        return jsonify(item), 201

    @app.get("/items/<int:item_id>")
    def get_item(item_id: int) -> Any:
        """Renvoie un item par son identifiant, ou 404 s'il n'existe pas."""
        item = items.get(item_id)
        if item is None:
            return jsonify({"error": "item introuvable"}), 404
        return jsonify(item), 200

    return app


# Point d'entrée pour un lancement direct en développement (``python -m app.app``).
if __name__ == "__main__":  # pragma: no cover
    create_app().run(host="127.0.0.1", port=5000, debug=True)
