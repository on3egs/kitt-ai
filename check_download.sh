#!/bin/bash
# Script pour vérifier la progression du téléchargement 7B

echo "═══════════════════════════════════════════════════"
echo "  TÉLÉCHARGEMENT QWEN 2.5 7B — Progression"
echo "═══════════════════════════════════════════════════"
echo ""

# Vérifier si le téléchargement est en cours
if pgrep -f "wget.*7B" > /dev/null; then
    echo "✅ Téléchargement en cours..."
    echo ""

    # Afficher les dernières lignes du log
    tail -3 /tmp/download_7b.log 2>/dev/null || echo "Log non disponible"

    echo ""
    echo "Taille actuelle du fichier:"
    du -h models/qwen2.5-7b-instruct-q5_k_m.gguf 2>/dev/null || echo "  Fichier pas encore créé"

    echo ""
    echo "Taille cible: ~4.8G"
    echo ""
    echo "Pour voir le log complet: tail -f /tmp/download_7b.log"

elif [ -f models/qwen2.5-7b-instruct-q5_k_m.gguf ]; then
    SIZE=$(du -h models/qwen2.5-7b-instruct-q5_k_m.gguf | cut -f1)
    echo "✅ Téléchargement TERMINÉ !"
    echo ""
    echo "Fichier: models/qwen2.5-7b-instruct-q5_k_m.gguf"
    echo "Taille: $SIZE"
    echo ""
    echo "Configuration: ✅ Déjà mise à jour dans start_kyronex.sh"
    echo ""
    echo "Prochaine étape:"
    echo "  bash start_kyronex.sh"

else
    echo "❌ Téléchargement pas encore démarré ou échoué"
    echo ""
    echo "Pour lancer le téléchargement:"
    echo "  cd ~/kitt-ai"
    echo "  wget -c https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q5_K_M.gguf -O models/qwen2.5-7b-instruct-q5_k_m.gguf"
fi

echo "═══════════════════════════════════════════════════"
