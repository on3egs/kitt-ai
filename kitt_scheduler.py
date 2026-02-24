#!/usr/bin/env python3
"""
KITT NIGHT SCHEDULER
Planificateur d'ameliorations autonomes de la Web UI KYRONEX
Usage: python3 kitt_scheduler.py
"""

import json, os, sys, time, subprocess, signal, re
from datetime import datetime, date
from pathlib import Path

# ── Chemins ──────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "kitt_schedule.json"
PID_FILE    = BASE_DIR / "kitt_scheduler.pid"
LOG_FILE    = Path("/tmp/kitt_scheduler.log")
IMPROVE_SH  = BASE_DIR / "kitt_night_improve.sh"

# ── Couleurs ANSI ─────────────────────────────────────────────────
R  = '\033[0;31m';   G  = '\033[0;32m';   Y  = '\033[1;33m'
C  = '\033[0;36m';   M  = '\033[0;35m';   W  = '\033[1;37m'
DG = '\033[0;90m';   NC = '\033[0m';       B  = '\033[1m'

# ── Whiptail helper ───────────────────────────────────────────────
def wt_input(title, prompt, default=""):
    r = subprocess.run(
        ["whiptail", "--title", title, "--inputbox", prompt, "10", "60", default],
        capture_output=True, text=True
    )
    return r.returncode == 0, r.stderr.strip()

def wt_menu(title, prompt, options):
    """options = list of (tag, description) tuples"""
    args = ["whiptail", "--title", title, "--menu", prompt, "22", "70", str(len(options))]
    for tag, desc in options:
        args += [str(tag), desc]
    r = subprocess.run(args, capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()

def wt_checklist(title, prompt, options):
    """options = list of (tag, desc, state) tuples"""
    args = ["whiptail", "--title", title, "--checklist", prompt, "22", "70", str(len(options))]
    for tag, desc, state in options:
        args += [str(tag), desc, state]
    r = subprocess.run(args, capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()

def wt_yesno(title, prompt):
    r = subprocess.run(
        ["whiptail", "--title", title, "--yesno", prompt, "10", "60"],
        capture_output=True, text=True
    )
    return r.returncode == 0

def wt_msg(title, msg, h=12, w=60):
    subprocess.run(
        ["whiptail", "--title", title, "--msgbox", msg, str(h), str(w)],
        capture_output=True
    )

# ── Config JSON ───────────────────────────────────────────────────
def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except:
            pass
    return {"windows": [], "next_id": 1}

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))

# ── Validation heure ──────────────────────────────────────────────
def parse_time(s):
    """Retourne (h, m) ou None si invalide"""
    s = s.strip()
    m = re.match(r'^(\d{1,2})[h:H](\d{2})$', s) or re.match(r'^(\d{1,2})$', s)
    if not m:
        return None
    h = int(m.group(1))
    mi = int(m.group(2)) if len(m.groups()) > 1 else 0
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return (h, mi)
    return None

def fmt_time(h, m):
    return f"{h:02d}:{m:02d}"

def time_in_window(start_h, start_m, end_h, end_m):
    """Vrai si l'heure actuelle est dans la fenetre (gere le passage minuit)"""
    now = datetime.now()
    cur = now.hour * 60 + now.minute
    start = start_h * 60 + start_m
    end   = end_h   * 60 + end_m
    if start <= end:
        return start <= cur < end
    else:  # Passe minuit (ex: 22:00 -> 06:00)
        return cur >= start or cur < end

def day_allowed(days):
    """Vrai si aujourd'hui est dans les jours autorises"""
    if "all" in days:
        return True
    day_names = ["lun","mar","mer","jeu","ven","sam","dim"]
    today = day_names[date.today().weekday()]
    return today in days

# ── Daemon ────────────────────────────────────────────────────────
def daemon_log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)

def run_daemon():
    """Boucle principale du daemon planificateur"""
    daemon_log("=== KITT Scheduler daemon demarre ===")
    # Suivi: {window_id: date_last_run}
    last_run = {}
    running_pids = {}

    while True:
        try:
            cfg = load_config()
            today_str = date.today().isoformat()

            for win in cfg.get("windows", []):
                if not win.get("enabled", True):
                    continue

                wid = win["id"]
                days      = win.get("days", ["all"])
                start_h, start_m = win["start_h"], win["start_m"]
                end_h,   end_m   = win["end_h"],   win["end_m"]
                iterations       = win.get("iterations", 10)

                # Verifier si deja tourne aujourd'hui
                if last_run.get(wid) == today_str:
                    continue

                # Verifier si dans la fenetre horaire et le bon jour
                if not time_in_window(start_h, start_m, end_h, end_m):
                    continue
                if not day_allowed(days):
                    continue

                # Verifier qu'une amelioration n'est pas deja en cours
                if wid in running_pids:
                    pid = running_pids[wid]
                    try:
                        os.kill(pid, 0)  # Check si process existe
                        daemon_log(f"Fenetre {wid}: amelioration deja en cours (PID {pid})")
                        continue
                    except ProcessLookupError:
                        del running_pids[wid]

                # Lancer les ameliorations
                log_path = f"/tmp/kitt_win{wid}_{today_str}.log"
                win_type = win.get("type", "auto")

                # Choisir le script selon la cible (interface ou site GitHub)
                target_script = Path(win.get("script", str(IMPROVE_SH)))
                if not target_script.exists():
                    target_script = IMPROVE_SH
                env = os.environ.copy()
                env["PATH"] = f"/home/kitt/.local/bin:{env.get('PATH', '')}"

                if win_type == "custom":
                    task_file = win.get("task_file", "")
                    if not Path(task_file).exists():
                        daemon_log(f"Fenetre {wid}: fichier tache introuvable {task_file}")
                        continue
                    daemon_log(f"Fenetre {wid}: tache custom ({iterations}x) — script: {target_script.name}")
                    proc = subprocess.Popen(
                        ["bash", str(target_script), str(iterations), task_file],
                        cwd=str(BASE_DIR),
                        stdout=open(log_path, "w"),
                        stderr=subprocess.STDOUT,
                        env=env,
                    )
                else:
                    daemon_log(f"Fenetre {wid}: ameliorations auto ({iterations}x) — script: {target_script.name}")
                    proc = subprocess.Popen(
                        ["bash", str(target_script), str(iterations)],
                        cwd=str(BASE_DIR),
                        stdout=open(log_path, "w"),
                        stderr=subprocess.STDOUT,
                        env=env,
                    )
                running_pids[wid] = proc.pid
                last_run[wid] = today_str
                daemon_log(f"Fenetre {wid}: PID {proc.pid} — log: {log_path}")

        except Exception as e:
            daemon_log(f"ERREUR daemon: {e}")

        time.sleep(60)  # Verifier toutes les minutes

def start_daemon():
    """Fork le daemon en arriere-plan"""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)
            return pid, False  # Deja actif
        except (ProcessLookupError, ValueError):
            PID_FILE.unlink(missing_ok=True)

    pid = os.fork()
    if pid == 0:
        # Processus enfant — devient le daemon
        os.setsid()
        pid2 = os.fork()
        if pid2 != 0:
            os._exit(0)
        PID_FILE.write_text(str(os.getpid()))
        sys.stdin  = open(os.devnull)
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        run_daemon()
        os._exit(0)
    else:
        os.waitpid(pid, 0)
        time.sleep(0.5)
        if PID_FILE.exists():
            return int(PID_FILE.read_text().strip()), True
        return None, False

def stop_daemon():
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        return True
    except:
        PID_FILE.unlink(missing_ok=True)
        return False

def daemon_status():
    if not PID_FILE.exists():
        return False, None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True, pid
    except:
        PID_FILE.unlink(missing_ok=True)
        return False, None

# ── Menus ─────────────────────────────────────────────────────────
def menu_add_window():
    cfg = load_config()

    # Heure de debut
    ok, val = wt_input("Nouvelle fenetre", "Heure de DEBUT (ex: 22:00 ou 22h00):", "22:00")
    if not ok: return
    t_start = parse_time(val)
    if not t_start:
        wt_msg("Erreur", f"Heure invalide: '{val}'\nFormat: HH:MM ou HHhMM")
        return

    # Heure de fin
    ok, val = wt_input("Nouvelle fenetre", "Heure de FIN (ex: 06:00 ou 6h00):", "06:00")
    if not ok: return
    t_end = parse_time(val)
    if not t_end:
        wt_msg("Erreur", f"Heure invalide: '{val}'\nFormat: HH:MM ou HHhMM")
        return

    # Nombre d'iterations
    ok, val = wt_input("Nouvelle fenetre", "Nombre d'ameliorations (iterations):", "10")
    if not ok: return
    try:
        iterations = max(1, min(50, int(val)))
    except:
        wt_msg("Erreur", "Nombre invalide. Entrez un chiffre entre 1 et 50.")
        return

    # Jours
    day_opts = [
        ("all", "Tous les jours",  "ON"),
        ("lun", "Lundi",           "OFF"),
        ("mar", "Mardi",           "OFF"),
        ("mer", "Mercredi",        "OFF"),
        ("jeu", "Jeudi",           "OFF"),
        ("ven", "Vendredi",        "OFF"),
        ("sam", "Samedi",          "OFF"),
        ("dim", "Dimanche",        "OFF"),
    ]
    ok, val = wt_checklist("Jours actifs", "Selectionnez les jours (Espace pour cocher):", day_opts)
    if not ok: return
    days = [d.strip('"') for d in val.split()] if val else ["all"]
    if not days:
        days = ["all"]

    # Sauvegarder
    win_id = cfg.get("next_id", 1)
    cfg["next_id"] = win_id + 1

    # Nom de la fenetre
    ok, name = wt_input("Nouvelle fenetre", "Nom de cette fenetre (optionnel):", f"Fenetre {win_id}")
    if not ok: name = f"Fenetre {win_id}"

    cfg["windows"].append({
        "id": win_id,
        "name": name or f"Fenetre {win_id}",
        "start_h": t_start[0], "start_m": t_start[1],
        "end_h":   t_end[0],   "end_m":   t_end[1],
        "iterations": iterations,
        "days": days,
        "enabled": True,
        "created": datetime.now().isoformat()
    })
    save_config(cfg)

    start_str = fmt_time(*t_start)
    end_str   = fmt_time(*t_end)
    jours = ", ".join(days)
    wt_msg("Fenetre ajoutee !",
           f"  Nom        : {name}\n"
           f"  Horaire    : {start_str} --> {end_str}\n"
           f"  Iterations : {iterations}x\n"
           f"  Jours      : {jours}\n\n"
           f"  KITT ameliorera ta page web\n"
           f"  pendant que tu dors !", 14, 60)

def menu_list_windows():
    cfg = load_config()
    wins = cfg.get("windows", [])
    if not wins:
        wt_msg("Fenetres", "Aucune fenetre programmee.\nUtilisez 'Ajouter' pour en creer une.")
        return

    lines = []
    for w in wins:
        s = fmt_time(w["start_h"], w["start_m"])
        e = fmt_time(w["end_h"],   w["end_m"])
        jours = ",".join(w.get("days", ["all"]))
        status = "ON " if w.get("enabled", True) else "OFF"
        lines.append(f"[{status}] #{w['id']} {w.get('name','?')[:18]:<18} {s}->{e}  {w['iterations']}x  {jours}")

    msg = "\n".join(lines)
    wt_msg("Fenetres programmees", msg, min(6 + len(lines), 22), 72)

def menu_delete_window():
    cfg = load_config()
    wins = [w for w in cfg.get("windows", []) if True]
    if not wins:
        wt_msg("Supprimer", "Aucune fenetre a supprimer.")
        return

    opts = []
    for w in wins:
        s = fmt_time(w["start_h"], w["start_m"])
        e = fmt_time(w["end_h"],   w["end_m"])
        opts.append((str(w["id"]), f"{w.get('name','?')[:16]:<16} {s}->{e} {w['iterations']}x"))

    ok, val = wt_menu("Supprimer une fenetre", "Selectionnez la fenetre a supprimer:", opts)
    if not ok or not val: return

    win_id = int(val)
    win = next((w for w in wins if w["id"] == win_id), None)
    if not win: return

    if wt_yesno("Confirmer", f"Supprimer la fenetre '{win.get('name','?')}' ?"):
        cfg["windows"] = [w for w in cfg["windows"] if w["id"] != win_id]
        save_config(cfg)
        wt_msg("Supprime", f"Fenetre #{win_id} supprimee.")

def menu_toggle_window():
    cfg = load_config()
    wins = cfg.get("windows", [])
    if not wins:
        wt_msg("Activer/Desactiver", "Aucune fenetre configuree.")
        return

    opts = []
    for w in wins:
        s = fmt_time(w["start_h"], w["start_m"])
        e = fmt_time(w["end_h"],   w["end_m"])
        st = "ON " if w.get("enabled", True) else "OFF"
        opts.append((str(w["id"]), f"[{st}] {w.get('name','?')[:16]:<16} {s}->{e} {w['iterations']}x"))

    ok, val = wt_menu("Activer / Desactiver", "Selectionnez la fenetre:", opts)
    if not ok or not val: return

    win_id = int(val)
    for w in cfg["windows"]:
        if w["id"] == win_id:
            w["enabled"] = not w.get("enabled", True)
            status = "activee" if w["enabled"] else "desactivee"
            save_config(cfg)
            wt_msg("Mise a jour", f"Fenetre #{win_id} '{w.get('name','?')}' {status}.")
            break

def menu_daemon():
    active, pid = daemon_status()

    status_line = f"Planificateur : ACTIF (PID {pid})" if active else "Planificateur : ARRETE"
    cfg = load_config()
    nb_win = len(cfg.get("windows", []))
    nb_on  = len([w for w in cfg.get("windows", []) if w.get("enabled", True)])

    opts = []
    if not active:
        opts.append(("start", "Demarrer le planificateur"))
    else:
        opts.append(("stop",  "Arreter le planificateur"))
        opts.append(("log",   "Voir les derniers logs"))
    opts.append(("back", "Retour au menu principal"))

    ok, val = wt_menu("Planificateur",
        f"{status_line}\nFenetres : {nb_on}/{nb_win} actives",
        opts)
    if not ok or val == "back": return

    if val == "start":
        pid, launched = start_daemon()
        if launched:
            wt_msg("Planificateur", f"Planificateur demarre ! PID: {pid}\n\nKITT va surveiller tes fenetres\net ameliorer ta page web automatiquement.")
        else:
            wt_msg("Info", f"Planificateur deja actif. PID: {pid}")

    elif val == "stop":
        if stop_daemon():
            wt_msg("Planificateur", "Planificateur arrete.")
        else:
            wt_msg("Info", "Le planificateur n'etait pas actif.")

    elif val == "log":
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text().splitlines()
            last = lines[-20:] if len(lines) > 20 else lines
            wt_msg("Logs du planificateur", "\n".join(last), 24, 78)
        else:
            wt_msg("Logs", "Aucun log disponible.")

def detach_run(cmd, log_path, cwd=None):
    """Lance un processus completement detache du terminal.
    Survit a la fermeture du terminal (double fork + setsid)."""
    pid = os.fork()
    if pid == 0:
        os.setsid()
        pid2 = os.fork()
        if pid2 != 0:
            os._exit(0)
        # Petit-fils : completement detache
        with open(log_path, 'w') as logf:
            subprocess.run(cmd, stdout=logf, stderr=logf,
                           cwd=cwd or str(BASE_DIR))
        os._exit(0)
    else:
        os.waitpid(pid, 0)
        time.sleep(0.3)

def menu_run_now():
    cfg = load_config()
    ok, val = wt_input("Lancer maintenant",
        "Nombre d'ameliorations a lancer MAINTENANT:", "5")
    if not ok: return
    try:
        n = max(1, min(50, int(val)))
    except:
        wt_msg("Erreur", "Nombre invalide.")
        return

    if wt_yesno("Confirmer", f"Lancer {n} amelioration(s) maintenant ?\n\nCela va modifier index.html\nKITT travaille en arriere-plan.\n\nContinue meme si tu fermes le terminal !"):
        log = f"/tmp/kitt_now_{datetime.now().strftime('%H%M%S')}.log"
        detach_run(["bash", str(IMPROVE_SH), str(n)], log)
        wt_msg("Lance !",
               f"KITT ameliore ta page ({n}x) !\n\n"
               f"Log : {log}\n\n"
               f"Suivre : tail -f {log}\n\n"
               f"Continue meme terminal ferme !")

def menu_custom_task():
    """Tache personnalisee : l'utilisateur ecrit sa propre demande a Claude."""

    # ── Etape 1 : Ecrire la tache dans nano ──────────────────────
    tmp = Path("/tmp/kitt_custom_task.txt")
    template = (
        "# Ecrivez votre demande a KITT ci-dessous (supprimez ces lignes #)\n"
        "# Exemple : Ajoute un bouton plein ecran dans le header de\n"
        "#           /home/kitt/kitt-ai/static/index.html\n"
        "# Vous pouvez ecrire autant de lignes que vous voulez.\n"
        "#\n"
    )
    tmp.write_text(template)

    # Ouvrir nano pour saisie libre
    subprocess.run(["nano", "--softwrap", str(tmp)])

    # Lire et nettoyer (enlever les lignes #)
    raw = tmp.read_text()
    lines = [l for l in raw.splitlines()
             if not l.strip().startswith('#') and l.strip()]
    task = '\n'.join(lines).strip()

    if not task:
        wt_msg("Annule", "Aucune tache saisie. Retour au menu.")
        return

    # ── Etape 2 : Apercu + confirmation ─────────────────────────
    preview = task[:180] + ('...' if len(task) > 180 else '')
    ok, choice = wt_menu(
        "Ma tache personnalisee",
        f"Tache :\n{preview}\n\nQuand executer ?",
        [
            ("now1",     "Maintenant — 1 fois"),
            ("now3",     "Maintenant — 3 fois"),
            ("now5",     "Maintenant — 5 fois"),
            ("schedule", "Programmer dans une fenetre horaire"),
        ]
    )
    if not ok: return

    if choice.startswith("now"):
        n = int(choice[3:]) if choice[3:].isdigit() else 1
        log = f"/tmp/kitt_custom_{datetime.now().strftime('%H%M%S')}.log"

        # Sauvegarder la tache dans un fichier pour le script
        task_file = Path("/tmp/kitt_running_task.txt")
        task_file.write_text(task)

        detach_run(
            ["bash", str(IMPROVE_SH), str(n), str(task_file)],
            log
        )
        wt_msg("Tache lancee !",
               f"Claude travaille en arriere-plan !\n\n"
               f"Log : {log}\n\n"
               f"Suivre : tail -f {log}\n\n"
               f"Continue meme terminal ferme !\n"
               f"Versions sauvees dans : static/versions/")

    elif choice == "schedule":
        # Ajouter comme fenetre programmee avec tache custom
        cfg = load_config()

        ok2, hd = wt_input("Fenetre horaire", "Heure de DEBUT (ex: 22:00):", "22:00")
        if not ok2: return
        t_start = parse_time(hd)
        if not t_start:
            wt_msg("Erreur", f"Heure invalide: '{hd}'"); return

        ok2, hf = wt_input("Fenetre horaire", "Heure de FIN (ex: 06:00):", "06:00")
        if not ok2: return
        t_end = parse_time(hf)
        if not t_end:
            wt_msg("Erreur", f"Heure invalide: '{hf}'"); return

        ok2, nval = wt_input("Repetitions", "Combien de fois executer la tache ?", "3")
        if not ok2: return
        try: n = max(1, min(20, int(nval)))
        except: n = 3

        win_id = cfg.get("next_id", 1)
        cfg["next_id"] = win_id + 1

        # Sauvegarder la tache dans un fichier dedie
        task_file = BASE_DIR / f"task_{win_id}.txt"
        task_file.write_text(task)

        cfg["windows"].append({
            "id": win_id,
            "name": f"Custom #{win_id}: {task[:30]}...",
            "type": "custom",
            "task_file": str(task_file),
            "start_h": t_start[0], "start_m": t_start[1],
            "end_h":   t_end[0],   "end_m":   t_end[1],
            "iterations": n,
            "days": ["all"],
            "enabled": True,
            "created": datetime.now().isoformat()
        })
        save_config(cfg)
        wt_msg("Programmee !",
               f"Tache programmee de {fmt_time(*t_start)}\n"
               f"a {fmt_time(*t_end)}, {n} fois.\n\n"
               f"N'oublie pas de demarrer\nle planificateur !")

# ── Menu principal ────────────────────────────────────────────────
def main_menu():
    while True:
        cfg = load_config()
        active, pid = daemon_status()
        nb_win = len(cfg.get("windows", []))
        nb_on  = len([w for w in cfg.get("windows", []) if w.get("enabled", True)])
        daemon_str = f"ACTIF PID:{pid}" if active else "ARRETE"

        opts = [
            ("custom", "Ma tache — Demander quelque chose a Claude"),
            ("now",    "Ameliorations auto MAINTENANT"),
            ("add",    f"Ajouter une fenetre horaire"),
            ("list",   f"Voir les fenetres ({nb_on}/{nb_win} actives)"),
            ("toggle", "Activer / Desactiver une fenetre"),
            ("delete", "Supprimer une fenetre"),
            ("daemon", f"Planificateur : {daemon_str}"),
            ("quit",   "Quitter"),
        ]

        ok, val = wt_menu(
            "KITT NIGHT SCHEDULER",
            "Planificateur d'ameliorations autonomes\nKITT ameliore ta page web quand tu dors !",
            opts
        )

        if not ok or val == "quit":
            active, _ = daemon_status()
            if active:
                if not wt_yesno("Quitter", f"Le planificateur est actif (PID {_}).\nIl continuera en arriere-plan.\n\nQuitter quand meme ?"):
                    continue
            break

        if   val == "custom": menu_custom_task()
        elif val == "add":    menu_add_window()
        elif val == "list":   menu_list_windows()
        elif val == "toggle": menu_toggle_window()
        elif val == "delete": menu_delete_window()
        elif val == "now":    menu_run_now()
        elif val == "daemon": menu_daemon()

# ── Entree ────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Mode daemon interne (appele par fork)
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        run_daemon()
        sys.exit(0)

    # Verifier que le script d'amelioration existe
    if not IMPROVE_SH.exists():
        print(f"{R}ERREUR: {IMPROVE_SH} introuvable !{NC}")
        sys.exit(1)

    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{Y}Au revoir !{NC}")
        sys.exit(0)
