"""
Thalamus (Neural Relay) - Gemini CLI Wrapper
=============================================
Utilise le quota Premium (1500 req/jour) via Gemini Code Assist.
AUCUN coût Vertex AI / Cloud.

Auth: OAuth Standard (Enterprise Tier)
"""

import subprocess
import os
import json

# Force l'utilisation de GCA (Gemini Code Assist) = quota Premium
os.environ["GOOGLE_GENAI_USE_GCA"] = "true"


def trinity_query_cli(prompt: str, json_output: bool = False, timeout: int = 60) -> str:
    """
    Appelle la CLI Gemini (incluse dans l'abonnement Premium)
    pour économiser les crédits Cloud.

    Args:
        prompt: Le prompt à envoyer à Gemini
        json_output: Si True, demande une réponse JSON brute
        timeout: Timeout en secondes

    Returns:
        La réponse de Gemini (texte ou JSON string)
    """
    try:
        # Si JSON demandé, on ajoute l'instruction au prompt
        if json_output:
            prompt = f"{prompt}\n\nRéponds uniquement au format JSON brut sans balises markdown."

        # Syntaxe CLI 2026: gemini "prompt" (positional)
        process = subprocess.run(
            ["gemini", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            env={**os.environ, "GOOGLE_GENAI_USE_GCA": "true"},
        )

        if process.returncode == 0:
            output = process.stdout.strip()
            # Nettoie les logs de la CLI si présents
            if "Loaded cached credentials." in output:
                output = output.replace("Loaded cached credentials.", "").strip()
            return output
        else:
            return f"Erreur CLI (code {process.returncode}): {process.stderr}"

    except subprocess.TimeoutExpired:
        return "Erreur: Timeout dépassé"
    except FileNotFoundError:
        return (
            "CLI Gemini non installée. Lancez: sudo npm install -g @google/gemini-cli"
        )


def trinity_query_cli_json(prompt: str, timeout: int = 60) -> dict:
    """
    Version JSON du wrapper - parse automatiquement la réponse.

    Returns:
        dict parsé ou {"error": "message"} en cas d'échec
    """
    response = trinity_query_cli(prompt, json_output=True, timeout=timeout)

    try:
        # Essaie d'extraire le JSON de la réponse
        # Parfois le modèle entoure de ```json ... ```
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        return json.loads(response)
    except json.JSONDecodeError:
        return {"error": "Parsing JSON échoué", "raw": response}


# === Test rapide ===
if __name__ == "__main__":
    print("🔥 Test CLI Gemini (Quota Premium)")
    print("=" * 40)

    # Test simple
    response = trinity_query_cli("Dis 'Trinity connectée' en une phrase.")
    print(f"Réponse: {response}")

    # Test JSON
    print("\n📊 Test JSON:")
    json_response = trinity_query_cli_json(
        "Donne-moi un objet JSON avec les clés 'status' et 'message'"
    )
    print(f"JSON: {json_response}")
