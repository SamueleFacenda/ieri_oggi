self:
{ config, lib, pkgs, ... }:

let
  cfg = config.services.ieri-oggi;

  stateDir = "/var/lib/ieri-oggi";

  # Genera e persiste una SECRET_KEY casuale al primo avvio, se l'utente non
  # ne fornisce una propria (cfg.secretKeyFile). Gira come utente del servizio
  # dentro la StateDirectory.
  generaSegreto = pkgs.writeShellScript "ieri-oggi-genera-segreto" ''
    set -eu
    dest="$STATE_DIRECTORY/secret_key"
    if [ ! -s "$dest" ]; then
      umask 077
      ${pkgs.coreutils}/bin/head -c 48 /dev/urandom \
        | ${pkgs.coreutils}/bin/base64 > "$dest"
    fi
  '';
in
{
  options.services.ieri-oggi = {
    enable = lib.mkEnableOption "la galleria Ieri & Oggi";

    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
      defaultText = lib.literalExpression "ieri-oggi.packages.\${system}.default";
      description = "Il pacchetto dell'applicazione da eseguire.";
    };

    bind = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1:8000";
      description = "Indirizzo host:porta su cui gunicorn ascolta (locale, dietro reverse proxy).";
    };

    workers = lib.mkOption {
      type = lib.types.ints.positive;
      default = 2;
      description = "Numero di worker gunicorn.";
    };

    passphraseFile = lib.mkOption {
      type = lib.types.path;
      description = ''
        Percorso di un file contenente la passphrase per creare/modificare i
        profili. Consegnato al servizio via systemd LoadCredential: non finisce
        nel Nix store né nell'ambiente del processo.
      '';
    };

    secretKeyFile = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = ''
        Percorso di un file con la SECRET_KEY per firmare i cookie di sessione.
        Se null (default), una chiave casuale viene generata e persistita in
        ${stateDir}/secret_key al primo avvio.
      '';
    };

    maxUploadMb = lib.mkOption {
      type = lib.types.ints.positive;
      default = 250;
      description = "Dimensione massima totale di un upload (MB). Allinea client_max_body_size in nginx.";
    };

    cookieSecure = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Imposta il flag Secure sui cookie di sessione. Attivalo quando servi dietro HTTPS.";
    };

    trustProxy = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = ''
        Onora gli header X-Forwarded-* (Proto/Host/For/Prefix) di un reverse
        proxy fidato. Necessario per servire l'app dietro HTTPS con URL corretti
        e, tramite X-Forwarded-Prefix, su un sottopercorso (es. /ieri). Attivalo
        solo quando c'è davvero un proxy davanti.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services.ieri-oggi = {
      description = "Ieri & Oggi — galleria profili";
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" ];

      environment = {
        BIND = cfg.bind;
        WEB_CONCURRENCY = toString cfg.workers;
        DATABASE_URL = "sqlite:///${stateDir}/app.db";
        MAX_UPLOAD_MB = toString cfg.maxUploadMb;
        COOKIE_SECURE = if cfg.cookieSecure then "1" else "0";
        TRUST_PROXY = if cfg.trustProxy then "1" else "0";
        # %d = directory delle credenziali (LoadCredential).
        PASSPHRASE_FILE = "%d/passphrase";
        SECRET_KEY_FILE =
          if cfg.secretKeyFile != null then "%d/secret_key"
          else "${stateDir}/secret_key";
      };

      serviceConfig = {
        ExecStart = "${lib.getExe cfg.package}";
        Restart = "on-failure";

        LoadCredential =
          [ "passphrase:${cfg.passphraseFile}" ]
          ++ lib.optional (cfg.secretKeyFile != null) "secret_key:${cfg.secretKeyFile}";

        ExecStartPre = lib.optional (cfg.secretKeyFile == null) generaSegreto;

        # --- Hardening systemd ---
        DynamicUser = true;
        StateDirectory = "ieri-oggi";
        StateDirectoryMode = "0700";
        ProtectSystem = "strict";
        ProtectHome = true;
        PrivateTmp = true;
        PrivateDevices = true;
        ProtectKernelTunables = true;
        ProtectKernelModules = true;
        ProtectKernelLogs = true;
        ProtectControlGroups = true;
        ProtectClock = true;
        ProtectHostname = true;
        ProtectProc = "invisible";
        ProcSubset = "pid";
        RestrictAddressFamilies = [ "AF_INET" "AF_INET6" "AF_UNIX" ];
        RestrictNamespaces = true;
        RestrictRealtime = true;
        RestrictSUIDSGID = true;
        LockPersonality = true;
        MemoryDenyWriteExecute = true;
        NoNewPrivileges = true;
        SystemCallArchitectures = "native";
        SystemCallFilter = [ "@system-service" ];
        SystemCallErrorNumber = "EPERM";
        CapabilityBoundingSet = "";
        UMask = "0077";
      };
    };
  };
}
