#!/usr/bin/env bash
# Copia de seguridad de la base de datos de DragonBall-EnhancedAPI (catálogo,
# colección, mazos y escáner) y de sus volúmenes de datos (imágenes propias de impresiones),
# con verificación, rotación y copia opcional a otro equipo.
#
# Uso:    scripts/backup.sh          (a diario lo lanza dbs-backup.timer; desde el admin,
#         «Hacer copia ahora» deja $BACKUP_DIR/request/now y dbs-backup-request.path la lanza)
# Config: variables de entorno o ~/.config/dbs-backup.env
#   BACKUP_DIR       carpeta de las copias              (~/backups/dbs)
#   BACKUP_PROJECTS  clones a respaldar, separados por espacios
#                    (este clon)
#   KEEP_DAILY       copias diarias a conservar          (7)
#   KEEP_WEEKLY      copias semanales (domingos)         (4)
#   BACKUP_REMOTE    destino rsync fuera del equipo, p. ej. usuario@192.168.178.83:  (vacío = no)
#   BACKUP_SSH_KEY   clave SSH para BACKUP_REMOTE        (~/.ssh/dbs_backup_ed25519)
#
# Restaurar: pg_restore --clean -U <usuario> -d <bd> < copia.dump (dentro del contenedor db),
# y los volúmenes con: docker run --rm -v <proyecto>_<volumen>:/data -i alpine tar xzf - -C /data < copia.tgz
set -Eeuo pipefail

CONF="${DBS_BACKUP_CONF:-$HOME/.config/dbs-backup.env}"
# shellcheck disable=SC1090
[ -f "$CONF" ] && . "$CONF"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/dbs}"
BACKUP_PROJECTS="${BACKUP_PROJECTS:-$(cd "$(dirname "$0")/.." && pwd)}"
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"
BACKUP_REMOTE="${BACKUP_REMOTE:-}"
BACKUP_SSH_KEY="${BACKUP_SSH_KEY:-$HOME/.ssh/dbs_backup_ed25519}"

log() { echo "$*"; logger -t dbs-backup "$*" 2>/dev/null || true; }
env_value() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '"' || true; }

STAMP="$(date +%Y-%m-%d_%H%M)"
TARGET="$BACKUP_DIR/daily/$STAMP"
mkdir -p "$TARGET"
chmod 700 "$BACKUP_DIR"

# Pedida desde el admin: se quita la petición (si no, dbs-backup-request.path la volvería a lanzar).
# La carpeta la monta el backend con escritura (docker-compose.prod.yml).
TRIGGER="programada"
mkdir -p "$BACKUP_DIR/request"
if [ -e "$BACKUP_DIR/request/now" ]; then
    TRIGGER="pedida desde el admin"
    rm -f "$BACKUP_DIR/request/now"
fi
# Mientras dura, el admin la enseña como «en curso».
RUNNING_FILE="$BACKUP_DIR/running.json"
printf '{"started_at": "%s", "trigger": "%s"}\n' "$(date -Iseconds)" "$TRIGGER" > "$RUNNING_FILE"

# Estado de la última copia, para /api/health/ (el backend monta esta carpeta en solo lectura).
STATUS_FILE="$BACKUP_DIR/last_status.json"
REMOTE_STATUS="off"
STEP="inicio"
write_status() {  # write_status <ok|error> <mensaje>
    local q="'" msg="${2//\\//}"   # el mensaje va dentro de un JSON: sin \, comillas dobles ni saltos de línea
    msg="${msg//\"/$q}"
    msg="$(printf '%s' "$msg" | tr '\n\t\r' '   ' | tr -d '\000-\037')"
    printf '{"status": "%s", "finished_at": "%s", "target": "%s", "size": "%s", "remote": "%s", "message": "%s", "trigger": "%s"}\n' \
        "$1" "$(date -Iseconds)" "$TARGET" "$(du -sh "$TARGET" 2>/dev/null | cut -f1)" "$REMOTE_STATUS" "$msg" "$TRIGGER" \
        > "$STATUS_FILE.tmp" && mv "$STATUS_FILE.tmp" "$STATUS_FILE"
}
# El error de verdad, para el estado (y el aviso por Telegram): el comando que falló y lo
# último que escribió en la salida de errores.
ERR_LOG="$(mktemp)"
exec 2> >(tee -a "$ERR_LOG" >&2)
FAILED_CMD=""
trap 'FAILED_CMD="línea $LINENO: $BASH_COMMAND"' ERR
on_exit() {
    local code=$? detail=""
    rm -f "$RUNNING_FILE"
    if [ "$code" -ne 0 ]; then
        [ -n "$FAILED_CMD" ] && detail=" · ${FAILED_CMD:0:200}"
        local errors
        errors="$(tail -n 3 "$ERR_LOG" 2>/dev/null | tr '\n' ' ' | cut -c1-300 || true)"
        [ -n "${errors// /}" ] && detail="$detail · $errors"
        write_status error "falló en: $STEP (código $code)$detail"
        log "copia FALLIDA en: $STEP (código $code)$detail"
    fi
    rm -f "$ERR_LOG"
}
trap on_exit EXIT

for dir in $BACKUP_PROJECTS; do
    name="$(basename "$dir")"
    cd "$dir"
    user="$(env_value POSTGRES_USER)"; user="${user:-dbs}"
    db="$(env_value POSTGRES_DB)"; db="${db:-dbs}"

    STEP="base de datos de $name"
    # Base de datos: formato custom de pg_dump (comprimido, restaurable con pg_restore).
    docker compose exec -T db pg_dump -U "$user" -d "$db" -Fc > "$TARGET/$name.dump"
    # Verificación: el volcado se puede leer entero.
    docker compose exec -T db pg_restore -l < "$TARGET/$name.dump" > /dev/null
    log "$name: base de datos $(du -h "$TARGET/$name.dump" | cut -f1)"

    # Volúmenes de datos (p. ej. imágenes propias de impresiones). La BD y Redis no: la BD
    # ya va en el volcado y Redis solo tiene datos temporales.
    project="$(docker compose config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["name"])')"
    for vol in $(docker compose config --volumes); do
        case "$vol" in pgdata|redisdata) continue ;; esac
        STEP="volumen $vol de $name"
        # Sin las fotos de los escaneos (scans/): duran un día y solo sirven para revisar un
        # escaneo reciente. Sí van las imágenes propias de impresiones (printings/), que no están en otro sitio.
        docker run --rm -v "${project}_${vol}:/data:ro" alpine:3.20 tar czf - -C /data --exclude=./scans . > "$TARGET/$name-$vol.tgz"
        tar tzf "$TARGET/$name-$vol.tgz" > /dev/null
        log "$name: volumen $vol $(du -h "$TARGET/$name-$vol.tgz" | cut -f1)"
    done
done

# Copia semanal (domingos), con enlaces duros: no ocupa espacio extra.
STEP="copia semanal"
if [ "$(date +%u)" = "7" ]; then
    mkdir -p "$BACKUP_DIR/weekly"
    cp -al "$TARGET" "$BACKUP_DIR/weekly/$STAMP"
fi

# Rotación. Con find, no con ls: un ls sobre una carpeta vacía sale con error y, con
# pipefail, daba la copia por fallida (pasó el 28/10/2026 con weekly/ vacía).
STEP="rotación"
prune() {
    local keep="$1" folder="$2"
    [ -d "$folder" ] || return 0
    find "$folder" -mindepth 1 -maxdepth 1 -type d | sort | head -n "-$keep" | xargs -r rm -rf
}
prune "$KEEP_DAILY" "$BACKUP_DIR/daily"
prune "$KEEP_WEEKLY" "$BACKUP_DIR/weekly"

# Copia fuera del equipo. Si falla, la copia local sigue siendo buena: se anota en el estado
# (y /api/health/ lo avisa) en vez de dar toda la copia por fallida.
if [ -n "$BACKUP_REMOTE" ]; then
    STEP="copia remota"
    if rsync -aH --delete --exclude /running.json --exclude /request/ -e "ssh -i $BACKUP_SSH_KEY -o BatchMode=yes -o StrictHostKeyChecking=accept-new" \
        "$BACKUP_DIR/" "$BACKUP_REMOTE"; then
        REMOTE_STATUS="ok"
        log "copia remota a $BACKUP_REMOTE"
    else
        REMOTE_STATUS="error"
        log "copia remota a $BACKUP_REMOTE FALLIDA"
    fi
fi

log "copia completa: $TARGET ($(du -sh "$TARGET" | cut -f1))"
write_status ok "copia completa"
